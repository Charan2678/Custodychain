import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Uuid, JSON
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class VerificationFinding(Base):
    __tablename__ = "verification_findings"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verification_run_id = Column(Uuid(as_uuid=True), ForeignKey("verification_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    custody_event_id = Column(Uuid(as_uuid=True), ForeignKey("custody_events.id", ondelete="SET NULL"), nullable=True)
    artifact_id = Column(Uuid(as_uuid=True), ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True)
    finding_type = Column(String(100), nullable=False)  # ARTIFACT_HASH_MISMATCH, SIGNATURE_INVALID, EVENT_HASH_MISMATCH, BROKEN_EVENT_LINK, DOWNSTREAM_AFFECTED, VALID
    severity = Column(String(50), nullable=False)  # CRITICAL, ERROR, WARNING, INFO
    expected_value = Column(Text, nullable=True)
    observed_value = Column(Text, nullable=True)
    message = Column(Text, nullable=False)
    is_first_break = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_json = Column(JSON, nullable=True)
