"""
Comprehensive test suite for app/auth/permissions.py.
Coverage: @require_admin decorator, @require_moderator decorator, role inheritance,
ban state handling, and edge cases (None user, deleted user, invalid tokens).
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from flask import Flask, jsonify, g
from flask_jwt_extended import get_jwt_identity

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import User, Role
from app.models.user import SUPERADMIN_THRESHOLD
from app.auth.permissions import (
    get_current_user,
    create_access_token,
    current_user_has_role,
    current_user_has_any_role,
    current_user_is_admin,
    current_user_role_level,
    current_user_is_super_admin,
    current_user_is_moderator,
    current_user_is_moderator_or_admin,
    current_user_can_write_news,
    current_user_is_banned,
    admin_may_edit_target,
    admin_may_assign_role_level,
    require_jwt_admin,
    require_jwt_moderator_or_admin,
    require_editor_or_n8n_service,
    _is_n8n_service_request,
)
from werkzeug.security import generate_password_hash


# ============= TEST FIXTURES =============

@pytest.fixture
def test_bp():
    """Blueprint for testing decorators."""
    from flask import Blueprint
    bp = Blueprint("test_auth", __name__)

    @bp.route("/admin-only", methods=["GET"])
    @require_jwt_admin
    def admin_only():
        return jsonify({"message": "admin access granted"}), 200

    @bp.route("/mod-or-admin", methods=["GET"])
    @require_jwt_moderator_or_admin
    def mod_or_admin():
        return jsonify({"message": "mod or admin access granted"}), 200

    @bp.route("/editor-or-service", methods=["GET"])
    @require_editor_or_n8n_service
    def editor_or_service():
        return jsonify({"message": "editor or service access granted"}), 200

    return bp


@pytest.fixture
def app_with_test_routes(test_bp):
    """Application with test routes for decorator testing."""
    application = create_app(TestingConfig)
    application.register_blueprint(test_bp)

    with application.app_context():
        db.create_all()
        from app.models.role import ensure_roles_seeded
        from app.models.area import ensure_areas_seeded
        ensure_roles_seeded()
        ensure_areas_seeded()
        yield application


@pytest.fixture
def client_with_routes(app_with_test_routes):
    """Test client with decorator test routes."""
    return app_with_test_routes.test_client()


# ============= TEST SETUP HELPERS =============

def create_test_user(app, username, role_name, role_level=0, is_banned=False):
    """Helper: create a user with specified role and level."""
    with app.app_context():
        role = Role.query.filter_by(name=role_name).first()
        user = User(
            username=username,
            password_hash=generate_password_hash("Password1"),
            role_id=role.id,
            role_level=role_level,
            is_banned=is_banned,
            banned_at=datetime.now(timezone.utc) if is_banned else None,
            ban_reason="Test ban" if is_banned else None,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, "Password1"


def get_jwt_token(client, username, password):
    """Helper: login and return JWT token."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        content_type="application/json",
    )
    assert resp.status_code == 200
    return resp.get_json()["access_token"]


# ============= get_current_user TESTS (lines 15-23) =============

class TestGetCurrentUser:
    """Test get_current_user() function."""

    def test_get_current_user_with_valid_user_id(self, app_with_test_routes):
        """get_current_user returns user when JWT identity is valid user ID."""
        with app_with_test_routes.app_context():
            # Create user within this app's context
            role = Role.query.filter_by(name="user").first()
            user = User(
                username="testuser",
                password_hash=generate_password_hash("Testpass1"),
                role_id=role.id,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)

            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_user():
                    result = get_current_user()
                    return result

                result = check_user()
                assert result is not None
                assert result.id == user.id
                assert result.username == "testuser"

    def test_get_current_user_with_none_identity(self, app_with_test_routes):
        """get_current_user returns None when JWT identity is None."""
        with app_with_test_routes.app_context():
            with app_with_test_routes.test_request_context():
                from flask_jwt_extended import jwt_required
                @jwt_required(optional=True)
                def check_user():
                    return get_current_user()

                result = check_user()
                assert result is None

    def test_get_current_user_with_invalid_type_identity(self, app_with_test_routes):
        """get_current_user returns None when JWT identity cannot be converted to int (line 22-23)."""
        with app_with_test_routes.app_context():
            token = create_access_token(identity="not-an-int")

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_user():
                    return get_current_user()

                result = check_user()
                assert result is None

    def test_get_current_user_with_nonexistent_user_id(self, app_with_test_routes):
        """get_current_user returns None when user ID doesn't exist in DB."""
        with app_with_test_routes.app_context():
            token = create_access_token(identity=99999)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_user():
                    return get_current_user()

                result = check_user()
                assert result is None


# ============= current_user_has_role TESTS (line 26-31) =============

class TestCurrentUserHasRole:
    """Test current_user_has_role() function."""

    def test_user_has_matching_role(self, app_with_test_routes):
        """User with matching role returns True."""
        with app_with_test_routes.app_context():
            role = Role.query.filter_by(name="user").first()
            user = User(
                username="testuser",
                password_hash=generate_password_hash("Testpass1"),
                role_id=role.id,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)

            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_role():
                    return current_user_has_role("user")

                assert check_role() is True

    def test_user_lacks_required_role(self, app_with_test_routes):
        """User without matching role returns False."""
        with app_with_test_routes.app_context():
            role = Role.query.filter_by(name="user").first()
            user = User(
                username="testuser",
                password_hash=generate_password_hash("Testpass1"),
                role_id=role.id,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)

            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_role():
                    return current_user_has_role("admin")

                assert check_role() is False

    def test_banned_user_has_no_roles(self, app_with_test_routes):
        """Banned user returns False even if role matches (line 29)."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "banneduser", "user", is_banned=True
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_role():
                    return current_user_has_role("user")

                assert check_role() is False

    def test_none_user_has_no_roles(self, app_with_test_routes):
        """None user returns False (line 29)."""
        with app_with_test_routes.app_context():
            token = create_access_token(identity=99999)  # Non-existent user

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_role():
                    return current_user_has_role("user")

                assert check_role() is False


# ============= current_user_has_any_role TESTS (line 34-39) =============

class TestCurrentUserHasAnyRole:
    """Test current_user_has_any_role() function."""

    @pytest.mark.parametrize("role_list,expected", [
        (["user"], True),
        (["user", "admin"], True),
        (["admin", "moderator"], False),
        ([], False),
    ])
    def test_user_has_any_of_roles(self, app_with_test_routes, role_list, expected):
        """User checks multiple roles correctly."""
        with app_with_test_routes.app_context():
            role = Role.query.filter_by(name="user").first()
            user = User(
                username="testuser",
                password_hash=generate_password_hash("Testpass1"),
                role_id=role.id,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)

            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_roles():
                    return current_user_has_any_role(role_list)

                assert check_roles() == expected

    def test_banned_user_has_any_role_returns_false(self, app_with_test_routes):
        """Banned user returns False for any role check (line 37-38)."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "banneduser", "user", is_banned=True
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_roles():
                    return current_user_has_any_role(["user", "admin"])

                assert check_roles() is False

    def test_none_user_has_any_role_returns_false(self, app_with_test_routes):
        """None user returns False (line 37-38)."""
        with app_with_test_routes.app_context():
            token = create_access_token(identity=99999)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_roles():
                    return current_user_has_any_role(["user", "admin"])

                assert check_roles() is False


# ============= current_user_is_admin TESTS (line 42-45) =============

class TestCurrentUserIsAdmin:
    """Test current_user_is_admin() function."""

    def test_admin_user_returns_true(self, app_with_test_routes):
        """Admin user returns True."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "admin", "admin", role_level=50
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_admin():
                    return current_user_is_admin()

                assert check_admin() is True

    def test_non_admin_user_returns_false(self, app_with_test_routes):
        """Non-admin user returns False."""
        with app_with_test_routes.app_context():
            role = Role.query.filter_by(name="user").first()
            user = User(
                username="testuser",
                password_hash=generate_password_hash("Testpass1"),
                role_id=role.id,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)

            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_admin():
                    return current_user_is_admin()

                assert check_admin() is False

    def test_banned_admin_returns_false(self, app_with_test_routes):
        """Banned admin returns False."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "banned_admin", "admin", role_level=50, is_banned=True
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_admin():
                    return current_user_is_admin()

                assert check_admin() is False


# ============= current_user_role_level TESTS (line 48-53) =============

class TestCurrentUserRoleLevel:
    """Test current_user_role_level() function."""

    @pytest.mark.parametrize("role_level,expected", [
        (0, 0),
        (10, 10),
        (50, 50),
        (100, 100),
    ])
    def test_role_level_returns_correct_value(self, app_with_test_routes, role_level, expected):
        """Role level is returned correctly for various levels."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, f"user_{role_level}", "admin", role_level=role_level
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def get_level():
                    return current_user_role_level()

                assert get_level() == expected

    def test_banned_user_role_level_returns_zero(self, app_with_test_routes):
        """Banned user's role_level returns 0 (line 50-52)."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "banned_user", "admin", role_level=50, is_banned=True
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def get_level():
                    return current_user_role_level()

                assert get_level() == 0

    def test_none_user_role_level_returns_zero(self, app_with_test_routes):
        """None user's role_level returns 0 (line 50-52)."""
        with app_with_test_routes.app_context():
            token = create_access_token(identity=99999)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def get_level():
                    return current_user_role_level()

                assert get_level() == 0

    def test_user_with_none_role_level_defaults_to_zero(self, app_with_test_routes):
        """User with None role_level defaults to 0 (line 53)."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "none_level_user", "user", role_level=0
            )
            # Manually set role_level to None to test fallback
            user.role_level = None
            db.session.commit()

            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def get_level():
                    return current_user_role_level()

                assert get_level() == 0


# ============= current_user_is_super_admin TESTS (line 56-59) =============

class TestCurrentUserIsSuperAdmin:
    """Test current_user_is_super_admin() function."""

    def test_super_admin_returns_true(self, app_with_test_routes):
        """Admin with role_level >= SUPERADMIN_THRESHOLD returns True."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "super_admin", "admin", role_level=SUPERADMIN_THRESHOLD
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_super():
                    return current_user_is_super_admin()

                assert check_super() is True

    def test_admin_below_threshold_returns_false(self, app_with_test_routes):
        """Admin with role_level < SUPERADMIN_THRESHOLD returns False."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "regular_admin", "admin", role_level=50
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_super():
                    return current_user_is_super_admin()

                assert check_super() is False

    def test_moderator_returns_false(self, app_with_test_routes):
        """Moderator (even high level) returns False."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "mod_user", "moderator", role_level=150
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_super():
                    return current_user_is_super_admin()

                assert check_super() is False

    def test_banned_super_admin_returns_false(self, app_with_test_routes):
        """Banned user with super admin config returns False."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "banned_super", "admin",
                role_level=SUPERADMIN_THRESHOLD, is_banned=True
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_super():
                    return current_user_is_super_admin()

                assert check_super() is False


# ============= current_user_is_moderator TESTS =============

class TestCurrentUserIsModerator:
    """Test current_user_is_moderator() function."""

    def test_moderator_returns_true(self, app_with_test_routes):
        """User with moderator role returns True."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "mod_user", "moderator"
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_mod():
                    return current_user_is_moderator()

                assert check_mod() is True

    def test_non_moderator_returns_false(self, app_with_test_routes):
        """User without moderator role returns False."""
        with app_with_test_routes.app_context():
            role = Role.query.filter_by(name="user").first()
            user = User(
                username="testuser",
                password_hash=generate_password_hash("Testpass1"),
                role_id=role.id,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)

            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_mod():
                    return current_user_is_moderator()

                assert check_mod() is False

    def test_banned_moderator_returns_false(self, app_with_test_routes):
        """Banned moderator returns False."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "banned_mod", "moderator", is_banned=True
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_mod():
                    return current_user_is_moderator()

                assert check_mod() is False


# ============= current_user_is_moderator_or_admin TESTS =============

class TestCurrentUserIsModeratorOrAdmin:
    """Test current_user_is_moderator_or_admin() function."""

    @pytest.mark.parametrize("role,expected", [
        ("moderator", True),
        ("admin", True),
        ("user", False),
    ])
    def test_moderator_or_admin_role_check(self, app_with_test_routes, role, expected):
        """Various roles checked correctly for moderator or admin."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, f"user_{role}", role
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_any():
                    return current_user_is_moderator_or_admin()

                assert check_any() == expected

    def test_banned_moderator_or_admin_returns_false(self, app_with_test_routes):
        """Banned moderator returns False for moderator_or_admin check."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "banned_mod_admin", "moderator", is_banned=True
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_any():
                    return current_user_is_moderator_or_admin()

                assert check_any() is False


# ============= current_user_can_write_news TESTS (line 88-96) =============

class TestCurrentUserCanWriteNews:
    """Test current_user_can_write_news() function."""

    @pytest.mark.parametrize("role,expected", [
        ("moderator", True),
        ("admin", True),
        ("user", False),
    ])
    def test_write_news_permission(self, app_with_test_routes, role, expected):
        """News write permission for various roles."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, f"user_{role}", role
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_write():
                    return current_user_can_write_news()

                assert check_write() == expected

    def test_banned_user_cannot_write_news(self, app_with_test_routes):
        """Banned moderator cannot write news (line 94-95)."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "banned_writer", "moderator", is_banned=True
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_write():
                    return current_user_can_write_news()

                assert check_write() is False

    def test_none_user_cannot_write_news(self, app_with_test_routes):
        """None user cannot write news (line 94-95)."""
        with app_with_test_routes.app_context():
            token = create_access_token(identity=99999)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_write():
                    return current_user_can_write_news()

                assert check_write() is False


# ============= current_user_is_banned TESTS (line 99-102) =============

class TestCurrentUserIsBanned:
    """Test current_user_is_banned() function."""

    def test_banned_user_returns_true(self, app_with_test_routes):
        """Banned user returns True."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "banned_user", "user", is_banned=True
            )
            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_banned():
                    return current_user_is_banned()

                assert check_banned() is True

    def test_non_banned_user_returns_false(self, app_with_test_routes):
        """Non-banned user returns False."""
        with app_with_test_routes.app_context():
            role = Role.query.filter_by(name="user").first()
            user = User(
                username="testuser",
                password_hash=generate_password_hash("Testpass1"),
                role_id=role.id,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)

            token = create_access_token(identity=user.id)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_banned():
                    return current_user_is_banned()

                assert check_banned() is False

    def test_none_user_is_not_banned(self, app_with_test_routes):
        """None user returns False (line 101-102)."""
        with app_with_test_routes.app_context():
            token = create_access_token(identity=99999)

            with app_with_test_routes.test_request_context(
                headers={"Authorization": f"Bearer {token}"}
            ):
                from flask_jwt_extended import jwt_required
                @jwt_required()
                def check_banned():
                    return current_user_is_banned()

                assert check_banned() is False


# ============= admin_may_edit_target TESTS (line 62-64) =============

class TestAdminMayEditTarget:
    """Test admin_may_edit_target() function."""

    @pytest.mark.parametrize("actor_level,target_level,expected", [
        (50, 10, True),   # Higher can edit lower
        (100, 50, True),  # Higher can edit lower
        (50, 50, False),  # Equal cannot edit equal (line 64)
        (10, 50, False),  # Lower cannot edit higher
        (0, 100, False),  # Much lower cannot edit
    ])
    def test_admin_hierarchy_checks(self, actor_level, target_level, expected):
        """Admin hierarchy: higher level may edit strictly lower levels only (line 64)."""
        result = admin_may_edit_target(actor_level, target_level)
        assert result == expected


# ============= admin_may_assign_role_level TESTS (line 67-75) =============

class TestAdminMayAssignRoleLevel:
    """Test admin_may_assign_role_level() function."""

    def test_admin_may_edit_other_user_with_lower_level(self):
        """Admin may set other user to lower level (line 75)."""
        actor_id = 1
        target_user_id = 2
        actor_level = 50
        new_level = 10

        result = admin_may_assign_role_level(actor_level, target_user_id, new_level, actor_id)
        assert result is True

    def test_admin_cannot_edit_equal_user_level(self):
        """Admin cannot set equal-level user to same or different level (line 75)."""
        actor_id = 1
        target_user_id = 2
        actor_level = 50
        new_level = 50

        result = admin_may_assign_role_level(actor_level, target_user_id, new_level, actor_id)
        assert result is False

    def test_admin_cannot_edit_higher_user(self):
        """Admin cannot set higher-level user (line 75)."""
        actor_id = 1
        target_user_id = 2
        actor_level = 50
        new_level = 75

        result = admin_may_assign_role_level(actor_level, target_user_id, new_level, actor_id)
        assert result is False

    def test_super_admin_may_elevate_self(self):
        """SuperAdmin may set own level >= SUPERADMIN_THRESHOLD (line 73-74)."""
        actor_id = 1
        target_user_id = 1
        actor_level = SUPERADMIN_THRESHOLD
        new_level = SUPERADMIN_THRESHOLD

        # Must have is_super_admin = True checked elsewhere
        result = admin_may_assign_role_level(actor_level, target_user_id, new_level, actor_id)
        assert result is True

    def test_admin_cannot_elevate_self_below_threshold(self):
        """Admin cannot set self to level below SUPERADMIN_THRESHOLD (line 73-74)."""
        actor_id = 1
        target_user_id = 1
        actor_level = 50  # Regular admin
        new_level = 50

        result = admin_may_assign_role_level(actor_level, target_user_id, new_level, actor_id)
        assert result is False

    def test_super_admin_can_lower_self(self):
        """SuperAdmin editing self with >= SUPERADMIN_THRESHOLD returns True (line 73-74)."""
        actor_id = 1
        target_user_id = 1
        actor_level = SUPERADMIN_THRESHOLD
        new_level = SUPERADMIN_THRESHOLD + 50

        result = admin_may_assign_role_level(actor_level, target_user_id, new_level, actor_id)
        assert result is True


# ============= @require_jwt_admin DECORATOR TESTS (line 105-112) =============

class TestRequireJwtAdminDecorator:
    """Test @require_jwt_admin decorator."""

    def test_admin_access_granted(self, app_with_test_routes, client_with_routes):
        """Admin user can access @require_jwt_admin endpoint."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "admin", "admin", role_level=50
            )
            token = get_jwt_token(client_with_routes, user.username, password)

        resp = client_with_routes.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["message"] == "admin access granted"

    def test_non_admin_access_denied(self, app_with_test_routes, client_with_routes):
        """Non-admin user gets 403 (line 22-23, 30)."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "user", "user"
            )
            token = get_jwt_token(client_with_routes, user.username, password)

        resp = client_with_routes.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403
        assert "Forbidden" in resp.get_json()["error"]

    def test_banned_admin_access_denied(self, app_with_test_routes, client_with_routes):
        """Banned admin user gets 403 (line 38)."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "banned_admin", "admin",
                role_level=50, is_banned=True
            )
            # Create token directly since banned users cannot login
            token = create_access_token(identity=user.id)

        resp = client_with_routes.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    def test_no_token_returns_401(self, client_with_routes):
        """Missing JWT token returns 401."""
        resp = client_with_routes.get("/admin-only")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client_with_routes):
        """Invalid JWT token returns 401."""
        resp = client_with_routes.get(
            "/admin-only",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, app_with_test_routes, client_with_routes):
        """Expired token returns 401."""
        with app_with_test_routes.app_context():
            # Create token that's already expired
            from datetime import timedelta
            token = create_access_token(
                identity=1,
                expires_delta=timedelta(seconds=-1)
            )

        resp = client_with_routes.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401


# ============= @require_jwt_moderator_or_admin DECORATOR TESTS (line 129-136) =============

class TestRequireJwtModeratorOrAdminDecorator:
    """Test @require_jwt_moderator_or_admin decorator."""

    @pytest.mark.parametrize("role,should_pass", [
        ("moderator", True),
        ("admin", True),
        ("user", False),
    ])
    def test_moderator_or_admin_access(self, app_with_test_routes, client_with_routes, role, should_pass):
        """Moderator and admin can access, user cannot (line 50-53, 73-75)."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, f"user_{role}", role
            )
            token = get_jwt_token(client_with_routes, user.username, password)

        resp = client_with_routes.get(
            "/mod-or-admin",
            headers={"Authorization": f"Bearer {token}"}
        )

        if should_pass:
            assert resp.status_code == 200
            assert resp.get_json()["message"] == "mod or admin access granted"
        else:
            assert resp.status_code == 403
            assert "Forbidden" in resp.get_json()["error"]

    def test_banned_moderator_access_denied(self, app_with_test_routes, client_with_routes):
        """Banned moderator gets 403 (line 73-75)."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "banned_mod", "moderator", is_banned=True
            )
            # Create token directly since banned users cannot login
            token = create_access_token(identity=user.id)

        resp = client_with_routes.get(
            "/mod-or-admin",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    def test_no_token_returns_401(self, client_with_routes):
        """Missing token returns 401."""
        resp = client_with_routes.get("/mod-or-admin")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client_with_routes):
        """Invalid token returns 401."""
        resp = client_with_routes.get(
            "/mod-or-admin",
            headers={"Authorization": "Bearer invalid"}
        )
        assert resp.status_code == 401


# ============= @require_editor_or_n8n_service DECORATOR TESTS (line 148-164) =============

class TestRequireEditorOrN8nServiceDecorator:
    """Test @require_editor_or_n8n_service decorator."""

    def test_valid_n8n_service_request_succeeds(self, app_with_test_routes, client_with_routes):
        """Valid X-Service-Key header grants access (line 144-145, 155-157)."""
        app_with_test_routes.config["N8N_SERVICE_TOKEN"] = "test-service-key"

        resp = client_with_routes.get(
            "/editor-or-service",
            headers={"X-Service-Key": "test-service-key"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["message"] == "editor or service access granted"

    def test_invalid_n8n_service_key_requires_jwt(self, app_with_test_routes, client_with_routes):
        """Invalid X-Service-Key falls back to JWT check (line 144-145)."""
        app_with_test_routes.config["N8N_SERVICE_TOKEN"] = "test-service-key"

        resp = client_with_routes.get(
            "/editor-or-service",
            headers={"X-Service-Key": "wrong-key"}
        )
        # Should now require JWT and return 401
        assert resp.status_code == 401

    def test_moderator_jwt_access_granted(self, app_with_test_routes, client_with_routes):
        """Moderator with JWT can access (line 161-162)."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "mod_user", "moderator"
            )
            token = get_jwt_token(client_with_routes, user.username, password)

        resp = client_with_routes.get(
            "/editor-or-service",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

    def test_admin_jwt_access_granted(self, app_with_test_routes, client_with_routes):
        """Admin with JWT can access (line 161-162)."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "admin_user", "admin", role_level=50
            )
            token = get_jwt_token(client_with_routes, user.username, password)

        resp = client_with_routes.get(
            "/editor-or-service",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

    def test_user_jwt_access_denied(self, app_with_test_routes, client_with_routes):
        """Regular user with JWT gets 403 (line 160, 162)."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "user", "user"
            )
            token = get_jwt_token(client_with_routes, user.username, password)

        resp = client_with_routes.get(
            "/editor-or-service",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    def test_no_token_no_service_key_returns_401(self, client_with_routes):
        """No JWT and no service key returns 401 (line 159-160)."""
        resp = client_with_routes.get("/editor-or-service")
        assert resp.status_code == 401

    def test_g_is_n8n_service_flag_set(self, app_with_test_routes, client_with_routes):
        """g.is_n8n_service is set to True for valid service request (line 156)."""
        app_with_test_routes.config["N8N_SERVICE_TOKEN"] = "test-key"

        # Create a test route that checks g.is_n8n_service
        from flask import Blueprint
        bp = Blueprint("check_flag", __name__)

        @bp.route("/check-flag", methods=["GET"])
        @require_editor_or_n8n_service
        def check_flag():
            return jsonify({"is_n8n_service": g.is_n8n_service}), 200

        app_with_test_routes.register_blueprint(bp)

        resp = client_with_routes.get(
            "/check-flag",
            headers={"X-Service-Key": "test-key"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["is_n8n_service"] is True

    def test_g_is_n8n_service_flag_false_for_jwt(self):
        """g.is_n8n_service is set to False for JWT request (line 158)."""
        # Create a fresh app for this test since we need to register new blueprints
        app = create_app(TestingConfig)

        with app.app_context():
            db.create_all()
            from app.models.role import ensure_roles_seeded
            from app.models.area import ensure_areas_seeded
            ensure_roles_seeded()
            ensure_areas_seeded()

            # Create test route
            from flask import Blueprint
            bp = Blueprint("check_flag_jwt", __name__)

            @bp.route("/check-flag-jwt", methods=["GET"])
            @require_editor_or_n8n_service
            def check_flag_jwt():
                return jsonify({"is_n8n_service": g.is_n8n_service}), 200

            app.register_blueprint(bp)

            # Create user and get token
            user, password = create_test_user(
                app, "mod_user", "moderator"
            )
            token = get_jwt_token(app.test_client(), user.username, password)

        client = app.test_client()
        resp = client.get(
            "/check-flag-jwt",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["is_n8n_service"] is False


# ============= _is_n8n_service_request TESTS (line 139-145) =============

class TestIsN8nServiceRequest:
    """Test _is_n8n_service_request() function."""

    def test_valid_service_key_returns_true(self, app_with_test_routes):
        """Valid X-Service-Key matching config returns True (line 144-145)."""
        with app_with_test_routes.app_context():
            app_with_test_routes.config["N8N_SERVICE_TOKEN"] = "secret-token"

            with app_with_test_routes.test_request_context(
                headers={"X-Service-Key": "secret-token"}
            ):
                assert _is_n8n_service_request() is True

    def test_invalid_service_key_returns_false(self, app_with_test_routes):
        """Invalid X-Service-Key returns False (line 145)."""
        with app_with_test_routes.app_context():
            app_with_test_routes.config["N8N_SERVICE_TOKEN"] = "secret-token"

            with app_with_test_routes.test_request_context(
                headers={"X-Service-Key": "wrong-token"}
            ):
                assert _is_n8n_service_request() is False

    def test_missing_service_token_config_returns_false(self, app_with_test_routes):
        """Missing N8N_SERVICE_TOKEN config returns False (line 141-142)."""
        with app_with_test_routes.app_context():
            app_with_test_routes.config["N8N_SERVICE_TOKEN"] = None

            with app_with_test_routes.test_request_context(
                headers={"X-Service-Key": "any-token"}
            ):
                assert _is_n8n_service_request() is False

    def test_missing_header_returns_false(self, app_with_test_routes):
        """Missing X-Service-Key header returns False."""
        with app_with_test_routes.app_context():
            app_with_test_routes.config["N8N_SERVICE_TOKEN"] = "secret-token"

            with app_with_test_routes.test_request_context():
                assert _is_n8n_service_request() is False

    def test_empty_service_key_returns_false(self, app_with_test_routes):
        """Empty X-Service-Key header returns False (line 145)."""
        with app_with_test_routes.app_context():
            app_with_test_routes.config["N8N_SERVICE_TOKEN"] = "secret-token"

            with app_with_test_routes.test_request_context(
                headers={"X-Service-Key": ""}
            ):
                assert _is_n8n_service_request() is False

    def test_whitespace_service_key_stripped(self, app_with_test_routes):
        """X-Service-Key with whitespace is stripped correctly (line 144)."""
        with app_with_test_routes.app_context():
            app_with_test_routes.config["N8N_SERVICE_TOKEN"] = "secret-token"

            with app_with_test_routes.test_request_context(
                headers={"X-Service-Key": "  secret-token  "}
            ):
                assert _is_n8n_service_request() is True


# ============= EDGE CASE INTEGRATION TESTS =============

class TestEdgeCasesIntegration:
    """Integration tests for complex edge cases."""

    def test_deleted_user_cannot_access_resources(self, app_with_test_routes, client_with_routes):
        """Deleted user (not in DB) cannot access protected resources."""
        with app_with_test_routes.app_context():
            # Create token for user ID that will be "deleted"
            token = create_access_token(identity=99999)

        resp = client_with_routes.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    def test_role_change_reflected_in_checks(self, app_with_test_routes, client_with_routes):
        """Role change is reflected in permission checks."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "role_change_user", "user"
            )
            user_id = user.id

        # Login with user role
        token = get_jwt_token(client_with_routes, "role_change_user", password)
        resp = client_with_routes.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

        # Promote user to admin
        with app_with_test_routes.app_context():
            user = User.query.get(user_id)
            admin_role = Role.query.filter_by(name="admin").first()
            user.role_id = admin_role.id
            user.role_level = 50
            db.session.commit()

        # Login again with new admin role
        token = get_jwt_token(client_with_routes, "role_change_user", password)
        resp = client_with_routes.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

    def test_ban_immediately_revokes_access(self, app_with_test_routes, client_with_routes):
        """Banning a user immediately revokes access."""
        with app_with_test_routes.app_context():
            user, password = create_test_user(
                app_with_test_routes, "ban_test_user", "admin", role_level=50
            )
            user_id = user.id

        # Login works as admin
        token = get_jwt_token(client_with_routes, "ban_test_user", password)
        resp = client_with_routes.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

        # Ban the user
        with app_with_test_routes.app_context():
            user = User.query.get(user_id)
            user.is_banned = True
            user.banned_at = datetime.now(timezone.utc)
            user.ban_reason = "Test ban"
            db.session.commit()

        # Now same token denies access
        resp = client_with_routes.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    def test_role_level_hierarchy_enforced(self, app_with_test_routes, client_with_routes):
        """Role level hierarchy is properly enforced across operations."""
        with app_with_test_routes.app_context():
            # Create two admins with different levels
            low_admin, low_pass = create_test_user(
                app_with_test_routes, "low_admin", "admin", role_level=10
            )
            high_admin, high_pass = create_test_user(
                app_with_test_routes, "high_admin", "admin", role_level=100
            )

        # Both should have admin access
        low_token = get_jwt_token(client_with_routes, "low_admin", low_pass)
        high_token = get_jwt_token(client_with_routes, "high_admin", high_pass)

        assert client_with_routes.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {low_token}"}
        ).status_code == 200

        assert client_with_routes.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {high_token}"}
        ).status_code == 200

        # But low admin cannot edit high admin
        with app_with_test_routes.app_context():
            assert admin_may_edit_target(10, 100) is False
            assert admin_may_edit_target(100, 10) is True
