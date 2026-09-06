import uuid
import base64
import mimetypes
from datetime import datetime, timezone
from typing import Optional, Union, List
from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.infrastructure.storage.storage_service import storage, compute_bytes_hash
from app.models.case import Case
from app.models.evidence import Evidence
from app.models.artifact import Artifact
from app.models.custody_event import CustodyEvent
from app.models.tool import Tool
from app.models.actor import Actor
from app.models.user import User
from app.models.verification_run import VerificationRun
from app.models.review import ReviewNote, EvidenceReview
from app.core.security import get_current_user, require_role, assert_case_access, assert_evidence_access, assert_artifact_access
from app.services.assignment_service import active_assignment, require_current_handler, complete_stage, assign_stage, handoff_after_intake
from app.schemas.evidence import EvidenceIntakeRequest, SimulationRequest
from app.api.v1.dashboard import get_cases_for_user
from app.services.custody_service import (
    intake_evidence,
    advance_custody_step,
    run_full_pipeline_simulation,
)

router = APIRouter(prefix="/evidence", tags=["Evidence & Custody Chain"])


class AdvanceStepRequest(BaseModel):
    simulate_tamper: bool = False


class UnifiedEvidenceCreateRequest(BaseModel):
    name: str
    content: str
    case_id: Optional[Union[str, int]] = None
    step_by_step: bool = True
    simulate_tamper: bool = False
    tamper_step: int = 0


class BulkEvidenceItem(BaseModel):
    name: str
    content: str
    description: Optional[str] = None


class BulkImportRequest(BaseModel):
    case_id: str
    items: List[BulkEvidenceItem]


class EvidenceEditRequest(BaseModel):
    """Editing evidence content creates a new artifact with different hash — triggers CHAIN_BROKEN on next verification."""
    new_content: Optional[str] = None
    new_content_base64: Optional[str] = None
    edit_reason: str = "Field edit by authorized user"


def _pending_action_roles(current_step: int) -> List[str]:
    """Next custodian roles that can action/transfer evidence from the current pipeline step."""
    if current_step <= 0:
        return ["EVIDENCE_OFFICER", "SYSTEM_ADMIN"]
    if current_step == 1:
        return ["FORENSIC_ANALYST", "EVIDENCE_OFFICER", "SYSTEM_ADMIN"]
    if current_step == 2:
        return ["FORENSIC_ANALYST", "SYSTEM_ADMIN"]
    if current_step == 3:
        return ["EVIDENCE_OFFICER", "FORENSIC_ANALYST", "SYSTEM_ADMIN"]
    return []


# ─── All roles can list evidence ────────────────────────────────────────────

@router.get("")
def list_all_evidence(
    case_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    accessible_cases = get_cases_for_user(db, current_user)
    accessible_ids = [c.id for c in accessible_cases]
    query = db.query(Evidence).filter(Evidence.case_id.in_(accessible_ids)) if accessible_ids else db.query(Evidence).filter(False)
    if case_id:
        try:
            case_uuid = uuid.UUID(case_id)
            if case_uuid not in accessible_ids and current_user.role != "SYSTEM_ADMIN":
                raise HTTPException(status_code=403, detail="Access denied to this case")
            query = query.filter(Evidence.case_id == case_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Case UUID")

    items = query.order_by(Evidence.created_at.desc()).all()
    results = []
    for item in items:
        event_count = db.query(CustodyEvent).filter(CustodyEvent.evidence_id == item.id).count()
        latest_run = (
            db.query(VerificationRun)
            .filter(VerificationRun.evidence_id == item.id)
            .order_by(VerificationRun.started_at.desc())
            .first()
        )
        latest_art = (
            db.query(Artifact)
            .filter(Artifact.evidence_id == item.id)
            .order_by(Artifact.created_at.desc())
            .first()
        )
        verdict = latest_run.verdict if latest_run else item.status
        pending_roles = _pending_action_roles(event_count)
        results.append({
            "id": str(item.id),
            "evidence_id": str(item.id),
            "exhibit_id": item.evidence_number,
            "evidence_number": item.evidence_number,
            "name": item.name,
            "description": item.description,
            "case_id": str(item.case_id),
            "status": verdict,
            "current_step": event_count,
            "latest_verdict": latest_run.verdict if latest_run else "PENDING",
            "pending_action_role": pending_roles[0] if pending_roles else "ARCHIVED",
            "pending_action_roles": pending_roles,
            "mime_type": latest_art.mime_type if latest_art else None,
            "original_filename": latest_art.original_filename if latest_art else None,
            "artifact_type": latest_art.artifact_type if latest_art else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })
    return results


# ─── All roles can create evidence (with audit trail) ───────────────────────

@router.post("")
def unified_create_evidence(
    payload: UnifiedEvidenceCreateRequest,
    current_user: User = Depends(require_role(["EVIDENCE_OFFICER"])),
    db: Session = Depends(get_db),
):
    from app.models.case import Case
    from app.services.verifier_service import run_independent_verification

    # Resolve target case explicitly; never silently select another case.
    if not payload.case_id:
        raise HTTPException(status_code=400, detail="case_id is required")
    try:
        case_uuid = uuid.UUID(str(payload.case_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Case UUID")
    target_case = assert_case_access(db, current_user, case_uuid)
    require_current_handler(db, current_user, target_case.id, "EVIDENCE_OFFICER")

    if not payload.step_by_step or payload.simulate_tamper:
        result = run_full_pipeline_simulation(
            db=db,
            case_id=target_case.id,
            name=payload.name,
            content=payload.content,
            user=current_user,
            tamper_step=payload.tamper_step if payload.simulate_tamper else 0,
        )
        return result
    else:
        ev = intake_evidence(
            db=db,
            case_id=target_case.id,
            name=payload.name,
            raw_data=payload.content.encode("utf-8"),
            user=current_user,
            description="Official forensic seizure",
        )
        handoff_after_intake(db, target_case.id, current_user)
        db.commit()
        return run_independent_verification(db, ev.id, requested_by_user_id=current_user.id)


# ─── File Upload (images, videos, text, binaries) ────────────────────────────

@router.post("/upload")
async def upload_evidence_file(
    case_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(["EVIDENCE_OFFICER"])),
    db: Session = Depends(get_db),
):
    """Upload any file type (image, video, PDF, text) as evidence. Stores raw bytes, computes SHA-256."""
    from app.services.verifier_service import run_independent_verification

    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Case UUID")

    case = assert_case_access(db, current_user, case_uuid)
    require_current_handler(db, current_user, case.id, "EVIDENCE_OFFICER")

    raw_data = await file.read()
    if len(raw_data) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"

    ev = intake_evidence(
        db=db,
        case_id=case_uuid,
        name=name or file.filename or "Uploaded Evidence",
        raw_data=raw_data,
        user=current_user,
        description=description or f"Uploaded file: {file.filename}",
        mime_type=mime,
        original_filename=file.filename,
    )
    handoff_after_intake(db, case_uuid, current_user)
    db.commit()
    return run_independent_verification(db, ev.id, requested_by_user_id=current_user.id)


# ─── Bulk Import (multiple text evidence items at once) ─────────────────────

@router.post("/bulk-import")
def bulk_import_evidence(
    payload: BulkImportRequest,
    current_user: User = Depends(require_role(["EVIDENCE_OFFICER"])),
    db: Session = Depends(get_db),
):
    """Import multiple evidence items in one request."""
    from app.services.verifier_service import run_independent_verification

    try:
        case_uuid = uuid.UUID(payload.case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Case UUID")

    assert_case_access(db, current_user, case_uuid)
    require_current_handler(db, current_user, case_uuid, "EVIDENCE_OFFICER")

    results = []
    errors = []
    for idx, item in enumerate(payload.items):
        try:
            ev = intake_evidence(
                db=db,
                case_id=case_uuid,
                name=item.name,
                raw_data=item.content.encode("utf-8"),
                user=current_user,
                description=item.description or "Bulk imported evidence",
            )
            handoff_after_intake(db, case_uuid, current_user)
            vr = run_independent_verification(db, ev.id, requested_by_user_id=current_user.id)
            results.append({
                "index": idx,
                "name": item.name,
                "evidence_id": str(ev.id),
                "verdict": vr.get("final_verdict", "CHAIN_INTACT"),
                "success": True,
            })
        except Exception as e:
            errors.append({"index": idx, "name": item.name, "error": str(e)})

    return {
        "imported": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    }


# ─── Evidence Edit (immutable bytes; attempts are auditable) ────────────────

@router.put("/{evidence_id}/edit")
@router.post("/{evidence_id}/edit")
def edit_evidence_content(
    evidence_id: str,
    payload: EvidenceEditRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject direct mutation, but preserve the attempted edit in the audit ledger."""
    try:
        ev_uuid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Evidence UUID")
    evidence = assert_evidence_access(db, current_user, ev_uuid)
    from app.services.audit_service import record_audit_event
    record_audit_event(
        db,
        user=current_user,
        action="UNAUTHORIZED_EDIT_ATTEMPT",
        resource_type="EVIDENCE",
        resource_id=str(evidence.id),
        case_id=evidence.case_id,
        evidence_id=evidence.id,
        details={"edit_reason": payload.edit_reason, "content_supplied": bool(payload.new_content or payload.new_content_base64)},
    )
    db.commit()
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Evidence bytes are immutable. Create a new derived artifact through the custody processing workflow instead of editing the stored artifact.",
    )


@router.post("/{evidence_id}/copy-attempt")
def record_evidence_copy_attempt(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record copying from the protected evidence preview as a monitored access event."""
    try:
        ev_uuid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Evidence UUID")
    evidence = assert_evidence_access(db, current_user, ev_uuid)
    from app.services.audit_service import record_audit_event
    record_audit_event(
        db,
        user=current_user,
        action="EVIDENCE_COPY_ATTEMPT",
        resource_type="EVIDENCE",
        resource_id=str(evidence.id),
        case_id=evidence.case_id,
        evidence_id=evidence.id,
        details={
            "message": f"Evidence content copied from protected preview by {current_user.role}",
            "actor_role": current_user.role,
            "actor_name": current_user.display_name,
            "evidence_name": evidence.name,
        },
    )
    db.commit()
    return {
        "status": "COPY_ATTEMPT_RECORDED",
        "evidence_id": str(evidence.id),
        "actor_role": current_user.role,
        "actor_name": current_user.display_name,
    }


@router.post("/intake")
def intake_new_evidence(
    payload: EvidenceIntakeRequest,
    current_user: User = Depends(require_role(["EVIDENCE_OFFICER"])),
    db: Session = Depends(get_db),
):
    try:
        case_uuid = uuid.UUID(payload.case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Case UUID")

    assert_case_access(db, current_user, case_uuid)
    require_current_handler(db, current_user, case_uuid, "EVIDENCE_OFFICER")

    ev = intake_evidence(
        db=db,
        case_id=case_uuid,
        name=payload.name,
        raw_data=payload.content.encode("utf-8"),
        user=current_user,
        evidence_number=payload.evidence_number,
        description=payload.description,
    )
    handoff_after_intake(db, case_uuid, current_user)
    db.commit()
    return {
        "id": str(ev.id),
        "case_id": str(ev.case_id),
        "evidence_number": ev.evidence_number,
        "name": ev.name,
        "status": ev.status,
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
    }


@router.get("/{evidence_id}")
def get_evidence_details(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        ev_uuid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Evidence UUID")

    ev = assert_evidence_access(db, current_user, ev_uuid)

    events = (
        db.query(CustodyEvent)
        .filter(CustodyEvent.evidence_id == ev.id)
        .order_by(CustodyEvent.sequence_number.asc())
        .all()
    )
    artifacts = (
        db.query(Artifact)
        .filter(Artifact.evidence_id == ev.id)
        .order_by(Artifact.created_at.asc())
        .all()
    )

    event_list = []
    for event in events:
        tool = db.query(Tool).filter(Tool.id == event.tool_id).first() if event.tool_id else None
        actor = db.query(Actor).filter(Actor.id == event.actor_id).first()
        out_art = db.query(Artifact).filter(Artifact.id == event.output_artifact_id).first()
        event_list.append({
            "sequence_number": event.sequence_number,
            "operation": event.operation,
            "tool_name": tool.name if tool else None,
            "actor_name": actor.name if actor else None,
            "sha256": out_art.sha256 if out_art else None,
            "event_hash": event.event_hash,
            "previous_event_hash": event.previous_event_hash,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            "has_actor_signature": bool(event.actor_signature),
            "has_tool_signature": bool(event.tool_signature),
        })

    return {
        "id": str(ev.id),
        "case_id": str(ev.case_id),
        "evidence_number": ev.evidence_number,
        "name": ev.name,
        "status": ev.status,
        "artifacts": [
            {
                "id": str(a.id),
                "artifact_type": a.artifact_type,
                "sha256": a.sha256,
                "size_bytes": a.size_bytes,
                "mime_type": a.mime_type,
                "original_filename": a.original_filename,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in artifacts
        ],
        "events": event_list,
    }


@router.get("/{evidence_id}/artifacts")
def list_evidence_artifacts(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        ev_uuid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Evidence UUID")

    ev = assert_evidence_access(db, current_user, ev_uuid)
    artifacts = db.query(Artifact).filter(Artifact.evidence_id == ev_uuid).order_by(Artifact.created_at.asc()).all()
    return [
        {
            "id": str(a.id),
            "evidence_id": str(a.evidence_id),
            "artifact_type": a.artifact_type,
            "storage_provider": a.storage_provider,
            "storage_key": a.storage_key,
            "sha256": a.sha256,
            "size_bytes": a.size_bytes,
            "mime_type": a.mime_type,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in artifacts
    ]


artifacts_router = APIRouter(prefix="/artifacts", tags=["Artifact Storage"])


@artifacts_router.get("/{artifact_id}")
def get_artifact_by_id(
    artifact_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        art_uuid = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Artifact UUID")

    art = assert_artifact_access(db, current_user, art_uuid)

    return {
        "id": str(art.id),
        "evidence_id": str(art.evidence_id),
        "artifact_type": art.artifact_type,
        "storage_provider": art.storage_provider,
        "storage_key": art.storage_key,
        "sha256": art.sha256,
        "size_bytes": art.size_bytes,
        "mime_type": art.mime_type,
        "status": art.status,
        "created_at": art.created_at.isoformat() if art.created_at else None,
    }


@artifacts_router.get("/{artifact_id}/preview")
def preview_artifact(
    artifact_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        art_uuid = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Artifact UUID")

    art = assert_artifact_access(db, current_user, art_uuid)
    if not storage.exists(art.storage_key):
        raise HTTPException(status_code=404, detail="Artifact file not found in storage")

    raw = storage.read(art.storage_key)
    is_text = True
    try:
        text_preview = raw[:20480].decode("utf-8")
    except UnicodeDecodeError:
        is_text = False
        text_preview = f"[Binary Stream: {len(raw)} bytes | MIME: {art.mime_type}]"

    return {
        "artifact_id": str(art.id),
        "mime_type": art.mime_type,
        "size_bytes": art.size_bytes,
        "sha256": art.sha256,
        "is_text": is_text,
        "preview": text_preview,
    }


@artifacts_router.get("/{artifact_id}/download")
def download_artifact(
    artifact_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        art_uuid = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Artifact UUID")

    art = assert_artifact_access(db, current_user, art_uuid)
    if not storage.exists(art.storage_key):
        raise HTTPException(status_code=404, detail="Artifact file not found in storage")

    raw = storage.read(art.storage_key)
    return Response(
        content=raw,
        media_type=art.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="artifact_{str(art.id)[:8]}.bin"',
            "X-SHA256-Checksum": art.sha256,
        },
    )


@router.get("/{evidence_id}/review")
def get_evidence_review_record(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        ev_uuid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Evidence UUID")

    ev = db.query(Evidence).filter(Evidence.id == ev_uuid).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    assert_case_access(db, current_user, ev.case_id)

    case = db.query(Case).filter(Case.id == ev.case_id).first()

    # Get events ordered by sequence
    events = (
        db.query(CustodyEvent)
        .filter(CustodyEvent.evidence_id == ev.id)
        .order_by(CustodyEvent.sequence_number.asc())
        .all()
    )
    latest_event = events[-1] if events else None
    current_step = latest_event.sequence_number if latest_event else 1

    latest_tool = db.query(Tool).filter(Tool.id == latest_event.tool_id).first() if (latest_event and latest_event.tool_id) else None

    # 4-stage pipeline definitions
    stage_map = {
        1: {
            "current_handler": "Evidence Collector",
            "next_step": 2,
            "next_handler": "Forensic Normalizer",
            "required_role": "Forensic Analyst",
            "allowed_roles": ["FORENSIC_ANALYST", "SYSTEM_ADMIN"],
        },
        2: {
            "current_handler": "Forensic Normalizer",
            "next_step": 3,
            "next_handler": "Evidence Exporter",
            "required_role": "Forensic Analyst",
            "allowed_roles": ["FORENSIC_ANALYST", "SYSTEM_ADMIN"],
        },
        3: {
            "current_handler": "Evidence Exporter",
            "next_step": 4,
            "next_handler": "Secure Vault Archiver",
            "required_role": "Forensic Analyst or Evidence Officer",
            "allowed_roles": ["FORENSIC_ANALYST", "EVIDENCE_OFFICER", "SYSTEM_ADMIN"],
        },
        4: {
            "current_handler": "Secure Vault Archiver",
            "next_step": None,
            "next_handler": "Vault Sealed (Complete)",
            "required_role": "Archived",
            "allowed_roles": [],
        },
    }
    stage_info = stage_map.get(current_step, stage_map[1])
    can_transfer = current_user.role in stage_info["allowed_roles"]

    # Get latest output artifact
    out_art = db.query(Artifact).filter(Artifact.id == latest_event.output_artifact_id).first() if latest_event else None
    if not out_art:
        out_art = db.query(Artifact).filter(Artifact.evidence_id == ev.id).order_by(Artifact.created_at.desc()).first()

    # Genesis artifact
    gen_art = db.query(Artifact).filter(Artifact.evidence_id == ev.id).order_by(Artifact.created_at.asc()).first()

    # Read physical storage bytes directly to verify ground truth
    raw_bytes = b""
    recomputed_sha256 = ""
    preview_content = ""
    if out_art and storage.exists(out_art.storage_key):
        raw_bytes = storage.read(out_art.storage_key)
        recomputed_sha256 = compute_bytes_hash(raw_bytes)
        try:
            preview_content = raw_bytes[:20480].decode("utf-8")
        except UnicodeDecodeError:
            preview_content = f"[Binary Object: {len(raw_bytes)} bytes | SHA-256: {recomputed_sha256}]"

    hash_matches = (recomputed_sha256 == out_art.sha256) if out_art else True

    # Review history and process marks
    reviews = db.query(EvidenceReview).filter(EvidenceReview.evidence_id == ev.id).order_by(EvidenceReview.created_at.desc()).all()
    latest_rev = reviews[0] if reviews else None
    has_approval = bool(latest_rev and latest_rev.decision == "APPROVE")

    can_transfer = (current_user.role in stage_info["allowed_roles"]) and has_approval

    process_marks = []
    for r in reviews:
        reviewer = db.query(User).filter(User.id == r.reviewer_id).first()
        process_marks.append({
            "id": str(r.id),
            "step": r.custody_step,
            "decision": r.decision,
            "notes": r.notes,
            "reviewer_name": reviewer.display_name if reviewer else "Forensic Authority",
            "reviewer_role": reviewer.role if reviewer else "AUTHORITY",
            "created_at": r.created_at.isoformat(),
        })

    return {
        "evidence_id": str(ev.id),
        "name": ev.name,
        "exhibit_id": ev.evidence_number,
        "case_title": case.title if case else "Active Case",
        "case_number": case.case_number if case else "CASE-2026",
        "current_step": current_step,
        "current_handler": latest_tool.name if latest_tool else stage_info["current_handler"],
        "next_step": stage_info["next_step"],
        "next_handler": stage_info["next_handler"],
        "required_role": stage_info["required_role"],
        "can_transfer": can_transfer,
        "transfer_status": "APPROVED_FOR_TRANSFER" if has_approval else "REQUIRES_REVIEW_APPROVAL",
        "original_hash": gen_art.sha256 if gen_art else "",
        "mime_type": out_art.mime_type if out_art else None,
        "original_filename": out_art.original_filename if out_art else None,
        "artifact": {
            "id": str(out_art.id) if out_art else None,
            "artifact_type": out_art.artifact_type if out_art else None,
            "sha256": out_art.sha256 if out_art else "",
            "size_bytes": out_art.size_bytes if out_art else len(raw_bytes),
            "recomputed_sha256": recomputed_sha256,
            "hash_matches": hash_matches,
            "mime_type": out_art.mime_type if out_art else None,
            "original_filename": out_art.original_filename if out_art else None,
            "storage_key": out_art.storage_key if out_art else None,
            "content": preview_content,
        },
        "event": {
            "signature": latest_event.tool_signature or latest_event.actor_signature if latest_event else None,
            "handler_name": latest_tool.name if latest_tool else stage_info["current_handler"],
            "timestamp": latest_event.occurred_at.isoformat() if latest_event else None,
            "event_hash": latest_event.event_hash if latest_event else None,
            "previous_event_hash": latest_event.previous_event_hash if latest_event else None,
        },
        "review_notes": process_marks,
        "process_marks": process_marks,
    }


class ReviewSubmissionPayload(BaseModel):
    decision: str = "APPROVE"  # APPROVE, REJECT, REQUEST_CLARIFICATION
    notes: Optional[str] = None
    note: Optional[str] = None
    finding: Optional[str] = None
    advance_handover: bool = False
    simulate_tamper: bool = False


@router.post("/{evidence_id}/review")
@router.post("/{evidence_id}/review-note")
def submit_evidence_review(
    evidence_id: str,
    payload: ReviewSubmissionPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        ev_uuid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Evidence UUID")

    ev = assert_evidence_access(db, current_user, ev_uuid)

    if current_user.role == "AUDITOR":
        raise HTTPException(status_code=403, detail="Auditors are read-only and cannot approve custody")

    events = db.query(CustodyEvent).filter(CustodyEvent.evidence_id == ev.id).all()
    step_str = f"Step {len(events)}"

    decision = payload.decision.upper() if payload.decision else ("APPROVE" if payload.finding == "VERIFIED_INTACT" else "REJECT")
    if decision not in {"APPROVE", "REJECT", "REQUEST_CLARIFICATION"}:
        raise HTTPException(status_code=422, detail="decision must be APPROVE, REJECT, or REQUEST_CLARIFICATION")
    notes_text = payload.notes or payload.note or "Review completed and logged."

    review_rec = EvidenceReview(
        evidence_id=ev.id,
        reviewer_id=current_user.id,
        custody_step=step_str,
        decision=decision,
        notes=notes_text,
        created_at=datetime.now(timezone.utc),
    )
    db.add(review_rec)

    # Log review through the same hash-linked audit service as every other security event.
    action_type = "REVIEW_APPROVED" if decision == "APPROVE" else ("REVIEW_REJECTED" if decision == "REJECT" else "REVIEW_CLARIFICATION_REQUESTED")
    from app.services.audit_service import record_audit_event
    record_audit_event(
        db,
        user=current_user,
        action=action_type,
        resource_type="EVIDENCE",
        resource_id=str(ev.id),
        case_id=ev.case_id,
        evidence_id=ev.id,
        details={
            "process_mark": f"{current_user.role} ({current_user.display_name}) decided: {decision}",
            "decision": decision,
            "step": step_str,
            "notes": notes_text[:200],
        },
    )
    db.commit()

    if payload.advance_handover:
        if decision != "APPROVE":
            raise HTTPException(
                status_code=409,
                detail="Cannot advance custody handover: review decision is not APPROVE"
            )
        advance_custody_step(
            db=db,
            evidence_id=ev.id,
            user=current_user,
            simulate_tamper=payload.simulate_tamper,
        )
        from app.services.verifier_service import run_independent_verification
        return run_independent_verification(db, ev.id, requested_by_user_id=current_user.id)

    return {
        "status": "NOTE_RECORDED",
        "review_id": str(review_rec.id),
        "evidence_id": str(ev.id),
        "decision": review_rec.decision,
        "step": step_str,
    }


@router.post("/{evidence_id}/transfer")
@router.post("/{evidence_id}/advance")
def advance_step(
    evidence_id: str,
    payload: AdvanceStepRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        ev_uuid = uuid.UUID(evidence_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Evidence UUID")

    # Resolve and authorize the evidence before touching custody state.
    ev = assert_evidence_access(db, current_user, ev_uuid)
    if current_user.role not in ["EVIDENCE_OFFICER", "FORENSIC_ANALYST", "SYSTEM_ADMIN"]:
        raise HTTPException(status_code=403, detail="This role cannot transfer custody")

    # Enforce review-before-transfer invariant for the current step.
    events = db.query(CustodyEvent).filter(CustodyEvent.evidence_id == ev_uuid).order_by(CustodyEvent.sequence_number.asc()).all()
    current_step_num = len(events)
    if current_step_num >= 1:
        require_current_handler(db, current_user, ev.case_id, "FORENSIC_ANALYST")
    if current_step_num > 0:
        latest_rev = (db.query(EvidenceReview)
            .filter(EvidenceReview.evidence_id == ev_uuid, EvidenceReview.custody_step == f"Step {current_step_num}")
            .order_by(EvidenceReview.created_at.desc())
            .first())
        if not latest_rev or latest_rev.decision != "APPROVE":
            raise HTTPException(
                status_code=409,
                detail=f"Evidence transfer blocked: Step {current_step_num} must be formally reviewed and APPROVED before custody transfer can proceed."
            )

    event = advance_custody_step(
        db=db,
        evidence_id=ev_uuid,
        user=current_user,
        simulate_tamper=payload.simulate_tamper,
    )
    return {
        "id": str(event.id),
        "sequence_number": event.sequence_number,
        "operation": event.operation,
        "event_hash": event.event_hash,
        "previous_event_hash": event.previous_event_hash,
    }


@router.post("/simulation")
def execute_pipeline_simulation(
    payload: SimulationRequest,
    current_user: User = Depends(require_role(["FORENSIC_ANALYST", "SYSTEM_ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Executes automated 4-stage pipeline demonstration.
    tamper_step=0: Clean intact custody run.
    tamper_step=3: Silent alteration at Evidence Exporter.
    """
    try:
        case_uuid = uuid.UUID(payload.case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Case UUID")
    assert_case_access(db, current_user, case_uuid)

    result = run_full_pipeline_simulation(
        db=db,
        case_id=case_uuid,
        name=payload.name,
        content=payload.content,
        user=current_user,
        tamper_step=payload.tamper_step,
    )
    return result
