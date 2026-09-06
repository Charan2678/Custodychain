"""Initial Core Schema

Revision ID: 001_initial_core_schema
Revises: 
Create Date: 2026-09-05 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial_core_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="FORENSIC_ANALYST"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("display_name <> ''", name="chk_user_display_name_not_empty"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. cases
    op.create_table(
        "cases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("case_number", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="OPEN"),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_cases_case_number", "cases", ["case_number"], unique=True)

    # 3. evidence
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_number", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACQUIRED"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("case_id", "evidence_number", name="uq_evidence_case_number"),
    )
    op.create_index("ix_evidence_case_id", "evidence", ["case_id"])

    # 4. artifacts
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("evidence_id", sa.Uuid(), sa.ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("artifact_type", sa.String(length=50), nullable=False),
        sa.Column("storage_provider", sa.String(length=50), nullable=False, server_default="MINIO"),
        sa.Column("storage_bucket", sa.String(length=200), nullable=False, server_default="evidence-artifacts"),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("original_filename", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACTIVE"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.CheckConstraint("size_bytes >= 0", name="chk_artifact_size_positive"),
        sa.CheckConstraint("length(sha256) = 64", name="chk_artifact_sha256_len"),
        sa.UniqueConstraint("storage_provider", "storage_bucket", "storage_key", name="uq_artifacts_storage_location"),
    )
    op.create_index("ix_artifacts_evidence_id", "artifacts", ["evidence_id"])
    op.create_index("ix_artifacts_sha256", "artifacts", ["sha256"])

    # 5. actors
    op.create_table(
        "actors",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )

    # 6. tools
    op.create_table(
        "tools",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("vendor", sa.String(length=300), nullable=True),
        sa.Column("version", sa.String(length=100), nullable=False),
        sa.Column("tool_type", sa.String(length=100), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("registered_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.UniqueConstraint("name", "version", name="uq_tools_name_version"),
    )

    # 7. custody_events
    op.create_table(
        "custody_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("evidence_id", sa.Uuid(), sa.ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sequence_number", sa.BigInteger(), nullable=False),
        sa.Column("input_artifact_id", sa.Uuid(), sa.ForeignKey("artifacts.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("output_artifact_id", sa.Uuid(), sa.ForeignKey("artifacts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tool_id", sa.Uuid(), sa.ForeignKey("tools.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("previous_event_hash", sa.String(length=64), nullable=True),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("actor_signature", sa.Text(), nullable=True),
        sa.Column("tool_signature", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("evidence_id", "sequence_number", name="uq_custody_events_evidence_sequence"),
        sa.CheckConstraint("length(event_hash) = 64", name="chk_custody_event_hash_len"),
    )
    op.create_index("ix_custody_events_evidence_id", "custody_events", ["evidence_id"])

    # 8. verification_runs
    op.create_table(
        "verification_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("evidence_id", sa.Uuid(), sa.ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requested_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="RUNNING"),
        sa.Column("verdict", sa.String(length=50), nullable=True),
        sa.Column("first_break_event_id", sa.Uuid(), sa.ForeignKey("custody_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("verification_version", sa.String(length=50), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_verification_runs_evidence_id", "verification_runs", ["evidence_id"])

    # 9. provenance_relations
    op.create_table(
        "provenance_relations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("parent_artifact_id", sa.Uuid(), sa.ForeignKey("artifacts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("child_artifact_id", sa.Uuid(), sa.ForeignKey("artifacts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("custody_event_id", sa.Uuid(), sa.ForeignKey("custody_events.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("relationship_type", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.CheckConstraint("parent_artifact_id <> child_artifact_id", name="chk_provenance_distinct_artifacts"),
        sa.UniqueConstraint("parent_artifact_id", "child_artifact_id", "custody_event_id", name="uq_provenance_relation"),
    )
    op.create_index("ix_provenance_parent", "provenance_relations", ["parent_artifact_id"])
    op.create_index("ix_provenance_child", "provenance_relations", ["child_artifact_id"])
    op.create_index("ix_provenance_event", "provenance_relations", ["custody_event_id"])

    # 10. verification_findings
    op.create_table(
        "verification_findings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("verification_run_id", sa.Uuid(), sa.ForeignKey("verification_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("custody_event_id", sa.Uuid(), sa.ForeignKey("custody_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("artifact_id", sa.Uuid(), sa.ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("finding_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("expected_value", sa.Text(), nullable=True),
        sa.Column("observed_value", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_first_break", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_findings_run_id", "verification_findings", ["verification_run_id"])

    # 11. audit_events
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("actors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence_id", sa.Uuid(), sa.ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("previous_event_hash", sa.String(length=64), nullable=True),
        sa.Column("event_hash", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])

    # 12. reports
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("verification_run_id", sa.Uuid(), sa.ForeignKey("verification_runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("report_type", sa.String(length=100), nullable=False, server_default="FORENSIC_CERTIFICATE"),
        sa.Column("storage_provider", sa.String(length=50), nullable=False, server_default="MINIO"),
        sa.Column("storage_bucket", sa.String(length=200), nullable=False, server_default="reports"),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("generated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_reports_verification_run_id", "reports", ["verification_run_id"])


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("audit_events")
    op.drop_table("verification_findings")
    op.drop_table("provenance_relations")
    op.drop_table("verification_runs")
    op.drop_table("custody_events")
    op.drop_table("tools")
    op.drop_table("actors")
    op.drop_table("artifacts")
    op.drop_table("evidence")
    op.drop_table("cases")
    op.drop_table("users")
