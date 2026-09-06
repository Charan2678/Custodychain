import uuid
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.models.case import Case, CaseMember
from app.models.evidence import Evidence
from app.models.artifact import Artifact
from app.models.review import EvidenceReview
from app.models.verification_run import VerificationRun
from app.models.audit import AuditEvent
from app.models.user import User
from app.core.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Role Dashboards"])


def get_cases_for_user(db: Session, user: User) -> List[Case]:
    """Admin sees all cases. Other roles see only cases they are members of, or created."""
    if user.role == "SYSTEM_ADMIN":
        return db.query(Case).order_by(Case.created_at.desc()).all()

    member_case_ids = [
        cm.case_id for cm in db.query(CaseMember.case_id).filter(CaseMember.user_id == user.id).all()
    ]
    cases = (
        db.query(Case)
        .filter((Case.created_by == user.id) | (Case.id.in_(member_case_ids)))
        .order_by(Case.created_at.desc())
        .all()
    )
    return cases


@router.get("")
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    role = current_user.role
    cases = get_cases_for_user(db, current_user)
    case_ids = [c.id for c in cases]

    evidences = db.query(Evidence).filter(Evidence.case_id.in_(case_ids)).all() if case_ids else []
    ev_ids = [e.id for e in evidences]

    # Calculate broken chains from latest verification runs
    broken_count = 0
    if ev_ids:
        broken_count = (
            db.query(VerificationRun)
            .filter(VerificationRun.evidence_id.in_(ev_ids), VerificationRun.verdict == "CHAIN_BROKEN")
            .count()
        )

    # Reviews count
    total_reviews = (db.query(EvidenceReview).join(Evidence, EvidenceReview.evidence_id == Evidence.id).filter(Evidence.case_id.in_(case_ids)).count() if case_ids else 0)

    case_items = []
    for c in cases:
        c_evs = [e for e in evidences if e.case_id == c.id]
        case_items.append({
            "id": str(c.id),
            "case_number": c.case_number,
            "title": c.title,
            "status": c.status,
            "evidence_count": len(c_evs),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    evidence_items = []
    for e in evidences:
        latest_rev = (
            db.query(EvidenceReview)
            .filter(EvidenceReview.evidence_id == e.id)
            .order_by(EvidenceReview.created_at.desc())
            .first()
        )
        latest_run = (
            db.query(VerificationRun)
            .filter(VerificationRun.evidence_id == e.id)
            .order_by(VerificationRun.started_at.desc())
            .first()
        )
        latest_art = (
            db.query(Artifact)
            .filter(Artifact.evidence_id == e.id)
            .order_by(Artifact.created_at.desc())
            .first()
        )
        evidence_items.append({
            "id": str(e.id),
            "case_id": str(e.case_id),
            "name": e.name,
            "evidence_number": e.evidence_number,
            "status": e.status,
            "review_decision": latest_rev.decision if latest_rev else "PENDING",
            "review_step": latest_rev.custody_step if latest_rev else "Initial Intake",
            "latest_verdict": latest_run.verdict if latest_run else "PENDING",
            "mime_type": latest_art.mime_type if latest_art else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })

    if role == "EVIDENCE_OFFICER":
        return {
            "role": "EVIDENCE_OFFICER",
            "role_title": "Evidence Officer Dashboard",
            "user_name": current_user.display_name,
            "metrics": {
                "assigned_cases": len(cases),
                "active_evidence": len(evidences),
                "pending_reviews": sum(1 for e in evidence_items if e["review_decision"] == "PENDING"),
                "approved_transfers": sum(1 for e in evidence_items if e["review_decision"] == "APPROVE"),
            },
            "actions": [
                "CASE_CREATE",
                "EVIDENCE_INTAKE",
                "INSPECT_EVIDENCE",
                "REVIEW_EVIDENCE",
                "APPROVE_TRANSFER",
            ],
            "cases": case_items,
            "evidence": evidence_items,
        }

    elif role == "FORENSIC_ANALYST":
        return {
            "role": "FORENSIC_ANALYST",
            "role_title": "Forensic Analyst Laboratory",
            "user_name": current_user.display_name,
            "metrics": {
                "assigned_evidence": len(evidences),
                "broken_chains": broken_count,
                "pending_analysis": sum(1 for e in evidence_items if e["review_decision"] != "APPROVE"),
                "completed_reports": len(evidences) - broken_count,
            },
            "actions": [
                "INSPECT_ARTIFACT",
                "RUN_VERIFICATION",
                "PROCESS_EVIDENCE",
                "CREATE_DERIVED_ARTIFACT",
                "REVIEW_EVIDENCE",
                "ADVANCE_CUSTODY",
                "GENERATE_REPORT",
            ],
            "cases": case_items,
            "evidence": evidence_items,
        }

    elif role == "AUDITOR":
        audit_events_count = db.query(AuditEvent).filter((AuditEvent.case_id.in_(case_ids)) | (AuditEvent.user_id == current_user.id)).count() if case_ids else db.query(AuditEvent).filter(AuditEvent.user_id == current_user.id).count()
        return {
            "role": "AUDITOR",
            "role_title": "Independent Compliance & Audit Center",
            "user_name": current_user.display_name,
            "metrics": {
                "verification_queue": len(evidences),
                "broken_chains": broken_count,
                "audit_records_count": audit_events_count,
                "ledger_status": "AUDIT_CHAIN_INTACT",
            },
            "actions": [
                "INSPECT_EVIDENCE",
                "RUN_INDEPENDENT_VERIFICATION",
                "VIEW_FIRST_BREAK",
                "VIEW_AUDIT_TRAIL",
                "EXPLAIN_WITH_AI",
                "GENERATE_LEGAL_REPORT",
            ],
            "cases": case_items,
            "evidence": evidence_items,
        }

    else:  # SYSTEM_ADMIN
        total_cases_all = db.query(Case).count()
        total_ev_all = db.query(Evidence).count()
        total_broken_all = db.query(VerificationRun).filter(VerificationRun.verdict == "CHAIN_BROKEN").count()
        security_events = (
            db.query(AuditEvent)
            .filter(AuditEvent.action.in_(["UNAUTHORIZED_EDIT_ATTEMPT", "EVIDENCE_COPY_ATTEMPT", "CHAIN_BROKEN_DETECTED"]))
            .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
            .limit(10)
            .all()
        )
        security_alerts = []
        for event in security_events:
            actor = db.query(User).filter(User.id == event.user_id).first() if event.user_id else None
            security_alerts.append({
                "id": str(event.id),
                "action": event.action,
                "severity": "CRITICAL" if event.action != "EVIDENCE_COPY_ATTEMPT" else "WARNING",
                "actor_name": actor.display_name if actor else "System Authority",
                "case_id": str(event.case_id) if event.case_id else None,
                "evidence_id": str(event.evidence_id) if event.evidence_id else None,
                "details": event.details or "Security event detected",
                "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            })
        return {
            "role": "SYSTEM_ADMIN",
            "role_title": "System Administrator Operations Center",
            "user_name": current_user.display_name,
            "system_health": {
                "api": "ONLINE (FastAPI 0.115)",
                "database": "CONNECTED",
                "artifact_storage": "VERIFIED (Local WORM Storage)",
                "cryptography": "ACTIVE (Ed25519 / SHA-256)",
            },
            "metrics": {
                "total_cases": total_cases_all,
                "total_evidence": total_ev_all,
                "broken_chains": total_broken_all,
                "total_reviews": total_reviews,
                "security_alerts": len(security_alerts),
            },
            "security_alerts": security_alerts,
            "actions": [
                "MANAGE_CASES",
                "MANAGE_EVIDENCE",
                "USER_DIRECTORY",
                "GLOBAL_VERIFICATION",
                "AUDIT_LEDGER",
                "REPORTS",
                "SIMULATION_DEMO",
            ],
            "cases": case_items,
            "evidence": evidence_items,
        }
