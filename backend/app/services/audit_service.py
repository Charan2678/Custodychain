import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
from sqlalchemy.orm import Session
from app.models.audit import AuditEvent
from app.models.user import User

GENESIS_AUDIT_BLOCK = "GENESIS_AUDIT_BLOCK"


def record_audit_event(
    db: Session,
    *,
    user: Optional[User],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    case_id: Optional[uuid.UUID] = None,
    evidence_id: Optional[uuid.UUID] = None,
    details: Optional[dict | str] = None,
) -> AuditEvent:
    """Create a hash-linked audit event. Callers commit the transaction."""
    previous = (
        db.query(AuditEvent)
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        .first()
    )
    previous_hash = previous.event_hash if previous and previous.event_hash else GENESIS_AUDIT_BLOCK
    occurred_at = datetime.now(timezone.utc)
    if previous and previous.occurred_at:
        previous_time = previous.occurred_at
        if previous_time.tzinfo is None:
            previous_time = previous_time.replace(tzinfo=timezone.utc)
        if occurred_at <= previous_time:
            occurred_at = previous_time + timedelta(microseconds=1)
    event = AuditEvent(
        id=uuid.uuid4(),
        actor_id=None,
        user_id=user.id if user else None,
        case_id=case_id,
        evidence_id=evidence_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details, sort_keys=True) if isinstance(details, dict) else details,
        previous_event_hash=previous_hash,
        occurred_at=occurred_at,
    )
    db.add(event)
    db.flush()
    canonical = f"{event.id}|{event.user_id}|{event.action}|{event.resource_type}|{event.resource_id}|{event.details}|{previous_hash}"
    event.event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return event
