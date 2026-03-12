from datetime import datetime, timezone

from app.extensions import db
from app.models.area import user_areas

# SuperAdmin: admin role with role_level >= this value. Used for hierarchy and self-elevation.
SUPERADMIN_THRESHOLD = 100


def _utc_now():
    return datetime.now(timezone.utc)


class User(db.Model):
    """User for auth (web session and API JWT). Primary role via Role model; role_level for hierarchy. Supports ban state."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role_level = db.Column(db.Integer, nullable=False, default=0)
    email_verified_at = db.Column(db.DateTime(timezone=True), nullable=True, default=None)
    is_banned = db.Column(db.Boolean(), nullable=False, default=False)
    banned_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ban_reason = db.Column(db.String(512), nullable=True)
    preferred_language = db.Column(db.String(10), nullable=True)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=True, default=_utc_now)

    role_rel = db.relationship("Role", backref="users", lazy="joined")
    areas = db.relationship("Area", secondary=user_areas, lazy="select", backref=db.backref("users", lazy="dynamic"))

    ROLE_USER = "user"
    ROLE_MODERATOR = "moderator"
    ROLE_ADMIN = "admin"
    ROLE_QA = "qa"

    @property
    def role(self) -> str:
        """Role name for API/templates. Use has_role / is_admin for checks."""
        return self.role_rel.name if self.role_rel else self.ROLE_USER

    def has_role(self, name: str) -> bool:
        """True if this user has the given role name."""
        return (self.role_rel and self.role_rel.name == name) or self.role == name

    def has_any_role(self, names) -> bool:
        """True if this user has any of the given role names."""
        r = self.role_rel.name if self.role_rel else self.role
        return r in names

    @property
    def is_admin(self) -> bool:
        """True if this user has admin role."""
        return self.has_role(self.ROLE_ADMIN)

    @property
    def is_super_admin(self) -> bool:
        """True if this user is admin with role_level >= SUPERADMIN_THRESHOLD."""
        return self.has_role(self.ROLE_ADMIN) and (self.role_level or 0) >= SUPERADMIN_THRESHOLD

    @property
    def is_moderator_or_admin(self) -> bool:
        """True if this user has moderator or admin role."""
        return self.has_any_role((self.ROLE_MODERATOR, self.ROLE_ADMIN))

    def to_dict(self, include_email: bool = False, include_ban: bool = False, include_areas: bool = False):
        out = {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "role_id": self.role_id,
            "role_level": getattr(self, "role_level", 0) or 0,
            "area_ids": [a.id for a in self.areas] if self.areas else [],
        }
        if include_areas and self.areas:
            out["areas"] = [a.to_dict() for a in self.areas]
        if self.preferred_language is not None:
            out["preferred_language"] = self.preferred_language
        out["created_at"] = self.created_at.isoformat() if self.created_at else None
        out["last_seen_at"] = self.last_seen_at.isoformat() if self.last_seen_at else None
        if include_email:
            out["email"] = self.email
        if include_ban:
            out["is_banned"] = self.is_banned
            out["banned_at"] = self.banned_at.isoformat() if self.banned_at else None
            out["ban_reason"] = self.ban_reason
        return out

    def can_write_news(self):
        """True if this user may create/update/delete/publish news (moderator or admin)."""
        return self.has_any_role((self.ROLE_MODERATOR, self.ROLE_ADMIN))

    def __repr__(self):
        return f"<User id={self.id} username={self.username!r}>"
