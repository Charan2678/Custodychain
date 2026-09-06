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
    """
    Executes independent multi-vector verification. Restricted to Forensic Analyst, Auditor, and Admin.
    Evidence Officers are prohibited from self-verifying intake under court forensic standards.
    """
    evidence = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    result = verify_evidence_integrity(db, evidence_id, auditor_name=current_user.name)
    return result


@router.get("/{evidence_id}")
def get_latest_verification(
    evidence_id: int,
    current_user: models.User = Depends(require_role(["SYSTEM_ADMIN", "EVIDENCE_OFFICER", "FORENSIC_ANALYST", "AUDITOR"])),
    db: Session = Depends(get_db),
):
    """
    Retrieves the authoritative multi-vector custody verification status for an exhibit.
    All authenticated roles in the forensic hierarchy may view the custody verification state.
    """
    evidence = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Authoritative verification inspection
    return verify_evidence_integrity(db, evidence_id, auditor_name=current_user.name)
