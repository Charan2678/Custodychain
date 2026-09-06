import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Uuid, BigInteger, JSON, CheckConstraint, UniqueConstraint
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class CustodyEvent(Base):
    __tablename__ = "custody_events"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(Uuid(as_uuid=True), ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False, index=True)
    sequence_number = Column(BigInteger, nullable=False)
    input_artifact_id = Column(Uuid(as_uuid=True), ForeignKey("artifacts.id", ondelete="RESTRICT"), nullable=True)
    output_artifact_id = Column(Uuid(as_uuid=True), ForeignKey("artifacts.id", ondelete="RESTRICT"), nullable=False)
    actor_id = Column(Uuid(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False)
    tool_id = Column(Uuid(as_uuid=True), ForeignKey("tools.id", ondelete="RESTRICT"), nullable=True)
    operation = Column(String(100), nullable=False)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    previous_event_hash = Column(String(64), nullable=True)
    event_hash = Column(String(64), nullable=False)
    actor_signature = Column(Text, nullable=True)
    tool_signature = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("evidence_id", "sequence_number", name="uq_custody_events_evidence_sequence"),
        CheckConstraint("length(event_hash) = 64", name="chk_custody_event_hash_len"),
    )
