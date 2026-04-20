"""initial users table

Revision ID: 001_initial
Revises:
Create Date: 2025-03-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if inspect(conn).has_table("users"):
        return  # table already exists (e.g. from init-db); skip
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )


def downgrade():
    op.drop_table("users")
