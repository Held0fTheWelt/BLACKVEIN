"""Slogan model for managed site copy: landing teaser, hero, promo, ad slots, etc."""
from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    return datetime.now(timezone.utc)


class Slogan(db.Model):
    """
    Managed slogan content. Selection: active only; valid_from/valid_until window;
    pinned overrides rotation for a placement; priority and rotation for multiple eligible.
    """
    __tablename__ = "slogans"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.Text(), nullable=False)
    category = db.Column(db.String(64), nullable=False)
    placement_key = db.Column(db.String(128), nullable=False)
    language_code = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean(), nullable=False, default=True)
    is_pinned = db.Column(db.Boolean(), nullable=False, default=False)
    priority = db.Column(db.Integer, nullable=False, default=0)
    valid_from = db.Column(db.DateTime(timezone=True), nullable=True)
    valid_until = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    CATEGORIES = ("landing_hero", "landing_teaser", "promo_banner", "ad_slot", "dashboard_notice")
    PLACEMENTS = ("landing.hero.primary", "landing.teaser.primary", "landing.ad.primary", "landing.ad.secondary")

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "category": self.category,
            "placement_key": self.placement_key,
            "language_code": self.language_code,
            "is_active": self.is_active,
            "is_pinned": self.is_pinned,
            "priority": self.priority,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
        }
