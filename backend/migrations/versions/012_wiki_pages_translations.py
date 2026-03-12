"""wiki_pages + wiki_page_translations, seed from wiki.md

Revision ID: 012_wiki_pages
Revises: 011_news_articles
Create Date: 2025-03-11

"""
import os
from pathlib import Path

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "012_wiki_pages"
down_revision = "011_news_articles"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = inspect(conn)

    if not insp.has_table("wiki_pages"):
        op.create_table(
            "wiki_pages",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("key", sa.String(length=128), nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["parent_id"], ["wiki_pages.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("key", name="uq_wiki_pages_key"),
        )
        op.create_index("ix_wiki_pages_key", "wiki_pages", ["key"])

    if not insp.has_table("wiki_page_translations"):
        op.create_table(
            "wiki_page_translations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("page_id", sa.Integer(), nullable=False),
            sa.Column("language_code", sa.String(length=10), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=255), nullable=False),
            sa.Column("content_markdown", sa.Text(), nullable=False),
            sa.Column("translation_status", sa.String(length=32), nullable=False, server_default="approved"),
            sa.Column("source_language", sa.String(length=10), nullable=True),
            sa.Column("source_version", sa.String(length=64), nullable=True),
            sa.Column("reviewed_by", sa.Integer(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["page_id"], ["wiki_pages.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("page_id", "language_code", name="uq_wiki_page_translation_page_lang"),
        )
        op.create_index("ix_wiki_page_translations_page_id", "wiki_page_translations", ["page_id"])
        op.create_index("ix_wiki_page_translations_language_code", "wiki_page_translations", ["language_code"])
        op.create_index("ix_wiki_page_translations_slug", "wiki_page_translations", ["slug"])

    # Seed one page from Backend/content/wiki.md if it exists (idempotent)
    result = conn.execute(sa.text("SELECT id FROM wiki_pages WHERE key = 'index'"))
    if result.fetchone() is not None:
        return

    backend_root = Path(__file__).resolve().parent.parent.parent
    wiki_path = backend_root / "content" / "wiki.md"
    content_md = ""
    if wiki_path.is_file():
        try:
            content_md = wiki_path.read_text(encoding="utf-8")
        except OSError:
            pass
    title = "World of Shadows – Wiki"
    if content_md.startswith("# "):
        first_line = content_md.split("\n")[0]
        title = first_line[2:].strip() or title

    conn.execute(sa.text("""
        INSERT INTO wiki_pages (key, sort_order, is_published, created_at, updated_at)
        VALUES ('index', 0, 1, datetime('now'), datetime('now'))
    """))
    result = conn.execute(sa.text("SELECT id FROM wiki_pages WHERE key = 'index'"))
    row = result.fetchone()
    page_id = row[0] if row else 1
    conn.execute(
        sa.text("""
            INSERT INTO wiki_page_translations (page_id, language_code, title, slug, content_markdown, translation_status, source_language)
            VALUES (:page_id, 'de', :title, 'wiki', :content, 'published', 'de')
        """),
        {"page_id": page_id, "title": title, "content": content_md},
    )


def downgrade():
    op.drop_table("wiki_page_translations")
    op.drop_table("wiki_pages")
