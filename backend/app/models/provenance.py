import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, JSON, CheckConstraint, UniqueConstraint
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class ProvenanceRelation(Base):
    __tablename__ = "provenance_relations"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_artifact_id = Column(Uuid(as_uuid=True), ForeignKey("artifacts.id", ondelete="RESTRICT"), nullable=False, index=True)
    child_artifact_id = Column(Uuid(as_uuid=True), ForeignKey("artifacts.id", ondelete="RESTRICT"), nullable=False, index=True)
    custody_event_id = Column(Uuid(as_uuid=True), ForeignKey("custody_events.id", ondelete="RESTRICT"), nullable=False, index=True)
    relationship_type = Column(String(100), nullable=False)  # COPIED_FROM, DERIVED_FROM, TRANSFORMED_FROM, EXPORTED_FROM
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_json = Column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint("parent_artifact_id <> child_artifact_id", name="chk_provenance_distinct_artifacts"),
        UniqueConstraint("parent_artifact_id", "child_artifact_id", "custody_event_id", name="uq_provenance_relation"),
    )
