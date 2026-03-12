"""Add last_seen_at and created_at to users for real active-user and growth metrics.

Revision ID: 014_last_seen
Revises: 013_wiki_slug
Create Date: 2025-03-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "014_last_seen"
down_revision = "013_wiki_slug"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = inspect(conn)
    cols = {c["name"] for c in insp.get_columns("users")}
    if "last_seen_at" not in cols:
        op.add_column(
            "users",
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "created_at" not in cols:
        op.add_column(
            "users",
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
        conn.execute(sa.text("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
    else:
        conn.execute(sa.text("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))


def downgrade():
    conn = op.get_bind()
    insp = inspect(conn)
    cols = {c["name"] for c in insp.get_columns("users")}
    if "created_at" in cols:
        op.drop_column("users", "created_at")
    if "last_seen_at" in cols:
        op.drop_column("users", "last_seen_at")
