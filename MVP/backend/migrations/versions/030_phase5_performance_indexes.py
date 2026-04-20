"""Phase 5: Add comprehensive performance indexes for search, pagination, and profile queries.

Revision ID: 030
Revises: 029_phase3_moderation_enhancements
Create Date: 2026-03-14

Indexes added:
1. forum_threads(category_id, status, created_at) - for category listing with visibility filtering
2. forum_threads(status, is_pinned, last_post_at) - for search/listing ordering
3. forum_tags(slug) - for tag lookup (already indexed but explicit)
4. forum_thread_tags(thread_id, tag_id) - for tag suggestions and batch operations
5. forum_thread_bookmarks(user_id, created_at) - for bookmark pagination
6. activity_log(category, action, created_at) - for moderation activity history

"""
from alembic import op
import sqlalchemy as sa


revision = "030"
down_revision = "029_phase3_moderation_enhancements"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # -- forum_threads indexes --
    existing_thread_indexes = {
        ix["name"] for ix in inspector.get_indexes("forum_threads")
    }

    # Composite index for category listing with visibility filtering
    # WHERE category_id = ? AND status NOT IN (...)
    if "ix_forum_threads_category_status_created" not in existing_thread_indexes:
        op.create_index(
            "ix_forum_threads_category_status_created",
            "forum_threads",
            ["category_id", "status", "created_at"],
            unique=False,
        )

    # Composite index for search/listing ordering
    # WHERE status != ? ORDER BY is_pinned DESC, last_post_at DESC
    if "ix_forum_threads_status_pinned_last_post" not in existing_thread_indexes:
        op.create_index(
            "ix_forum_threads_status_pinned_last_post",
            "forum_threads",
            ["status", "is_pinned", "last_post_at"],
            unique=False,
        )

    # -- forum_tags indexes --
    existing_tag_indexes = {
        ix["name"] for ix in inspector.get_indexes("forum_tags")
    }
    # Note: slug is already indexed in the model definition, but explicit here for clarity
    if "ix_forum_tags_slug" not in existing_tag_indexes:
        op.create_index(
            "ix_forum_tags_slug",
            "forum_tags",
            ["slug"],
            unique=True,
        )

    # -- forum_thread_tags indexes --
    existing_thread_tag_indexes = {
        ix["name"] for ix in inspector.get_indexes("forum_thread_tags")
    }
    # Composite index for tag suggestions: find threads with multiple matching tags
    if "ix_forum_thread_tags_thread_tag" not in existing_thread_tag_indexes:
        op.create_index(
            "ix_forum_thread_tags_thread_tag",
            "forum_thread_tags",
            ["thread_id", "tag_id"],
            unique=False,
        )

    # -- forum_thread_bookmarks indexes --
    existing_bookmark_indexes = {
        ix["name"] for ix in inspector.get_indexes("forum_thread_bookmarks")
    }
    # Pagination: ORDER BY created_at DESC
    if "ix_forum_thread_bookmarks_user_created" not in existing_bookmark_indexes:
        op.create_index(
            "ix_forum_thread_bookmarks_user_created",
            "forum_thread_bookmarks",
            ["user_id", "created_at"],
            unique=False,
        )

    # -- activity_logs indexes --
    if inspector.has_table("activity_logs"):
        existing_activity_indexes = {
            ix["name"] for ix in inspector.get_indexes("activity_logs")
        }
        # Moderation activity history: WHERE category = ? AND action = ? ORDER BY created_at DESC
        if "ix_activity_logs_category_action_created" not in existing_activity_indexes:
            op.create_index(
                "ix_activity_logs_category_action_created",
                "activity_logs",
                ["category", "action", "created_at"],
                unique=False,
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Drop activity_logs index
    if inspector.has_table("activity_logs"):
        existing_activity_indexes = {
            ix["name"] for ix in inspector.get_indexes("activity_logs")
        }
        if "ix_activity_logs_category_action_created" in existing_activity_indexes:
            op.drop_index("ix_activity_logs_category_action_created", table_name="activity_logs")

    # Drop forum_thread_bookmarks index
    existing_bookmark_indexes = {
        ix["name"] for ix in inspector.get_indexes("forum_thread_bookmarks")
    }
    if "ix_forum_thread_bookmarks_user_created" in existing_bookmark_indexes:
        op.drop_index("ix_forum_thread_bookmarks_user_created", table_name="forum_thread_bookmarks")

    # Drop forum_thread_tags index
    existing_thread_tag_indexes = {
        ix["name"] for ix in inspector.get_indexes("forum_thread_tags")
    }
    if "ix_forum_thread_tags_thread_tag" in existing_thread_tag_indexes:
        op.drop_index("ix_forum_thread_tags_thread_tag", table_name="forum_thread_tags")

    # Drop forum_threads indexes
    existing_thread_indexes = {
        ix["name"] for ix in inspector.get_indexes("forum_threads")
    }
    if "ix_forum_threads_status_pinned_last_post" in existing_thread_indexes:
        op.drop_index("ix_forum_threads_status_pinned_last_post", table_name="forum_threads")
    if "ix_forum_threads_category_status_created" in existing_thread_indexes:
        op.drop_index("ix_forum_threads_category_status_created", table_name="forum_threads")
