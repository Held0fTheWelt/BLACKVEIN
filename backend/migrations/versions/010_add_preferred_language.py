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
        with op.batch_alter_table("users", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("preferred_language", sa.String(length=10), nullable=True),
            )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("preferred_language")
