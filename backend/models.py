from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from database import Base


# ---------------------------------------------------------------------------
# Identity & RBAC Models
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(50), default="FORENSIC_ANALYST", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Case & Investigation Context Models
# ---------------------------------------------------------------------------
class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), default="OPEN", nullable=False)
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Evidence Artifacts (WORM Storage Mapping)
# ---------------------------------------------------------------------------
class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    parent_artifact_id = Column(Integer, ForeignKey("artifacts.id"), nullable=True)
    sequence = Column(Integer, default=0, nullable=False)
    storage_key = Column(String(255), nullable=False)
    sha256 = Column(String(64), nullable=False)
    size_bytes = Column(Integer, nullable=True)
    media_type = Column(String(100), default="text/plain", nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    @property
    def sha256_hash(self):
        return self.sha256


# ---------------------------------------------------------------------------
# Core Evidence Record
# ---------------------------------------------------------------------------
class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    exhibit_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    original_hash = Column(String(64), nullable=False)
    size_bytes = Column(Integer, default=0)
    original_content = Column(Text, nullable=False)
    status = Column(String(20), default="ACQUIRED", nullable=False)
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Cryptographic Custody Ledger (Hash-Chained & Ed25519 Signed)
# ---------------------------------------------------------------------------
class CustodyEvent(Base):
    __tablename__ = "custody_events"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    handler_name = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    input_artifact_id = Column(Integer, ForeignKey("artifacts.id"), nullable=True)
    output_artifact_id = Column(Integer, ForeignKey("artifacts.id"), nullable=True)
    hash_before = Column(String(64), nullable=False)
    hash_after = Column(String(64), nullable=False)
    declared_status = Column(String(20), default="success", nullable=False)
    verification_status = Column(String(20), default="UNVERIFIED", nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    previous_event_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False)
    signature = Column(Text, nullable=False)
    public_key = Column(Text, nullable=False)


# ---------------------------------------------------------------------------
# System Audit Trail (Cryptographic Hash Chained)
# ---------------------------------------------------------------------------
class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(100), default="Charan", nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    previous_event_hash = Column(String(64), nullable=True)
    event_hash = Column(String(64), nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Handlers & Legacy compatibility models
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
    broken_step_order = Column(Integer, nullable=True)
    broken_handler_id = Column(Integer, ForeignKey("handlers.id"), nullable=True)
    broken_step_id = Column(Integer, ForeignKey("handlers.id"), nullable=True)
    checked_at = Column(DateTime, server_default=func.now())
