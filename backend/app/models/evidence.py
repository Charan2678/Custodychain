import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Uuid, JSON, UniqueConstraint
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(Uuid(as_uuid=True), ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False, index=True)
    evidence_number = Column(String(100), nullable=False)
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="ACQUIRED", nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_by = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("case_id", "evidence_number", name="uq_evidence_case_number"),
    )
