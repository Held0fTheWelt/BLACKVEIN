"""Add performance indexes for common forum query patterns.

Revision ID: 028_forum_performance_indexes
Revises: 027_forum_report_resolution_note
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa


revision = "028_forum_performance_indexes"
down_revision = "027_forum_report_resolution_note"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # -- forum_posts indexes --
    existing_post_indexes = {
        ix["name"] for ix in inspector.get_indexes("forum_posts")
    }

    # Post visibility filtering (WHERE status = 'visible' etc.)
    if "ix_forum_posts_status" not in existing_post_indexes:
        op.create_index(
            "ix_forum_posts_status",
            "forum_posts",
            ["status"],
            unique=False,
        )

    # Post list within thread filtered by status (thread detail page)
    if "ix_forum_posts_thread_status" not in existing_post_indexes:
        op.create_index(
            "ix_forum_posts_thread_status",
            "forum_posts",
            ["thread_id", "status"],
            unique=False,
        )

    # -- forum_threads indexes --
    existing_thread_indexes = {
        ix["name"] for ix in inspector.get_indexes("forum_threads")
    }

    # Thread visibility filtering (WHERE status != 'deleted' etc.)
    if "ix_forum_threads_status" not in existing_thread_indexes:
        op.create_index(
            "ix_forum_threads_status",
            "forum_threads",
            ["status"],
            unique=False,
        )

    # -- notifications indexes --
    existing_notif_indexes = {
        ix["name"] for ix in inspector.get_indexes("notifications")
    }

    # Notification list with unread filter (WHERE user_id = ? AND is_read = ?)
    if "ix_notifications_user_is_read" not in existing_notif_indexes:
        op.create_index(
            "ix_notifications_user_is_read",
            "notifications",
            ["user_id", "is_read"],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_notif_indexes = {
        ix["name"] for ix in inspector.get_indexes("notifications")
    }
    if "ix_notifications_user_is_read" in existing_notif_indexes:
        op.drop_index("ix_notifications_user_is_read", table_name="notifications")

    existing_thread_indexes = {
        ix["name"] for ix in inspector.get_indexes("forum_threads")
    }
    if "ix_forum_threads_status" in existing_thread_indexes:
        op.drop_index("ix_forum_threads_status", table_name="forum_threads")

    existing_post_indexes = {
        ix["name"] for ix in inspector.get_indexes("forum_posts")
    }
    if "ix_forum_posts_thread_status" in existing_post_indexes:
        op.drop_index("ix_forum_posts_thread_status", table_name="forum_posts")
    if "ix_forum_posts_status" in existing_post_indexes:
        op.drop_index("ix_forum_posts_status", table_name="forum_posts")
