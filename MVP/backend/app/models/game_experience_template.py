from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    return datetime.now(timezone.utc)


class GameExperienceTemplate(db.Model):
    __tablename__ = "game_experience_templates"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    template_id = db.Column(db.String(120), nullable=False, unique=True, index=True)
    slug = db.Column(db.String(140), nullable=False, unique=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(40), nullable=False, index=True)
    summary = db.Column(db.Text, nullable=True)
    style_profile = db.Column(db.String(80), nullable=False, default="retro_pulp")
    tags_json = db.Column(db.JSON, nullable=False, default=list)
    payload_json = db.Column(db.JSON, nullable=False)
    source = db.Column(db.String(40), nullable=False, default="authored")
    version = db.Column(db.Integer, nullable=False, default=1)
    is_published = db.Column(db.Boolean, nullable=False, default=False, index=True)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)
    content_lifecycle = db.Column(db.String(32), nullable=False, default="draft", index=True)
    governance_provenance_json = db.Column(db.JSON, nullable=False, default=dict)

    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    updated_by = db.relationship("User", foreign_keys=[updated_by_user_id])

    def to_dict(self, *, include_payload: bool = False) -> dict:
        lifecycle = self.content_lifecycle or "draft"
        provenance = self.governance_provenance_json if isinstance(self.governance_provenance_json, dict) else {}
        publish_allowed = lifecycle in ("approved", "publishable") or (
            self.template_id == "god_of_carnage_solo" and self.source == "authored_seed"
        )
        data = {
            "id": self.id,
            "template_id": self.template_id,
            "slug": self.slug,
            "title": self.title,
            "kind": self.kind,
            "summary": self.summary,
            "style_profile": self.style_profile,
            "tags": list(self.tags_json or []),
            "source": self.source,
            "version": self.version,
            "is_published": bool(self.is_published),
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "content_lifecycle": lifecycle,
            "governance_provenance": provenance,
            "publish_allowed": bool(publish_allowed),
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_payload:
            data["payload"] = self.payload_json
        return data

    def __repr__(self) -> str:
        return f"<GameExperienceTemplate id={self.id} template_id={self.template_id!r} published={self.is_published}>"
