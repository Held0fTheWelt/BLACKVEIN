"""add preferred_language to users

Revision ID: 010_preferred_lang
Revises: 009_ban_editor_to_mod
Create Date: 2025-03-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "010_preferred_lang"
down_revision = "009_ban_editor_to_mod"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = inspect(conn)
    if not any(c["name"] == "preferred_language" for c in insp.get_columns("users")):
        op.add_column(
            "users",
            sa.Column("preferred_language", sa.String(length=10), nullable=True),
        )


def downgrade():
    op.drop_column("users", "preferred_language")
