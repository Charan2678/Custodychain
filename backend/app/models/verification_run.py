import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, JSON
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class VerificationRun(Base):
    __tablename__ = "verification_runs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(Uuid(as_uuid=True), ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False, index=True)
    requested_by = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="RUNNING", nullable=False)  # QUEUED, RUNNING, COMPLETED, FAILED
    verdict = Column(String(50), nullable=True)  # VALID, BROKEN, INCONCLUSIVE
    first_break_event_id = Column(Uuid(as_uuid=True), ForeignKey("custody_events.id", ondelete="SET NULL"), nullable=True)
    verification_version = Column(String(50), default="1.0", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_json = Column(JSON, nullable=True)
