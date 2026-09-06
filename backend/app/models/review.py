import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Uuid
from sqlalchemy.sql import func
from app.core.database import Base


class EvidenceReview(Base):
    __tablename__ = "evidence_reviews"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(Uuid(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    custody_step = Column(String(100), nullable=False)
    decision = Column(String(50), default="APPROVE", nullable=False)  # APPROVE, REJECT, REQUEST_CLARIFICATION
    notes = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# Backward compatibility alias
ReviewNote = EvidenceReview
