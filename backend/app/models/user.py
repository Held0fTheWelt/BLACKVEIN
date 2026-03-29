from datetime import datetime, timezone
import json

from werkzeug.security import check_password_hash

from app.extensions import db
from app.models.area import user_areas

# SuperAdmin: admin role with role_level >= this value. Used for hierarchy and self-elevation.
SUPERADMIN_THRESHOLD = 100


def _utc_now():
    return datetime.now(timezone.utc)


class PasswordHistory(db.Model):
    __tablename__ = "password_histories"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)

    user_rel = db.relationship("User", backref=db.backref("password_histories", lazy="dynamic", cascade="all, delete-orphan"))


class User(db.Model):
    """User for auth (web session and API JWT). Primary role via Role model; role_level for hierarchy. Supports ban state."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    role_level = db.Column(db.Integer, nullable=False, default=0)
    email_verified_at = db.Column(db.DateTime(timezone=True), nullable=True, default=None)
    is_banned = db.Column(db.Boolean(), nullable=False, default=False)
    banned_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ban_reason = db.Column(db.String(512), nullable=True)
    preferred_language = db.Column(db.String(10), nullable=True)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=True, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True, default=_utc_now, onupdate=_utc_now)
    is_active = db.Column(db.Boolean(), nullable=False, default=True)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    password_history = db.Column(db.Text, nullable=True)

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
            "is_active": self.is_active,
        }
        if include_areas and self.areas:
            out["areas"] = [a.to_dict() for a in self.areas]
        if self.preferred_language is not None:
            out["preferred_language"] = self.preferred_language
        out["created_at"] = self.created_at.isoformat() if self.created_at else None
        out["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
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

    def is_password_in_history(self, plaintext_password: str) -> bool:
        """
        Check if plaintext_password matches any of the last 3 password hashes in history.
        Returns True if found (reuse detected), False otherwise.
        """
        if not self.password_history:
            return False
        history = json.loads(self.password_history)
        for password_hash in history:
            if check_password_hash(password_hash, plaintext_password):
                return True
        return False

    def add_to_password_history(self, password_hash: str) -> None:
        """
        Add password_hash to history and keep only the last 3 hashes.
        Called after setting a new password.
        """
        # Update JSON password_history field
        history = json.loads(self.password_history or "[]")
        history.append(password_hash)
        # Keep only last 3
        if len(history) > 3:
            history = history[-3:]
        self.password_history = json.dumps(history)
        db.session.commit()

    def __repr__(self):
        return f"<User id={self.id} username={self.username!r}>"
