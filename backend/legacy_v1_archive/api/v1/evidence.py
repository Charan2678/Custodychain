import hashlib
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
import models
from security.auth import get_current_user, require_role
from services.custody_service import (
    process_evidence_pipeline,
    intake_evidence_step1,
    advance_custody_transfer,
)
from services.audit_service import log_audit_event
from services.verifier_service import verify_evidence_integrity
from services.storage_service import storage

router = APIRouter(prefix="/evidence", tags=["Digital Evidence"])


class IngestEvidenceRequest(BaseModel):
    case_id: int | None = None
    exhibit_id: str | None = None
    name: str
    content: str
    step_by_step: bool = False
    simulate_tamper: bool = False
    tamper_step: int = 0  # 0 for clean, 2-5 for specific handlers


class CustodyTransferRequest(BaseModel):
    simulate_tamper: bool = False


class ReviewNoteRequest(BaseModel):
    finding: str = "VERIFIED_INTACT"
    note: str
    advance_handover: bool = False
    simulate_tamper: bool = False


@router.post("")
def ingest_evidence(
    payload: IngestEvidenceRequest,
    current_user: models.User = Depends(require_role(["FORENSIC_ANALYST", "EVIDENCE_OFFICER", "SYSTEM_ADMIN"])),
    db: Session = Depends(get_db),
):
    target_case_id = payload.case_id
    if target_case_id:
        c = db.query(models.Case).filter(models.Case.id == target_case_id).first()
        if not c:
            raise HTTPException(status_code=400, detail=f"Case ID {target_case_id} does not exist.")
    else:
        # Require case selection
        first_case = db.query(models.Case).first()
        if not first_case:
            raise HTTPException(status_code=400, detail="No cases available. Please create a case first.")
        target_case_id = first_case.id

    if payload.step_by_step:
        # Initial intake only: Step 1 (Collector) executed, evidence in custody awaiting handover
        evidence = intake_evidence_step1(
            db=db,
            evidence_name=payload.name,
            content=payload.content,
            case_id=target_case_id,
            exhibit_id=payload.exhibit_id,
            created_by=current_user.name,
        )
    else:
        # Full automated lifecycle
        evidence = process_evidence_pipeline(
            db=db,
            evidence_name=payload.name,
            content=payload.content,
            case_id=target_case_id,
            exhibit_id=payload.exhibit_id,
            simulate_tamper=payload.simulate_tamper,
            tamper_step=payload.tamper_step,
            created_by=current_user.name,
        )

    # Return authoritative verification state for immediate timeline rendering
    return verify_evidence_integrity(db, evidence.id, auditor_name=current_user.name)


@router.post("/{evidence_id}/transfer")
def transfer_custody(
    evidence_id: int,
    payload: CustodyTransferRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Executes a role-enforced custody handover to the next handler in the chain:
    - Step 1 -> 2: Evidence Officer authorizes transfer to Forensic Analyst
    - Step 2 -> 3: Forensic Analyst processes in Laboratory / Export Tool
    - Step 3 -> 4: Transferred to Legal Reviewer
    - Step 4 -> 5: Sealed into Archive Vault
    """
    return advance_custody_transfer(
        db=db,
        evidence_id=evidence_id,
        current_user=current_user,
        simulate_tamper=payload.simulate_tamper,
    )


@router.get("")
def list_all_evidence(case_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Evidence)
    if case_id:
        query = query.filter(models.Evidence.case_id == case_id)
    items = query.order_by(models.Evidence.id.desc()).all()
    results = []
    for e in items:
        case = db.query(models.Case).filter(models.Case.id == e.case_id).first() if e.case_id else None
        latest_verdict = (
            db.query(models.VerificationResult)
            .filter(models.VerificationResult.evidence_id == e.id)
            .order_by(models.VerificationResult.id.desc())
            .first()
        )
        latest_event = (
            db.query(models.CustodyEvent)
            .filter(models.CustodyEvent.evidence_id == e.id)
            .order_by(models.CustodyEvent.sequence_number.desc())
            .first()
        )
        current_step = latest_event.sequence_number if latest_event else 0
        current_handler = latest_event.handler_name if latest_event else "Intake"

        # Determine responsible custody role
        if current_step == 1:
            custody_holder = "Officer John Vance (Evidence Officer)"
            pending_action_role = "FORENSIC_ANALYST"
        elif current_step in (2, 3):
            custody_holder = "Dr. Elena Rostova (Forensic Analyst)"
            pending_action_role = "FORENSIC_ANALYST"
        elif current_step == 4:
            custody_holder = "Legal Review Division"
            pending_action_role = "FORENSIC_ANALYST"
        else:
            custody_holder = "Forensic Archive Vault (Sealed)"
            pending_action_role = "SYSTEM_ADMIN"


        verdict_str = latest_verdict.final_verdict if latest_verdict else ("CHAIN_INTACT" if e.status != "BROKEN" else "BROKEN")

        results.append({
            "id": e.id,
            "case_id": e.case_id,
            "case_number": case.case_number if case else "None",
            "exhibit_id": e.exhibit_id,
            "name": e.name,
            "original_hash": e.original_hash,
            "size_bytes": e.size_bytes,
            "status": e.status,
            "current_step": current_step,
            "current_handler": current_handler,
            "custody_holder": custody_holder,
            "pending_action_role": pending_action_role,
            "latest_verdict": verdict_str,
            "created_by": e.created_by,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })
    return results


@router.get("/{evidence_id}/review")
def review_evidence_for_role(
    evidence_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Dedicated endpoint for authorized roles to review and inspect digital evidence
    prior to executing custody handovers or logging audit reviews.
    """
    e = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Evidence not found")

    case = db.query(models.Case).filter(models.Case.id == e.case_id).first() if e.case_id else None

    # Latest custody event
    latest_event = (
        db.query(models.CustodyEvent)
        .filter(models.CustodyEvent.evidence_id == e.id)
        .order_by(models.CustodyEvent.sequence_number.desc())
        .first()
    )

    current_step = latest_event.sequence_number if latest_event else 0
    current_handler = latest_event.handler_name if latest_event else "Intake"
    next_step = current_step + 1 if current_step < 5 else None

    # Determine next handler name
    pipeline_handlers = ["Collector", "Analyst Tool", "Export Tool", "Reviewer", "Archive"]
    next_handler = pipeline_handlers[current_step] if current_step < 5 else "Vault Sealed"

    # Evaluate permission for next handover
    can_transfer = False
    required_role = "None"
    if next_step == 2:
        can_transfer = current_user.role in ["EVIDENCE_OFFICER", "FORENSIC_ANALYST", "SYSTEM_ADMIN"]
        required_role = "Evidence Officer, Forensic Analyst, or System Admin"
    elif next_step in (3, 4, 5):
        can_transfer = current_user.role in ["FORENSIC_ANALYST", "SYSTEM_ADMIN"]
        required_role = "Forensic Analyst or System Admin"


    # Latest artifact and raw content preview
    latest_artifact = (
        db.query(models.Artifact)
        .filter(models.Artifact.evidence_id == e.id)
        .order_by(models.Artifact.sequence.desc())
        .first()
    )

    artifact_content = ""
    artifact_exists = False
    recomputed_sha256 = None
    if latest_artifact and storage.exists(latest_artifact.storage_key):
        artifact_exists = True
        raw_bytes = storage.get(latest_artifact.storage_key)
        recomputed_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        try:
            artifact_content = raw_bytes.decode("utf-8")
        except Exception:
            artifact_content = f"<Binary Data: {len(raw_bytes)} bytes>"

    latest_verdict = (
        db.query(models.VerificationResult)
        .filter(models.VerificationResult.evidence_id == e.id)
        .order_by(models.VerificationResult.id.desc())
        .first()
    )

    return {
        "evidence_id": e.id,
        "name": e.name,
        "exhibit_id": e.exhibit_id,
        "case_id": e.case_id,
        "case_number": case.case_number if case else None,
        "case_title": case.title if case else None,
        "original_hash": e.original_hash,
        "current_step": current_step,
        "current_handler": current_handler,
        "next_step": next_step,
        "next_handler": next_handler,
        "can_transfer": can_transfer,
        "required_role": required_role,
        "user_role": current_user.role,
        "user_name": current_user.name,
        "is_intact": (latest_verdict.final_verdict == "CHAIN_INTACT") if latest_verdict else True,
        "verdict": latest_verdict.final_verdict if latest_verdict else "NOT_VERIFIED",
        "artifact": {
            "id": latest_artifact.id if latest_artifact else None,
            "sequence": latest_artifact.sequence if latest_artifact else 0,
            "storage_key": latest_artifact.storage_key if latest_artifact else None,
            "sha256": latest_artifact.sha256 if latest_artifact else None,
            "recomputed_sha256": recomputed_sha256,
            "hash_matches": (recomputed_sha256 == latest_artifact.sha256) if (latest_artifact and recomputed_sha256) else False,
            "size_bytes": latest_artifact.size_bytes if latest_artifact else 0,
            "content": artifact_content,
        } if latest_artifact else None,
        "event": {
            "sequence": latest_event.sequence_number,
            "handler_name": latest_event.handler_name,
            "action": latest_event.action,
            "hash_before": latest_event.hash_before,
            "hash_after": latest_event.hash_after,
            "timestamp": latest_event.timestamp.isoformat() if latest_event.timestamp else None,
            "signature": latest_event.signature,
            "public_key": latest_event.public_key,
        } if latest_event else None,
    }


@router.post("/{evidence_id}/review-note")
def log_review_note(
    evidence_id: int,
    payload: ReviewNoteRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allows an authorized role to record a formal forensic review note into the
    immutable audit ledger, and optionally advance the custody handover.
    """
    e = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Evidence not found")

    log_audit_event(
        db,
        user_name=current_user.name,
        action="FORENSIC_REVIEW",
        resource_type="EVIDENCE",
        resource_id=str(evidence_id),
        details=f"Formal review by {current_user.name} ({current_user.role}): [{payload.finding}] {payload.note}",
    )

    if payload.advance_handover:
        return advance_custody_transfer(
            db=db,
            evidence_id=evidence_id,
            current_user=current_user,
            simulate_tamper=payload.simulate_tamper,
        )

    return {
        "status": "REVIEW_LOGGED",
        "evidence_id": evidence_id,
        "reviewer": current_user.name,
        "role": current_user.role,
        "finding": payload.finding,
        "note": payload.note,
    }


@router.get("/{evidence_id}")
def get_evidence_details(evidence_id: int, db: Session = Depends(get_db)):

    e = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Evidence not found")

    case = db.query(models.Case).filter(models.Case.id == e.case_id).first() if e.case_id else None
    latest_verdict = (
        db.query(models.VerificationResult)
        .filter(models.VerificationResult.evidence_id == e.id)
        .order_by(models.VerificationResult.id.desc())
        .first()
    )

    return {
        "id": e.id,
        "case_id": e.case_id,
        "case_number": case.case_number if case else None,
        "case_title": case.title if case else None,
        "exhibit_id": e.exhibit_id,
        "name": e.name,
        "original_hash": e.original_hash,
        "media_type": e.media_type,
        "size_bytes": e.size_bytes,
        "status": e.status,
        "latest_verdict": latest_verdict.final_verdict if latest_verdict else "NOT_VERIFIED",
        "created_by": e.created_by,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/{evidence_id}/events")
def get_custody_events(evidence_id: int, db: Session = Depends(get_db)):
    events = (
        db.query(models.CustodyEvent)
        .filter(models.CustodyEvent.evidence_id == evidence_id)
        .order_by(models.CustodyEvent.sequence_number.asc())
        .all()
    )
    if not events:
        raise HTTPException(status_code=404, detail="No custody events found for this evidence")

    return [
        {
            "sequence_number": ev.sequence_number,
            "handler_name": ev.handler_name,
            "action": ev.action,
            "input_artifact_id": ev.input_artifact_id,
            "output_artifact_id": ev.output_artifact_id,
            "hash_before": ev.hash_before,
            "hash_after": ev.hash_after,
            "declared_status": ev.declared_status,
            "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
            "previous_event_hash": ev.previous_event_hash,
            "event_hash": ev.event_hash,
            "signature": ev.signature,
            "public_key": ev.public_key,
        }
        for ev in events
    ]


@router.get("/{evidence_id}/artifacts")
def get_artifacts(evidence_id: int, db: Session = Depends(get_db)):
    artifacts = (
        db.query(models.Artifact)
        .filter(models.Artifact.evidence_id == evidence_id)
        .order_by(models.Artifact.sequence.asc())
        .all()
    )
    return [
        {
            "id": a.id,
            "sequence": a.sequence,
            "storage_key": a.storage_key,
            "sha256": a.sha256,
            "size_bytes": a.size_bytes,
            "media_type": a.media_type,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in artifacts
    ]


@router.get("/{evidence_id}/artifacts/{artifact_id}/content")
def download_artifact_content(evidence_id: int, artifact_id: int, db: Session = Depends(get_db)):
    art = db.query(models.Artifact).filter(
        models.Artifact.id == artifact_id,
        models.Artifact.evidence_id == evidence_id,
    ).first()
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if not storage.exists(art.storage_key):
        raise HTTPException(status_code=404, detail="Artifact file missing from storage")

    content_bytes = storage.get(art.storage_key)
    return Response(
        content=content_bytes,
        media_type=art.media_type or "text/plain",
        headers={"Content-Disposition": f"inline; filename={art.storage_key.split('/')[-1]}"},
    )
