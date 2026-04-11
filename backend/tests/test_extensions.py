"""Tests for app.extensions: TestLimiter, get_rate_limit_key, JWT blocklist callback."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from flask import Flask, jsonify
from flask_jwt_extended import create_access_token

from app.extensions import TestLimiter as ExtensionsTestLimiter, get_rate_limit_key, jwt
from app.models import RefreshToken, TokenBlacklist


def test_test_limiter_returns_429_after_burst():
    limiter = ExtensionsTestLimiter()

    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/limited")
    @limiter.limit("2 per minute")
    def _view():
        return jsonify({"ok": True})

    client = app.test_client()
    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 200
    r3 = client.get("/limited")
    assert r3.status_code == 429
    assert r3.get_json().get("error") == "Too many requests"


def test_get_rate_limit_key_remote_address(app):
    with app.test_request_context(environ_base={"REMOTE_ADDR": "198.51.100.10"}):
        assert get_rate_limit_key() == "198.51.100.10"


def test_get_rate_limit_key_prefers_jwt_identity(app, test_user):
    user, _ = test_user
    with app.app_context():
        token = create_access_token(identity=str(user.id))
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        key = get_rate_limit_key()
    assert key == f"user:{user.id}"


def test_jwt_blocklist_loader_revoked_refresh_token(app, test_user):
    user, _ = test_user
    with app.app_context():
        RefreshToken.create(user.id, "blocklist-refresh-jti", "hashblk", 604800)
        RefreshToken.revoke(user.id, "blocklist-refresh-jti")
        payload = {
            "jti": "blocklist-refresh-jti",
            "type": "refresh",
            "sub": str(user.id),
        }
        assert jwt._token_in_blocklist_callback(None, payload) is True


def test_jwt_blocklist_loader_access_token_blacklisted(app, test_user):
    user, _ = test_user
    with app.app_context():
        TokenBlacklist.add(
            "access-blacklist-jti",
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        payload = {"jti": "access-blacklist-jti", "type": "access"}
        assert jwt._token_in_blocklist_callback(None, payload) is True


def test_jwt_blocklist_loader_non_revoked_refresh_returns_false(app, test_user):
    user, _ = test_user
    with app.app_context():
        RefreshToken.create(user.id, "valid-refresh-jti", "hashok", 604800)
        payload = {
            "jti": "valid-refresh-jti",
            "type": "refresh",
            "sub": str(user.id),
        }
        assert jwt._token_in_blocklist_callback(None, payload) is False
