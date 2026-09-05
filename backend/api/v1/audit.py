from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
import models

router = APIRouter(prefix="/audit", tags=["Security Audit Trail"])


@router.get("")
def list_audit_events(limit: int = 50, db: Session = Depends(get_db)):
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
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        }
        for e in events
    ]
