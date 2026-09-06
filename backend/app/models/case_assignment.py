import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, Index, text
from sqlalchemy.sql import func
from app.core.database import Base


class CaseAssignment(Base):
    __tablename__ = "case_assignments"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(Uuid(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_by = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    stage = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="ACTIVE")
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "uq_active_case_assignment_stage",
            "case_id",
            "stage",
            unique=True,
            sqlite_where=text("status = 'ACTIVE'"),
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )
