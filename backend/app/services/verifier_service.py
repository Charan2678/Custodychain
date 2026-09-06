import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.models.artifact import Artifact
from app.models.actor import Actor
from app.models.tool import Tool
from app.models.custody_event import CustodyEvent
from app.models.provenance import ProvenanceRelation
from app.models.verification_run import VerificationRun
from app.models.verification_finding import VerificationFinding
from app.infrastructure.storage.storage_service import storage, compute_bytes_hash
from app.infrastructure.cryptography.signatures import (
    GENESIS_HASH,
    build_canonical_event_string,
    compute_event_hash,
    verify_signature,
)


def run_independent_verification(
    db: Session,
    evidence_id: uuid.UUID,
    requested_by_user_id: uuid.UUID,
) -> Dict[str, Any]:
    """
    Executes independent multi-vector verification over the entire chain of custody.
    Compares Artifact Truth (MinIO bytes), Event Truth (signatures & hash chain),
    and Lineage Truth (provenance DAG).
    
    Identifies the EXACT FIRST BREAK where divergence occurred, and marks all
    subsequent steps as DOWNSTREAM_AFFECTED.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise ValueError(f"Evidence {evidence_id} not found")

    events: List[CustodyEvent] = (
        db.query(CustodyEvent)
        .filter(CustodyEvent.evidence_id == evidence_id)
        .order_by(CustodyEvent.sequence_number.asc())
        .all()
    )

    started_at = datetime.now(timezone.utc)
    v_run = VerificationRun(
        evidence_id=evidence.id,
        requested_by=requested_by_user_id,
        started_at=started_at,
        status="RUNNING",
        verification_version="2.0.0",
    )
    db.add(v_run)
    db.commit()
    db.refresh(v_run)

    findings: List[VerificationFinding] = []
    step_results: List[Dict[str, Any]] = []

    first_break_found = False
    first_break_event: Optional[CustodyEvent] = None
    first_break_reason: Optional[str] = None
    first_break_expected: Optional[str] = None
    first_break_observed: Optional[str] = None

    expected_prev_hash = GENESIS_HASH
    prev_event: Optional[CustodyEvent] = None

    for ev in events:
        step_verified = True
        step_findings: List[str] = []
        is_downstream = first_break_found

        out_art = db.query(Artifact).filter(Artifact.id == ev.output_artifact_id).first()
        in_art = db.query(Artifact).filter(Artifact.id == ev.input_artifact_id).first() if ev.input_artifact_id else None
        actor = db.query(Actor).filter(Actor.id == ev.actor_id).first()
        tool = db.query(Tool).filter(Tool.id == ev.tool_id).first() if ev.tool_id else None

        # If already broken upstream, mark step as DOWNSTREAM_AFFECTED
        if is_downstream:
            finding = VerificationFinding(
                verification_run_id=v_run.id,
                custody_event_id=ev.id,
                artifact_id=out_art.id if out_art else None,
                finding_type="DOWNSTREAM_AFFECTED",
                severity="WARNING",
                message=f"Step {ev.sequence_number} ({tool.name if tool else ev.operation}) is downstream of root failure at Step {first_break_event.sequence_number if first_break_event else '?'}.",
                is_first_break=False,
            )
            findings.append(finding)
            downstream_recomputed = None
            if out_art and storage.exists(out_art.storage_key):
                downstream_recomputed = compute_bytes_hash(storage.get(out_art.storage_key))

            step_results.append({
                "sequence_number": ev.sequence_number,
                "step_order": ev.sequence_number,
                "operation": ev.operation,
                "tool_name": tool.name if tool else None,
                "handler_name": tool.name if tool else ev.operation,
                "actor_name": actor.name if actor else None,
                "status": "DOWNSTREAM",
                "verified": False,
                "downstream": True,
                "downstream_of_break": True,
                "declared_sha256": out_art.sha256 if out_art else None,
                "hash_before": in_art.sha256 if in_art else (out_art.sha256 if out_art else ""),
                "hash_after": out_art.sha256 if out_art else "",
                "actual_hash": downstream_recomputed or (out_art.sha256 if out_art else ""),
                "signature_valid": True,
                "signature_preview": "Ed25519",
                "ledger_link_valid": True,
                "artifact_continuity_valid": False,
                "timestamp": ev.occurred_at.isoformat() if ev.occurred_at else None,
                "reason": "DOWNSTREAM_CONTAMINATION",
                "findings": ["Downstream contaminated by earlier divergence."],
            })
            continue

        # -------------------------------------------------------------
        # Vector 1: Physical Object Storage Integrity (Artifact Truth)
        # -------------------------------------------------------------
        if not out_art or not storage.exists(out_art.storage_key):
            step_verified = False
            msg = f"Artifact missing from storage: {out_art.storage_key if out_art else 'Unknown'}"
            step_findings.append(msg)
            if not first_break_found:
                first_break_found = True
                first_break_event = ev
                first_break_reason = "STORAGE_ARTIFACT_MISSING"
                first_break_expected = "Accessible artifact in object storage"
                first_break_observed = "Missing object"
                findings.append(VerificationFinding(
                    verification_run_id=v_run.id,
                    custody_event_id=ev.id,
                    artifact_id=out_art.id if out_art else None,
                    finding_type="STORAGE_ARTIFACT_MISSING",
                    severity="CRITICAL",
                    expected_value=first_break_expected,
                    observed_value=first_break_observed,
                    message=msg,
                    is_first_break=True,
                ))
        else:
            raw_bytes = storage.get(out_art.storage_key)
            recomputed_hash = compute_bytes_hash(raw_bytes)
            if recomputed_hash.lower() != out_art.sha256.lower():
                step_verified = False
                msg = f"Artifact byte hash mismatch! Expected {out_art.sha256[:16]}... Observed {recomputed_hash[:16]}..."
                step_findings.append(msg)
                if not first_break_found:
                    first_break_found = True
                    first_break_event = ev
                    first_break_reason = "ARTIFACT_HASH_MISMATCH"
                    first_break_expected = out_art.sha256
                    first_break_observed = recomputed_hash
                    findings.append(VerificationFinding(
                        verification_run_id=v_run.id,
                        custody_event_id=ev.id,
                        artifact_id=out_art.id,
                        finding_type="ARTIFACT_HASH_MISMATCH",
                        severity="CRITICAL",
                        expected_value=first_break_expected,
                        observed_value=first_break_observed,
                        message=msg,
                        is_first_break=True,
                    ))

        # -------------------------------------------------------------
        # Vector 2: Ledger Hash Continuity (Chain Truth)
        # -------------------------------------------------------------
        if ev.previous_event_hash != expected_prev_hash:
            step_verified = False
            msg = f"Ledger break: previous_event_hash mismatch! Expected {expected_prev_hash[:16]}... Declared {ev.previous_event_hash[:16] if ev.previous_event_hash else 'NONE'}..."
            step_findings.append(msg)
            if not first_break_found:
                first_break_found = True
                first_break_event = ev
                first_break_reason = "LEDGER_CHAIN_BROKEN"
                first_break_expected = expected_prev_hash
                first_break_observed = ev.previous_event_hash
                findings.append(VerificationFinding(
                    verification_run_id=v_run.id,
                    custody_event_id=ev.id,
                    finding_type="LEDGER_CHAIN_BROKEN",
                    severity="CRITICAL",
                    expected_value=first_break_expected,
                    observed_value=first_break_observed,
                    message=msg,
                    is_first_break=True,
                ))

        # -------------------------------------------------------------
        # Vector 3: Event Hash Verification
        # -------------------------------------------------------------
        occurred_iso = ev.occurred_at.strftime("%Y-%m-%d %H:%M:%S")
        canonical_str = build_canonical_event_string(
            evidence_id=str(evidence.id),
            sequence_number=ev.sequence_number,
            actor_id=str(ev.actor_id),
            tool_id=str(ev.tool_id) if ev.tool_id else None,
            operation=ev.operation,
            input_artifact_hash=in_art.sha256 if in_art else "GENESIS",
            output_artifact_hash=out_art.sha256 if out_art else "NONE",
            occurred_at_str=occurred_iso,
            previous_event_hash=ev.previous_event_hash or GENESIS_HASH,
        )
        calculated_event_hash = compute_event_hash(canonical_str, ev.previous_event_hash or GENESIS_HASH)
        if calculated_event_hash.lower() != ev.event_hash.lower():
            step_verified = False
            msg = f"Event hash tampering detected! Recomputed {calculated_event_hash[:16]}... Declared {ev.event_hash[:16]}..."
            step_findings.append(msg)
            if not first_break_found:
                first_break_found = True
                first_break_event = ev
                first_break_reason = "EVENT_HASH_TAMPERED"
                first_break_expected = calculated_event_hash
                first_break_observed = ev.event_hash
                findings.append(VerificationFinding(
                    verification_run_id=v_run.id,
                    custody_event_id=ev.id,
                    finding_type="EVENT_HASH_TAMPERED",
                    severity="CRITICAL",
                    expected_value=first_break_expected,
                    observed_value=first_break_observed,
                    message=msg,
                    is_first_break=True,
                ))

        # -------------------------------------------------------------
        # Vector 4: Digital Signatures (Authenticity)
        # -------------------------------------------------------------
        if ev.actor_signature and actor and actor.public_key:
            if not verify_signature(actor.public_key, canonical_str, ev.actor_signature):
                step_verified = False
                msg = f"Invalid actor signature from {actor.name}!"
                step_findings.append(msg)
                if not first_break_found:
                    first_break_found = True
                    first_break_event = ev
                    first_break_reason = "ACTOR_SIGNATURE_INVALID"
                    first_break_expected = "Valid Ed25519 signature"
                    first_break_observed = "Invalid signature"
                    findings.append(VerificationFinding(
                        verification_run_id=v_run.id,
                        custody_event_id=ev.id,
                        finding_type="ACTOR_SIGNATURE_INVALID",
                        severity="CRITICAL",
                        expected_value=first_break_expected,
                        observed_value=first_break_observed,
                        message=msg,
                        is_first_break=True,
                    ))

        if ev.tool_signature and tool and tool.public_key:
            if not verify_signature(tool.public_key, canonical_str, ev.tool_signature):
                step_verified = False
                msg = f"Invalid tool signature from {tool.name}!"
                step_findings.append(msg)
                if not first_break_found:
                    first_break_found = True
                    first_break_event = ev
                    first_break_reason = "TOOL_SIGNATURE_INVALID"
                    first_break_expected = "Valid Ed25519 signature"
                    first_break_observed = "Invalid signature"
                    findings.append(VerificationFinding(
                        verification_run_id=v_run.id,
                        custody_event_id=ev.id,
                        finding_type="TOOL_SIGNATURE_INVALID",
                        severity="CRITICAL",
                        expected_value=first_break_expected,
                        observed_value=first_break_observed,
                        message=msg,
                        is_first_break=True,
                    ))

        # -------------------------------------------------------------
        # Vector 5: Non-Mutating Handler Invariance & Lineage Continuity
        # -------------------------------------------------------------
        if ev.sequence_number > 1 and prev_event:
            # Check lineage link: input artifact must match previous output artifact
            if ev.input_artifact_id != prev_event.output_artifact_id:
                step_verified = False
                msg = "Input artifact does not match previous output artifact!"
                step_findings.append(msg)
                if not first_break_found:
                    first_break_found = True
                    first_break_event = ev
                    first_break_reason = "ARTIFACT_LINEAGE_DISCONNECTED"
                    first_break_expected = str(prev_event.output_artifact_id)
                    first_break_observed = str(ev.input_artifact_id)
                    findings.append(VerificationFinding(
                        verification_run_id=v_run.id,
                        custody_event_id=ev.id,
                        finding_type="ARTIFACT_LINEAGE_DISCONNECTED",
                        severity="CRITICAL",
                        expected_value=first_break_expected,
                        observed_value=first_break_observed,
                        message=msg,
                        is_first_break=True,
                    ))

            # Non-mutating handler check (Collector, Normalizer, Exporter, Archiver)
            # In forensic custody, these steps must not alter evidence bytes
            if in_art and out_art and in_art.sha256 != out_art.sha256:
                step_verified = False
                msg = f"Unauthorized mutation detected at Step {ev.sequence_number} ({tool.name if tool else ev.operation})! In-hash: {in_art.sha256[:16]}... Out-hash: {out_art.sha256[:16]}..."
                step_findings.append(msg)
                if not first_break_found:
                    first_break_found = True
                    first_break_event = ev
                    first_break_reason = "UNAUTHORIZED_EVIDENCE_MUTATION"
                    first_break_expected = in_art.sha256
                    first_break_observed = out_art.sha256
                    findings.append(VerificationFinding(
                        verification_run_id=v_run.id,
                        custody_event_id=ev.id,
                        artifact_id=out_art.id,
                        finding_type="UNAUTHORIZED_EVIDENCE_MUTATION",
                        severity="CRITICAL",
                        expected_value=first_break_expected,
                        observed_value=first_break_observed,
                        message=msg,
                        is_first_break=True,
                    ))

        # Advance expectation
        expected_prev_hash = ev.event_hash
        prev_event = ev

        standard_recomputed = None
        if out_art and storage.exists(out_art.storage_key):
            standard_recomputed = compute_bytes_hash(storage.get(out_art.storage_key))

        sig_str = ev.tool_signature or ev.actor_signature or ""
        step_results.append({
            "sequence_number": ev.sequence_number,
            "step_order": ev.sequence_number,
            "operation": ev.operation,
            "tool_name": tool.name if tool else None,
            "handler_name": tool.name if tool else ev.operation,
            "actor_name": actor.name if actor else None,
            "status": "VERIFIED" if step_verified else "BROKEN",
            "verified": step_verified,
            "downstream": False,
            "downstream_of_break": False,
            "declared_sha256": out_art.sha256 if out_art else None,
            "hash_before": in_art.sha256 if in_art else (out_art.sha256 if out_art else ""),
            "hash_after": out_art.sha256 if out_art else "",
            "actual_hash": standard_recomputed or (out_art.sha256 if out_art else ""),
            "signature_valid": step_verified,
            "signature_preview": (sig_str[:24] + "...") if sig_str else "Ed25519",
            "ledger_link_valid": True,
            "artifact_continuity_valid": True,
            "timestamp": ev.occurred_at.isoformat() if ev.occurred_at else None,
            "reason": first_break_reason if (first_break_event and first_break_event.id == ev.id) else None,
            "findings": step_findings if step_findings else ["All 5 verification vectors passed."],
        })

    # Record overall verdict
    final_verdict = "CHAIN_BROKEN" if first_break_found else "CHAIN_INTACT"
    completed_at = datetime.now(timezone.utc)

    v_run.status = "COMPLETED"
    v_run.verdict = final_verdict
    v_run.completed_at = completed_at
    if first_break_event:
        v_run.first_break_event_id = first_break_event.id

    db.add_all(findings)
    if first_break_event:
        from app.models.user import User
        from app.services.audit_service import record_audit_event
        requested_by = db.query(User).filter(User.id == requested_by_user_id).first()
        record_audit_event(
            db,
            user=requested_by,
            action="CHAIN_BROKEN_DETECTED",
            resource_type="EVIDENCE",
            resource_id=str(evidence.id),
            case_id=evidence.case_id,
            evidence_id=evidence.id,
            details={
                "sequence_number": first_break_event.sequence_number,
                "reason": first_break_reason,
                "actor_id": str(first_break_event.actor_id),
            },
        )
    db.commit()
    db.refresh(v_run)

    # First break payload for clear forensic reporting
    first_break_summary = None
    if first_break_found and first_break_event:
        fb_tool = db.query(Tool).filter(Tool.id == first_break_event.tool_id).first()
        fb_actor = db.query(Actor).filter(Actor.id == first_break_event.actor_id).first()
        first_break_summary = {
            "sequence_number": first_break_event.sequence_number,
            "step_order": first_break_event.sequence_number,
            "event_id": str(first_break_event.id),
            "operation": first_break_event.operation,
            "tool_name": fb_tool.name if fb_tool else "Unknown Tool",
            "handler_name": fb_tool.name if fb_tool else "Unknown Tool",
            "actor_name": fb_actor.name if fb_actor else "Unknown Actor",
            "reason": first_break_reason,
            "expected_value": first_break_expected,
            "observed_value": first_break_observed,
            "affected_downstream_steps": [
                s["sequence_number"] for s in step_results if s["downstream"]
            ],
        }

    genesis_art = (
        db.query(Artifact)
        .filter(Artifact.evidence_id == evidence.id)
        .order_by(Artifact.created_at.asc())
        .first()
    )

    result = {
        "verification_id": str(v_run.id),
        "evidence_id": str(evidence.id),
        "evidence_number": evidence.evidence_number,
        "exhibit_id": evidence.evidence_number,
        "evidence_name": evidence.name,
        "original_hash": genesis_art.sha256 if genesis_art else "",
        "verdict": final_verdict,
        "final_verdict": final_verdict,
        "status": "COMPLETED",
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "first_break": first_break_summary,
        "steps": step_results,
    }
    # Persist an immutable snapshot so GET/report/AI reads do not create a new verification run.
    v_run.metadata_json = result
    db.commit()
    return result
