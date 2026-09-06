import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, JSON, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class Tool(Base):
    __tablename__ = "tools"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False)
    vendor = Column(String(300), nullable=True)
    version = Column(String(100), nullable=False)
    tool_type = Column(String(100), nullable=False)  # INTAKE, PARSER, NORMALIZER, EXPORTER, ARCHIVER
    public_key = Column(Text, nullable=True)  # Ed25519 Public Key (Base64)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    registered_by = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_tools_name_version"),
    )
