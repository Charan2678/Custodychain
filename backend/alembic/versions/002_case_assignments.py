"""Add explicit case workflow assignments.

Revision ID: 002_case_assignments
Revises: 001_initial_core_schema
"""
from alembic import op
import sqlalchemy as sa

revision = "002_case_assignments"
down_revision = "001_initial_core_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_case_assignments_case_id", "case_assignments", ["case_id"])
    op.create_index("ix_case_assignments_user_id", "case_assignments", ["user_id"])
    op.create_index(
        "uq_active_case_assignment_stage",
        "case_assignments",
        ["case_id", "stage"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        sqlite_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index("uq_active_case_assignment_stage", table_name="case_assignments")
    op.drop_index("ix_case_assignments_user_id", table_name="case_assignments")
    op.drop_index("ix_case_assignments_case_id", table_name="case_assignments")
    op.drop_table("case_assignments")
