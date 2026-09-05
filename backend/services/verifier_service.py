import hashlib
from sqlalchemy.orm import Session

import models
from utils.hashing import compute_hash
from services.storage_service import storage
from security.signatures import (
    build_canonical_event_string,
    verify_event_signature,
    KeyProvider,
)
from services.audit_service import log_audit_event

NON_MUTATING_STEPS = {"Analyst Tool", "Export Tool", "Reviewer", "Archive"}
GENESIS_PREV_HASH = "0" * 64


def verify_evidence_integrity(db: Session, evidence_id: int, auditor_name: str = "System Verifier") -> dict:
    """
    Executes authoritative, multi-vector verification:
    Vector 1: Cryptographic Ledger Continuity (previous_event_hash -> event_hash)
    Vector 2: Handler Ed25519 Digital Signatures against Registered Public Keys
    Vector 3: Physical Storage Artifact Integrity & Hash Recomputation
    Vector 4: Artifact Relationship Continuity (Step N input == Step N-1 output)
    Vector 5: Forensic Non-Mutating Handler Invariance
    """
    evidence = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not evidence:
        return {"error": "Evidence not found"}

    events = (
        db.query(models.CustodyEvent)
        .filter(models.CustodyEvent.evidence_id == evidence_id)
        .order_by(models.CustodyEvent.sequence_number.asc())
        .all()
    )

    if not events:
        from services.verifier import verify_chain
        return verify_chain(db, evidence_id)

    step_results = []
    broken_step_order = None
    broken_step_reason = None
    final_verdict = "CHAIN_INTACT"
    chain_broken_already = False
    expected_prev_hash = GENESIS_PREV_HASH
    previous_content_hash = evidence.original_hash
    previous_output_artifact_id = None

    for ev in events:
        step_errors = []

        # --- Vector 1: Ledger Chain Continuity ---
        ledger_valid = (ev.previous_event_hash == expected_prev_hash)
        if not ledger_valid:
            step_errors.append("Ledger hash link mismatch.")

        # Reconstruct canonical string
        if hasattr(ev.timestamp, "strftime"):
            ts_str = ev.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            ts_str = str(ev.timestamp)[:19]
        canonical_str = build_canonical_event_string(
            evidence_id=ev.evidence_id,
            sequence=ev.sequence_number,
            handler_name=ev.handler_name,
            action=ev.action,
            hash_before=ev.hash_before,
            hash_after=ev.hash_after,
            timestamp_iso=ts_str,
            previous_event_hash=ev.previous_event_hash,
        )

        expected_event_hash = hashlib.sha256(f"{ev.previous_event_hash}|{canonical_str}".encode("utf-8")).hexdigest()
        event_hash_valid = (ev.event_hash == expected_event_hash)
        if not event_hash_valid:
            step_errors.append("Event hash recalculation mismatch.")

        # --- Vector 2: Digital Signature Verification ---
        sig_valid = verify_event_signature(ev.public_key, canonical_str, ev.signature)
        if not sig_valid:
            step_errors.append("Ed25519 digital signature invalid or forged.")

        # --- Vector 3: Physical Storage Artifact Integrity ---
        artifact_recomputed_hash = None
        artifact_valid = True
        if ev.output_artifact_id:
            art = db.query(models.Artifact).filter(models.Artifact.id == ev.output_artifact_id).first()
            if art and storage.exists(art.storage_key):
                raw_bytes = storage.get(art.storage_key)
                artifact_recomputed_hash = hashlib.sha256(raw_bytes).hexdigest()
                if artifact_recomputed_hash != ev.hash_after:
                    artifact_valid = False
                    step_errors.append(f"Storage artifact hash mismatch ({artifact_recomputed_hash[:8]} vs {ev.hash_after[:8]}).")
            else:
                artifact_valid = False
                step_errors.append("Output artifact missing from storage.")

        # --- Vector 4: Artifact Relationship Continuity ---
        artifact_continuity_valid = True
        if ev.sequence_number > 1 and previous_output_artifact_id:
            if ev.input_artifact_id != previous_output_artifact_id:
                artifact_continuity_valid = False
                step_errors.append(
                    f"Artifact continuity severed: Input artifact #{ev.input_artifact_id} "
                    f"does not match preceding output artifact #{previous_output_artifact_id}."
                )

        # Confirm artifacts belong to this evidence
        if ev.input_artifact_id:
            in_art = db.query(models.Artifact).filter(models.Artifact.id == ev.input_artifact_id).first()
            if not in_art or in_art.evidence_id != evidence_id:
                artifact_continuity_valid = False
                step_errors.append(f"Input artifact #{ev.input_artifact_id} does not belong to this evidence.")

        if ev.output_artifact_id:
            out_art = db.query(models.Artifact).filter(models.Artifact.id == ev.output_artifact_id).first()
            if not out_art or out_art.evidence_id != evidence_id:
                artifact_continuity_valid = False
                step_errors.append(f"Output artifact #{ev.output_artifact_id} does not belong to this evidence.")

        # --- Vector 5: Non-Mutating Handler Invariance ---
        content_intact = True
        if ev.handler_name in NON_MUTATING_STEPS:
            if artifact_recomputed_hash:
                content_intact = (artifact_recomputed_hash == previous_content_hash)
            else:
                content_intact = (ev.hash_after == previous_content_hash)
            if not content_intact:
                step_errors.append(f"Unauthorized mutation: hash changed from {previous_content_hash[:8]}... to {ev.hash_after[:8]}...")

        is_step_verified = (
            ledger_valid and
            event_hash_valid and
            sig_valid and
            artifact_valid and
            artifact_continuity_valid and
            content_intact
        )

        if not is_step_verified and not chain_broken_already:
            broken_step_order = ev.sequence_number
            handler_slug = ev.handler_name.replace(" ", "_").upper()
            if not sig_valid:
                final_verdict = f"SIGNATURE_INVALID_AT_STEP_{ev.sequence_number}_{handler_slug}"
                broken_step_reason = "SIGNATURE_INVALID"
            elif not ledger_valid or not event_hash_valid:
                final_verdict = f"LEDGER_BROKEN_AT_STEP_{ev.sequence_number}_{handler_slug}"
                broken_step_reason = "LEDGER_LINK_BROKEN"
            elif not artifact_continuity_valid:
                final_verdict = f"ARTIFACT_CHAIN_DISCONNECTED_AT_STEP_{ev.sequence_number}_{handler_slug}"
                broken_step_reason = "ARTIFACT_CHAIN_DISCONNECTED"
            else:
                final_verdict = f"CHAIN_BROKEN_AT_STEP_{ev.sequence_number}_{handler_slug}"
                broken_step_reason = "STORAGE_HASH_MISMATCH"
            chain_broken_already = True

        step_results.append({
            "step_order": ev.sequence_number,
            "handler_name": ev.handler_name,
            "action": ev.action,
            "hash_before": ev.hash_before,
            "hash_after": ev.hash_after,
            "actual_hash": artifact_recomputed_hash or ev.hash_after,
            "declared_status": ev.declared_status,
            "status": "VERIFIED" if is_step_verified else ("BROKEN" if not chain_broken_already or (broken_step_order == ev.sequence_number) else "DOWNSTREAM"),
            "verified": is_step_verified,
            "downstream_of_break": chain_broken_already and (broken_step_order != ev.sequence_number),
            "signature_valid": sig_valid,
            "ledger_link_valid": ledger_valid,
            "artifact_continuity_valid": artifact_continuity_valid,
            "event_hash": ev.event_hash,
            "signature_preview": f"{ev.signature[:16]}...{ev.signature[-8:]}",
            "errors": step_errors,
        })

        expected_prev_hash = ev.event_hash
        previous_content_hash = ev.hash_after
        previous_output_artifact_id = ev.output_artifact_id

    # Construct authoritative first_break dictionary
    first_break = None
    broken_handler_id = None
    if broken_step_order is not None:
        broken_step_info = next((s for s in step_results if s["step_order"] == broken_step_order), None)
        handler_name = broken_step_info["handler_name"] if broken_step_info else f"Step {broken_step_order}"
        handler_row = db.query(models.Handler).filter(models.Handler.name == handler_name).first()
        broken_handler_id = handler_row.id if handler_row else broken_step_order

        first_break = {
            "step_order": broken_step_order,
            "handler_id": broken_handler_id,
            "handler_name": handler_name,
            "reason": broken_step_reason or "STORAGE_HASH_MISMATCH",
        }

    # Update evidence overall status
    evidence.status = "VERIFIED" if final_verdict == "CHAIN_INTACT" else "BROKEN"
    db.commit()

    # Persist verification result with both handler ID and step order
    result = models.VerificationResult(
        evidence_id=evidence_id,
        final_verdict=final_verdict,
        broken_step_order=broken_step_order,
        broken_handler_id=broken_handler_id,
        broken_step_id=broken_handler_id,
    )
    db.add(result)
    db.commit()

    log_audit_event(
        db,
        user_name=auditor_name,
        action="VERIFY_EVIDENCE",
        resource_type="EVIDENCE",
        resource_id=str(evidence_id),
        details=f"Verification verdict: {final_verdict}",
    )

    return {
        "evidence_id": evidence.id,
        "case_id": evidence.case_id,
        "exhibit_id": evidence.exhibit_id,
        "evidence_name": evidence.name,
        "original_hash": evidence.original_hash,
        "final_verdict": final_verdict,
        "broken_step_order": broken_step_order,
        "broken_handler_id": broken_handler_id,
        "broken_step_id": broken_step_order,
        "first_break": first_break,
        "steps": step_results,
    }
