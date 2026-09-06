import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.models.evidence import Evidence
from app.models.verification_run import VerificationRun
from app.models.verification_finding import VerificationFinding
from app.models.custody_event import CustodyEvent
from app.models.tool import Tool
from app.models.actor import Actor
from app.models.user import User
from app.core.security import get_current_user, require_role, assert_evidence_access
from app.services.verifier_service import run_independent_verification

router = APIRouter(prefix="/verification", tags=["Forensic Verification Authority"])


@router.post("/{evidence_id}")
def verify_evidence(
    evidence_id: str,
    current_user: User = Depends(require_role(["FORENSIC_ANALYST", "AUDITOR", "SYSTEM_ADMIN"])),
    db: Session = Depends(get_db),
):
    try:
        ev_uuid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Evidence UUID")

    assert_evidence_access(db, current_user, ev_uuid)
    result = run_independent_verification(
        db=db,
        evidence_id=ev_uuid,
        requested_by_user_id=current_user.id,
    )
    return result


@router.get("/{evidence_id}")
def get_latest_verification(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        ev_uuid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Evidence UUID")

    assert_evidence_access(db, current_user, ev_uuid)
    latest = (db.query(VerificationRun)
              .filter(VerificationRun.evidence_id == ev_uuid)
              .order_by(VerificationRun.started_at.desc())
              .first())
    if not latest:
        raise HTTPException(status_code=404, detail="No verification run exists for this evidence")
    if latest.metadata_json:
        return latest.metadata_json
    # Backward compatibility for runs created before snapshot persistence was added.
    return run_independent_verification(
        db=db, evidence_id=ev_uuid, requested_by_user_id=current_user.id
    )


@router.post("/{evidence_id}/explain")
def generate_ai_forensic_explanation(
    evidence_id: str,
    current_user: User = Depends(require_role(["EVIDENCE_OFFICER", "FORENSIC_ANALYST", "AUDITOR", "SYSTEM_ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    AI Forensic Explanation Layer.
    Principle: Cryptography Decides (Deterministic Verifier), AI Explains (Human-Readable Judicial Narrative).
    """
    try:
        ev_uuid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Evidence UUID")

    assert_evidence_access(db, current_user, ev_uuid)

    # 1. Read the latest persisted deterministic verification. Only run a new verification
    # when no completed snapshot exists; requesting an explanation must not mutate custody history.
    latest = (db.query(VerificationRun)
              .filter(VerificationRun.evidence_id == ev_uuid, VerificationRun.status == "COMPLETED")
              .order_by(VerificationRun.completed_at.desc(), VerificationRun.id.desc())
              .first())
    if latest and latest.metadata_json:
        v_data = latest.metadata_json
    else:
        v_data = run_independent_verification(
            db=db,
            evidence_id=ev_uuid,
            requested_by_user_id=current_user.id,
        )

    verdict = v_data["verdict"]
    fb = v_data.get("first_break")
    steps = v_data.get("steps", [])
    ev_name = v_data.get("evidence_name", "Digital Exhibit")

    # 2. AI Explanation Engine synthesizes court-admissible forensic narrative
    facts = {
        "evidence_id": str(ev_uuid),
        "evidence_name": ev_name,
        "verdict": verdict,
        "first_break": fb,
        "steps": steps,
        "completed_at": v_data.get("completed_at"),
    }
    from app.services.ai_explanation_service import explain_verification_with_gemini
    return explain_verification_with_gemini(facts)
