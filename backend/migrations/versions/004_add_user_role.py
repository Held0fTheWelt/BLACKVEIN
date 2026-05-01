"""add user role for news permissions

Revision ID: 004_role
Revises: 003_news
Create Date: 2025-03-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "004_role"
down_revision = "003_news"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if any(c["name"] == "role" for c in inspect(conn).get_columns("users")):
        return
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("role", sa.String(length=20), nullable=False, server_default="editor"),
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("role")
