"""Wiki: page (language-neutral) plus per-language translations."""
from datetime import datetime, timezone

from app.extensions import db
from app.i18n import TRANSLATION_STATUS_APPROVED


def _utc_now():
    return datetime.now(timezone.utc)


class WikiPage(db.Model):
    """Language-neutral wiki page. Content lives in WikiPageTranslation."""

    __tablename__ = "wiki_pages"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(128), unique=True, nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("wiki_pages.id", ondelete="SET NULL"), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_published = db.Column(db.Boolean, nullable=False, default=True)
    discussion_thread_id = db.Column(db.Integer, db.ForeignKey("forum_threads.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)

    translations = db.relationship(
        "WikiPageTranslation",
        backref="page",
        foreign_keys="WikiPageTranslation.page_id",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class WikiPageTranslation(db.Model):
    """Per-language translation of a wiki page."""

    __tablename__ = "wiki_page_translations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    page_id = db.Column(db.Integer, db.ForeignKey("wiki_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    language_code = db.Column(db.String(10), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False, index=True)
    content_markdown = db.Column(db.Text, nullable=False, default="")
    translation_status = db.Column(db.String(32), nullable=False, default=TRANSLATION_STATUS_APPROVED)
    source_language = db.Column(db.String(10), nullable=True)
    source_version = db.Column(db.String(64), nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("page_id", "language_code", name="uq_wiki_page_translation_page_lang"),
        db.UniqueConstraint("language_code", "slug", name="uq_wiki_page_translation_lang_slug"),
    )


class WikiPageForumThread(db.Model):
    """Explicit related forum threads for a wiki page."""

    __tablename__ = "wiki_page_forum_threads"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    page_id = db.Column(
        db.Integer,
        db.ForeignKey("wiki_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    thread_id = db.Column(
        db.Integer,
        db.ForeignKey("forum_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type = db.Column(db.String(32), nullable=False, default="related")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)

    __table_args__ = (
        db.UniqueConstraint("page_id", "thread_id", name="uq_wiki_page_forum_threads_page_thread"),
    )
