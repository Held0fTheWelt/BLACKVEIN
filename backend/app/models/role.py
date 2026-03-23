"""Role model for RBAC. Centralizes role names, optional description and default_role_level."""
from app.extensions import db


class Role(db.Model):
    """Named role for users. Supports user, moderator, admin, qa. Optional description and default_role_level."""

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(512), nullable=True)
    default_role_level = db.Column(db.Integer, nullable=True)

    NAME_USER = "user"
    NAME_MODERATOR = "moderator"
    NAME_ADMIN = "admin"
    NAME_QA = "qa"
    NAME_MAX_LENGTH = 20

    def to_dict(self):
        out = {"id": self.id, "name": self.name}
        if self.description is not None:
            out["description"] = self.description
        if self.default_role_level is not None:
            out["default_role_level"] = self.default_role_level
        return out

    def __repr__(self):
        return f"<Role id={self.id} name={self.name!r}>"


def get_role_by_name(name: str):
    """Return Role by name or None."""
    if not name or not isinstance(name, str):
        return None
    return Role.query.filter_by(name=name.strip().lower()).first()


def ensure_roles_seeded():
    """Insert default roles if they do not exist. Safe to call on init or in tests. Roles: user, moderator, admin, qa."""
    defaults = (
        (Role.NAME_USER, 0),
        (Role.NAME_QA, 5),
        (Role.NAME_MODERATOR, 10),
        (Role.NAME_ADMIN, 50),
    )
    for name, level in defaults:
        if Role.query.filter_by(name=name).first() is None:
            db.session.add(Role(name=name, default_role_level=level))
    db.session.commit()
