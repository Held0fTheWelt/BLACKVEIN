"""Phase 3: Add moderation enhancements (priority, escalation reason, assigned_to, escalated_at).

Revision ID: 029_phase3_moderation_enhancements
Revises: 028_forum_performance_indexes
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa


revision = "029_phase3_moderation_enhancements"
down_revision = "028_forum_performance_indexes"
branch_labels = None
depends_on = None


def upgrade():
    """Add non-breaking columns to forum_reports."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Get existing columns
    columns = {col["name"] for col in inspector.get_columns("forum_reports")}
    existing_indexes = {
        ix["name"] for ix in inspector.get_indexes("forum_reports")
    }

    with op.batch_alter_table("forum_reports", schema=None) as batch_op:
        # Add priority (enum: low, normal, high, critical) with default 'normal'
        if "priority" not in columns:
            batch_op.add_column(
                sa.Column(
                    "priority",
                    sa.String(16),
                    nullable=False,
                    server_default="normal"
                ),
            )

        # Add escalation_reason (text field)
        if "escalation_reason" not in columns:
            batch_op.add_column(
                sa.Column("escalation_reason", sa.Text, nullable=True),
            )

        # Add assigned_to (FK to users, nullable)
        if "assigned_to" not in columns:
            batch_op.add_column(
                sa.Column(
                    "assigned_to",
                    sa.Integer,
                    nullable=True,
                ),
            )

        # Add escalated_at (timestamp)
        if "escalated_at" not in columns:
            batch_op.add_column(
                sa.Column(
                    "escalated_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                ),
            )

        # Add index on assigned_to for quick lookup of reports assigned to a moderator
        if "ix_forum_reports_assigned_to" not in existing_indexes:
            batch_op.create_index(
                "ix_forum_reports_assigned_to",
                ["assigned_to"],
                unique=False,
            )

        # Add index on priority + escalated_at for escalation queue queries
        if "ix_forum_reports_priority_escalated" not in existing_indexes:
            batch_op.create_index(
                "ix_forum_reports_priority_escalated",
                ["priority", "escalated_at"],
                unique=False,
            )

        # Add index on status + created_at for review queue queries
        if "ix_forum_reports_status_created" not in existing_indexes:
            batch_op.create_index(
                "ix_forum_reports_status_created",
                ["status", "created_at"],
                unique=False,
            )


def downgrade():
    """Remove Phase 3 moderation enhancement columns."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Get existing columns and indexes
    existing_indexes = {
        ix["name"] for ix in inspector.get_indexes("forum_reports")
    }
    columns = {col["name"] for col in inspector.get_columns("forum_reports")}

    with op.batch_alter_table("forum_reports", schema=None) as batch_op:
        # Drop indexes
        if "ix_forum_reports_status_created" in existing_indexes:
            batch_op.drop_index("ix_forum_reports_status_created")
        if "ix_forum_reports_priority_escalated" in existing_indexes:
            batch_op.drop_index("ix_forum_reports_priority_escalated")
        if "ix_forum_reports_assigned_to" in existing_indexes:
            batch_op.drop_index("ix_forum_reports_assigned_to")

        # Drop columns
        if "escalated_at" in columns:
            batch_op.drop_column("escalated_at")
        if "assigned_to" in columns:
            batch_op.drop_column("assigned_to")
        if "escalation_reason" in columns:
            batch_op.drop_column("escalation_reason")
        if "priority" in columns:
            batch_op.drop_column("priority")
