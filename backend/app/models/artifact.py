import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Uuid, BigInteger, JSON, CheckConstraint, UniqueConstraint
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(Uuid(as_uuid=True), ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False, index=True)
    artifact_type = Column(String(50), nullable=False)  # ORIGINAL, FORENSIC_COPY, TRANSFORMED, EXPORT, ARCHIVE
    storage_provider = Column(String(50), default="MINIO", nullable=False)
    storage_bucket = Column(String(200), default="evidence-artifacts", nullable=False)
    storage_key = Column(Text, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(255), nullable=True)
    original_filename = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, QUARANTINED, RETAINED
    metadata_json = Column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="chk_artifact_size_positive"),
        CheckConstraint("length(sha256) = 64", name="chk_artifact_sha256_len"),
        UniqueConstraint("storage_provider", "storage_bucket", "storage_key", name="uq_artifacts_storage_location"),
    )
