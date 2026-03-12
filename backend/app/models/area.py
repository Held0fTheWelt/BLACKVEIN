"""Area model for area-based access control. Users can be assigned to one or many areas; 'all' is wildcard."""
from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    return datetime.now(timezone.utc)


# Many-to-many: users <-> areas
user_areas = db.Table(
    "user_areas",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("area_id", db.Integer, db.ForeignKey("areas.id", ondelete="CASCADE"), primary_key=True),
)


class Area(db.Model):
    """
    Named area for scoping admin/dashboard/frontend feature access.
    Users assigned to an area may access features assigned to that area.
    Slug 'all' is the special wildcard (global access).
    """
    __tablename__ = "areas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    slug = db.Column(db.String(64), unique=True, nullable=False, index=True)
    description = db.Column(db.String(512), nullable=True)
    is_system = db.Column(db.Boolean(), nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)

    SLUG_ALL = "all"

    def to_dict(self):
        out = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "is_system": self.is_system,
        }
        if self.description is not None:
            out["description"] = self.description
        out["created_at"] = self.created_at.isoformat() if self.created_at else None
        out["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        return out

    @property
    def is_global(self) -> bool:
        """True if this area is the wildcard 'all' (global access)."""
        return self.slug == self.SLUG_ALL

    def __repr__(self):
        return f"<Area id={self.id} slug={self.slug!r}>"


DEFAULT_AREAS = (
    ("all", "all", "Global access (wildcard). Users with this area can access all area-scoped features.", True),
    ("community", "community", "Community moderation and content.", False),
    ("website_content", "website content", "Website and editorial content.", False),
    ("rules_and_system", "rules and system", "Rules and system configuration.", False),
    ("ai_integration", "ai integration", "AI integration features.", False),
    ("game", "game", "Game-related features.", False),
    ("wiki", "wiki", "Wiki and documentation.", False),
)


def ensure_areas_seeded():
    """Insert default areas if they do not exist. Safe to call on init or in tests. Does not overwrite existing."""
    for slug, name, description, is_system in DEFAULT_AREAS:
        if Area.query.filter_by(slug=slug).first() is not None:
            continue
        db.session.add(Area(
            name=name,
            slug=slug,
            description=description or None,
            is_system=is_system,
        ))
    db.session.commit()
