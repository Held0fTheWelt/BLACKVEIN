"""Slogans table for managed site copy (landing teaser, hero, promo, ad slots).

Revision ID: 015_slogans
Revises: 014_last_seen
Create Date: 2025-03-11

"""
from alembic import op
import sqlalchemy as sa

revision = "015_slogans"
down_revision = "014_last_seen"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "slogans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("placement_key", sa.String(length=128), nullable=False),
        sa.Column("language_code", sa.String(length=10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("slogans")
