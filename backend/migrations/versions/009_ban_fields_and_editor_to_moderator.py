"""add ban fields to users and migrate editor role to moderator

Revision ID: 009_ban_editor_to_mod
Revises: 008_logs
Create Date: 2025-03-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "009_ban_editor_to_mod"
down_revision = "008_logs"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = inspect(conn)

    with op.batch_alter_table("users", schema=None) as batch_op:
        if not any(c["name"] == "is_banned" for c in insp.get_columns("users")):
            batch_op.add_column(
                sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            )
        if not any(c["name"] == "banned_at" for c in insp.get_columns("users")):
            batch_op.add_column(
                sa.Column("banned_at", sa.DateTime(timezone=True), nullable=True),
            )
        if not any(c["name"] == "ban_reason" for c in insp.get_columns("users")):
            batch_op.add_column(
                sa.Column("ban_reason", sa.String(length=512), nullable=True),
            )

    # Migrate users with editor role to moderator (editor role is being removed)
    op.execute(
        sa.text(
            "UPDATE users SET role_id = (SELECT id FROM roles WHERE name = 'moderator') "
            "WHERE role_id IN (SELECT id FROM roles WHERE name = 'editor')"
        )
    )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("ban_reason")
        batch_op.drop_column("banned_at")
        batch_op.drop_column("is_banned")
