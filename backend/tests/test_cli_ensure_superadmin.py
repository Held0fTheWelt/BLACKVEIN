"""Promote existing users to SuperAdmin (cli_ops + thin Flask CLI in run.py)."""

import pytest
from werkzeug.security import generate_password_hash

from app.cli_ops import ensure_superadmin_for_username
from app.extensions import db
from app.models import Role, User
from app.models.area import Area
from app.models.area import ensure_areas_seeded
from app.models.role import ensure_roles_seeded


def test_ensure_superadmin_updates_existing_user(app):
    with app.app_context():
        ensure_roles_seeded()
        ensure_areas_seeded()
        user_role = Role.query.filter_by(name=Role.NAME_USER).first()
        u = User(
            username="existingmod",
            password_hash=generate_password_hash("Testpass1"),
            role_id=user_role.id,
            role_level=0,
        )
        db.session.add(u)
        db.session.commit()

        msg = ensure_superadmin_for_username("existingmod")
        assert "Updated existingmod" in msg
        assert "admin" in msg.lower()

        u2 = User.query.filter_by(username="existingmod").first()
        assert u2.has_role(Role.NAME_ADMIN)
        assert u2.role_level == 100
        assert any(a.slug == Area.SLUG_ALL for a in u2.areas)


def test_ensure_superadmin_unknown_user(app):
    with app.app_context():
        ensure_roles_seeded()
        ensure_areas_seeded()
        with pytest.raises(ValueError, match="not found"):
            ensure_superadmin_for_username("nobody_xyz_123")
