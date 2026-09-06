import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Uuid, BigInteger, JSON
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verification_run_id = Column(Uuid(as_uuid=True), ForeignKey("verification_runs.id", ondelete="RESTRICT"), nullable=False, index=True)
    report_type = Column(String(100), default="FORENSIC_CERTIFICATE", nullable=False)
    storage_provider = Column(String(50), default="MINIO", nullable=False)
    storage_bucket = Column(String(200), default="reports", nullable=False)
    storage_key = Column(Text, nullable=False)
    sha256 = Column(String(64), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    generated_by = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_json = Column(JSON, nullable=True)
