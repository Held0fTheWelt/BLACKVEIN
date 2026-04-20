"""Add feature_areas table for feature/view-to-area access mapping.

Revision ID: 020_feature_areas
Revises: 019_areas
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa

revision = "020_feature_areas"
down_revision = "019_areas"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "feature_areas",
        sa.Column("feature_id", sa.String(length=128), nullable=False),
        sa.Column("area_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["areas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("feature_id", "area_id"),
    )


def downgrade():
    op.drop_table("feature_areas")
