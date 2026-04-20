"""Add related forum threads tables for news and wiki.

Revision ID: 024_news_wiki_related_forum_threads
Revises: 023_notifications
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa


revision = "024_news_wiki_related_forum_threads"
down_revision = "023_notifications"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "news_article_forum_threads" not in existing_tables:
        op.create_table(
            "news_article_forum_threads",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "article_id",
                sa.Integer(),
                sa.ForeignKey("news_articles.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "thread_id",
                sa.Integer(),
                sa.ForeignKey("forum_threads.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("relation_type", sa.String(length=32), nullable=False, server_default="related"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_unique_constraint(
            "uq_news_article_forum_threads_article_thread",
            "news_article_forum_threads",
            ["article_id", "thread_id"],
        )
        op.create_index(
            "ix_news_article_forum_threads_article_id",
            "news_article_forum_threads",
            ["article_id"],
            unique=False,
        )
        op.create_index(
            "ix_news_article_forum_threads_thread_id",
            "news_article_forum_threads",
            ["thread_id"],
            unique=False,
        )

    if "wiki_page_forum_threads" not in existing_tables:
        op.create_table(
            "wiki_page_forum_threads",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "page_id",
                sa.Integer(),
                sa.ForeignKey("wiki_pages.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "thread_id",
                sa.Integer(),
                sa.ForeignKey("forum_threads.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("relation_type", sa.String(length=32), nullable=False, server_default="related"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_unique_constraint(
            "uq_wiki_page_forum_threads_page_thread",
            "wiki_page_forum_threads",
            ["page_id", "thread_id"],
        )
        op.create_index(
            "ix_wiki_page_forum_threads_page_id",
            "wiki_page_forum_threads",
            ["page_id"],
            unique=False,
        )
        op.create_index(
            "ix_wiki_page_forum_threads_thread_id",
            "wiki_page_forum_threads",
            ["thread_id"],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "wiki_page_forum_threads" in existing_tables:
        op.drop_index("ix_wiki_page_forum_threads_thread_id", table_name="wiki_page_forum_threads")
        op.drop_index("ix_wiki_page_forum_threads_page_id", table_name="wiki_page_forum_threads")
        op.drop_constraint("uq_wiki_page_forum_threads_page_thread", "wiki_page_forum_threads", type_="unique")
        op.drop_table("wiki_page_forum_threads")

    if "news_article_forum_threads" in existing_tables:
        op.drop_index("ix_news_article_forum_threads_thread_id", table_name="news_article_forum_threads")
        op.drop_index("ix_news_article_forum_threads_article_id", table_name="news_article_forum_threads")
        op.drop_constraint("uq_news_article_forum_threads_article_thread", "news_article_forum_threads", type_="unique")
        op.drop_table("news_article_forum_threads")

