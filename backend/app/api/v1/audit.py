import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.models.audit import AuditEvent
from app.models.user import User
from app.core.security import require_role
import hashlib


def sha256_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

router = APIRouter(prefix="/audit", tags=["System Audit Trail"])


@router.get("")
def get_audit_trail(
    limit: int = Query(default=50, ge=1, le=500),
    current_user: User = Depends(require_role(["AUDITOR", "SYSTEM_ADMIN"])),
    db: Session = Depends(get_db),
):
    events = (
        db.query(AuditEvent)
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        .limit(limit)
        .all()
    )

    results = []
    for ev in events:
        user = db.query(User).filter(User.id == ev.user_id).first() if ev.user_id else None
        user_name = user.display_name if user else "System Authority"

        details_str = ev.details or ""
        try:
            parsed = json.loads(details_str)
            if isinstance(parsed, dict):
                details_str = ", ".join(f"{k}: {v}" for k, v in parsed.items())
        except Exception:
            pass

        results.append({
            "id": str(ev.id),
            "timestamp": ev.occurred_at.isoformat(),
            "user_name": user_name,
            "action": ev.action,
            "resource_type": ev.resource_type,
            "resource_id": ev.resource_id or "—",
            "details": details_str,
            "event_hash": ev.event_hash,
        })
    return results


@router.get("/verify")
def verify_audit_ledger_continuity(
    current_user: User = Depends(require_role(["AUDITOR", "SYSTEM_ADMIN"])),
    db: Session = Depends(get_db),
):
    events = db.query(AuditEvent).order_by(AuditEvent.occurred_at.asc(), AuditEvent.id.asc()).all()

    if not events:
        return {
            "status": "AUDIT_CHAIN_INTACT",
            "valid": True,
            "count": 0,
            "events_checked": 0,
            "broken_at_id": None,
        }

    prev_hash = "GENESIS_AUDIT_BLOCK"
    broken_id = None
    valid = True

    for ev in events:
        if ev.previous_event_hash and ev.previous_event_hash != prev_hash:
            valid = False
            broken_id = str(ev.id)
            break

        canonical = f"{ev.id}|{ev.user_id}|{ev.action}|{ev.resource_type}|{ev.resource_id}|{ev.details}|{prev_hash}"
        computed = sha256_hash(canonical.encode("utf-8"))

        if not ev.event_hash or ev.event_hash != computed:
            valid = False
            broken_id = str(ev.id)
            break

        prev_hash = ev.event_hash

    return {
        "status": "AUDIT_CHAIN_INTACT" if valid else "AUDIT_CHAIN_BROKEN",
        "valid": valid,
        "count": len(events),
        "events_checked": len(events),
        "broken_at_id": broken_id,
    }
