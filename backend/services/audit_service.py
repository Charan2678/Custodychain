from sqlalchemy.orm import Session
import models


def log_audit_event(
    db: Session,
    user_name: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: str | None = None,
) -> models.AuditEvent:
    """
    Appends an immutable audit event recording forensic actions,
    verifications, artifact access, and report generation.
    """
    event = models.AuditEvent(
        user_name=user_name,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
