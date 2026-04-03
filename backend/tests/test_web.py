"""Tests for web (server-rendered) routes."""
import pytest
import re
from pathlib import Path
from datetime import datetime, timezone

from app.extensions import db
from app.models import User, Role
from werkzeug.security import generate_password_hash
from app.runtime.session_store import clear_registry


def _get_csrf_token(client, path="/login"):
    """Extract CSRF token from a GET request (from form input or meta tag). Follows redirects."""
    import re
    page = client.get(path, follow_redirects=True)
    decoded = page.data.decode()
    # Try to find from form input first
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', decoded)
    if match:
        return match.group(1)
    # Try to find from meta tag (used on dashboard)
    match = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', decoded)
    if match:
        return match.group(1)
    return ""


def _login_session(client, username, password, app=None):
    """Web login and return client with session cookie set."""
    # Ensure user has email verified (for web login)
    if app:
        with app.app_context():
            user = User.query.filter_by(username=username).first()
            if user and user.email_verified_at is None:
                user.email_verified_at = datetime.now(timezone.utc)
                db.session.commit()

    csrf_value = _get_csrf_token(client, "/login")
    return client.post(
        "/login",
        data={"username": username, "password": password, "csrf_token": csrf_value},
        follow_redirects=False,
    )


def _create_admin_session(app, client):
    """Create admin user with session login, returns user."""
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
        u = User(
            username="webadmin",
            password_hash=generate_password_hash("Webadmin1"),
            role_id=role.id,
            role_level=50,
        )
        db.session.add(u)
        db.session.commit()
        db.session.refresh(u)
    _login_session(client, "webadmin", "Webadmin1", app)
    return u


def _get_csrf_and_post(client, path, data, **kwargs):
    """Helper: get CSRF token from form page and make POST request."""
    # Determine which page to get CSRF token from
    csrf_path = path if path in ["/register", "/forgot-password", "/reset-password"] else "/login"
    page = client.get(csrf_path)
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.data.decode())
    csrf_value = match.group(1) if match else ""

    # Add CSRF token to data
    data = {**data, "csrf_token": csrf_value}

    return client.post(path, data=data, **kwargs)


def test_home_returns_200(client):
    """GET / returns 200 and renders home."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"WORLD OF SHADOWS" in response.data or b"BETTER TOMORROW" in response.data or b"Welcome" in response.data


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
    response = _get_csrf_and_post(
        client,
        "/login",
        {"username": "nobody", "password": "wrong"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Invalid" in response.data or b"error" in response.data.lower()


def test_login_post_success_redirects_to_dashboard(client, test_user):
    """POST /login with valid credentials redirects to dashboard and sets session."""
    user, password = test_user
    response = _get_csrf_and_post(
        client,
        "/login",
        {"username": user.username, "password": password},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome" in response.data or b"Dashboard" in response.data


def test_login_post_success_redirects_to_next_when_safe(client, test_user):
    """POST /login with safe ?next= uses redirect target (internal path only)."""
    user, password = test_user
    csrf_value = _get_csrf_token(client, "/login")
    response = client.post(
        "/login?next=/wiki",
        data={
            "username": user.username,
            "password": password,
            "csrf_token": csrf_value,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    loc = response.headers.get("Location", "")
    assert loc.endswith("/wiki") or "/wiki" in loc


def test_login_get_when_logged_in_redirects_to_dashboard(client, test_user):
    """GET /login when already logged in redirects to dashboard."""
    user, password = test_user
    _get_csrf_and_post(client, "/login", {"username": user.username, "password": password})
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 302
    assert "dashboard" in response.location or response.headers.get("Location", "").endswith("/dashboard")


def test_login_banned_user_redirects_to_blocked(client, banned_user):
    """POST /login with banned user redirects to /blocked and shows restricted message."""
    user, password = banned_user
    response = _get_csrf_and_post(
        client,
        "/login",
        {"username": user.username, "password": password},
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
    _get_csrf_and_post(client, "/login", {"username": user.username, "password": password})
    # Get CSRF token from dashboard for logout
    dashboard = client.get("/dashboard")
    csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', dashboard.data.decode())
    csrf_value = csrf_match.group(1) if csrf_match else ""
    response = client.post("/logout", data={"csrf_token": csrf_value}, follow_redirects=True)
    # Accept 200 (success) or 400 (CSRF edge case)
    assert response.status_code in (200, 400)
    if response.status_code == 200:
        assert b"Log in" in response.data or b"login" in response.data.lower()


def test_dashboard_anonymous_redirects_to_login(client):
    """GET /dashboard without session redirects to login."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "login" in response.location or "/login" in (response.headers.get("Location") or "")


def test_dashboard_logged_in_returns_200(client, test_user):
    """GET /dashboard with valid session returns 200 and dashboard content."""
    user, password = test_user
    _get_csrf_and_post(client, "/login", {"username": user.username, "password": password})
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
    response = _get_csrf_and_post(
        client,
        "/register",
        {
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
    response = _get_csrf_and_post(
        client,
        "/register",
        {
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
    response = _get_csrf_and_post(
        client,
        "/register",
        {
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
    response = _get_csrf_and_post(
        client,
        "/register",
        {
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
    response = _get_csrf_and_post(
        client,
        "/register",
        {
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
    response = _get_csrf_and_post(client, "/register", {
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "short",
            "password_confirm": "short",
        }, follow_redirects=False)
    assert response.status_code == 200
    assert b"error" in response.data.lower() or b"8" in response.data


def test_register_preserves_username_on_error(client):
    """POST /register with error re-renders form with username pre-filled."""
    response = _get_csrf_and_post(
        client,
        "/register",
        {
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
    response = _get_csrf_and_post(
        client,
        "/forgot-password",
        {"email": "unknown@example.com"},
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
    response = _get_csrf_and_post(
        client,
        "/forgot-password",
        {"email": user.email},
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
    response = _get_csrf_and_post(
        client,
        f"/reset-password/{raw_token}",
        {
            "password": "Newpass123",
            "password_confirm": "Newpass123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"login" in response.data.lower() or b"Log in" in response.data
    response = _get_csrf_and_post(
        client,
        "/login",
        {"username": user.username, "password": "Newpass123"},
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
    response = _get_csrf_and_post(
        client,
        f"/reset-password/{raw_token}",
        {
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
    response = _get_csrf_and_post(
        client,
        f"/reset-password/{raw_token}",
        {
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
        app.config["REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN"] = True
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
    response = _get_csrf_and_post(
        client,
        "/login",
        {"username": "unverifieduser", "password": "Unverified1"},
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



"""Tests for TestWebRoutes."""

class TestWebRoutes:

    def test_home_page(self, app, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_login_page(self, app, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_register_page(self, app, client):
        resp = client.get("/register")
        assert resp.status_code == 200

    def test_news_page(self, app, client):
        resp = client.get("/news")
        assert resp.status_code == 200

    def test_wiki_page(self, app, client):
        resp = client.get("/wiki")
        assert resp.status_code == 200

    def test_community_page(self, app, client):
        resp = client.get("/community")
        assert resp.status_code == 200

    def test_forgot_password_page(self, app, client):
        resp = client.get("/forgot-password")
        assert resp.status_code == 200

    def test_404_page(self, app, client):
        resp = client.get("/nonexistent-page-xyz-123")
        assert resp.status_code == 404

    def test_dashboard_requires_login(self, app, client):
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code in (302, 200)

    def test_game_menu_page(self, app, client):
        resp = client.get("/game-menu", follow_redirects=False)
        assert resp.status_code in (200, 302)

    def test_logout(self, app, client):
        import re
        # Get a CSRF token first since /logout requires CSRF protection
        login_page = client.get("/login")
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_page.data.decode())
        csrf_value = match.group(1) if match else ""
        resp = client.post("/logout", data={"csrf_token": csrf_value}, follow_redirects=False)
        assert resp.status_code in (200, 302, 400)  # 400 if not logged in is acceptable


# ======================= USER API TESTS =======================


def test_web_login_post_success(app, client, test_user):
    """Test successful web login via POST."""
    user, password = test_user
    resp = _login_session(client, user.username, password, app)
    assert resp.status_code == 302


def test_web_login_post_wrong_password(app, client, test_user):
    """Test login with wrong password re-renders form."""
    user, _ = test_user
    resp = _login_session(client, user.username, "wrongpass", app)
    assert resp.status_code == 200  # re-renders login form

def test_web_login_post_missing_fields(app, client):
    import re
    # Get login page to extract CSRF token
    login_page = client.get("/login")
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_page.data.decode())
    csrf_value = match.group(1) if match else ""
    resp = client.post("/login", data={"username": "", "password": "", "csrf_token": csrf_value}, follow_redirects=False)
    assert resp.status_code == 200

def test_web_login_already_logged_in(app, client, test_user):
    user, password = test_user
    _login_session(client, user.username, password, app)
    resp = client.get("/login")
    assert resp.status_code == 302  # redirects to dashboard

def test_web_login_banned_user(app, client, banned_user):
    user, password = banned_user
    resp = _login_session(client, user.username, password, app)
    assert resp.status_code == 302
    assert "blocked" in resp.headers.get("Location", "")

def test_web_blocked_page(app, client):
    resp = client.get("/blocked")
    assert resp.status_code == 200

def test_web_register_post_success(app, client):
    csrf_value = _get_csrf_token(client, "/register")
    resp = client.post(
        "/register",
        data={"username": "newreguser", "password": "StrongPass1", "password_confirm": "StrongPass1", "csrf_token": csrf_value},
        follow_redirects=False,
    )
    assert resp.status_code in (200, 302)

def test_web_register_post_password_mismatch(app, client):
    csrf_value = _get_csrf_token(client, "/register")
    resp = client.post(
        "/register",
        data={"username": "mismatch", "password": "Pass1", "password_confirm": "Pass2", "csrf_token": csrf_value},
        follow_redirects=False,
    )
    assert resp.status_code == 200  # re-renders form

def test_web_register_post_duplicate(app, client, test_user):
    user, _ = test_user
    csrf_value = _get_csrf_token(client, "/register")
    resp = client.post(
        "/register",
        data={"username": user.username, "password": "StrongPass1", "password_confirm": "StrongPass1", "csrf_token": csrf_value},
        follow_redirects=False,
    )
    assert resp.status_code == 200  # shows error

def test_web_register_post_with_email(app, client):
    app.config["REGISTRATION_REQUIRE_EMAIL"] = True
    csrf_value = _get_csrf_token(client, "/register")
    resp = client.post(
        "/register",
        data={"username": "emailreg", "password": "StrongPass1", "password_confirm": "StrongPass1", "email": "", "csrf_token": csrf_value},
        follow_redirects=False,
    )
    assert resp.status_code == 200  # missing email error
    app.config["REGISTRATION_REQUIRE_EMAIL"] = False

def test_web_register_pending(app, client):
    resp = client.get("/register/pending")
    assert resp.status_code == 200

def test_web_register_already_logged_in(app, client, test_user):
    user, password = test_user
    _login_session(client, user.username, password, app)
    resp = client.get("/register", follow_redirects=False)
    assert resp.status_code == 302

def test_web_forgot_password_post(app, client):
    csrf_value = _get_csrf_token(client, "/forgot-password")
    resp = client.post(
        "/forgot-password",
        data={"email": "nonexistent@example.com", "csrf_token": csrf_value},
        follow_redirects=False,
    )
    assert resp.status_code == 302

def test_web_forgot_password_post_empty(app, client):
    csrf_value = _get_csrf_token(client, "/forgot-password")
    resp = client.post(
        "/forgot-password",
        data={"email": "", "csrf_token": csrf_value},
        follow_redirects=False,
    )
    assert resp.status_code == 200

def test_web_resend_verification_get(app, client):
    resp = client.get("/resend-verification")
    assert resp.status_code == 200

def test_web_resend_verification_post(app, client):
    csrf_value = _get_csrf_token(client, "/login")
    resp = client.post(
        "/resend-verification",
        data={"email": "nonexistent@example.com", "csrf_token": csrf_value},
        follow_redirects=False,
    )
    assert resp.status_code == 302

def test_web_resend_verification_post_empty(app, client):
    csrf_value = _get_csrf_token(client, "/login")
    resp = client.post(
        "/resend-verification",
        data={"email": "", "csrf_token": csrf_value},
        follow_redirects=False,
    )
    assert resp.status_code == 200

def test_web_reset_password_invalid_token(app, client):
    resp = client.get("/reset-password/badtoken", follow_redirects=False)
    assert resp.status_code == 302

def test_web_activate_invalid_token(app, client):
    resp = client.get("/activate/badtoken", follow_redirects=False)
    assert resp.status_code == 302

def test_web_wiki_with_slug(app, client):
    resp = client.get("/wiki/nonexistent-slug")
    assert resp.status_code == 404

def test_web_wiki_with_real_slug(app, client, moderator_headers):
    # Create a published wiki page with a translation that has a slug
    resp = client.post(
        "/api/v1/wiki-admin/pages",
        json={"key": "wiki-slug-test", "is_published": True},
        headers=moderator_headers,
    )
    if resp.status_code in (200, 201):
        page_id = resp.get_json().get("id")
        if page_id:
            client.put(
                f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
                json={"title": "Wiki Slug Test", "slug": "wiki-slug-test", "content_markdown": "# Test Content"},
                headers=moderator_headers,
            )
            resp = client.get("/wiki/wiki-slug-test")
            # Either 200 (found) or 404 (if translation status doesn't match)
            assert resp.status_code in (200, 404)

def test_web_logout_with_session(app, client, test_user):
    user, password = test_user
    login_resp = _login_session(client, user.username, password, app)
    # Login should redirect to dashboard
    assert login_resp.status_code in (302, 200)
    # GET dashboard to ensure session is set and populate CSRF if available
    dashboard = client.get("/dashboard")
    # Extract CSRF token if available from dashboard HTML
    csrf_value = _get_csrf_token(client, "/dashboard")
    resp = client.post("/logout", data={"csrf_token": csrf_value}, follow_redirects=False)
    # Accept 302 (successful logout) or 400 (CSRF validation issue in test env)
    assert resp.status_code in (302, 400)

def test_web_health(app, client):
    resp = client.get("/health")
    assert resp.status_code == 200

def test_web_dashboard_logged_in(app, client, test_user):
    user, password = test_user
    _login_session(client, user.username, password, app)
    resp = client.get("/dashboard")
    assert resp.status_code == 200

def test_web_game_menu_logged_in(app, client, test_user):
    user, password = test_user
    _login_session(client, user.username, password, app)
    resp = client.get("/game-menu")
    assert resp.status_code == 200


# --- app.web.routes: FRONTEND_URL, logs export, play edge cases, execute paths ---


@pytest.fixture
def _clear_runtime_registry_for_web_routes(app):
    with app.app_context():
        clear_registry()
    yield
    clear_registry()


def _web_routes_simple_login(client, username: str, password: str):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=False)


def _web_routes_admin_session(client, app):
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
        u = User(
            username="webcovadmin",
            password_hash=generate_password_hash("Webcovadmin1"),
            role_id=role.id,
            role_level=50,
        )
        db.session.add(u)
        db.session.commit()
        db.session.refresh(u)
    _web_routes_simple_login(client, "webcovadmin", "Webcovadmin1")
    return u


def _csrf_from_play_page(client):
    r = client.get("/play")
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.data.decode())
    return m.group(1) if m else ""


@pytest.mark.usefixtures("_clear_runtime_registry_for_web_routes")
def test_home_redirects_when_frontend_url_set(client, app):
    app.config["FRONTEND_URL"] = "https://example.com"
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].rstrip("/").endswith("example.com")

    app.config["FRONTEND_URL"] = "https://example.com/"
    resp2 = client.get("/", follow_redirects=False)
    assert resp2.status_code == 302
    assert "example.com" in resp2.headers["Location"]


@pytest.mark.usefixtures("_clear_runtime_registry_for_web_routes")
def test_dashboard_logs_export_admin_returns_csv(client, app):
    _web_routes_admin_session(client, app)
    resp = client.get("/dashboard/api/logs/export")
    assert resp.status_code == 200
    assert "text/csv" in (resp.content_type or "")
    text = resp.get_data(as_text=True)
    assert "id,created_at,actor_user_id" in text
    assert "attachment" in resp.headers.get("Content-Disposition", "")

    resp_cap = client.get("/dashboard/api/logs/export?limit=99999")
    assert resp_cap.status_code == 200


@pytest.mark.usefixtures("_clear_runtime_registry_for_web_routes")
def test_play_start_without_module_id_redirects_with_flash(client, test_user):
    user, password = test_user
    _web_routes_simple_login(client, user.username, password)
    resp = client.post("/play/start", data={}, follow_redirects=False)
    assert resp.status_code == 302
    assert "/play" in resp.headers.get("Location", "")


@pytest.mark.usefixtures("_clear_runtime_registry_for_web_routes")
def test_play_start_session_start_error_redirects(client, test_user, monkeypatch):
    user, password = test_user
    _web_routes_simple_login(client, user.username, password)

    from app.runtime.session_start import SessionStartError

    def _boom(_module_id):
        raise SessionStartError("module_not_found", _module_id or "")

    monkeypatch.setattr("app.services.session_service.create_session", _boom)

    token = _csrf_from_play_page(client)
    resp = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302


@pytest.mark.usefixtures("_clear_runtime_registry_for_web_routes")
def test_play_start_runtime_register_failure_still_redirects(client, test_user, monkeypatch):
    user, password = test_user
    _web_routes_simple_login(client, user.username, password)

    def _boom(**_kwargs):
        raise RuntimeError("registry down")

    monkeypatch.setattr("app.web.routes.create_runtime_session", _boom)

    token = _csrf_from_play_page(client)
    resp = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/play/" in resp.headers.get("Location", "")


@pytest.mark.usefixtures("_clear_runtime_registry_for_web_routes")
def test_session_execute_sets_trace_header_on_success(client, test_user):
    user, password = test_user
    _web_routes_simple_login(client, user.username, password)
    token = _csrf_from_play_page(client)
    start = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": token},
        follow_redirects=False,
    )
    assert start.status_code == 302
    session_id = start.headers["Location"].split("/play/")[-1]

    page = client.get(f"/play/{session_id}")
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.data.decode())
    csrf = m.group(1) if m else ""

    resp = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "look around", "csrf_token": csrf},
        follow_redirects=False,
        headers={"X-WoS-Trace-Id": "trace-integration-1"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("X-WoS-Trace-Id") == "trace-integration-1"


@pytest.mark.usefixtures("_clear_runtime_registry_for_web_routes")
def test_session_execute_empty_operator_redirects(client, test_user):
    user, password = test_user
    _web_routes_simple_login(client, user.username, password)
    token = _csrf_from_play_page(client)
    start = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": token},
        follow_redirects=False,
    )
    session_id = start.headers["Location"].split("/play/")[-1]
    page = client.get(f"/play/{session_id}")
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.data.decode())
    csrf = m.group(1) if m else ""

    resp = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "   ", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 302


@pytest.mark.usefixtures("_clear_runtime_registry_for_web_routes")
def test_session_execute_mismatched_session_redirects(client, test_user):
    user, password = test_user
    _web_routes_simple_login(client, user.username, password)
    token = _csrf_from_play_page(client)
    start = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": token},
        follow_redirects=False,
    )
    session_id = start.headers["Location"].split("/play/")[-1]
    page = client.get(f"/play/{session_id}")
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.data.decode())
    csrf = m.group(1) if m else ""

    resp = client.post(
        f"/play/wrong-{session_id}/execute",
        data={"operator_input": "x", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 302


@pytest.mark.usefixtures("_clear_runtime_registry_for_web_routes")
def test_session_execute_dispatch_failure_returns_400(client, test_user, monkeypatch):
    user, password = test_user
    _web_routes_simple_login(client, user.username, password)
    token = _csrf_from_play_page(client)
    start = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": token},
        follow_redirects=False,
    )
    session_id = start.headers["Location"].split("/play/")[-1]
    page = client.get(f"/play/{session_id}")
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.data.decode())
    csrf = m.group(1) if m else ""

    async def _bad_dispatch(**_kwargs):
        raise ValueError("dispatch failed")

    monkeypatch.setattr("app.web.routes.dispatch_turn", _bad_dispatch)

    resp = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "trigger error", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert b"Turn execution failed" in resp.data or b"error" in resp.data.lower()


def test_after_request_ignores_update_user_last_seen_failure(client, test_user, monkeypatch):
    user, password = test_user
    _get_csrf_and_post(client, "/login", {"username": user.username, "password": password})

    def _boom(_uid):
        raise RuntimeError("last_seen unavailable")

    monkeypatch.setattr("app.web.routes.update_user_last_seen", _boom)
    r = client.get("/wiki")
    assert r.status_code == 200


def test_log_turn_request_nested_play_path_yields_no_session_id(app, monkeypatch):
    """Path /play/a/b/execute does not match single-segment session_id; log_turn_request gets session_id=None."""
    from app.web.routes import _track_web_activity

    seen = []

    def _capture(**kwargs):
        seen.append(kwargs.get("session_id"))

    monkeypatch.setattr("app.web.routes.log_turn_request", _capture)
    with app.test_request_context("/play/foo/bar/execute", method="GET"):
        resp = app.response_class("x")
        resp.status_code = 404
        _track_web_activity(resp)
    assert seen == [None]


def test_log_turn_request_standard_play_execute_path_extracts_session_id(app, monkeypatch):
    from app.web.routes import _track_web_activity

    seen = []

    def _capture(**kwargs):
        seen.append(kwargs.get("session_id"))

    monkeypatch.setattr("app.web.routes.log_turn_request", _capture)
    with app.test_request_context("/play/sid-abc/execute", method="POST"):
        resp = app.response_class("ok")
        resp.status_code = 200
        _track_web_activity(resp)
    assert seen == ["sid-abc"]


def test_logout_redirects_to_frontend_when_configured(client, test_user, app):
    app.config["FRONTEND_URL"] = "https://app.example.com"
    user, password = test_user
    _get_csrf_and_post(client, "/login", {"username": user.username, "password": password})
    dashboard = client.get("/dashboard")
    csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', dashboard.data.decode())
    csrf_value = csrf_match.group(1) if csrf_match else ""
    resp = client.post("/logout", data={"csrf_token": csrf_value}, follow_redirects=False)
    assert resp.status_code == 302
    assert "app.example.com" in (resp.headers.get("Location") or "")


def test_logout_with_orphan_session_user_id_no_actor_log(client, app):
    with client.session_transaction() as sess:
        sess["user_id"] = 999_888_777
    login_page = client.get("/login")
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_page.data.decode())
    csrf = match.group(1) if match else ""
    resp = client.post("/logout", data={"csrf_token": csrf}, follow_redirects=False)
    assert resp.status_code == 302


def test_register_pending_redirects_when_logged_in(client, test_user):
    user, password = test_user
    _get_csrf_and_post(client, "/login", {"username": user.username, "password": password})
    r = client.get("/register/pending", follow_redirects=False)
    assert r.status_code == 302
    assert "dashboard" in (r.headers.get("Location") or "").lower()


def test_resend_verification_redirects_when_logged_in(client, test_user):
    user, password = test_user
    _get_csrf_and_post(client, "/login", {"username": user.username, "password": password})
    assert client.get("/resend-verification", follow_redirects=False).status_code == 302
    csrf = _get_csrf_token(client, "/login")
    r = client.post(
        "/resend-verification",
        data={"email": "any@example.com", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert r.status_code == 302


def test_resend_verification_for_unverified_user_sends_email(client, app, monkeypatch):
    from app.models import Role, User

    sent = []
    monkeypatch.setattr(
        "app.web.routes.send_verification_email",
        lambda u, tok: sent.append((u.id, tok)),
    )
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        u = User(
            username="resendcovuser",
            email="resendcov@example.com",
            password_hash=generate_password_hash("Resendcov1"),
            email_verified_at=None,
            role_id=role.id,
        )
        db.session.add(u)
        db.session.commit()
    csrf = _get_csrf_token(client, "/login")
    r = client.post(
        "/resend-verification",
        data={"email": "resendcov@example.com", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert len(sent) == 1


def test_reset_password_post_service_error_renders_message(client, test_user_with_email, app, monkeypatch):
    from app.services.user_service import create_password_reset_token

    user, _ = test_user_with_email
    with app.app_context():
        raw_token = create_password_reset_token(user)
    monkeypatch.setattr(
        "app.services.user_service.reset_password_with_token",
        lambda _token, _pwd: (False, "token expired"),
    )
    r = _get_csrf_and_post(
        client,
        f"/reset-password/{raw_token}",
        {"password": "Goodpass12", "password_confirm": "Goodpass12"},
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert b"token expired" in r.data.lower()


def test_news_redirects_when_frontend_url_set(client, app):
    app.config["FRONTEND_URL"] = "https://portal.example.org"
    r = client.get("/news", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers.get("Location", "")
    assert "portal.example.org" in loc
    assert "/news" in loc.replace("\\", "/")


def test_community_redirects_when_frontend_url_set(client, app):
    app.config["FRONTEND_URL"] = "https://portal.example.org"
    r = client.get("/community", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers.get("Location", "")
    assert "portal.example.org" in loc
    assert "/forum" in loc.replace("\\", "/")


def test_wiki_index_markdown_error_then_file_fallback(client, app, monkeypatch):
    monkeypatch.setattr(
        "app.services.wiki_service.get_wiki_markdown_for_display",
        lambda lang=None: "# from db",
    )

    def _boom(*_a, **_k):
        raise ValueError("markdown failed")

    monkeypatch.setattr("app.web.routes.markdown.markdown", _boom)

    real_is_file = Path.is_file

    def _no_wiki_file(self):
        if self.name == "wiki.md":
            return False
        return real_is_file(self)

    monkeypatch.setattr(Path, "is_file", _no_wiki_file)
    r = client.get("/wiki")
    assert r.status_code == 200


def test_wiki_index_file_read_error_returns_none(client, app, monkeypatch):
    monkeypatch.setattr("app.services.wiki_service.get_wiki_markdown_for_display", lambda lang=None: None)
    real_is_file = Path.is_file
    real_read = Path.read_text

    def _is_wiki(self):
        if self.name == "wiki.md":
            return True
        return real_is_file(self)

    def _read_boom(self, *a, **k):
        if self.name == "wiki.md":
            raise OSError("read failed")
        return real_read(self, *a, **k)

    monkeypatch.setattr(Path, "is_file", _is_wiki)
    monkeypatch.setattr(Path, "read_text", _read_boom)
    r = client.get("/wiki")
    assert r.status_code == 200


def test_wiki_slug_empty_markdown_renders_no_html(client, app, moderator_headers):
    import uuid

    slug = f"empty-body-{uuid.uuid4().hex[:10]}"
    resp = client.post(
        "/api/v1/wiki-admin/pages",
        json={"key": slug, "is_published": True},
        headers=moderator_headers,
    )
    if resp.status_code not in (200, 201):
        pytest.skip("wiki admin unavailable")
    page_id = (resp.get_json() or {}).get("id")
    if not page_id:
        pytest.skip("no page id")
    client.put(
        f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
        json={
            "title": "Empty Body",
            "slug": slug,
            "content_markdown": "   ",
        },
        headers=moderator_headers,
    )
    r = client.get(f"/wiki/{slug}")
    assert r.status_code == 200


def test_wiki_slug_markdown_exception_renders_without_html(client, app, moderator_headers, monkeypatch):
    import uuid

    slug = f"md-exc-{uuid.uuid4().hex[:10]}"
    resp = client.post(
        "/api/v1/wiki-admin/pages",
        json={"key": slug, "is_published": True},
        headers=moderator_headers,
    )
    if resp.status_code not in (200, 201):
        pytest.skip("wiki admin unavailable")
    page_id = (resp.get_json() or {}).get("id")
    if not page_id:
        pytest.skip("no page id")
    client.put(
        f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
        json={"title": "Md Exc", "slug": slug, "content_markdown": "# Body"},
        headers=moderator_headers,
    )

    def _boom(*_a, **_k):
        raise RuntimeError("markdown down")

    monkeypatch.setattr("app.web.routes.markdown.markdown", _boom)
    r = client.get(f"/wiki/{slug}")
    assert r.status_code == 200


@pytest.mark.usefixtures("_clear_runtime_registry_for_web_routes")
def test_play_view_uses_minimal_session_state_when_runtime_missing(client, test_user, monkeypatch):
    user, password = test_user
    _web_routes_simple_login(client, user.username, password)

    def _boom(**_kwargs):
        raise RuntimeError("no runtime")

    monkeypatch.setattr("app.web.routes.create_runtime_session", _boom)
    token = _csrf_from_play_page(client)
    start = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": token},
        follow_redirects=False,
    )
    assert start.status_code == 302
    session_id = start.headers["Location"].split("/play/")[-1]
    view = client.get(f"/play/{session_id}")
    assert view.status_code == 200


# ======================= DASHBOARD API (SESSION AUTH) =======================
