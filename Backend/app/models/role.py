"""Role model for RBAC. Centralizes role names and supports future permission granularity."""
from app.extensions import db


class Role(db.Model):
    """Named role for users. Seed: user, moderator, editor, admin."""

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), unique=True, nullable=False)

    NAME_USER = "user"
    NAME_MAX_LENGTH = 20

    def to_dict(self):
        return {"id": self.id, "name": self.name}

    NAME_MODERATOR = "moderator"
    NAME_EDITOR = "editor"
    NAME_ADMIN = "admin"

    def __repr__(self):
        return f"<Role id={self.id} name={self.name!r}>"


def get_role_by_name(name: str):
    """Return Role by name or None."""
    if not name or not isinstance(name, str):
        return None
    return Role.query.filter_by(name=name.strip().lower()).first()


def ensure_roles_seeded():
    """Insert default roles if they do not exist. Safe to call on init or in tests."""
    for name in (Role.NAME_USER, Role.NAME_MODERATOR, Role.NAME_EDITOR, Role.NAME_ADMIN):
        if Role.query.filter_by(name=name).first() is None:
            db.session.add(Role(name=name))
    db.session.commit()
