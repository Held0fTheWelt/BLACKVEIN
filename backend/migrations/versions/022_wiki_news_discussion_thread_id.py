"""Add discussion_thread_id to wiki_pages and news_articles.

Revision ID: 022_wiki_news_discussion_thread_id
Revises: 021_forum_models
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa


revision = "022_wiki_news_discussion_thread_id"
down_revision = "021_forum_models"
branch_labels = None
depends_on = None


def _has_column(inspector, table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns(table))


def _has_index(inspector, table: str, index: str) -> bool:
    return any(i["name"] == index for i in inspector.get_indexes(table))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "wiki_pages", "discussion_thread_id"):
        op.add_column(
            "wiki_pages",
            sa.Column(
                "discussion_thread_id",
                sa.Integer(),
                sa.ForeignKey("forum_threads.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        if not _has_index(inspector, "wiki_pages", "ix_wiki_pages_discussion_thread_id"):
            op.create_index(
                "ix_wiki_pages_discussion_thread_id",
                "wiki_pages",
                ["discussion_thread_id"],
                unique=False,
            )

    if not _has_column(inspector, "news_articles", "discussion_thread_id"):
        op.add_column(
            "news_articles",
            sa.Column(
                "discussion_thread_id",
                sa.Integer(),
                sa.ForeignKey("forum_threads.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        if not _has_index(inspector, "news_articles", "ix_news_articles_discussion_thread_id"):
            op.create_index(
                "ix_news_articles_discussion_thread_id",
                "news_articles",
                ["discussion_thread_id"],
                unique=False,
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_index(inspector, "news_articles", "ix_news_articles_discussion_thread_id"):
        op.drop_index("ix_news_articles_discussion_thread_id", table_name="news_articles")
    if _has_column(inspector, "news_articles", "discussion_thread_id"):
        op.drop_column("news_articles", "discussion_thread_id")

    if _has_index(inspector, "wiki_pages", "ix_wiki_pages_discussion_thread_id"):
        op.drop_index("ix_wiki_pages_discussion_thread_id", table_name="wiki_pages")
    if _has_column(inspector, "wiki_pages", "discussion_thread_id"):
        op.drop_column("wiki_pages", "discussion_thread_id")
