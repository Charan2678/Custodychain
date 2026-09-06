import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Uuid, JSON, Text
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class Actor(Base):
    __tablename__ = "actors"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_type = Column(String(50), nullable=False)  # HUMAN, SERVICE, EXTERNAL_SYSTEM, AUTOMATED_PROCESS
    name = Column(String(300), nullable=False)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    public_key = Column(Text, nullable=True)  # Ed25519 Public Key (Base64)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_json = Column(JSON, nullable=True)
