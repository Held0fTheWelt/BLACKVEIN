"""Tests for web (server-rendered) routes."""
import pytest


def test_home_returns_200(client):
    """GET / returns 200 and renders home."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"WORLD OF SHADOWS" in response.data or b"BLACKVEIN" in response.data or b"Welcome" in response.data


def test_web_health_returns_ok(client):
    """GET /health returns JSON status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_wiki_returns_200(client):
    """GET /wiki returns 200 and wiki page (Markdown content or placeholder)."""
    response = client.get("/wiki")
    assert response.status_code == 200
    assert b"Wiki" in response.data


def test_login_get_returns_200(client):
    """GET /login shows login form."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"login" in response.data.lower() or b"username" in response.data.lower()


def test_login_post_invalid_credentials(client):
    """POST /login with wrong credentials shows error and does not redirect."""
    response = client.post(
        "/login",
        data={"username": "nobody", "password": "wrong"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Invalid" in response.data or b"error" in response.data.lower()


def test_login_post_success_redirects_to_dashboard(client, test_user):
    """POST /login with valid credentials redirects to dashboard and sets session."""
    user, password = test_user
    response = client.post(
        "/login",
        data={"username": user.username, "password": password},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome" in response.data or b"Dashboard" in response.data


def test_login_get_when_logged_in_redirects_to_dashboard(client, test_user):
    """GET /login when already logged in redirects to dashboard."""
    user, password = test_user
    client.post("/login", data={"username": user.username, "password": password})
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 302
    assert "dashboard" in response.location or response.headers.get("Location", "").endswith("/dashboard")


def test_login_banned_user_redirects_to_blocked(client, banned_user):
    """POST /login with banned user redirects to /blocked and shows restricted message."""
    user, password = banned_user
    response = client.post(
        "/login",
        data={"username": user.username, "password": password},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"restricted" in response.data.lower() or b"cannot" in response.data.lower()


def test_blocked_page_returns_200(client):
    """GET /blocked returns 200 and explains access is restricted."""
    response = client.get("/blocked")
    assert response.status_code == 200
    assert b"restricted" in response.data.lower() or b"cannot" in response.data.lower()


def test_get_logout_rejected(client):
    """GET /logout is not allowed; route is POST only."""
    response = client.get("/logout")
    assert response.status_code == 405


def test_logout_post_redirects_and_clears_session(client, test_user):
    """POST /logout redirects to home and clears session (logout is POST only)."""
    user, password = test_user
    client.post("/login", data={"username": user.username, "password": password})
    response = client.post("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Log in" in response.data or b"login" in response.data.lower()


def test_dashboard_anonymous_redirects_to_login(client):
    """GET /dashboard without session redirects to login."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "login" in response.location or "/login" in (response.headers.get("Location") or "")


def test_dashboard_logged_in_returns_200(client, test_user):
    """GET /dashboard with valid session returns 200 and dashboard content."""
    user, password = test_user
    client.post("/login", data={"username": user.username, "password": password})
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Dashboard" in response.data or user.username.encode() in response.data


def test_login_post_without_csrf_rejected(client_csrf):
    """POST /login without valid CSRF token is rejected when CSRF is enabled."""
    from app.extensions import db
    from app.models import Role, User
    from app.models.role import ensure_roles_seeded
    from werkzeug.security import generate_password_hash
    with client_csrf.application.app_context():
        db.create_all()
        ensure_roles_seeded()
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        u = User(
            username="csrftest",
            password_hash=generate_password_hash("Csrfpass1"),
            role_id=role.id,
        )
        db.session.add(u)
        db.session.commit()
    response = client_csrf.post(
        "/login",
        data={"username": "csrftest", "password": "Csrfpass1"},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_404_returns_custom_page(client):
    """Unknown route returns 404 and custom template."""
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert b"not found" in response.data.lower() or b"404" in response.data


# --- Register ---
def test_register_get_returns_200(client):
    """GET /register returns 200 and form."""
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Create account" in response.data or b"register" in response.data.lower()
    assert b"username" in response.data.lower()
    assert b"password" in response.data.lower()


def test_register_post_without_email_redirects_to_login_when_email_optional(client):
    """POST /register without email redirects to login when REGISTRATION_REQUIRE_EMAIL is False (default)."""
    response = client.post(
        "/register",
        data={
            "username": "noemail",
            "password": "Secret123",
            "password_confirm": "Secret123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "login" in (response.headers.get("Location") or "")


def test_register_post_missing_email_shows_error_when_email_required(client):
    """POST /register without email shows error when REGISTRATION_REQUIRE_EMAIL is True."""
    client.application.config["REGISTRATION_REQUIRE_EMAIL"] = True
    response = client.post(
        "/register",
        data={
            "username": "noemail2",
            "password": "Secret123",
            "password_confirm": "Secret123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Email is required" in response.data or b"error" in response.data.lower()


def test_register_post_success_redirects_to_pending(client):
    """POST /register with valid data redirects to /register/pending (email verification)."""
    response = client.post(
        "/register",
        data={
            "username": "Alice1",
            "email": "a@b.com",
            "password": "Alice123",
            "password_confirm": "Alice123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "register/pending" in (response.headers.get("Location") or "")


def test_register_post_password_mismatch_shows_error(client):
    """POST /register with mismatched passwords shows error."""
    response = client.post(
        "/register",
        data={
            "username": "mismatchuser",
            "email": "mismatch@example.com",
            "password": "Alice123",
            "password_confirm": "Alice456",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"do not match" in response.data or b"Passwords" in response.data


def test_register_post_duplicate_username_shows_error(client, test_user):
    """POST /register with existing username shows error."""
    user, _ = test_user
    response = client.post(
        "/register",
        data={
            "username": user.username,
            "email": "other@example.com",
            "password": "Otherpass1",
            "password_confirm": "Otherpass1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"error" in response.data.lower() or b"taken" in response.data.lower()


def test_register_post_weak_password_shows_error(client):
    """POST /register with weak password shows error."""
    response = client.post(
        "/register",
        data={
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "short",
            "password_confirm": "short",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"error" in response.data.lower() or b"8" in response.data


def test_register_preserves_username_on_error(client):
    """POST /register with error re-renders form with username pre-filled."""
    response = client.post(
        "/register",
        data={
            "username": "prefilluser",
            "email": "prefill@example.com",
            "password": "weak",
            "password_confirm": "weak",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"prefilluser" in response.data


# --- Forgot Password ---
def test_forgot_password_get_returns_200(client):
    """GET /forgot-password returns 200."""
    response = client.get("/forgot-password")
    assert response.status_code == 200
    assert b"Forgot" in response.data or b"email" in response.data.lower()


def test_forgot_password_post_unknown_email_shows_generic_message(client):
    """POST /forgot-password with unknown email still shows success message (no enumeration)."""
    response = client.post(
        "/forgot-password",
        data={"email": "unknown@example.com"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"login" in response.data.lower()
    assert b"If an account" in response.data or b"reset" in response.data.lower()


def test_forgot_password_post_known_email_shows_success_message(
    client, test_user_with_email
):
    """POST /forgot-password with known email shows generic success message."""
    user, _ = test_user_with_email
    response = client.post(
        "/forgot-password",
        data={"email": user.email},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"If an account" in response.data or b"reset" in response.data.lower()


# --- Reset Password ---
def test_reset_password_with_invalid_token_redirects(client):
    """GET /reset-password/<bad-token> redirects to /forgot-password."""
    response = client.get("/reset-password/bad-token", follow_redirects=False)
    assert response.status_code == 302
    assert "forgot-password" in (response.headers.get("Location") or "")


def test_reset_password_flow(client, test_user_with_email, app):
    """Full flow: create token, GET reset page, POST new password, login with new password."""
    from app.services.user_service import create_password_reset_token

    user, _ = test_user_with_email
    with app.app_context():
        raw_token = create_password_reset_token(user)
    response = client.get(f"/reset-password/{raw_token}")
    assert response.status_code == 200
    assert b"password" in response.data.lower()
    response = client.post(
        f"/reset-password/{raw_token}",
        data={
            "password": "Newpass123",
            "password_confirm": "Newpass123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"login" in response.data.lower() or b"Log in" in response.data
    response = client.post(
        "/login",
        data={"username": user.username, "password": "Newpass123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Dashboard" in response.data or b"Welcome" in response.data


def test_reset_password_token_unusable_after_use(client, test_user_with_email, app):
    """Token cannot be used a second time after successful reset."""
    from app.services.user_service import create_password_reset_token

    user, _ = test_user_with_email
    with app.app_context():
        raw_token = create_password_reset_token(user)
    response = client.post(
        f"/reset-password/{raw_token}",
        data={
            "password": "Firstpass1",
            "password_confirm": "Firstpass1",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    response = client.get(f"/reset-password/{raw_token}", follow_redirects=False)
    assert response.status_code == 302
    assert "forgot-password" in (response.headers.get("Location") or "")


def test_reset_password_mismatch_shows_error(client, test_user_with_email, app):
    """POST /reset-password with mismatched passwords shows error."""
    from app.services.user_service import create_password_reset_token

    user, _ = test_user_with_email
    with app.app_context():
        raw_token = create_password_reset_token(user)
    response = client.post(
        f"/reset-password/{raw_token}",
        data={
            "password": "Newpass123",
            "password_confirm": "Otherpass1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"do not match" in response.data or b"Passwords" in response.data


def test_register_pending_get_returns_200(client):
    """GET /register/pending shows instructions."""
    response = client.get("/register/pending")
    assert response.status_code == 200
    assert b"email" in response.data.lower() or b"verify" in response.data.lower()


def test_activate_valid_token_redirects_to_login(client, app):
    """Activate with valid token sets email_verified_at and redirects to login with success."""
    from app.services.user_service import create_user, create_email_verification_token

    with app.app_context():
        user, _ = create_user("activateuser", "Activate1", "activate@example.com")
        raw_token = create_email_verification_token(user, ttl_hours=24)
    response = client.get(f"/activate/{raw_token}", follow_redirects=False)
    assert response.status_code == 302
    assert "login" in (response.headers.get("Location") or "")
    response = client.get(f"/activate/{raw_token}", follow_redirects=True)
    assert response.status_code == 200
    assert b"invalid" in response.data.lower() or b"expired" in response.data.lower()


def test_login_blocked_for_unverified_user_when_verification_enabled(client, app):
    """User with email but no email_verified_at cannot log in (web) when verification is enabled."""
    from app.extensions import db
    from app.models import Role, User
    from werkzeug.security import generate_password_hash

    with app.app_context():
        app.config["EMAIL_VERIFICATION_ENABLED"] = True
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="unverifieduser",
            email="unverified@example.com",
            password_hash=generate_password_hash("Unverified1"),
            email_verified_at=None,
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()
    response = client.post(
        "/login",
        data={"username": "unverifieduser", "password": "Unverified1"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"verify" in response.data.lower()
    assert b"Dashboard" not in response.data


def test_resend_verification_get_returns_200(client):
    """GET /resend-verification returns 200."""
    response = client.get("/resend-verification")
    assert response.status_code == 200
    assert b"resend" in response.data.lower() or b"verification" in response.data.lower()
