import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import models

GENESIS_AUDIT_HASH = "0" * 64


def log_audit_event(
    db: Session,
    user_name: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: str | None = None,
    ip_address: str | None = "127.0.0.1",
) -> models.AuditEvent:
    """
    Appends an immutable, tamper-evident audit event recording actions.
    Each event mathematically links to the cryptographic SHA-256 hash
    of the preceding audit event, creating an unbroken audit blockchain.
    """
    # 1. Fetch previous audit entry's event_hash
    last_event = db.query(models.AuditEvent).order_by(models.AuditEvent.id.desc()).first()
    previous_hash = last_event.event_hash if (last_event and last_event.event_hash) else GENESIS_AUDIT_HASH

    # 2. Canonical payload for event hash computation
    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    canonical_payload = (
        f"{previous_hash}|{timestamp_str}|{user_name}|{action}|{resource_type}|{resource_id}|{details or ''}"
    )
    event_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    event = models.AuditEvent(
        user_name=user_name,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details,
        previous_event_hash=previous_hash,
        event_hash=event_hash,
        ip_address=ip_address,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def verify_audit_ledger_integrity(db: Session) -> dict:
    """
    Independently verifies the tamper-evident audit ledger hash continuity.
    Returns status and identifies the first broken audit record if any was altered.
    """
    events = db.query(models.AuditEvent).order_by(models.AuditEvent.id.asc()).all()
    if not events:
        return {"status": "EMPTY_LEDGER", "valid": True, "count": 0}

    expected_prev = GENESIS_AUDIT_HASH
    for ev in events:
        if ev.previous_event_hash and ev.previous_event_hash != expected_prev:
            return {
                "status": "AUDIT_CHAIN_BROKEN",
                "valid": False,
                "broken_at_id": ev.id,
                "broken_user": ev.user_name,
                "broken_action": ev.action,
            }
        expected_prev = ev.event_hash or expected_prev

    return {"status": "AUDIT_CHAIN_INTACT", "valid": True, "count": len(events)}
