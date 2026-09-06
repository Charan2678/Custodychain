from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.case import CaseMember
from app.models.case_assignment import CaseAssignment
from app.models.user import User

STAGE_ROLES = {
    "EVIDENCE_OFFICER": "EVIDENCE_OFFICER",
    "FORENSIC_ANALYST": "FORENSIC_ANALYST",
    "AUDITOR": "AUDITOR",
}


def active_assignment(db: Session, case_id: uuid.UUID, stage: str) -> CaseAssignment | None:
    return (
        db.query(CaseAssignment)
        .filter(
            CaseAssignment.case_id == case_id,
            CaseAssignment.stage == stage,
            CaseAssignment.status == "ACTIVE",
        )
        .first()
    )


def require_current_handler(db: Session, user: User, case_id: uuid.UUID, stage: str) -> CaseAssignment:
    assignment = active_assignment(db, case_id, stage)
    if not assignment or assignment.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only the assigned {stage.replace('_', ' ').title()} may perform this custody step.",
        )
    return assignment


def assign_stage(
    db: Session,
    case_id: uuid.UUID,
    assignee: User,
    assigned_by: User,
    stage: str,
) -> CaseAssignment:
    if stage not in STAGE_ROLES:
        raise HTTPException(status_code=422, detail=f"Unsupported assignment stage: {stage}")
    if assignee.role != STAGE_ROLES[stage]:
        raise HTTPException(
            status_code=422,
            detail=f"Assignment stage {stage} requires role {STAGE_ROLES[stage]}.",
        )

    current = active_assignment(db, case_id, stage)
    if current:
        if current.user_id == assignee.id:
            return current
        current.status = "COMPLETED"
        current.completed_at = datetime.now(timezone.utc)
        db.flush()

    member = (
        db.query(CaseMember)
        .filter(CaseMember.case_id == case_id, CaseMember.user_id == assignee.id)
        .first()
    )
    if not member and assignee.id != assigned_by.id:
        db.add(CaseMember(case_id=case_id, user_id=assignee.id, access_level="AUDITOR" if stage == "AUDITOR" else "EDITOR"))

    assignment = CaseAssignment(
        case_id=case_id,
        user_id=assignee.id,
        assigned_by=assigned_by.id,
        stage=stage,
        status="ACTIVE",
    )
    db.add(assignment)
    db.flush()
    return assignment


def complete_stage(db: Session, case_id: uuid.UUID, stage: str) -> None:
    assignment = active_assignment(db, case_id, stage)
    if assignment:
        assignment.status = "COMPLETED"
        assignment.completed_at = datetime.now(timezone.utc)


def handoff_after_intake(db: Session, case_id: uuid.UUID, officer: User) -> None:
    complete_stage(db, case_id, "EVIDENCE_OFFICER")
    analyst = (
        db.query(User)
        .filter(User.role == "FORENSIC_ANALYST", User.is_active.is_(True))
        .order_by(User.created_at.asc())
        .first()
    )
    if analyst:
        assign_stage(db, case_id, analyst, officer, "FORENSIC_ANALYST")
