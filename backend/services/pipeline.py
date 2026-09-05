from sqlalchemy.orm import Session
from utils.hashing import compute_hash
from services.handlers import HANDLER_PIPELINE
import models


def run_pipeline(db: Session, evidence_name: str, initial_content: str, simulate_tamper: bool = True) -> models.Evidence:
    """
    Runs the evidence through all 5 handlers in sequence.
    Creates one Evidence row and one CustodyLog row per handler step.
    Each log row stores the actual content snapshot after that step,
    which allows the Verifier to independently recompute hashes later
    without trusting any handler's self-reported hash_after value.
    """
    original_hash = compute_hash(initial_content)

    # Create the evidence record
    evidence = models.Evidence(
        name=evidence_name,
        original_content=initial_content,
        original_hash=original_hash,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    current_content = initial_content

    for step_order, handler_name, handler_fn in HANDLER_PIPELINE:
        handler_row = db.query(models.Handler).filter(
            models.Handler.step_order == step_order
        ).first()

        if handler_row is None:
            raise RuntimeError(
                f"Handler with step_order={step_order} not found in DB. "
                "Ensure handlers are seeded (run schema.sql or restart the app)."
            )

        hash_before = compute_hash(current_content)
        if handler_name == "Export Tool":
            new_content, declared_status = handler_fn(current_content, simulate_tamper)
        else:
            new_content, declared_status = handler_fn(current_content)
        hash_after = compute_hash(new_content)

        log_entry = models.CustodyLog(
            evidence_id=evidence.id,
            handler_id=handler_row.id,
            hash_before=hash_before,
            hash_after=hash_after,
            actual_content_snapshot=new_content,
            status_declared=declared_status,
        )
        db.add(log_entry)
        db.commit()

        current_content = new_content

    return evidence
