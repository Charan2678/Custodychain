import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.case import Case
from app.models.evidence import Evidence
from app.models.artifact import Artifact
from app.models.actor import Actor
from app.models.tool import Tool
from app.models.custody_event import CustodyEvent
from app.models.provenance import ProvenanceRelation
from app.models.user import User
from app.infrastructure.storage.storage_service import storage, compute_bytes_hash
from app.core.config import settings
from app.infrastructure.cryptography.signatures import (
    GENESIS_HASH,
    build_canonical_event_string,
    compute_event_hash,
    sign_payload,
)
from app.services.assignment_service import active_assignment, require_current_handler, complete_stage, assign_stage
from app.infrastructure.cryptography.key_manager import key_manager
from app.services.handlers import HANDLER_PIPELINE
from app.services.verifier_service import run_independent_verification


def get_or_create_actor(db: Session, name: str, actor_type: str = "HUMAN", user_id: Optional[uuid.UUID] = None) -> Actor:
    actor = db.query(Actor).filter(Actor.name == name).first()
    if not actor:
        pub_key = key_manager.get_public_key(f"actor_{name}")
        actor = Actor(
            name=name,
            actor_type=actor_type,
            user_id=user_id,
            public_key=pub_key,
        )
        db.add(actor)
        db.commit()
        db.refresh(actor)
    return actor


def get_or_create_tool(db: Session, name: str, version: str, tool_type: str, registered_by: Optional[uuid.UUID] = None) -> Tool:
    tool = db.query(Tool).filter(Tool.name == name, Tool.version == version).first()
    if not tool:
        pub_key = key_manager.get_public_key(f"tool_{name}_{version}")
        tool = Tool(
            name=name,
            version=version,
            vendor="CustodyChain Core",
            tool_type=tool_type,
            public_key=pub_key,
            registered_by=registered_by,
        )
        db.add(tool)
        db.commit()
        db.refresh(tool)
    return tool


def intake_evidence(
    db: Session,
    case_id: uuid.UUID,
    name: str,
    raw_data: bytes,
    user: User,
    evidence_number: Optional[str] = None,
    description: Optional[str] = None,
    mime_type: str = "application/octet-stream",
    original_filename: Optional[str] = None,
) -> Evidence:
    """
    Step 1: Evidence Ingestion & Collector Handler Execution.
    1. Creates logical Evidence record (no raw data in DB).
    2. Stores raw original bitstream in MinIO/Object Storage as Artifact 0.
    3. Runs Step 1 Collector handler to produce Artifact 1.
    4. Records ProvenanceRelation and Ed25519-signed CustodyEvent #1.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    ev_number = evidence_number or f"EX-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    original_hash = compute_bytes_hash(raw_data)

    evidence = Evidence(
        case_id=case.id,
        evidence_number=ev_number,
        name=name,
        description=description or "Forensic evidence acquired at scene",
        status="IN_CUSTODY",
        created_by=user.id,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    # 1. Store Genesis Artifact (Raw Intake)
    genesis_key = f"evidence_{evidence.id}/artifact_0_original.bin"
    storage.put(genesis_key, raw_data)
    art_0 = Artifact(
        evidence_id=evidence.id,
        artifact_type="ORIGINAL",
        storage_provider=settings.STORAGE_PROVIDER.upper(),
        storage_bucket="evidence-artifacts",
        storage_key=genesis_key,
        sha256=original_hash,
        size_bytes=len(raw_data),
        mime_type=mime_type,
        original_filename=original_filename,
        created_by=user.id,
    )
    db.add(art_0)
    db.commit()
    db.refresh(art_0)

    # 2. Execute Step 1: Collector
    step_num, tool_name, tool_ver, tool_type, handler_fn = HANDLER_PIPELINE[0]
    actor = get_or_create_actor(db, name=user.display_name, actor_type="HUMAN", user_id=user.id)
    tool = get_or_create_tool(db, name=tool_name, version=tool_ver, tool_type=tool_type, registered_by=user.id)

    collector_bytes, _ = handler_fn(raw_data, False)
    collector_hash = compute_bytes_hash(collector_bytes)
    collector_key = f"evidence_{evidence.id}/artifact_1_collector.bin"
    storage.put(collector_key, collector_bytes)

    art_1 = Artifact(
        evidence_id=evidence.id,
        artifact_type="COLLECTOR_CONTAINER",
        storage_provider=settings.STORAGE_PROVIDER.upper(),
        storage_bucket="evidence-artifacts",
        storage_key=collector_key,
        sha256=collector_hash,
        size_bytes=len(collector_bytes),
        mime_type="application/octet-stream",
        created_by=user.id,
    )
    db.add(art_1)
    db.commit()
    db.refresh(art_1)

    # 3. Provenance Link
    prov = ProvenanceRelation(
        parent_artifact_id=art_0.id,
        child_artifact_id=art_1.id,
        custody_event_id=uuid.uuid4(),  # updated after event creation
        relationship_type="INGESTED_FROM",
    )

    # 4. Cryptographic Custody Event #1
    occurred_dt = datetime.now(timezone.utc).replace(microsecond=0)
    occurred_str = occurred_dt.strftime("%Y-%m-%d %H:%M:%S")
    operation = "Acquired by Evidence Collector"

    canonical_str = build_canonical_event_string(
        evidence_id=str(evidence.id),
        sequence_number=1,
        actor_id=str(actor.id),
        tool_id=str(tool.id),
        operation=operation,
        input_artifact_hash=art_0.sha256,
        output_artifact_hash=art_1.sha256,
        occurred_at_str=occurred_str,
        previous_event_hash=GENESIS_HASH,
    )
    event_hash = compute_event_hash(canonical_str, GENESIS_HASH)

    actor_priv = key_manager.get_private_key(f"actor_{actor.name}")
    tool_priv = key_manager.get_private_key(f"tool_{tool.name}_{tool.version}")

    actor_sig = sign_payload(actor_priv, canonical_str)
    tool_sig = sign_payload(tool_priv, canonical_str)

    ev_1 = CustodyEvent(
        evidence_id=evidence.id,
        sequence_number=1,
        input_artifact_id=art_0.id,
        output_artifact_id=art_1.id,
        actor_id=actor.id,
        tool_id=tool.id,
        operation=operation,
        occurred_at=occurred_dt,
        previous_event_hash=GENESIS_HASH,
        event_hash=event_hash,
        actor_signature=actor_sig,
        tool_signature=tool_sig,
    )
    db.add(ev_1)
    db.commit()
    db.refresh(ev_1)

    prov.custody_event_id = ev_1.id
    db.add(prov)
    from app.services.audit_service import record_audit_event
    record_audit_event(db, user=user, action="EVIDENCE_INTAKE", resource_type="EVIDENCE", resource_id=str(evidence.id), case_id=evidence.case_id, evidence_id=evidence.id, details={"evidence_number": evidence.evidence_number, "sha256": original_hash})
    db.commit()

    return evidence


def advance_custody_step(
    db: Session,
    evidence_id: uuid.UUID,
    user: User,
    simulate_tamper: bool = False,
) -> CustodyEvent:
    """
    Advances custody to the next step in the pipeline (Steps 2, 3, or 4).
    Enforces RBAC, reads artifact bytes from storage, executes tool handler,
    writes derived artifact, and cryptographically hash-chains the event.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    last_event = (
        db.query(CustodyEvent)
        .filter(CustodyEvent.evidence_id == evidence.id)
        .order_by(CustodyEvent.sequence_number.desc())
        .first()
    )
    current_seq = last_event.sequence_number if last_event else 0
    next_seq = current_seq + 1

    if next_seq > len(HANDLER_PIPELINE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evidence has reached final archive custody. No further transfers possible.",
        )

    # RBAC Enforcement — evidence is shared between all active investigation roles.
    # Auditors remain strictly read-only to preserve investigative neutrality.
    if user.role == "AUDITOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auditors have read-only clearance and cannot modify evidence custody.",
        )

    ALLOWED_TRANSFER_ROLES = ["EVIDENCE_OFFICER", "FORENSIC_ANALYST", "SYSTEM_ADMIN"]
    if user.role not in ALLOWED_TRANSFER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Custody transfer requires one of {ALLOWED_TRANSFER_ROLES}, your role is '{user.role}'.",
        )

    if current_seq >= 1:
        require_current_handler(db, user, evidence.case_id, "FORENSIC_ANALYST")

    step_num, tool_name, tool_ver, tool_type, handler_fn = HANDLER_PIPELINE[next_seq - 1]

    # Transfer is allowed only after an APPROVE review for the current custody step.
    from app.models.review import EvidenceReview
    current_review = (db.query(EvidenceReview)
        .filter(EvidenceReview.evidence_id == evidence.id,
                EvidenceReview.custody_step == f"Step {current_seq}")
        .order_by(EvidenceReview.created_at.desc())
        .first())
    if not current_review or current_review.decision != "APPROVE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Step {current_seq} must be reviewed and approved before transfer")

    # Retrieve input artifact
    input_art = db.query(Artifact).filter(Artifact.id == last_event.output_artifact_id).first()
    if not input_art or not storage.exists(input_art.storage_key):
        raise HTTPException(status_code=500, detail="Previous custody artifact missing from storage")

    input_bytes = storage.get(input_art.storage_key)

    # Execute tool handler
    output_bytes, _ = handler_fn(input_bytes, simulate_tamper=simulate_tamper)
    output_hash = compute_bytes_hash(output_bytes)

    clean_name = tool_name.lower().replace(" ", "_")
    output_key = f"evidence_{evidence.id}/artifact_{next_seq}_{clean_name}.bin"
    storage.put(output_key, output_bytes)

    output_art = Artifact(
        evidence_id=evidence.id,
        artifact_type=f"{tool_type}_CONTAINER",
        storage_provider=settings.STORAGE_PROVIDER.upper(),
        storage_bucket="evidence-artifacts",
        storage_key=output_key,
        sha256=output_hash,
        size_bytes=len(output_bytes),
        mime_type="application/octet-stream",
        created_by=user.id,
    )
    db.add(output_art)
    db.commit()
    db.refresh(output_art)

    actor = get_or_create_actor(db, name=user.display_name, actor_type="HUMAN", user_id=user.id)
    tool = get_or_create_tool(db, name=tool_name, version=tool_ver, tool_type=tool_type, registered_by=user.id)

    occurred_dt = datetime.now(timezone.utc).replace(microsecond=0)
    occurred_str = occurred_dt.strftime("%Y-%m-%d %H:%M:%S")
    operation = f"Processed by {tool.name}"

    canonical_str = build_canonical_event_string(
        evidence_id=str(evidence.id),
        sequence_number=next_seq,
        actor_id=str(actor.id),
        tool_id=str(tool.id),
        operation=operation,
        input_artifact_hash=input_art.sha256,
        output_artifact_hash=output_art.sha256,
        occurred_at_str=occurred_str,
        previous_event_hash=last_event.event_hash,
    )
    event_hash = compute_event_hash(canonical_str, last_event.event_hash)

    actor_priv = key_manager.get_private_key(f"actor_{actor.name}")
    tool_priv = key_manager.get_private_key(f"tool_{tool.name}_{tool.version}")

    actor_sig = sign_payload(actor_priv, canonical_str)
    tool_sig = sign_payload(tool_priv, canonical_str)

    new_event = CustodyEvent(
        evidence_id=evidence.id,
        sequence_number=next_seq,
        input_artifact_id=input_art.id,
        output_artifact_id=output_art.id,
        actor_id=actor.id,
        tool_id=tool.id,
        operation=operation,
        occurred_at=occurred_dt,
        previous_event_hash=last_event.event_hash,
        event_hash=event_hash,
        actor_signature=actor_sig,
        tool_signature=tool_sig,
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    prov = ProvenanceRelation(
        parent_artifact_id=input_art.id,
        child_artifact_id=output_art.id,
        custody_event_id=new_event.id,
        relationship_type="TRANSFORMED_BY",
    )
    db.add(prov)
    from app.services.audit_service import record_audit_event
    record_audit_event(db, user=user, action="CUSTODY_TRANSFERRED", resource_type="EVIDENCE", resource_id=str(evidence.id), case_id=evidence.case_id, evidence_id=evidence.id, details={"sequence_number": next_seq, "tool": tool.name, "event_hash": new_event.event_hash})

    db.commit()

    if next_seq == len(HANDLER_PIPELINE):
        complete_stage(db, evidence.case_id, "FORENSIC_ANALYST")
        auditor = (
            db.query(User)
            .filter(User.role == "AUDITOR", User.is_active.is_(True))
            .order_by(User.created_at.asc())
            .first()
        )
        if auditor:
            assign_stage(db, evidence.case_id, auditor, user, "AUDITOR")
        db.commit()

    return new_event


def run_full_pipeline_simulation(
    db: Session,
    case_id: uuid.UUID,
    name: str,
    content: str,
    user: User,
    tamper_step: int = 0,
) -> Dict[str, Any]:
    """
    Executes the full 4-stage pipeline demonstration deterministically.
    If tamper_step == 3: Exporter silently alters artifact bytes while claiming SUCCESS.
    Immediately runs independent verification and returns forensic results.
    """
    content_bytes = content.encode("utf-8")
    evidence = intake_evidence(
        db=db,
        case_id=case_id,
        name=name,
        raw_data=content_bytes,
        user=user,
        description="Automated forensic intake simulation stream",
    )

    # The standalone demo may be called directly by engine tests without an API-created assignment.
    if not active_assignment(db, case_id, "FORENSIC_ANALYST") and user.role == "FORENSIC_ANALYST":
        complete_stage(db, case_id, "EVIDENCE_OFFICER")
        assign_stage(db, case_id, user, user, "FORENSIC_ANALYST")
        db.commit()

    from app.models.review import EvidenceReview

    # Step 2: Normalizer
    db.add(EvidenceReview(evidence_id=evidence.id, reviewer_id=user.id, custody_step="Step 1", decision="APPROVE", notes="Approved for Normalization."))
    db.commit()
    advance_custody_step(db, evidence.id, user, simulate_tamper=(tamper_step == 2))

    # Step 3: Exporter (Silent tamper trigger)
    db.add(EvidenceReview(evidence_id=evidence.id, reviewer_id=user.id, custody_step="Step 2", decision="APPROVE", notes="Approved for Export Packaging."))
    db.commit()
    advance_custody_step(db, evidence.id, user, simulate_tamper=(tamper_step == 3))

    # Step 4: Archiver
    db.add(EvidenceReview(evidence_id=evidence.id, reviewer_id=user.id, custody_step="Step 3", decision="APPROVE", notes="Approved for Archive Vault Sealing."))
    db.commit()
    advance_custody_step(db, evidence.id, user, simulate_tamper=(tamper_step == 4))

    # Execute Independent Verification
    return run_independent_verification(db, evidence.id, requested_by_user_id=user.id)
