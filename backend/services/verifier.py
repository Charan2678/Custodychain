from sqlalchemy.orm import Session
from utils.hashing import compute_hash
import models


# These steps are contractually required to leave evidence byte-for-byte unchanged.
# The Collector is the trusted origin point, so it is always considered the baseline.
NON_MUTATING_STEPS = {"Analyst Tool", "Export Tool", "Reviewer", "Archive"}


def verify_chain(db: Session, evidence_id: int) -> dict:
    """
    Independently verifies the chain of custody for a given evidence item.

    The Verifier NEVER trusts any handler's self-reported status or declared
    hash_after value. Instead, it reads the actual_content_snapshot stored at
    each step and recomputes the hash itself — then checks whether the result
    matches what the previous step's content produced.

    For any step in NON_MUTATING_STEPS:
      - The content that came IN should be byte-for-byte identical to what came OUT.
      - If the recomputed hash of the step's output doesn't match the recomputed
        hash of the previous step's output, that step altered the evidence without
        authorization — regardless of what status_declared says.

    This is precisely how Export Tool gets caught: it reports 'success', but
    its actual_content_snapshot has different bytes than what went in, so the
    hashes don't match, and verified=False.
    """
    evidence = db.query(models.Evidence).filter(
        models.Evidence.id == evidence_id
    ).first()

    if not evidence:
        return {"error": "Evidence not found"}

    logs = (
        db.query(models.CustodyLog, models.Handler)
        .join(models.Handler, models.CustodyLog.handler_id == models.Handler.id)
        .filter(models.CustodyLog.evidence_id == evidence_id)
        .order_by(models.Handler.step_order)
        .all()
    )

    previous_content = evidence.original_content
    step_results = []
    broken_step_id = None
    final_verdict = "CHAIN_INTACT"
    chain_already_broken = False

    for log, handler in logs:
        # Independently recompute the hash of what this step actually produced
        actual_hash_now = compute_hash(log.actual_content_snapshot)

        if handler.name in NON_MUTATING_STEPS:
            # Compare what this step output vs what came into it
            expected_hash = compute_hash(previous_content)
            is_verified = (actual_hash_now == expected_hash)
        else:
            # Collector: trusted origin, always the baseline
            is_verified = True

        step_results.append({
            "step_order": handler.step_order,
            "handler_name": handler.name,
            "declared_status": log.status_declared,
            "hash_before": log.hash_before,
            "hash_after": log.hash_after,
            "actual_hash": actual_hash_now,
            "verified": is_verified,
            "downstream_of_break": chain_already_broken,
        })

        if not is_verified and broken_step_id is None:
            broken_step_id = handler.id
            final_verdict = (
                f"CHAIN_BROKEN_AT_STEP_{handler.step_order}_"
                f"{handler.name.replace(' ', '_').upper()}"
            )
            chain_already_broken = True

        previous_content = log.actual_content_snapshot

    # Persist verification result
    result = models.VerificationResult(
        evidence_id=evidence_id,
        final_verdict=final_verdict,
        broken_step_id=broken_step_id,
    )
    db.add(result)
    db.commit()

    return {
        "evidence_id": evidence_id,
        "evidence_name": evidence.name,
        "final_verdict": final_verdict,
        "broken_step_id": broken_step_id,
        "steps": step_results,
    }
