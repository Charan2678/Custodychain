import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Uuid, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="OPEN", nullable=False)  # DRAFT, OPEN, UNDER_INVESTIGATION, CLOSED, ARCHIVED
    created_by = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class CaseMember(Base):
    __tablename__ = "case_members"

    case_id = Column(Uuid(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    access_level = Column(String(50), default="EDITOR", nullable=False)  # OWNER, EDITOR, VIEWER, AUDITOR
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
