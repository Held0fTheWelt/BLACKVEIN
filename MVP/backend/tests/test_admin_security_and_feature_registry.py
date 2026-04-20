"""Internal admin_security helpers, decorator behavior, and feature_registry area logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from flask import Flask, jsonify
from werkzeug.security import generate_password_hash

from app.auth import admin_security as admin_security_module
from app.auth.admin_security import AdminSecurityConfig
from app.auth.feature_registry import (
    FEATURE_DASHBOARD_METRICS,
    FEATURE_DASHBOARD_USER_SETTINGS,
    FEATURE_MANAGE_GAME_CONTENT,
    FEATURE_MANAGE_GAME_OPERATIONS,
    FEATURE_MANAGE_NEWS,
    _user_area_ids,
    _user_has_area_all,
    get_feature_area_ids,
    is_valid_feature_id,
    set_feature_areas,
    user_can_access_feature,
)
from app.extensions import db
from app.models import Area, Role, User


def _make_security_user(*, is_admin=True, is_banned=False, role_level=50, username="admin"):
    user = SimpleNamespace(
        id=1,
        username=username,
        is_admin=is_admin,
        is_banned=is_banned,
        role_level=role_level,
    )
    return user


@pytest.mark.usefixtures("isolated_app_context")
def test_check_rate_limit_helpers_and_ip_extraction():
    app = Flask(__name__)
    app.config.update(TESTING=False)

    admin_security_module._rate_limit_cache.clear()
    with app.test_request_context("/admin", environ_base={"REMOTE_ADDR": "10.0.0.2"}):
        assert admin_security_module._get_client_ip() == "10.0.0.2"
        assert admin_security_module._is_ip_whitelisted("10.0.0.2") is True
        assert admin_security_module._check_rate_limit("u1", "1/minute") is True
        assert admin_security_module._check_rate_limit("u1", "1/minute") is False
        assert admin_security_module._check_rate_limit("u2", "bad-format") is True
        assert admin_security_module._check_rate_limit("u3", "5/fortnight") is True

    with app.test_request_context("/admin", headers={"X-Forwarded-For": "203.0.113.5, 10.0.0.2"}):
        assert admin_security_module._get_client_ip() == "203.0.113.5"

    app.config.update(TESTING=True, ADMIN_IP_WHITELIST=["127.0.0.1"])
    with app.test_request_context("/admin", environ_base={"REMOTE_ADDR": "10.0.0.2"}):
        assert admin_security_module._check_rate_limit("u4", "1/minute") is True
        assert admin_security_module._is_ip_whitelisted("10.0.0.2") is False


@pytest.mark.usefixtures("isolated_app_context")
def test_verify_2fa_variants():
    no_attrs = SimpleNamespace()
    assert admin_security_module._verify_2fa(no_attrs) is True

    disabled = SimpleNamespace(two_factor_enabled=False)
    assert admin_security_module._verify_2fa(disabled) is True

    missing_verification = SimpleNamespace(two_factor_enabled=True, two_factor_verified_at=None)
    assert admin_security_module._verify_2fa(missing_verification) is False

    stale = SimpleNamespace(two_factor_enabled=True, two_factor_verified_at=datetime.now(timezone.utc) - timedelta(hours=2))
    assert admin_security_module._verify_2fa(stale) is False

    naive_recent = SimpleNamespace(
        two_factor_enabled=True,
        two_factor_verified_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    assert admin_security_module._verify_2fa(naive_recent) is True


def test_admin_security_config_and_context_helpers(monkeypatch):
    app = Flask(__name__)
    app.config.update(TESTING=True)
    monkeypatch.setattr(admin_security_module, "jwt_required", lambda *args, **kwargs: (lambda f: f))

    user = _make_security_user()
    monkeypatch.setattr(admin_security_module, "get_current_user", lambda: user)
    monkeypatch.setattr(admin_security_module, "current_user_is_super_admin", lambda: True)

    logs = []
    monkeypatch.setattr(admin_security_module, "_log_admin_action", lambda *args, **kwargs: logs.append((args, kwargs)))
    monkeypatch.setattr(admin_security_module, "_log_security_violation", lambda *args, **kwargs: logs.append((args, kwargs)))

    @admin_security_module.admin_security(require_2fa=True, require_super_admin=True, rate_limit="2/minute")
    def endpoint():
        return jsonify({"ok": True})

    with app.test_request_context("/admin/test", method="POST"):
        response = endpoint()
        assert response.status_code == 200
        assert response.get_json() == {"ok": True}
        assert isinstance(admin_security_module.get_admin_security_context(), AdminSecurityConfig)
        assert admin_security_module.get_admin_security_user() is user
        assert logs


def test_admin_security_rejects_unauthorized_conditions(monkeypatch):
    app = Flask(__name__)
    app.config.update(TESTING=False, ADMIN_IP_WHITELIST=["127.0.0.1"])
    monkeypatch.setattr(admin_security_module, "jwt_required", lambda *args, **kwargs: (lambda f: f))

    admin_security_module._rate_limit_cache.clear()
    violations = []
    monkeypatch.setattr(admin_security_module, "_log_admin_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_security_module, "_log_security_violation", lambda *args, **kwargs: violations.append((args, kwargs)))

    @admin_security_module.admin_security(require_super_admin=True, require_2fa=True, rate_limit="1/minute")
    def endpoint():
        return jsonify({"ok": True})

    with app.test_request_context("/admin", environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        monkeypatch.setattr(admin_security_module, "get_current_user", lambda: None)
        response, status = endpoint()
        assert status == 401
        assert response.get_json() == {"error": "Unauthorized"}

    with app.test_request_context("/admin", environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        monkeypatch.setattr(admin_security_module, "get_current_user", lambda: _make_security_user(is_banned=True))
        response, status = endpoint()
        assert status == 401

    with app.test_request_context("/admin", environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        monkeypatch.setattr(admin_security_module, "get_current_user", lambda: _make_security_user(is_admin=False, username="mod"))
        response, status = endpoint()
        assert status == 403
        assert response.get_json() == {"error": "Forbidden"}

    with app.test_request_context("/admin", environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        monkeypatch.setattr(admin_security_module, "get_current_user", lambda: _make_security_user(role_level=50))
        monkeypatch.setattr(admin_security_module, "current_user_is_super_admin", lambda: False)
        response, status = endpoint()
        assert status == 403
        assert response.get_json()["code"] == "INSUFFICIENT_PRIVILEGE"

    with app.test_request_context("/admin", environ_base={"REMOTE_ADDR": "10.0.0.1"}):
        monkeypatch.setattr(admin_security_module, "get_current_user", lambda: _make_security_user(role_level=100))
        monkeypatch.setattr(admin_security_module, "current_user_is_super_admin", lambda: True)
        response, status = endpoint()
        assert status == 403
        assert response.get_json()["code"] == "IP_NOT_WHITELISTED"

    with app.test_request_context("/admin", environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        user_with_2fa = _make_security_user(role_level=100)
        user_with_2fa.two_factor_enabled = True
        user_with_2fa.two_factor_verified_at = None
        monkeypatch.setattr(admin_security_module, "get_current_user", lambda: user_with_2fa)
        monkeypatch.setattr(admin_security_module, "current_user_is_super_admin", lambda: True)
        response, status = endpoint()
        assert status == 403
        assert response.get_json()["code"] == "2FA_REQUIRED"

    fresh_user = _make_security_user(role_level=100, username="success_user")
    fresh_user.id = 999
    fresh_user.two_factor_enabled = True
    fresh_user.two_factor_verified_at = datetime.now(timezone.utc)
    with app.test_request_context("/admin", environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        monkeypatch.setattr(admin_security_module, "get_current_user", lambda: fresh_user)
        monkeypatch.setattr(admin_security_module, "current_user_is_super_admin", lambda: True)
        response = endpoint()
        assert response.status_code == 200

    with app.test_request_context("/admin", environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        monkeypatch.setattr(admin_security_module, "get_current_user", lambda: fresh_user)
        monkeypatch.setattr(admin_security_module, "current_user_is_super_admin", lambda: True)
        response, status = endpoint()
        assert status == 429
        assert response.get_json()["code"] == "RATE_LIMIT_EXCEEDED"

    assert violations


def test_admin_security_logs_and_reraises_errors(monkeypatch):
    app = Flask(__name__)
    app.config.update(TESTING=True)
    monkeypatch.setattr(admin_security_module, "jwt_required", lambda *args, **kwargs: (lambda f: f))
    monkeypatch.setattr(admin_security_module, "get_current_user", lambda: _make_security_user())
    monkeypatch.setattr(admin_security_module, "current_user_is_super_admin", lambda: True)

    violations = []
    monkeypatch.setattr(admin_security_module, "_log_admin_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_security_module, "_log_security_violation", lambda *args, **kwargs: violations.append((args, kwargs)))

    @admin_security_module.admin_security()
    def endpoint():
        raise RuntimeError("boom")

    with app.test_request_context("/admin/error", method="DELETE"):
        with pytest.raises(RuntimeError, match="boom"):
            endpoint()

    assert violations


def test_feature_registry_area_and_role_logic(app):
    with app.app_context():
        admin_role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
        moderator_role = Role.query.filter_by(name=Role.NAME_MODERATOR).first()
        user_role = Role.query.filter_by(name=Role.NAME_USER).first()

        admin = User(username="feature-admin", password_hash=generate_password_hash("pw"), role_id=admin_role.id)
        moderator = User(username="feature-mod", password_hash=generate_password_hash("pw"), role_id=moderator_role.id)
        regular = User(username="feature-user", password_hash=generate_password_hash("pw"), role_id=user_role.id)
        banned = User(username="feature-banned", password_hash=generate_password_hash("pw"), role_id=admin_role.id, is_banned=True)
        db.session.add_all([admin, moderator, regular, banned])
        db.session.commit()

        area_all = Area.query.filter_by(slug=Area.SLUG_ALL).first()
        area_game = Area.query.filter_by(slug="game").first()
        area_wiki = Area.query.filter_by(slug="wiki").first()

        moderator.areas.append(area_game)
        admin.areas.append(area_all)
        regular.areas.append(area_wiki)
        db.session.commit()

        assert is_valid_feature_id(FEATURE_MANAGE_NEWS) is True
        assert is_valid_feature_id("missing.feature") is False
        assert _user_has_area_all(admin) is True
        assert _user_has_area_all(moderator) is False
        assert area_game.id in _user_area_ids(moderator)
        assert _user_area_ids(None) == set()

        set_feature_areas(FEATURE_MANAGE_GAME_CONTENT, [area_game.id])
        assert get_feature_area_ids(FEATURE_MANAGE_GAME_CONTENT) == [area_game.id]

        set_feature_areas(FEATURE_MANAGE_GAME_CONTENT, [])
        assert get_feature_area_ids(FEATURE_MANAGE_GAME_CONTENT) == []

        with pytest.raises(ValueError, match="Unknown feature_id"):
            set_feature_areas("missing.feature", [area_game.id])

        set_feature_areas(FEATURE_MANAGE_GAME_OPERATIONS, [area_game.id])
        assert user_can_access_feature(admin, FEATURE_MANAGE_GAME_OPERATIONS) is True
        assert user_can_access_feature(moderator, FEATURE_MANAGE_GAME_OPERATIONS) is True

        # Admin with no user_areas: must still see area-scoped features (no assignment = no area filter).
        admin_no_areas = User(
            username="feature-admin-no-areas",
            password_hash=generate_password_hash("pw"),
            role_id=admin_role.id,
        )
        db.session.add(admin_no_areas)
        db.session.commit()
        assert user_can_access_feature(admin_no_areas, FEATURE_MANAGE_GAME_OPERATIONS) is True
        assert user_can_access_feature(regular, FEATURE_MANAGE_GAME_OPERATIONS) is False
        assert user_can_access_feature(banned, FEATURE_MANAGE_GAME_OPERATIONS) is False
        assert user_can_access_feature(None, FEATURE_MANAGE_GAME_OPERATIONS) is False
        assert user_can_access_feature(admin, "missing.feature") is False

        assert user_can_access_feature(regular, FEATURE_DASHBOARD_USER_SETTINGS) is True
        assert user_can_access_feature(moderator, FEATURE_MANAGE_NEWS) is True
        assert user_can_access_feature(moderator, FEATURE_DASHBOARD_METRICS) is False
