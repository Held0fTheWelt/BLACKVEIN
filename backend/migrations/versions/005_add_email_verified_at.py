"""add email_verified_at to users (0.0.7)

Revision ID: 005_email_verified
Revises: 004_role
Create Date: 2025-03-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "005_email_verified"
down_revision = "004_role"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if any(c["name"] == "email_verified_at" for c in inspect(conn).get_columns("users")):
        return
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("users", "email_verified_at")
