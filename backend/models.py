from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from database import Base


# ---------------------------------------------------------------------------
# Core User & Identity
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(50), default="FORENSIC_ANALYST", nullable=False)
    # Roles: EVIDENCE_OFFICER, FORENSIC_ANALYST, AUDITOR, SYSTEM_ADMIN
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Investigation Cases
# ---------------------------------------------------------------------------
class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), default="OPEN", nullable=False)  # OPEN, CLOSED, ARCHIVED
    created_by = Column(String(100), default="Charan", nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Digital Evidence Root
# ---------------------------------------------------------------------------
class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True, index=True)
    exhibit_id = Column(String(50), nullable=True)  # e.g., EV-001, EXHIBIT-A
    name = Column(String(255), nullable=False)
    original_content = Column(Text, nullable=False)  # Legacy string preservation
    original_hash = Column(String(64), nullable=False)
    media_type = Column(String(100), default="text/plain")
    size_bytes = Column(Integer, default=0)
    status = Column(String(30), default="VERIFIED")  # PENDING, VERIFIED, BROKEN, ARCHIVED
    created_by = Column(String(100), default="Investigator")
    created_at = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Immutable Versioned Artifacts
# ---------------------------------------------------------------------------
class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False, index=True)
    parent_artifact_id = Column(Integer, ForeignKey("artifacts.id"), nullable=True)
    sequence = Column(Integer, nullable=False)
    storage_key = Column(String(255), nullable=False)
    sha256 = Column(String(64), nullable=False)
    size_bytes = Column(Integer, default=0)
    media_type = Column(String(100), default="text/plain")
    created_at = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Hash-Linked & Signed Custody Ledger
# ---------------------------------------------------------------------------
class CustodyEvent(Base):
    __tablename__ = "custody_events"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False, index=True)
    sequence_number = Column(Integer, nullable=False)
    handler_name = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    input_artifact_id = Column(Integer, nullable=True)
    output_artifact_id = Column(Integer, nullable=True)
    hash_before = Column(String(64), nullable=False)
    hash_after = Column(String(64), nullable=False)
    declared_status = Column(String(30), default="success")
    verification_status = Column(String(30), default="VERIFIED")  # VERIFIED, BROKEN, DOWNSTREAM
    timestamp = Column(DateTime, server_default=func.now())
    previous_event_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False)
    signature = Column(Text, nullable=False)
    public_key = Column(Text, nullable=False)


# ---------------------------------------------------------------------------
# System Audit Trail
# ---------------------------------------------------------------------------
class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(100), default="Charan", nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Legacy compatibility models
# ---------------------------------------------------------------------------
class Handler(Base):
    __tablename__ = "handlers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    step_order = Column(Integer, nullable=False)


class CustodyLog(Base):
    __tablename__ = "custody_log"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    handler_id = Column(Integer, ForeignKey("handlers.id"), nullable=False)
    hash_before = Column(String(64), nullable=False)
    hash_after = Column(String(64), nullable=False)
    actual_content_snapshot = Column(Text, nullable=False)
    status_declared = Column(String(20), default="success")
    timestamp = Column(DateTime, server_default=func.now())


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    final_verdict = Column(String(50), nullable=False)
    broken_step_id = Column(Integer, ForeignKey("handlers.id"), nullable=True)
    checked_at = Column(DateTime, server_default=func.now())
