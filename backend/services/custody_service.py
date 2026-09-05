import hashlib
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from utils.hashing import compute_hash
from services.handlers import HANDLER_PIPELINE
from services.storage_service import storage
from security.signatures import KeyProvider, build_canonical_event_string, sign_event
from services.audit_service import log_audit_event
from services.verifier_service import verify_evidence_integrity

GENESIS_PREV_HASH = "0" * 64


def intake_evidence_step1(
    db: Session,
    evidence_name: str,
    content: str,
    case_id: int,
    exhibit_id: str | None = None,
    created_by: str = "Officer",
) -> models.Evidence:
    """
    Step 1 Initial Intake:
    Executed by Evidence Officer or Admin when evidence is registered into a case.
    Creates genesis artifact and records Step 1 (Collector) event.
    Leaves evidence in IN_CUSTODY state, ready to be passed to Forensic Analyst.
    """
    original_hash = compute_hash(content)
    content_bytes = content.encode("utf-8")

    evidence = models.Evidence(
        case_id=case_id,
        exhibit_id=exhibit_id or f"EX-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        name=evidence_name,
        original_content=content,
        original_hash=original_hash,
        size_bytes=len(content_bytes),
        status="IN_CUSTODY",
        created_by=created_by,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    # Store genesis artifact (sequence 0)
    genesis_key = f"evidence_{evidence.id}/artifact_0_original.txt"
    storage.put(genesis_key, content_bytes)
    genesis_artifact = models.Artifact(
        evidence_id=evidence.id,
        parent_artifact_id=None,
        sequence=0,
        storage_key=genesis_key,
        sha256=original_hash,
        size_bytes=len(content_bytes),
        media_type="text/plain",
    )
    db.add(genesis_artifact)
    db.commit()
    db.refresh(genesis_artifact)

    # Step 1 Handler: Collector
    step_order, handler_name, handler_fn = HANDLER_PIPELINE[0]
    handler_row = db.query(models.Handler).filter(models.Handler.step_order == 1).first()
    if not handler_row:
        handler_row = models.Handler(name=handler_name, step_order=1)
        db.add(handler_row)
        db.commit()
        db.refresh(handler_row)

    new_content, declared_status = handler_fn(content, simulate_tamper=False)
    new_bytes = new_content.encode("utf-8")
    hash_after = compute_hash(new_content)

    art_key = f"evidence_{evidence.id}/artifact_1_collector.txt"
    storage.put(art_key, new_bytes)

    output_artifact = models.Artifact(
        evidence_id=evidence.id,
        parent_artifact_id=genesis_artifact.id,
        sequence=1,
        storage_key=art_key,
        sha256=hash_after,
        size_bytes=len(new_bytes),
        media_type="text/plain",
    )
    db.add(output_artifact)
    db.commit()
    db.refresh(output_artifact)

    event_dt = datetime.now(timezone.utc).replace(microsecond=0)
    timestamp_str = event_dt.strftime("%Y-%m-%d %H:%M:%S")
    action_name = f"Acquired by {handler_name}"
    canonical_str = build_canonical_event_string(
        evidence_id=evidence.id,
        sequence=1,
        handler_name=handler_name,
        action=action_name,
        hash_before=original_hash,
        hash_after=hash_after,
        timestamp_iso=timestamp_str,
        previous_event_hash=GENESIS_PREV_HASH,
    )

    sig_b64 = sign_event(handler_name, canonical_str)
    pubkey_b64 = KeyProvider.get_public_key_b64(handler_name)
    event_hash = hashlib.sha256(f"{GENESIS_PREV_HASH}|{canonical_str}".encode("utf-8")).hexdigest()

    custody_event = models.CustodyEvent(
        evidence_id=evidence.id,
        sequence_number=1,
        handler_name=handler_name,
        action=action_name,
        input_artifact_id=genesis_artifact.id,
        output_artifact_id=output_artifact.id,
        hash_before=original_hash,
        hash_after=hash_after,
        declared_status=declared_status,
        timestamp=event_dt,
        previous_event_hash=GENESIS_PREV_HASH,
        event_hash=event_hash,
        signature=sig_b64,
        public_key=pubkey_b64,
    )
    db.add(custody_event)

    legacy_log = models.CustodyLog(
        evidence_id=evidence.id,
        handler_id=handler_row.id,
        hash_before=original_hash,
        hash_after=hash_after,
        actual_content_snapshot=new_content,
        status_declared=declared_status,
    )
    db.add(legacy_log)
    db.commit()

    log_audit_event(
        db,
        user_name=created_by,
        action="EVIDENCE_INTAKE",
        resource_type="EVIDENCE",
        resource_id=str(evidence.id),
        details=f"Exhibit {evidence.exhibit_id} intake registered in case #{case_id} by {created_by}",
    )

    return evidence


def advance_custody_transfer(
    db: Session,
    evidence_id: int,
    current_user: models.User,
    simulate_tamper: bool = False,
) -> dict:
    """
    Step-by-step custody handover ("Passing to next person"):
    1 -> 2: Evidence Officer passes custody to Forensic Analyst
    2 -> 3: Forensic Analyst runs Laboratory Processing / Export
    3 -> 4: Transferred to Legal Reviewer
    4 -> 5: Sealed into Secure Archive Vault
    """
    evidence = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Determine latest custody event
    latest_event = (
        db.query(models.CustodyEvent)
        .filter(models.CustodyEvent.evidence_id == evidence_id)
        .order_by(models.CustodyEvent.sequence_number.desc())
        .first()
    )

    current_step = latest_event.sequence_number if latest_event else 0
    next_step = current_step + 1

    if next_step > len(HANDLER_PIPELINE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evidence exhibit has reached final archive custody; cannot transfer further.",
        )

    # Enforce strict Role-Based Access Control for each handover transition
    if current_user.role == "AUDITOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Auditors hold read-only compliance clearance and cannot execute custody handovers.",
        )

    if next_step == 2:
        # Transfer from Evidence Officer to Forensic Analyst
        if current_user.role not in ["EVIDENCE_OFFICER", "SYSTEM_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: Only Evidence Officers or System Admins may authorize custody transfer to Forensic Analysts.",
            )
    elif next_step in (3, 4):
        # Laboratory Analysis & Packaging by Forensic Analyst
        if current_user.role not in ["FORENSIC_ANALYST", "SYSTEM_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: Only Forensic Analysts or System Admins may execute laboratory analysis and export processing.",
            )
    elif next_step == 5:
        # Final sealing to archive
        if current_user.role not in ["FORENSIC_ANALYST", "SYSTEM_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: Only Forensic Analysts or System Admins may authorize final archival vault sealing.",
            )

    step_order, handler_name, handler_fn = HANDLER_PIPELINE[next_step - 1]

    # Handler row for legacy compatibility
    handler_row = db.query(models.Handler).filter(models.Handler.step_order == next_step).first()
    if not handler_row:
        handler_row = models.Handler(name=handler_name, step_order=next_step)
        db.add(handler_row)
        db.commit()
        db.refresh(handler_row)

    # Read current content snapshot from previous artifact
    current_art = db.query(models.Artifact).filter(models.Artifact.id == latest_event.output_artifact_id).first()
    if not current_art or not storage.exists(current_art.storage_key):
        raise HTTPException(status_code=500, detail="Previous custody artifact missing from storage")

    current_bytes = storage.get(current_art.storage_key)
    current_content = current_bytes.decode("utf-8")
    hash_before = compute_hash(current_content)

    # Execute handler logic
    new_content, declared_status = handler_fn(current_content, simulate_tamper=simulate_tamper)
    new_bytes = new_content.encode("utf-8")
    hash_after = compute_hash(new_content)

    clean_name = handler_name.lower().replace(" ", "_")
    art_key = f"evidence_{evidence.id}/artifact_{next_step}_{clean_name}.txt"
    storage.put(art_key, new_bytes)

    output_artifact = models.Artifact(
        evidence_id=evidence.id,
        parent_artifact_id=current_art.id,
        sequence=next_step,
        storage_key=art_key,
        sha256=hash_after,
        size_bytes=len(new_bytes),
        media_type="text/plain",
    )
    db.add(output_artifact)
    db.commit()
    db.refresh(output_artifact)

    event_dt = datetime.now(timezone.utc).replace(microsecond=0)
    timestamp_str = event_dt.strftime("%Y-%m-%d %H:%M:%S")
    action_name = f"Transferred to {handler_name}"
    canonical_str = build_canonical_event_string(
        evidence_id=evidence.id,
        sequence=next_step,
        handler_name=handler_name,
        action=action_name,
        hash_before=hash_before,
        hash_after=hash_after,
        timestamp_iso=timestamp_str,
        previous_event_hash=latest_event.event_hash,
    )

    sig_b64 = sign_event(handler_name, canonical_str)
    pubkey_b64 = KeyProvider.get_public_key_b64(handler_name)
    event_hash = hashlib.sha256(f"{latest_event.event_hash}|{canonical_str}".encode("utf-8")).hexdigest()

    custody_event = models.CustodyEvent(
        evidence_id=evidence.id,
        sequence_number=next_step,
        handler_name=handler_name,
        action=action_name,
        input_artifact_id=current_art.id,
        output_artifact_id=output_artifact.id,
        hash_before=hash_before,
        hash_after=hash_after,
        declared_status=declared_status,
        timestamp=event_dt,
        previous_event_hash=latest_event.event_hash,
        event_hash=event_hash,
        signature=sig_b64,
        public_key=pubkey_b64,
    )
    db.add(custody_event)

    legacy_log = models.CustodyLog(
        evidence_id=evidence.id,
        handler_id=handler_row.id,
        hash_before=hash_before,
        hash_after=hash_after,
        actual_content_snapshot=new_content,
        status_declared=declared_status,
    )
    db.add(legacy_log)
    db.commit()

    log_audit_event(
        db,
        user_name=current_user.name,
        action="CUSTODY_HANDOVER",
        resource_type="EVIDENCE",
        resource_id=str(evidence.id),
        details=f"Step {next_step} ({handler_name}) custody transfer authorized by {current_user.name} ({current_user.role})",
    )

    # Re-evaluate verification status
    return verify_evidence_integrity(db, evidence.id, auditor_name=current_user.name)


def process_evidence_pipeline(
    db: Session,
    evidence_name: str,
    content: str,
    case_id: int | None = None,
    exhibit_id: str | None = None,
    simulate_tamper: bool = False,
    tamper_step: int = 0,
    created_by: str = "Charan",
) -> models.Evidence:
    """
    Executes the full automated digital custody pipeline for demonstration:
    Defaults to clean authentic chain (simulate_tamper=False, tamper_step=0).
    """
    original_hash = compute_hash(content)
    content_bytes = content.encode("utf-8")

    # 1. Create Evidence record
    evidence = models.Evidence(
        case_id=case_id,
        exhibit_id=exhibit_id or f"EX-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        name=evidence_name,
        original_content=content,
        original_hash=original_hash,
        size_bytes=len(content_bytes),
        status="PENDING",
        created_by=created_by,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    # 2. Store genesis artifact
    genesis_key = f"evidence_{evidence.id}/artifact_0_original.txt"
    storage.put(genesis_key, content_bytes)
    genesis_artifact = models.Artifact(
        evidence_id=evidence.id,
        parent_artifact_id=None,
        sequence=0,
        storage_key=genesis_key,
        sha256=original_hash,
        size_bytes=len(content_bytes),
        media_type="text/plain",
    )
    db.add(genesis_artifact)
    db.commit()
    db.refresh(genesis_artifact)

    # 3. Step through pipeline handlers
    current_content = content
    current_artifact_id = genesis_artifact.id
    prev_event_hash = GENESIS_PREV_HASH

    for step_order, handler_name, handler_fn in HANDLER_PIPELINE:
        # Retrieve legacy handler row for backward compatibility
        handler_row = db.query(models.Handler).filter(models.Handler.step_order == step_order).first()
        if not handler_row:
            handler_row = models.Handler(name=handler_name, step_order=step_order)
            db.add(handler_row)
            db.commit()
            db.refresh(handler_row)

        hash_before = compute_hash(current_content)
        should_tamper = simulate_tamper and (step_order == tamper_step)
        new_content, declared_status = handler_fn(current_content, simulate_tamper=should_tamper)
        hash_after = compute_hash(new_content)
        new_bytes = new_content.encode("utf-8")

        # Save stage artifact to storage
        clean_name = handler_name.lower().replace(" ", "_")
        art_key = f"evidence_{evidence.id}/artifact_{step_order}_{clean_name}.txt"
        storage.put(art_key, new_bytes)

        output_artifact = models.Artifact(
            evidence_id=evidence.id,
            parent_artifact_id=current_artifact_id,
            sequence=step_order,
            storage_key=art_key,
            sha256=hash_after,
            size_bytes=len(new_bytes),
            media_type="text/plain",
        )
        db.add(output_artifact)
        db.commit()
        db.refresh(output_artifact)

        # Build canonical signed event string
        event_dt = datetime.now(timezone.utc).replace(microsecond=0)
        timestamp_str = event_dt.strftime("%Y-%m-%d %H:%M:%S")
        action_name = f"Process through {handler_name}"
        canonical_str = build_canonical_event_string(
            evidence_id=evidence.id,
            sequence=step_order,
            handler_name=handler_name,
            action=action_name,
            hash_before=hash_before,
            hash_after=hash_after,
            timestamp_iso=timestamp_str,
            previous_event_hash=prev_event_hash,
        )

        # Ed25519 signature
        sig_b64 = sign_event(handler_name, canonical_str)
        pubkey_b64 = KeyProvider.get_public_key_b64(handler_name)

        # Calculate event hash (cryptographic link)
        event_hash_payload = f"{prev_event_hash}|{canonical_str}"
        event_hash = hashlib.sha256(event_hash_payload.encode("utf-8")).hexdigest()

        # Save CustodyEvent
        custody_event = models.CustodyEvent(
            evidence_id=evidence.id,
            sequence_number=step_order,
            handler_name=handler_name,
            action=action_name,
            input_artifact_id=current_artifact_id,
            output_artifact_id=output_artifact.id,
            hash_before=hash_before,
            hash_after=hash_after,
            declared_status=declared_status,
            timestamp=event_dt,
            previous_event_hash=prev_event_hash,
            event_hash=event_hash,
            signature=sig_b64,
            public_key=pubkey_b64,
        )
        db.add(custody_event)

        # Save legacy CustodyLog
        legacy_log = models.CustodyLog(
            evidence_id=evidence.id,
            handler_id=handler_row.id,
            hash_before=hash_before,
            hash_after=hash_after,
            actual_content_snapshot=new_content,
            status_declared=declared_status,
        )
        db.add(legacy_log)
        db.commit()

        # Update pointers for next loop
        current_content = new_content
        current_artifact_id = output_artifact.id
        prev_event_hash = event_hash

    # Record Audit entry
    log_audit_event(
        db,
        user_name=created_by,
        action="EVIDENCE_PIPELINE_RUN",
        resource_type="EVIDENCE",
        resource_id=str(evidence.id),
        details=f"Exhibit {evidence.exhibit_id} processed (tamper_step={tamper_step if simulate_tamper else 'None'}).",
    )

    return evidence
