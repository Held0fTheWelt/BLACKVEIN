"""Add resolution_note column to forum_reports.

Revision ID: 027_forum_report_resolution_note
Revises: 026_forum_moderation_indexes
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa


revision = "027_forum_report_resolution_note"
down_revision = "026_forum_moderation_indexes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "forum_reports",
        sa.Column("resolution_note", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column("forum_reports", "resolution_note")
