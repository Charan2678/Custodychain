import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.models.case import Case, CaseMember
from app.models.case_assignment import CaseAssignment
from app.models.evidence import Evidence
from app.models.user import User
from app.core.security import get_current_user, require_role, assert_case_access
from app.schemas.evidence import CaseCreateRequest, CaseEvidenceCreateRequest, CaseAssignmentRequest
from app.api.v1.dashboard import get_cases_for_user
from app.services.assignment_service import assign_stage, active_assignment, complete_stage, handoff_after_intake

router = APIRouter(prefix="/cases", tags=["Investigation Cases"])


@router.get("")
def list_cases(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cases = get_cases_for_user(db, current_user)
    results = []
    for c in cases:
        ev_count = db.query(Evidence).filter(Evidence.case_id == c.id).count()
        results.append({
            "id": str(c.id),
            "case_number": c.case_number,
            "title": c.title,
            "description": c.description,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "evidence_count": ev_count,
        })
    return results


@router.post("")
def create_case(
    payload: CaseCreateRequest,
    current_user: User = Depends(require_role(["EVIDENCE_OFFICER", "SYSTEM_ADMIN"])),
    db: Session = Depends(get_db),
):
    existing = db.query(Case).filter(Case.case_number == payload.case_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Case number already exists")

    new_case = Case(
        case_number=payload.case_number,
        title=payload.title,
        description=payload.description,
        created_by=current_user.id,
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    # Membership controls visibility; assignment controls who may act next.
    member_ids = {str(current_user.id)}
    db.add(CaseMember(case_id=new_case.id, user_id=current_user.id, access_level="OWNER"))
    # Seed the standard demo investigation team as explicit case members.
    # The membership is still enforced by every downstream endpoint.
    analysts = db.query(User).filter(User.role == "FORENSIC_ANALYST", User.is_active.is_(True)).all()
    auditors = db.query(User).filter(User.role == "AUDITOR", User.is_active.is_(True)).all()
    for member_user in analysts:
        if str(member_user.id) not in member_ids:
            db.add(CaseMember(case_id=new_case.id, user_id=member_user.id, access_level="EDITOR"))
            member_ids.add(str(member_user.id))
    for member_user in auditors:
        if str(member_user.id) not in member_ids:
            db.add(CaseMember(case_id=new_case.id, user_id=member_user.id, access_level="AUDITOR"))
            member_ids.add(str(member_user.id))

    if current_user.role == "SYSTEM_ADMIN":
        if payload.evidence_officer_id:
            try:
                officer_id = uuid.UUID(payload.evidence_officer_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid Evidence Officer UUID")
            officer = db.query(User).filter(User.id == officer_id, User.is_active.is_(True)).first()
        else:
            officer = db.query(User).filter(User.role == "EVIDENCE_OFFICER", User.is_active.is_(True)).order_by(User.created_at.asc()).first()
        if not officer or officer.role != "EVIDENCE_OFFICER":
            raise HTTPException(status_code=409, detail="An active Evidence Officer must be assigned before opening the case")
        assign_stage(db, new_case.id, officer, current_user, "EVIDENCE_OFFICER")
    else:
        assign_stage(db, new_case.id, current_user, current_user, "EVIDENCE_OFFICER")
    from app.services.audit_service import record_audit_event
    record_audit_event(db, user=current_user, action="CASE_CREATED", resource_type="CASE", resource_id=str(new_case.id), case_id=new_case.id, details={"case_number": new_case.case_number, "title": new_case.title})
    db.commit()

    return {
        "id": str(new_case.id),
        "case_number": new_case.case_number,
        "title": new_case.title,
        "description": new_case.description,
        "status": new_case.status,
        "created_at": new_case.created_at.isoformat() if new_case.created_at else None,
    }


@router.get("/{case_id}/assignments")
def list_case_assignments(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Case UUID")
    assert_case_access(db, current_user, case_uuid)
    assignments = db.query(CaseAssignment).filter(CaseAssignment.case_id == case_uuid).order_by(CaseAssignment.assigned_at.asc()).all()
    users = {u.id: u for u in db.query(User).filter(User.id.in_([a.user_id for a in assignments] or [uuid.uuid4()])).all()}
    return [
        {
            "id": str(a.id),
            "stage": a.stage,
            "status": a.status,
            "user_id": str(a.user_id),
            "user_name": users[a.user_id].display_name if a.user_id in users else None,
            "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        }
        for a in assignments
    ]


@router.post("/{case_id}/assign")
def assign_case_stage(
    case_id: str,
    payload: CaseAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        case_uuid = uuid.UUID(case_id)
        assignee_uuid = uuid.UUID(payload.assignee_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case or assignee UUID")
    assert_case_access(db, current_user, case_uuid)
    assignee = db.query(User).filter(User.id == assignee_uuid, User.is_active.is_(True)).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")

    allowed_handoffs = {
        "SYSTEM_ADMIN": ("EVIDENCE_OFFICER", None),
        "EVIDENCE_OFFICER": ("FORENSIC_ANALYST", "EVIDENCE_OFFICER"),
        "FORENSIC_ANALYST": ("AUDITOR", "FORENSIC_ANALYST"),
    }
    expected_stage, required_current_stage = allowed_handoffs.get(current_user.role, (None, None))
    if payload.stage != expected_stage:
        raise HTTPException(status_code=403, detail=f"{current_user.role} may only assign the next workflow stage: {expected_stage}")
    if required_current_stage:
        require_assignment = active_assignment(db, case_uuid, required_current_stage)
        if not require_assignment or require_assignment.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the current stage owner may hand off this case")
        complete_stage(db, case_uuid, required_current_stage)

    assignment = assign_stage(db, case_uuid, assignee, current_user, payload.stage)
    from app.services.audit_service import record_audit_event
    record_audit_event(db, user=current_user, action="CASE_ASSIGNED", resource_type="CASE", resource_id=case_id, case_id=case_uuid, details={"stage": payload.stage, "assignee_id": payload.assignee_id})
    db.commit()
    return {"id": str(assignment.id), "stage": assignment.stage, "status": assignment.status, "assignee_id": str(assignment.user_id)}


@router.get("/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Case UUID")

    c = db.query(Case).filter(Case.id == case_uuid).first()
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")

    assert_case_access(db, current_user, c.id)

    ev_list = db.query(Evidence).filter(Evidence.case_id == c.id).order_by(Evidence.created_at.desc()).all()

    return {
        "id": str(c.id),
        "case_number": c.case_number,
        "title": c.title,
        "description": c.description,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "evidence": [
            {
                "id": str(e.id),
                "evidence_number": e.evidence_number,
                "name": e.name,
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in ev_list
        ],
    }


@router.post("/{case_id}/evidence")
def create_case_evidence(
    case_id: str,
    payload: CaseEvidenceCreateRequest,
    current_user: User = Depends(require_role(["EVIDENCE_OFFICER"])),
    db: Session = Depends(get_db),
):
    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Case UUID")
    assert_case_access(db, current_user, case_uuid)

    from app.services.custody_service import intake_evidence

    ev = intake_evidence(
        db=db,
        case_id=case_uuid,
        name=payload.name,
        raw_data=payload.content.encode("utf-8"),
        user=current_user,
        evidence_number=payload.evidence_number,
        description=payload.description,
    )
    handoff_after_intake(db, case_uuid, current_user)
    db.commit()
    return {
        "id": str(ev.id),
        "case_id": str(ev.case_id),
        "evidence_number": ev.evidence_number,
        "name": ev.name,
        "status": ev.status,
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
    }


@router.get("/{case_id}/evidence")
def list_case_evidence(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Case UUID")
    assert_case_access(db, current_user, case_uuid)

    from app.models.review import EvidenceReview
    from app.models.verification_run import VerificationRun
    from app.models.artifact import Artifact

    ev_list = db.query(Evidence).filter(Evidence.case_id == case_uuid).order_by(Evidence.created_at.desc()).all()
    results = []
    for e in ev_list:
        latest_rev = (
            db.query(EvidenceReview)
            .filter(EvidenceReview.evidence_id == e.id)
            .order_by(EvidenceReview.created_at.desc())
            .first()
        )
        latest_run = (
            db.query(VerificationRun)
            .filter(VerificationRun.evidence_id == e.id)
            .order_by(VerificationRun.started_at.desc())
            .first()
        )
        latest_art = (
            db.query(Artifact)
            .filter(Artifact.evidence_id == e.id)
            .order_by(Artifact.created_at.desc())
            .first()
        )
        results.append({
            "id": str(e.id),
            "case_id": str(e.case_id),
            "evidence_number": e.evidence_number,
            "name": e.name,
            "description": e.description,
            "status": e.status,
            "latest_verdict": latest_run.verdict if latest_run else "PENDING",
            "review_decision": latest_rev.decision if latest_rev else "PENDING",
            "review_step": latest_rev.custody_step if latest_rev else "Initial Intake",
            "mime_type": latest_art.mime_type if latest_art else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })
    return results
