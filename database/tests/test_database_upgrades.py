"""High-level database smoke tests for current schema and migration visibility."""
from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.models import Area, Role, User


class TestDatabaseUpgrades:
    def test_schema_is_readable_after_create_all(self, db):
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        assert "users" in tables
        assert "roles" in tables
        assert "forum_threads" in tables
        assert "news_articles" in tables

    def test_seeded_core_rows_exist(self, db):
        assert Role.query.filter_by(name=Role.NAME_USER).first() is not None
        assert Role.query.filter_by(name=Role.NAME_ADMIN).first() is not None
        assert Area.query.filter_by(slug="all").first() is not None
        assert Area.query.filter_by(slug="game").first() is not None

    def test_schema_allows_basic_role_and_user_persistence(self, db):
        role = Role(name="custom_role", default_role_level=12)
        db.session.add(role)
        db.session.commit()

        user = User(
            username="schema_user",
            password_hash=generate_password_hash("StrongPass1!"),
            role_id=role.id,
            role_level=12,
        )
        db.session.add(user)
        db.session.commit()

        loaded = User.query.filter_by(username="schema_user").first()
        assert loaded is not None
        assert loaded.role == "custom_role"
        assert loaded.role_rel.id == role.id

    def test_integrity_error_rollback_keeps_session_usable(self, db):
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        db.session.add(User(username="rollback-user", password_hash=generate_password_hash("StrongPass1!"), role_id=role.id))
        db.session.commit()

        db.session.add(User(username="rollback-user", password_hash=generate_password_hash("StrongPass2!"), role_id=role.id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        count = User.query.filter_by(username="rollback-user").count()
        assert count == 1
