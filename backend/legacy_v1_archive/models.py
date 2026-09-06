from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from database import Base


# ---------------------------------------------------------------------------
# Identity & RBAC
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
# Case & Investigation Context
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
# Evidence Record
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
    status = Column(String(20), default="IN_CUSTODY", nullable=False)
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Artifact — one concrete file version per custody step
# Stored in MinIO/local under storage_key.
# sha256 = what the handler declared. Verifier recomputes independently.
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
# Custody Event — the cryptographic ledger (hash-chained, Ed25519 signed).
# Every step in the pipeline produces exactly one CustodyEvent.
# declared_status is NEVER trusted — verifier recomputes everything.
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
    timestamp = Column(DateTime, server_default=func.now())
    previous_event_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False)
    signature = Column(Text, nullable=False)
    public_key = Column(Text, nullable=False)


# ---------------------------------------------------------------------------
# Audit Trail — immutable, hash-chained system-level log
# ---------------------------------------------------------------------------
class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    previous_event_hash = Column(String(64), nullable=True)
    event_hash = Column(String(64), nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, server_default=func.now())
