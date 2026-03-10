from app.extensions import db


class User(db.Model):
    """User for auth (web session and API JWT)."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")

    ROLE_USER = "user"
    ROLE_EDITOR = "editor"
    ROLE_ADMIN = "admin"

    def to_dict(self):
        return {"id": self.id, "username": self.username, "role": self.role}

    def can_write_news(self):
        """True if this user may create/update/delete/publish news."""
        return self.role in (self.ROLE_EDITOR, self.ROLE_ADMIN)

    def __repr__(self):
        return f"<User id={self.id} username={self.username!r}>"
