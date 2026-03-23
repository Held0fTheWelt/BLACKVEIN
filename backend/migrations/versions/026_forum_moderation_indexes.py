"""Add supporting indexes for forum moderation and search.

Revision ID: 026_forum_moderation_indexes
Revises: 025_forum_bookmarks_and_tags
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa


revision = "026_forum_moderation_indexes"
down_revision = "025_forum_bookmarks_and_tags"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("forum_reports")}

    # Index to support moderation dashboards listing open reports by created_at
    if "ix_forum_reports_status_created_at" not in existing_indexes:
        op.create_index(
            "ix_forum_reports_status_created_at",
            "forum_reports",
            ["status", "created_at"],
            unique=False,
        )

    existing_thread_indexes = {ix["name"] for ix in inspector.get_indexes("forum_threads")}

    # Index to support common thread listing/search ordering by category + pinned + last_post_at
    if "ix_forum_threads_category_pinned_last_post_at" not in existing_thread_indexes:
        op.create_index(
            "ix_forum_threads_category_pinned_last_post_at",
            "forum_threads",
            ["category_id", "is_pinned", "last_post_at"],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("forum_reports")}
    if "ix_forum_reports_status_created_at" in existing_indexes:
        op.drop_index("ix_forum_reports_status_created_at", table_name="forum_reports")

    existing_thread_indexes = {ix["name"] for ix in inspector.get_indexes("forum_threads")}
    if "ix_forum_threads_category_pinned_last_post_at" in existing_thread_indexes:
        op.drop_index("ix_forum_threads_category_pinned_last_post_at", table_name="forum_threads")

