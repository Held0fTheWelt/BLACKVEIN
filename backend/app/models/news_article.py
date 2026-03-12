"""News article: language-neutral base entity plus per-language translations."""
from datetime import datetime, timezone

from app.extensions import db
from app.i18n import (
    TRANSLATION_STATUS_APPROVED,
    TRANSLATION_STATUS_PUBLISHED,
)


def _utc_now():
    return datetime.now(timezone.utc)


class NewsArticle(db.Model):
    """Language-neutral news article. Content lives in NewsArticleTranslation."""

    __tablename__ = "news_articles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="draft")
    default_language = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(64), nullable=True)
    cover_image = db.Column(db.String(512), nullable=True)
    discussion_thread_id = db.Column(db.Integer, db.ForeignKey("forum_threads.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)

    author = db.relationship("User", backref="news_articles", foreign_keys=[author_id])
    translations = db.relationship(
        "NewsArticleTranslation",
        backref="article",
        foreign_keys="NewsArticleTranslation.article_id",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class NewsArticleTranslation(db.Model):
    """Per-language translation of a news article."""

    __tablename__ = "news_article_translations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    article_id = db.Column(db.Integer, db.ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False, index=True)
    language_code = db.Column(db.String(10), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False, index=True)
    summary = db.Column(db.String(500), nullable=True)
    content = db.Column(db.Text, nullable=False)
    seo_title = db.Column(db.String(255), nullable=True)
    seo_description = db.Column(db.String(512), nullable=True)
    translation_status = db.Column(db.String(32), nullable=False, default=TRANSLATION_STATUS_APPROVED)
    source_language = db.Column(db.String(10), nullable=True)
    source_version = db.Column(db.String(64), nullable=True)
    translated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("article_id", "language_code", name="uq_news_article_translation_article_lang"),
        db.UniqueConstraint("language_code", "slug", name="uq_news_article_translation_lang_slug"),
    )
