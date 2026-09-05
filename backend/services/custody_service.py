import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session

import models
from utils.hashing import compute_hash
from services.handlers import HANDLER_PIPELINE
from services.storage_service import storage
from security.signatures import KeyProvider, build_canonical_event_string, sign_event
from services.audit_service import log_audit_event

GENESIS_PREV_HASH = "0" * 64


def process_evidence_pipeline(
    db: Session,
    evidence_name: str,
    content: str,
    case_id: int | None = None,
    exhibit_id: str | None = None,
    simulate_tamper: bool = True,
    tamper_step: int = 3,
    created_by: str = "Charan",
) -> models.Evidence:
    """
    Executes the digital custody pipeline for a given exhibit:
    1. Persists the baseline Evidence record.
    2. Stores immutable Artifacts in dedicated storage for every stage.
    3. Cryptographically seals each transition into a hash-linked signed CustodyEvent.
    4. Populates legacy CustodyLog to ensure 100% backward compatibility.
    5. Emits an immutable audit log.
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
