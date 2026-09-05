from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
from security.auth import require_role
from services.verifier_service import verify_evidence_integrity

router = APIRouter(prefix="/verification", tags=["Forensic Verification"])


@router.post("/{evidence_id}")
def run_verification(
    evidence_id: int,
    current_user: models.User = Depends(require_role(["FORENSIC_ANALYST", "AUDITOR", "SYSTEM_ADMIN"])),
    db: Session = Depends(get_db),
):
    evidence = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    result = verify_evidence_integrity(db, evidence_id, auditor_name=current_user.name)
    return result


@router.get("/{evidence_id}")
def get_latest_verification(
    evidence_id: int,
    current_user: models.User = Depends(require_role(["FORENSIC_ANALYST", "AUDITOR", "SYSTEM_ADMIN"])),
    db: Session = Depends(get_db),
):
    verdict = (
        db.query(models.VerificationResult)
        .filter(models.VerificationResult.evidence_id == evidence_id)
        .order_by(models.VerificationResult.id.desc())
        .first()
    )
    if not verdict:
        # Run verification automatically if not yet run
        return verify_evidence_integrity(db, evidence_id, auditor_name=current_user.name)

    return {
        "evidence_id": evidence_id,
        "final_verdict": verdict.final_verdict,
        "broken_step_order": verdict.broken_step_order,
        "broken_handler_id": verdict.broken_handler_id,
        "broken_step_id": verdict.broken_handler_id or verdict.broken_step_order,
        "checked_at": verdict.checked_at.isoformat() if verdict.checked_at else None,
    }
