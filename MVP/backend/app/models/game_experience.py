from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db


class GameExperienceTemplate(db.Model):
    """Shadow schema for unit tests only — not the production `game_experience_templates` table."""

    __tablename__ = "game_experience_template_shadow"

    STATUS_DRAFT = "draft"
    STATUS_REVIEW = "review"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"

    TYPE_SOLO = "solo_story"
    TYPE_GROUP = "group_story"
    TYPE_OPEN_WORLD = "open_world"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    experience_type = db.Column(db.String(32), nullable=False, default=TYPE_SOLO)
    summary = db.Column(db.Text, nullable=True)
    tags = db.Column(db.JSON, nullable=False, default=list)
    style_profile = db.Column(db.String(80), nullable=False, default="retro_pulp")
    status = db.Column(db.String(32), nullable=False, default=STATUS_DRAFT)
    current_version = db.Column(db.Integer, nullable=False, default=1)
    published_version = db.Column(db.Integer, nullable=True)
    draft_payload = db.Column(db.JSON, nullable=False, default=dict)
    published_payload = db.Column(db.JSON, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    published_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    published_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self, *, include_payload: bool = True, include_published_payload: bool = False) -> dict:
        data = {
            "id": self.id,
            "key": self.key,
            "title": self.title,
            "experience_type": self.experience_type,
            "summary": self.summary,
            "tags": list(self.tags or []),
            "style_profile": self.style_profile,
            "status": self.status,
            "current_version": self.current_version,
            "published_version": self.published_version,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "published_by": self.published_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
        if include_payload:
            data["draft_payload"] = self.draft_payload or {}
        if include_published_payload:
            data["published_payload"] = self.published_payload or None
        return data
