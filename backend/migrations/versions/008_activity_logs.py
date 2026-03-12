"""activity_logs table for structured admin activity log

Revision ID: 008_logs
Revises: 007_roles
Create Date: 2025-03-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "008_logs"
down_revision = "007_roles"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if inspect(conn).has_table("activity_logs"):
        return
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_username_snapshot", sa.String(length=80), nullable=True),
        sa.Column("actor_role_snapshot", sa.String(length=20), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="info"),
        sa.Column("message", sa.String(length=512), nullable=True),
        sa.Column("route", sa.String(length=256), nullable=True),
        sa.Column("method", sa.String(length=10), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activity_logs_category"), "activity_logs", ["category"], unique=False)
    op.create_index(op.f("ix_activity_logs_action"), "activity_logs", ["action"], unique=False)
    op.create_index(op.f("ix_activity_logs_created_at"), "activity_logs", ["created_at"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_activity_logs_created_at"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_action"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_category"), table_name="activity_logs")
    op.drop_table("activity_logs")
