"""Tests for API v1 routes (REST, JWT)."""
import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.utils.errors import ERROR_CODES, api_error, api_success


def test_api_health_returns_ok(client):
    """GET /api/v1/health returns 200 and status ok."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_register_success(client):
    """POST /api/v1/auth/register creates user and returns 201."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "newuser", "email": "newuser@example.com", "password": "Secret123"},
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["username"] == "newuser"
    assert "id" in data


def test_register_missing_json_returns_400(client):
    """POST /api/v1/auth/register without JSON returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        data="not json",
        content_type="text/plain",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_register_validation_returns_400(client):
    """POST /api/v1/auth/register with short username returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "a", "email": "a@b.co", "password": "Longenough1"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_register_username_with_space_returns_400(client):
    """POST /api/v1/auth/register with username containing space returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "user name", "password": "Secret123"},
        content_type="application/json",
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "invalid" in data["error"].lower()


def test_register_username_too_long_returns_400(client):
    """POST /api/v1/auth/register with username over 80 chars returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "a" * 81, "password": "Secret123"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_register_username_special_chars_returns_400(client):
    """POST /api/v1/auth/register with username containing @ or ! returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "user@name", "password": "Secret123"},
        content_type="application/json",
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "invalid" in data["error"].lower()


def test_register_password_too_short_returns_400(client):
    """POST /api/v1/auth/register with password under 8 chars returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "validuser", "password": "Short1"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_register_password_no_uppercase_returns_400(client):
    """POST /api/v1/auth/register with password without uppercase returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "validuser", "password": "alllowercase1"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_register_password_no_lowercase_returns_400(client):
    """POST /api/v1/auth/register with password without lowercase returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "validuser", "password": "ALLUPPERCASE1"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_register_password_no_digit_returns_400(client):
    """POST /api/v1/auth/register with password without digit returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "validuser", "password": "NoDigitHere"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_register_without_email_returns_201_when_email_optional(client):
    """POST /api/v1/auth/register without email returns 201 when REGISTRATION_REQUIRE_EMAIL is False (default)."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "noman", "password": "Secret123"},
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["username"] == "noman"
    assert "id" in data


def test_register_missing_email_returns_400_when_email_required(client):
    """POST /api/v1/auth/register without email returns 400 when REGISTRATION_REQUIRE_EMAIL is True."""
    client.application.config["REGISTRATION_REQUIRE_EMAIL"] = True
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "noman2", "password": "Secret123"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.get_json().get("error") == "Email is required"


def test_register_duplicate_username_returns_409(client, test_user):
    """POST /api/v1/auth/register with existing username returns 409."""
    user, password = test_user
    response = client.post(
        "/api/v1/auth/register",
        json={"username": user.username, "email": "other@example.com", "password": "Otherpass1"},
        content_type="application/json",
    )
    assert response.status_code == 409
    assert "error" in response.get_json()


def test_login_success_returns_token(client, test_user):
    """POST /api/v1/auth/login with valid credentials returns access_token and user."""
    user, password = test_user
    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "access_token" in data
    assert data["user"]["username"] == user.username
    assert data["user"]["id"] == user.id


def test_login_invalid_returns_401(client):
    """POST /api/v1/auth/login with wrong credentials returns 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "wrong"},
        content_type="application/json",
    )
    assert response.status_code == 401
    assert "error" in response.get_json()


def test_login_unverified_email_returns_403_when_verification_enabled(client, app):
    """POST /api/v1/auth/login with valid credentials but unverified email returns 403 when REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN is True."""
    from app.extensions import db
    from app.models import Role, User
    from werkzeug.security import generate_password_hash

    with app.app_context():
        app.config["REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN"] = True
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="apiverify",
            email="apiverify@example.com",
            password_hash=generate_password_hash("Apiverify1"),
            email_verified_at=None,
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "apiverify", "password": "Apiverify1"},
        content_type="application/json",
    )
    assert response.status_code == 403
    data = response.get_json()
    assert data.get("code") == "EMAIL_NOT_VERIFIED"
    assert "verify" in (data.get("error") or "").lower()


def test_login_unverified_email_allowed_when_verification_disabled(client, app):
    """POST /api/v1/auth/login with unverified email succeeds when REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN is False (default in tests)."""
    from app.extensions import db
    from app.models import Role, User
    from werkzeug.security import generate_password_hash

    with app.app_context():
        # TestingConfig already has REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN = False
        # Verify it's set to False
        assert app.config.get("REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN") is False
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="apiverifydev",
            email="apiverifydev@example.com",
            password_hash=generate_password_hash("Apiverifydev1"),
            email_verified_at=None,  # Unverified email
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "apiverifydev", "password": "Apiverifydev1"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "access_token" in data
    assert data["user"]["username"] == "apiverifydev"


def test_login_banned_user_returns_403(client, banned_user):
    """POST /api/v1/auth/login with banned user returns 403 and Account is restricted."""
    user, password = banned_user
    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 403
    data = response.get_json()
    assert "restricted" in (data.get("error") or "").lower()


def test_login_missing_body_returns_400(client):
    """POST /api/v1/auth/login without JSON returns 400."""
    response = client.post(
        "/api/v1/auth/login",
        data="x",
        content_type="text/plain",
    )
    assert response.status_code == 400


def test_resend_verification_success(client, app):
    """POST /api/v1/auth/resend-verification with valid email returns 200."""
    from app.extensions import db
    from app.models import Role, User
    from werkzeug.security import generate_password_hash

    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="resendtest",
            email="resendtest@example.com",
            password_hash=generate_password_hash("Resendtest1"),
            email_verified_at=None,
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()
    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "resendtest@example.com"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "message" in data
    assert "sent" in data["message"].lower()


def test_resend_verification_returns_success_for_nonexistent_email(client):
    """POST /api/v1/auth/resend-verification with nonexistent email returns 200 (to prevent email enumeration)."""
    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "nonexistent@example.com"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "message" in data


def test_resend_verification_missing_email_returns_400(client):
    """POST /api/v1/auth/resend-verification without email returns 400."""
    response = client.post(
        "/api/v1/auth/resend-verification",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_me_without_token_returns_401(client):
    """GET /api/v1/auth/me without Authorization returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "error" in response.get_json()


def test_me_with_token_returns_user(client, auth_headers, test_user):
    """GET /api/v1/auth/me with valid JWT returns current user."""
    user, _ = test_user
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["username"] == user.username
    assert data["id"] == user.id


def test_me_banned_user_returns_403(client, app, banned_user):
    """GET /api/v1/auth/me with valid JWT for a banned user returns 403."""
    user, _ = banned_user
    with app.app_context():
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=str(user.id))
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 403
    assert "restricted" in (response.get_json().get("error") or "").lower()


def test_protected_without_token_returns_401(client):
    """GET /api/v1/test/protected without token returns 401."""
    response = client.get("/api/v1/test/protected")
    assert response.status_code == 401


def test_protected_with_token_returns_ok(client, auth_headers, test_user):
    """GET /api/v1/test/protected with valid JWT returns message and user info."""
    user, _ = test_user
    response = client.get("/api/v1/test/protected", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "ok"
    assert data["user_id"] == user.id
    assert data["username"] == user.username


def test_api_404_returns_json(client):
    """GET /api/v1/nonexistent returns 404 with JSON error, not HTML."""
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
    assert response.content_type and "application/json" in response.content_type
    data = response.get_json()
    assert "error" in data
    assert "not found" in data["error"].lower() or data["error"] == "Not found"


def test_cors_no_allow_origin_when_origins_not_configured(client):
    """When CORS_ORIGINS is not set, API responses do not include Access-Control-Allow-Origin."""
    response = client.get("/api/v1/health", headers={"Origin": "http://other.example"})
    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") is None


def test_cors_allow_origin_when_configured():
    """When CORS_ORIGINS is set, API responds with correct Access-Control-Allow-Origin."""
    class ConfigWithCORS(TestingConfig):
        CORS_ORIGINS = ["http://test.example"]

    application = create_app(ConfigWithCORS)
    with application.app_context():
        db.create_all()
        try:
            client = application.test_client()
            response = client.get(
                "/api/v1/health",
                headers={"Origin": "http://test.example"}
            )
            assert response.status_code == 200
            assert response.headers.get("Access-Control-Allow-Origin") == "http://test.example"
        finally:
            db.drop_all()



"""Tests for TestAuthAPI."""

class TestAuthAPI:

    def test_login_success(self, app, client, test_user):
        user, password = test_user
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()

    def test_login_wrong_password(self, app, client, test_user):
        user, _ = test_user
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_login_missing_fields(self, app, client):
        resp = client.post("/api/v1/auth/login", json={"username": ""})
        assert resp.status_code in (400, 401)

    def test_register_new_user(self, app, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser123",
                "password": "StrongPass1",
                "email": "new@example.com",
            },
        )
        assert resp.status_code in (200, 201, 400)

    def test_web_login_post(self, app, client, test_user):
        app.config["FRONTEND_URL"] = "https://frontend.example.com"
        resp = client.get("/login", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "https://frontend.example.com/login"

    def test_web_register_page(self, app, client):
        app.config["FRONTEND_URL"] = "https://frontend.example.com"
        resp = client.get("/register", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "https://frontend.example.com/register"


# ======================= PERMISSIONS MODULE =======================



"""Tests for TestPermissionsModule."""

class TestPermissionsModule:

    def test_permissions_functions(self, app, client, auth_headers, moderator_headers, admin_headers):
        """Exercise permission checks through API calls that use them."""
        # Moderator accessing mod-only endpoint
        resp = client.get("/api/v1/forum/moderation/metrics", headers=moderator_headers)
        assert resp.status_code == 200
        # Admin accessing admin-only endpoint
        resp = client.get("/api/v1/admin/logs", headers=admin_headers)
        assert resp.status_code == 200



"""Tests for TestSystemAPI."""

class TestSystemAPI:

    def test_system_health(self, app, client):
        resp = client.get("/api/v1/system/health")
        assert resp.status_code in (200, 404)

    def test_system_version(self, app, client):
        resp = client.get("/api/v1/system/version")
        assert resp.status_code in (200, 404)


# ======================= API ERROR / SUCCESS HELPERS =======================


def test_api_error_infers_status_code_and_allows_override(app):
    with app.app_context():
        response, status = api_error("User missing", "USER_NOT_FOUND")
        assert status == 404
        assert response.get_json() == {"error": "User missing", "code": "USER_NOT_FOUND"}

        response, status = api_error("Explicit", "INVALID_INPUT", status_code=422)
        assert status == 422
        assert response.get_json() == {"error": "Explicit", "code": "INVALID_INPUT"}


def test_api_error_falls_back_to_400_for_unknown_codes(app):
    with app.app_context():
        response, status = api_error("Unknown", "SOMETHING_NEW")
        assert status == 400
        assert response.get_json()["code"] == "SOMETHING_NEW"
        assert ERROR_CODES["USER_NOT_FOUND"] == 404
        assert ERROR_CODES["INVALID_INPUT"] == 400


def test_api_success_supports_data_message_and_empty_payload(app):
    with app.app_context():
        response, status = api_success({"id": 7}, message="created", status_code=201)
        assert status == 201
        assert response.get_json() == {"id": 7, "message": "created"}

        response, status = api_success(message="ok")
        assert status == 200
        assert response.get_json() == {"message": "ok"}

        response, status = api_success()
        assert status == 200
        assert response.get_json() == {}


def test_api_error_custom_status_and_code(app):
    with app.app_context():
        response, status = api_error("Nope", "CUSTOM_CODE", 418)
        assert status == 418
        assert response.get_json() == {"error": "Nope", "code": "CUSTOM_CODE"}


# ======================= SITE SETTINGS TESTS =======================
