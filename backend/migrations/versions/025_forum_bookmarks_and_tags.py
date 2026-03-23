"""Add forum thread bookmarks and tags.

Revision ID: 025_forum_bookmarks_and_tags
Revises: 024_news_wiki_related_forum_threads
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa


revision = "025_forum_bookmarks_and_tags"
down_revision = "024_news_wiki_related_forum_threads"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "forum_thread_bookmarks" not in existing_tables:
        op.create_table(
            "forum_thread_bookmarks",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "thread_id",
                sa.Integer(),
                sa.ForeignKey("forum_threads.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        # SQLite can't ALTER TABLE to add constraints; use a unique index instead.
        op.create_index(
            "uq_forum_thread_bookmark_thread_user",
            "forum_thread_bookmarks",
            ["thread_id", "user_id"],
            unique=True,
        )
        op.create_index(
            "ix_forum_thread_bookmarks_user_id",
            "forum_thread_bookmarks",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            "ix_forum_thread_bookmarks_thread_id",
            "forum_thread_bookmarks",
            ["thread_id"],
            unique=False,
        )

    if "forum_tags" not in existing_tables:
        op.create_table(
            "forum_tags",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("slug", sa.String(length=64), nullable=False),
            sa.Column("label", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_forum_tags_slug",
            "forum_tags",
            ["slug"],
            unique=True,
        )

    if "forum_thread_tags" not in existing_tables:
        op.create_table(
            "forum_thread_tags",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "thread_id",
                sa.Integer(),
                sa.ForeignKey("forum_threads.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "tag_id",
                sa.Integer(),
                sa.ForeignKey("forum_tags.id", ondelete="CASCADE"),
                nullable=False,
            ),
        )
        # SQLite can't ALTER TABLE to add constraints; use a unique index instead.
        op.create_index(
            "uq_forum_thread_tags_thread_tag",
            "forum_thread_tags",
            ["thread_id", "tag_id"],
            unique=True,
        )
        op.create_index(
            "ix_forum_thread_tags_thread_id",
            "forum_thread_tags",
            ["thread_id"],
            unique=False,
        )
        op.create_index(
            "ix_forum_thread_tags_tag_id",
            "forum_thread_tags",
            ["tag_id"],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "forum_thread_tags" in existing_tables:
        op.drop_index("ix_forum_thread_tags_tag_id", table_name="forum_thread_tags")
        op.drop_index("ix_forum_thread_tags_thread_id", table_name="forum_thread_tags")
        op.drop_index("uq_forum_thread_tags_thread_tag", table_name="forum_thread_tags")
        op.drop_table("forum_thread_tags")

    if "forum_tags" in existing_tables:
        op.drop_index("ix_forum_tags_slug", table_name="forum_tags")
        op.drop_table("forum_tags")

    if "forum_thread_bookmarks" in existing_tables:
        op.drop_index("ix_forum_thread_bookmarks_thread_id", table_name="forum_thread_bookmarks")
        op.drop_index("ix_forum_thread_bookmarks_user_id", table_name="forum_thread_bookmarks")
        op.drop_index("uq_forum_thread_bookmark_thread_user", table_name="forum_thread_bookmarks")
        op.drop_table("forum_thread_bookmarks")

