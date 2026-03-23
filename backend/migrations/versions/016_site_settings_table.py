"""Site settings table for admin-editable options (slogan rotation, etc.).

Revision ID: 016_site_settings
Revises: 015_slogans
Create Date: 2025-03-11

"""
from alembic import op
import sqlalchemy as sa

revision = "016_site_settings"
down_revision = "015_slogans"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "site_settings",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade():
    op.drop_table("site_settings")
