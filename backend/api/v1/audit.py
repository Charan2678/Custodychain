from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
import models
from security.auth import require_role
from services.audit_service import verify_audit_ledger_integrity

router = APIRouter(prefix="/audit", tags=["Security Audit Trail"])


@router.get("")
def list_audit_events(
    limit: int = 50,
    current_user: models.User = Depends(require_role(["AUDITOR", "SYSTEM_ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Returns immutable audit records.
    Restricted to AUDITOR and SYSTEM_ADMIN roles.
    Includes cryptographic hash links proving the audit ledger is unbroken.
    """
    events = (
        db.query(models.AuditEvent)
        .order_by(models.AuditEvent.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "user_name": e.user_name,
            "action": e.action,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "details": e.details,
            "previous_event_hash": e.previous_event_hash,
            "event_hash": e.event_hash,
            "ip_address": e.ip_address,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        }
        for e in events
    ]


@router.get("/verify")
def verify_audit_ledger(
    current_user: models.User = Depends(require_role(["AUDITOR", "SYSTEM_ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Independently verifies the cryptographic hash continuity of the audit trail.
    """
    return verify_audit_ledger_integrity(db)
