"""News article model for the public news system."""
from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    return datetime.now(timezone.utc)


class News(db.Model):
    """A single news article. Slug is unique for stable URLs."""

    __tablename__ = "news"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)
    summary = db.Column(db.String(500), nullable=True)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )
    cover_image = db.Column(db.String(512), nullable=True)
    category = db.Column(db.String(64), nullable=True)

    author = db.relationship("User", backref="news_articles", foreign_keys=[author_id])

    def to_dict(self):
        """Serialize for API. Resolve author username when present."""
        out = {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "summary": self.summary,
            "content": self.content,
            "is_published": self.is_published,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "cover_image": self.cover_image,
            "category": self.category,
        }
        if self.author_id is not None:
            out["author_id"] = self.author_id
            out["author_name"] = self.author.username if self.author else None
        else:
            out["author_id"] = None
            out["author_name"] = None
        return out

    def __repr__(self):
        return f"<News id={self.id} slug={self.slug!r} title={self.title!r}>"
