import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Uuid, JSON
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(Uuid(as_uuid=True), ForeignKey("actors.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    case_id = Column(Uuid(as_uuid=True), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)
    evidence_id = Column(Uuid(as_uuid=True), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    previous_event_hash = Column(String(64), nullable=True)
    event_hash = Column(String(64), nullable=True)
    request_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    metadata_json = Column(JSON, nullable=True)
