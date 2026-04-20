"""Add notifications table for user notification events.

Revision ID: 023_notifications
Revises: 022_wiki_news_discussion_thread_id
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa


revision = "023_notifications"
down_revision = "022_wiki_news_discussion_thread_id"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "notifications" not in existing_tables:
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("target_type", sa.String(length=32), nullable=False),
            sa.Column("target_id", sa.Integer(), nullable=False),
            sa.Column("message", sa.String(length=512), nullable=False),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
        op.create_index("ix_notifications_event_type", "notifications", ["event_type"], unique=False)
        op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "notifications" in existing_tables:
        op.drop_index("ix_notifications_created_at", table_name="notifications")
        op.drop_index("ix_notifications_event_type", table_name="notifications")
        op.drop_index("ix_notifications_user_id", table_name="notifications")
        op.drop_table("notifications")
