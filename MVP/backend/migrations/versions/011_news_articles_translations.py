"""news_articles + news_article_translations, migrate from news, drop news

Revision ID: 011_news_articles
Revises: 010_preferred_lang
Create Date: 2025-03-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "011_news_articles"
down_revision = "010_preferred_lang"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = inspect(conn)

    if not insp.has_table("news_articles"):
        op.create_table(
            "news_articles",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("author_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
            sa.Column("default_language", sa.String(length=10), nullable=False, server_default="de"),
            sa.Column("category", sa.String(length=64), nullable=True),
            sa.Column("cover_image", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not insp.has_table("news_article_translations"):
        op.create_table(
            "news_article_translations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("article_id", sa.Integer(), nullable=False),
            sa.Column("language_code", sa.String(length=10), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=255), nullable=False),
            sa.Column("summary", sa.String(length=500), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("seo_title", sa.String(length=255), nullable=True),
            sa.Column("seo_description", sa.String(length=512), nullable=True),
            sa.Column("translation_status", sa.String(length=32), nullable=False, server_default="approved"),
            sa.Column("source_language", sa.String(length=10), nullable=True),
            sa.Column("source_version", sa.String(length=64), nullable=True),
            sa.Column("translated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reviewed_by", sa.Integer(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["article_id"], ["news_articles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("article_id", "language_code", name="uq_news_article_translation_article_lang"),
            sa.UniqueConstraint("language_code", "slug", name="uq_news_article_translation_lang_slug"),
        )
        op.create_index("ix_news_article_translations_article_id", "news_article_translations", ["article_id"])
        op.create_index("ix_news_article_translations_language_code", "news_article_translations", ["language_code"])
        op.create_index("ix_news_article_translations_slug", "news_article_translations", ["slug"])

    if insp.has_table("news"):
        op.execute(sa.text("""
            INSERT INTO news_articles (id, author_id, status, default_language, category, cover_image, created_at, updated_at, published_at)
            SELECT id, author_id,
                   CASE WHEN is_published = 1 THEN 'published' ELSE 'draft' END,
                   'de', category, cover_image, created_at, updated_at, published_at
            FROM news
        """))
        op.execute(sa.text("""
            INSERT INTO news_article_translations (article_id, language_code, title, slug, summary, content, translation_status, source_language, translated_at)
            SELECT id, 'de', title, slug, summary, content,
                   CASE WHEN is_published = 1 THEN 'published' ELSE 'approved' END,
                   'de', updated_at
            FROM news
        """))
        op.drop_table("news")


def downgrade():
    op.drop_table("news_article_translations")
    op.drop_table("news_articles")
