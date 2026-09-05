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
def list_all_evidence(db: Session = Depends(get_db)):
    items = db.query(models.Evidence).order_by(models.Evidence.id.desc()).all()
    results = []
    for e in items:
        case = db.query(models.Case).filter(models.Case.id == e.case_id).first() if e.case_id else None
        latest_verdict = (
            db.query(models.VerificationResult)
            .filter(models.VerificationResult.evidence_id == e.id)
            .order_by(models.VerificationResult.id.desc())
            .first()
        )
        results.append({
            "id": e.id,
            "case_id": e.case_id,
            "case_number": case.case_number if case else "None",
            "exhibit_id": e.exhibit_id,
            "name": e.name,
            "original_hash": e.original_hash,
            "size_bytes": e.size_bytes,
            "status": e.status,
            "latest_verdict": latest_verdict.final_verdict if latest_verdict else "NOT_VERIFIED",
            "created_by": e.created_by,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })
    return results


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
