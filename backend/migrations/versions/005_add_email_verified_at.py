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
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("email_verified_at")
