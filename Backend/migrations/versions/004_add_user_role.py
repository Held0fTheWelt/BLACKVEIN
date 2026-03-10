"""add user role for news permissions

Revision ID: 004_role
Revises: 003_news
Create Date: 2025-03-10

"""
from alembic import op
import sqlalchemy as sa

revision = "004_role"
down_revision = "003_news"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="editor"),
    )


def downgrade():
    op.drop_column("users", "role")
