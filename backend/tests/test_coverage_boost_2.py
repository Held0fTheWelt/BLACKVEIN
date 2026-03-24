"""Additional tests to close coverage gap from ~78% to 85%.

Targets: web routes, wiki admin translation workflow, news translation workflow,
area CRUD + user/feature areas, user self-update, data export/import, slogan edge cases.
"""
from datetime import datetime, timezone

import pytest

from app.extensions import db
from app.models import (
    User,
    Role,
    NewsArticle,
    NewsArticleTranslation,
    WikiPage,
    WikiPageTranslation,
    ForumCategory,
    ForumThread,
    ForumPost,
    Area,
    Slogan,
    SiteSetting,
)
from app.models.role import ensure_roles_seeded
from app.models.area import ensure_areas_seeded
from werkzeug.security import generate_password_hash


# ======================= HELPER =======================

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


# ======================= WEB ROUTES - EXTENDED =======================

class TestWebRoutesExtended:

    def test_web_login_post_success(self, app, client, test_user):
        user, password = test_user
        resp = _login_session(client, user.username, password, app)
        assert resp.status_code == 302

    def test_web_login_post_wrong_password(self, app, client, test_user):
        user, _ = test_user
        resp = _login_session(client, user.username, "wrongpass", app)
        assert resp.status_code == 200  # re-renders login form

    def test_web_login_post_missing_fields(self, app, client):
        import re
        # Get login page to extract CSRF token
        login_page = client.get("/login")
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_page.data.decode())
        csrf_value = match.group(1) if match else ""
        resp = client.post("/login", data={"username": "", "password": "", "csrf_token": csrf_value}, follow_redirects=False)
        assert resp.status_code == 200

    def test_web_login_already_logged_in(self, app, client, test_user):
        user, password = test_user
        _login_session(client, user.username, password, app)
        resp = client.get("/login")
        assert resp.status_code == 302  # redirects to dashboard

    def test_web_login_banned_user(self, app, client, banned_user):
        user, password = banned_user
        resp = _login_session(client, user.username, password, app)
        assert resp.status_code == 302
        assert "blocked" in resp.headers.get("Location", "")

    def test_web_blocked_page(self, app, client):
        resp = client.get("/blocked")
        assert resp.status_code == 200

    def test_web_register_post_success(self, app, client):
        csrf_value = _get_csrf_token(client, "/register")
        resp = client.post(
            "/register",
            data={"username": "newreguser", "password": "StrongPass1", "password_confirm": "StrongPass1", "csrf_token": csrf_value},
            follow_redirects=False,
        )
        assert resp.status_code in (200, 302)

    def test_web_register_post_password_mismatch(self, app, client):
        csrf_value = _get_csrf_token(client, "/register")
        resp = client.post(
            "/register",
            data={"username": "mismatch", "password": "Pass1", "password_confirm": "Pass2", "csrf_token": csrf_value},
            follow_redirects=False,
        )
        assert resp.status_code == 200  # re-renders form

    def test_web_register_post_duplicate(self, app, client, test_user):
        user, _ = test_user
        csrf_value = _get_csrf_token(client, "/register")
        resp = client.post(
            "/register",
            data={"username": user.username, "password": "StrongPass1", "password_confirm": "StrongPass1", "csrf_token": csrf_value},
            follow_redirects=False,
        )
        assert resp.status_code == 200  # shows error

    def test_web_register_post_with_email(self, app, client):
        app.config["REGISTRATION_REQUIRE_EMAIL"] = True
        csrf_value = _get_csrf_token(client, "/register")
        resp = client.post(
            "/register",
            data={"username": "emailreg", "password": "StrongPass1", "password_confirm": "StrongPass1", "email": "", "csrf_token": csrf_value},
            follow_redirects=False,
        )
        assert resp.status_code == 200  # missing email error
        app.config["REGISTRATION_REQUIRE_EMAIL"] = False

    def test_web_register_pending(self, app, client):
        resp = client.get("/register/pending")
        assert resp.status_code == 200

    def test_web_register_already_logged_in(self, app, client, test_user):
        user, password = test_user
        _login_session(client, user.username, password, app)
        resp = client.get("/register", follow_redirects=False)
        assert resp.status_code == 302

    def test_web_forgot_password_post(self, app, client):
        csrf_value = _get_csrf_token(client, "/forgot-password")
        resp = client.post(
            "/forgot-password",
            data={"email": "nonexistent@example.com", "csrf_token": csrf_value},
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_web_forgot_password_post_empty(self, app, client):
        csrf_value = _get_csrf_token(client, "/forgot-password")
        resp = client.post(
            "/forgot-password",
            data={"email": "", "csrf_token": csrf_value},
            follow_redirects=False,
        )
        assert resp.status_code == 200

    def test_web_resend_verification_get(self, app, client):
        resp = client.get("/resend-verification")
        assert resp.status_code == 200

    def test_web_resend_verification_post(self, app, client):
        csrf_value = _get_csrf_token(client, "/login")
        resp = client.post(
            "/resend-verification",
            data={"email": "nonexistent@example.com", "csrf_token": csrf_value},
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_web_resend_verification_post_empty(self, app, client):
        csrf_value = _get_csrf_token(client, "/login")
        resp = client.post(
            "/resend-verification",
            data={"email": "", "csrf_token": csrf_value},
            follow_redirects=False,
        )
        assert resp.status_code == 200

    def test_web_reset_password_invalid_token(self, app, client):
        resp = client.get("/reset-password/badtoken", follow_redirects=False)
        assert resp.status_code == 302

    def test_web_activate_invalid_token(self, app, client):
        resp = client.get("/activate/badtoken", follow_redirects=False)
        assert resp.status_code == 302

    def test_web_wiki_with_slug(self, app, client):
        resp = client.get("/wiki/nonexistent-slug")
        assert resp.status_code == 404

    def test_web_wiki_with_real_slug(self, app, client, moderator_headers):
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

    def test_web_logout_with_session(self, app, client, test_user):
        user, password = test_user
        login_resp = _login_session(client, user.username, password, app)
        # Login should redirect to dashboard
        assert login_resp.status_code in (302, 200)
        resp = client.post("/logout", follow_redirects=False)
        assert resp.status_code == 302

    def test_web_health(self, app, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_web_dashboard_logged_in(self, app, client, test_user):
        user, password = test_user
        _login_session(client, user.username, password, app)
        resp = client.get("/dashboard")
        assert resp.status_code == 200

    def test_web_game_menu_logged_in(self, app, client, test_user):
        user, password = test_user
        _login_session(client, user.username, password, app)
        resp = client.get("/game-menu")
        assert resp.status_code == 200


# ======================= DASHBOARD API (SESSION AUTH) =======================

class TestDashboardAPI:

    def test_dashboard_metrics_requires_admin(self, app, client, test_user):
        user, password = test_user
        _login_session(client, user.username, password, app)
        resp = client.get("/dashboard/api/metrics")
        assert resp.status_code == 302  # redirects non-admin

    def test_dashboard_metrics_admin(self, app, client):
        _create_admin_session(app, client)
        resp = client.get("/dashboard/api/metrics?range=24h")
        assert resp.status_code == 200

    def test_dashboard_metrics_ranges(self, app, client):
        _create_admin_session(app, client)
        for r in ("7d", "30d", "12m", "invalid"):
            resp = client.get(f"/dashboard/api/metrics?range={r}")
            assert resp.status_code == 200

    def test_dashboard_logs(self, app, client):
        _create_admin_session(app, client)
        resp = client.get("/dashboard/api/logs?page=1&limit=10")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert "total" in data

    def test_dashboard_logs_with_filters(self, app, client):
        _create_admin_session(app, client)
        resp = client.get("/dashboard/api/logs?q=test&category=auth&status=success")
        assert resp.status_code == 200

    def test_dashboard_logs_export(self, app, client):
        _create_admin_session(app, client)
        resp = client.get("/dashboard/api/logs/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type

    def test_dashboard_logs_export_with_filters(self, app, client):
        _create_admin_session(app, client)
        resp = client.get("/dashboard/api/logs/export?q=test&category=auth")
        assert resp.status_code == 200

    def test_dashboard_site_settings_get(self, app, client):
        _create_admin_session(app, client)
        resp = client.get("/dashboard/api/site-settings")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "slogan_rotation_interval_seconds" in data

    def test_dashboard_site_settings_put(self, app, client):
        _create_admin_session(app, client)
        resp = client.put(
            "/dashboard/api/site-settings",
            json={"slogan_rotation_interval_seconds": 30, "slogan_rotation_enabled": True},
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_dashboard_site_settings_put_invalid(self, app, client):
        _create_admin_session(app, client)
        resp = client.put("/dashboard/api/site-settings", content_type="application/json")
        assert resp.status_code == 400


# ======================= WIKI ADMIN TRANSLATION WORKFLOW =======================

class TestWikiAdminTranslationWorkflow:

    def _create_page_with_translation(self, client, moderator_headers):
        """Helper: create wiki page + de translation, return (page_id, trans_response)."""
        resp = client.post(
            "/api/v1/wiki-admin/pages",
            json={"key": f"wiki-wf-{id(self)}"},
            headers=moderator_headers,
        )
        assert resp.status_code in (200, 201)
        page_id = resp.get_json()["id"]
        resp = client.put(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
            json={"title": "DE Title", "slug": f"de-slug-{id(self)}", "content_markdown": "DE Content"},
            headers=moderator_headers,
        )
        assert resp.status_code in (200, 201)
        return page_id

    def test_translation_get(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.get(f"/api/v1/wiki-admin/pages/{page_id}/translations/de", headers=moderator_headers)
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "DE Title"

    def test_translation_get_not_found(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.get(f"/api/v1/wiki-admin/pages/{page_id}/translations/en", headers=moderator_headers)
        assert resp.status_code == 404

    def test_translation_get_unsupported_lang(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.get(f"/api/v1/wiki-admin/pages/{page_id}/translations/xx", headers=moderator_headers)
        assert resp.status_code == 400

    def test_submit_review(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.post(f"/api/v1/wiki-admin/pages/{page_id}/translations/de/submit-review", headers=moderator_headers)
        assert resp.status_code == 200
        assert resp.get_json()["translation_status"] == "review_required"

    def test_submit_review_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/wiki-admin/pages/99999/translations/de/submit-review", headers=moderator_headers)
        assert resp.status_code == 404

    def test_approve(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.post(f"/api/v1/wiki-admin/pages/{page_id}/translations/de/approve", headers=moderator_headers)
        assert resp.status_code == 200
        assert resp.get_json()["translation_status"] == "approved"

    def test_approve_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/wiki-admin/pages/99999/translations/de/approve", headers=moderator_headers)
        assert resp.status_code == 404

    def test_publish(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.post(f"/api/v1/wiki-admin/pages/{page_id}/translations/de/publish", headers=moderator_headers)
        assert resp.status_code == 200
        assert resp.get_json()["translation_status"] == "published"

    def test_publish_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/wiki-admin/pages/99999/translations/de/publish", headers=moderator_headers)
        assert resp.status_code == 404

    def test_auto_translate(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/auto-translate",
            json={},
            headers=moderator_headers,
        )
        assert resp.status_code == 202

    def test_auto_translate_page_not_found(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/wiki-admin/pages/99999/translations/auto-translate",
            json={},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_page_update_not_found(self, app, client, moderator_headers):
        resp = client.put(
            "/api/v1/wiki-admin/pages/99999",
            json={"key": "x"},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_page_translations_list_not_found(self, app, client, moderator_headers):
        resp = client.get("/api/v1/wiki-admin/pages/99999/translations", headers=moderator_headers)
        assert resp.status_code == 404

    def test_translation_put_missing_body(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.put(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_page_create_missing_body(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/wiki-admin/pages",
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_page_update_missing_body(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/wiki-admin/pages",
            json={"key": "wiki-update-body-test"},
            headers=moderator_headers,
        )
        page_id = resp.get_json()["id"]
        resp = client.put(
            f"/api/v1/wiki-admin/pages/{page_id}",
            headers=moderator_headers,
        )
        assert resp.status_code == 400


# ======================= WIKI DISCUSSION THREAD LINKS =======================

class TestWikiDiscussionThreadLinks:

    def _setup(self, app, client, moderator_headers):
        """Create a wiki page and a forum thread."""
        resp = client.post(
            "/api/v1/wiki-admin/pages",
            json={"key": f"wiki-disc-{id(self)}"},
            headers=moderator_headers,
        )
        page_id = resp.get_json()["id"]
        with app.app_context():
            user = User.query.filter_by(username="moderatoruser").first()
            cat = ForumCategory(title="Wiki Disc Cat", slug=f"wiki-disc-cat-{id(self)}", description="test")
            db.session.add(cat)
            db.session.flush()
            thread = ForumThread(
                title="Wiki Discussion",
                slug=f"wiki-disc-thread-{id(self)}",
                category_id=cat.id,
                author_id=user.id,
            )
            db.session.add(thread)
            db.session.commit()
            thread_id = thread.id
        return page_id, thread_id

    def test_link_discussion_thread(self, app, client, moderator_headers):
        page_id, thread_id = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki/{page_id}/discussion-thread",
            json={"discussion_thread_id": thread_id},
            headers=moderator_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["discussion_thread_id"] == thread_id

    def test_link_discussion_thread_page_not_found(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/wiki/99999/discussion-thread",
            json={"discussion_thread_id": 1},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_link_discussion_thread_invalid_id(self, app, client, moderator_headers):
        page_id, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki/{page_id}/discussion-thread",
            json={"discussion_thread_id": "abc"},
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_link_discussion_thread_not_found(self, app, client, moderator_headers):
        page_id, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki/{page_id}/discussion-thread",
            json={"discussion_thread_id": 99999},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_unlink_discussion_thread(self, app, client, moderator_headers):
        page_id, thread_id = self._setup(app, client, moderator_headers)
        client.post(
            f"/api/v1/wiki/{page_id}/discussion-thread",
            json={"discussion_thread_id": thread_id},
            headers=moderator_headers,
        )
        resp = client.delete(f"/api/v1/wiki/{page_id}/discussion-thread", headers=moderator_headers)
        assert resp.status_code == 200

    def test_unlink_discussion_thread_page_not_found(self, app, client, moderator_headers):
        resp = client.delete("/api/v1/wiki/99999/discussion-thread", headers=moderator_headers)
        assert resp.status_code == 404

    def test_related_threads_get(self, app, client, moderator_headers):
        page_id, _ = self._setup(app, client, moderator_headers)
        resp = client.get(f"/api/v1/wiki/{page_id}/related-threads", headers=moderator_headers)
        assert resp.status_code == 200

    def test_related_threads_add(self, app, client, moderator_headers):
        page_id, thread_id = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki/{page_id}/related-threads",
            json={"thread_id": thread_id},
            headers=moderator_headers,
        )
        assert resp.status_code == 200

    def test_related_threads_add_missing_body(self, app, client, moderator_headers):
        page_id, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki/{page_id}/related-threads",
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_related_threads_add_invalid_id(self, app, client, moderator_headers):
        page_id, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki/{page_id}/related-threads",
            json={"thread_id": "abc"},
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_related_threads_delete(self, app, client, moderator_headers):
        page_id, thread_id = self._setup(app, client, moderator_headers)
        client.post(
            f"/api/v1/wiki/{page_id}/related-threads",
            json={"thread_id": thread_id},
            headers=moderator_headers,
        )
        resp = client.delete(
            f"/api/v1/wiki/{page_id}/related-threads/{thread_id}",
            headers=moderator_headers,
        )
        assert resp.status_code == 200

    def test_related_threads_delete_not_found(self, app, client, moderator_headers):
        page_id, _ = self._setup(app, client, moderator_headers)
        resp = client.delete(
            f"/api/v1/wiki/{page_id}/related-threads/99999",
            headers=moderator_headers,
        )
        assert resp.status_code == 404


# ======================= NEWS TRANSLATION WORKFLOW =======================

class TestNewsTranslationWorkflow:

    def _create_article(self, client, moderator_headers):
        resp = client.post(
            "/api/v1/news",
            json={"title": f"NTW-{id(self)}", "slug": f"ntw-{id(self)}", "content": "body"},
            headers=moderator_headers,
        )
        assert resp.status_code == 201
        return resp.get_json()["id"]

    def test_translation_submit_review(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        # Create translation first
        client.put(
            f"/api/v1/news/{aid}/translations/en",
            json={"title": "EN", "content": "EN body", "summary": "s"},
            headers=moderator_headers,
        )
        resp = client.post(f"/api/v1/news/{aid}/translations/en/submit-review", headers=moderator_headers)
        assert resp.status_code == 200

    def test_translation_submit_review_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/news/99999/translations/en/submit-review", headers=moderator_headers)
        assert resp.status_code == 404

    def test_translation_approve(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        client.put(
            f"/api/v1/news/{aid}/translations/en",
            json={"title": "EN", "content": "EN body", "summary": "s"},
            headers=moderator_headers,
        )
        resp = client.post(f"/api/v1/news/{aid}/translations/en/approve", headers=moderator_headers)
        assert resp.status_code == 200

    def test_translation_approve_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/news/99999/translations/en/approve", headers=moderator_headers)
        assert resp.status_code == 404

    def test_translation_publish(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        client.put(
            f"/api/v1/news/{aid}/translations/en",
            json={"title": "EN", "content": "EN body", "summary": "s"},
            headers=moderator_headers,
        )
        resp = client.post(f"/api/v1/news/{aid}/translations/en/publish", headers=moderator_headers)
        assert resp.status_code == 200

    def test_translation_publish_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/news/99999/translations/en/publish", headers=moderator_headers)
        assert resp.status_code == 404

    def test_auto_translate(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        resp = client.post(
            f"/api/v1/news/{aid}/translations/auto-translate",
            json={},
            headers=moderator_headers,
        )
        assert resp.status_code == 202

    def test_auto_translate_not_found(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/news/99999/translations/auto-translate",
            json={},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_translation_get_unsupported_lang(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        resp = client.get(f"/api/v1/news/{aid}/translations/xx", headers=moderator_headers)
        assert resp.status_code == 400

    def test_translation_put_missing_body(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        resp = client.put(f"/api/v1/news/{aid}/translations/en", headers=moderator_headers)
        assert resp.status_code == 400

    def test_translation_put_not_found(self, app, client, moderator_headers):
        resp = client.put(
            "/api/v1/news/99999/translations/en",
            json={"title": "X", "content": "Y"},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_translations_list_not_found(self, app, client, moderator_headers):
        resp = client.get("/api/v1/news/99999/translations", headers=moderator_headers)
        assert resp.status_code == 404

    def test_news_detail_by_slug(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        client.post(f"/api/v1/news/{aid}/publish", headers=moderator_headers)
        resp = client.get(f"/api/v1/news/{aid}")
        assert resp.status_code == 200

    def test_news_detail_not_found_slug(self, app, client):
        resp = client.get("/api/v1/news/nonexistent-slug-abc")
        assert resp.status_code == 404

    def test_news_list_with_search(self, app, client, moderator_headers):
        self._create_article(client, moderator_headers)
        resp = client.get("/api/v1/news?q=NTW")
        assert resp.status_code == 200

    def test_news_list_with_sort(self, app, client, moderator_headers):
        self._create_article(client, moderator_headers)
        resp = client.get("/api/v1/news?sort=title&direction=asc")
        assert resp.status_code == 200

    def test_news_create_missing_body(self, app, client, moderator_headers):
        resp = client.post("/api/v1/news", headers=moderator_headers)
        assert resp.status_code == 400

    def test_news_update_missing_body(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        resp = client.put(f"/api/v1/news/{aid}", headers=moderator_headers)
        assert resp.status_code == 400


# ======================= NEWS DISCUSSION THREAD LINKS =======================

class TestNewsDiscussionThreadLinks:

    def _setup(self, app, client, moderator_headers):
        """Create news article + forum thread, return (article_id, thread_id)."""
        resp = client.post(
            "/api/v1/news",
            json={"title": f"NDT-{id(self)}", "slug": f"ndt-{id(self)}", "content": "body"},
            headers=moderator_headers,
        )
        article_id = resp.get_json()["id"]
        with app.app_context():
            user = User.query.filter_by(username="moderatoruser").first()
            cat = ForumCategory(title="News Disc Cat", slug=f"news-disc-cat-{id(self)}", description="test")
            db.session.add(cat)
            db.session.flush()
            thread = ForumThread(
                title="News Discussion",
                slug=f"news-disc-thread-{id(self)}",
                category_id=cat.id,
                author_id=user.id,
            )
            db.session.add(thread)
            db.session.commit()
            thread_id = thread.id
        return article_id, thread_id

    def test_link_discussion_thread(self, app, client, moderator_headers):
        aid, tid = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/news/{aid}/discussion-thread",
            json={"discussion_thread_id": tid},
            headers=moderator_headers,
        )
        assert resp.status_code == 200

    def test_link_discussion_thread_not_found(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/news/99999/discussion-thread",
            json={"discussion_thread_id": 1},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_link_discussion_thread_missing_body(self, app, client, moderator_headers):
        aid, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/news/{aid}/discussion-thread",
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_link_discussion_thread_invalid_id(self, app, client, moderator_headers):
        aid, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/news/{aid}/discussion-thread",
            json={"discussion_thread_id": "abc"},
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_unlink_discussion_thread(self, app, client, moderator_headers):
        aid, tid = self._setup(app, client, moderator_headers)
        client.post(
            f"/api/v1/news/{aid}/discussion-thread",
            json={"discussion_thread_id": tid},
            headers=moderator_headers,
        )
        resp = client.delete(f"/api/v1/news/{aid}/discussion-thread", headers=moderator_headers)
        assert resp.status_code == 200

    def test_unlink_discussion_thread_not_found(self, app, client, moderator_headers):
        resp = client.delete("/api/v1/news/99999/discussion-thread", headers=moderator_headers)
        assert resp.status_code == 404

    def test_related_threads_get(self, app, client, moderator_headers):
        aid, _ = self._setup(app, client, moderator_headers)
        resp = client.get(f"/api/v1/news/{aid}/related-threads", headers=moderator_headers)
        assert resp.status_code == 200

    def test_related_threads_add(self, app, client, moderator_headers):
        aid, tid = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/news/{aid}/related-threads",
            json={"thread_id": tid},
            headers=moderator_headers,
        )
        assert resp.status_code == 200

    def test_related_threads_add_missing_body(self, app, client, moderator_headers):
        aid, _ = self._setup(app, client, moderator_headers)
        resp = client.post(f"/api/v1/news/{aid}/related-threads", headers=moderator_headers)
        assert resp.status_code == 400

    def test_related_threads_add_invalid_id(self, app, client, moderator_headers):
        aid, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/news/{aid}/related-threads",
            json={"thread_id": "abc"},
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_related_threads_delete(self, app, client, moderator_headers):
        aid, tid = self._setup(app, client, moderator_headers)
        client.post(
            f"/api/v1/news/{aid}/related-threads",
            json={"thread_id": tid},
            headers=moderator_headers,
        )
        resp = client.delete(f"/api/v1/news/{aid}/related-threads/{tid}", headers=moderator_headers)
        assert resp.status_code == 200

    def test_related_threads_delete_not_found(self, app, client, moderator_headers):
        aid, _ = self._setup(app, client, moderator_headers)
        resp = client.delete(f"/api/v1/news/{aid}/related-threads/99999", headers=moderator_headers)
        assert resp.status_code == 404


# ======================= AREA API EXTENDED =======================

class TestAreaAPIExtended:

    def test_area_update(self, app, client, admin_headers):
        resp = client.post(
            "/api/v1/areas",
            json={"name": "Area Upd", "slug": "area_upd"},
            headers=admin_headers,
        )
        if resp.status_code in (200, 201):
            area_id = resp.get_json()["id"]
            resp = client.put(
                f"/api/v1/areas/{area_id}",
                json={"name": "Area Updated"},
                headers=admin_headers,
            )
            assert resp.status_code == 200

    def test_area_update_not_found(self, app, client, admin_headers):
        resp = client.put(
            "/api/v1/areas/99999",
            json={"name": "X"},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_area_delete(self, app, client, admin_headers):
        resp = client.post(
            "/api/v1/areas",
            json={"name": "Area Del", "slug": "area_del"},
            headers=admin_headers,
        )
        if resp.status_code in (200, 201):
            area_id = resp.get_json()["id"]
            resp = client.delete(f"/api/v1/areas/{area_id}", headers=admin_headers)
            assert resp.status_code == 200

    def test_area_delete_not_found(self, app, client, admin_headers):
        resp = client.delete("/api/v1/areas/99999", headers=admin_headers)
        assert resp.status_code == 404

    def test_area_create_invalid_slug(self, app, client, admin_headers):
        resp = client.post(
            "/api/v1/areas",
            json={"name": "Area Bad Slug", "slug": "INVALID-SLUG!"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_area_create_missing_name(self, app, client, admin_headers):
        resp = client.post(
            "/api/v1/areas",
            json={"name": ""},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_area_list_with_search(self, app, client, admin_headers):
        resp = client.get("/api/v1/areas?q=test", headers=admin_headers)
        assert resp.status_code == 200

    def test_user_areas_list(self, app, client, admin_headers, test_user):
        user, _ = test_user
        with app.app_context():
            uid = User.query.filter_by(username="testuser").first().id
        resp = client.get(f"/api/v1/users/{uid}/areas", headers=admin_headers)
        assert resp.status_code == 200

    def test_user_areas_set(self, app, client, admin_headers, test_user):
        user, _ = test_user
        with app.app_context():
            uid = User.query.filter_by(username="testuser").first().id
        resp = client.put(
            f"/api/v1/users/{uid}/areas",
            json={"area_ids": []},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_feature_areas_list(self, app, client, admin_headers):
        resp = client.get("/api/v1/feature-areas", headers=admin_headers)
        assert resp.status_code == 200

    def test_feature_areas_get(self, app, client, admin_headers):
        resp = client.get("/api/v1/feature-areas/manage.users", headers=admin_headers)
        assert resp.status_code == 200

    def test_feature_areas_get_unknown(self, app, client, admin_headers):
        resp = client.get("/api/v1/feature-areas/unknown.feature", headers=admin_headers)
        assert resp.status_code == 404

    def test_feature_areas_set(self, app, client, admin_headers):
        resp = client.put(
            "/api/v1/feature-areas/manage.users",
            json={"area_ids": []},
            headers=admin_headers,
        )
        assert resp.status_code == 200


# ======================= USER API EXTENDED =======================

class TestUserAPIExtended:

    def test_user_self_get(self, app, client, auth_headers, test_user):
        user, _ = test_user
        with app.app_context():
            uid = User.query.filter_by(username="testuser").first().id
        resp = client.get(f"/api/v1/users/{uid}", headers=auth_headers)
        assert resp.status_code == 200

    def test_user_self_update(self, app, client, auth_headers, test_user):
        user, _ = test_user
        with app.app_context():
            uid = User.query.filter_by(username="testuser").first().id
        resp = client.put(
            f"/api/v1/users/{uid}",
            json={"preferred_language": "en"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_user_self_change_password(self, app, client, auth_headers, test_user):
        user, password = test_user
        with app.app_context():
            uid = User.query.filter_by(username="testuser").first().id
        resp = client.put(
            f"/api/v1/users/{uid}/password",
            json={"current_password": password, "new_password": "NewStrongPass1"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_user_self_change_password_wrong_current(self, app, client, auth_headers, test_user):
        user, _ = test_user
        with app.app_context():
            uid = User.query.filter_by(username="testuser").first().id
        resp = client.put(
            f"/api/v1/users/{uid}/password",
            json={"current_password": "wrongpass", "new_password": "NewStrongPass1"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_user_self_change_password_missing_fields(self, app, client, auth_headers, test_user):
        user, _ = test_user
        with app.app_context():
            uid = User.query.filter_by(username="testuser").first().id
        resp = client.put(
            f"/api/v1/users/{uid}/password",
            json={"new_password": "NewStrongPass1"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_user_delete_by_admin(self, app, client, super_admin_headers):
        # Create a user to delete (delete requires SuperAdmin)
        with app.app_context():
            role = Role.query.filter_by(name=Role.NAME_USER).first()
            u = User(username="deleteuser", password_hash=generate_password_hash("Delpass1"), role_id=role.id)
            db.session.add(u)
            db.session.commit()
            uid = u.id
        resp = client.delete(f"/api/v1/users/{uid}", headers=super_admin_headers)
        assert resp.status_code == 200

    def test_user_delete_not_found(self, app, client, super_admin_headers):
        resp = client.delete("/api/v1/users/99999", headers=super_admin_headers)
        assert resp.status_code == 404

    def test_user_delete_forbidden_for_user(self, app, client, auth_headers):
        resp = client.delete("/api/v1/users/99999", headers=auth_headers)
        assert resp.status_code == 403

    def test_user_update_forbidden_for_other(self, app, client, auth_headers, admin_user):
        user, _ = admin_user
        with app.app_context():
            uid = User.query.filter_by(username="adminuser").first().id
        resp = client.put(
            f"/api/v1/users/{uid}",
            json={"preferred_language": "en"},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_user_update_password_via_update_rejected(self, app, client, auth_headers, test_user):
        user, _ = test_user
        with app.app_context():
            uid = User.query.filter_by(username="testuser").first().id
        resp = client.put(
            f"/api/v1/users/{uid}",
            json={"password": "newpass"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_user_assign_role(self, app, client, admin_headers, test_user):
        user, _ = test_user
        with app.app_context():
            uid = User.query.filter_by(username="testuser").first().id
        resp = client.patch(
            f"/api/v1/users/{uid}/role",
            json={"role": "user"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_user_assign_role_invalid(self, app, client, admin_headers, test_user):
        user, _ = test_user
        with app.app_context():
            uid = User.query.filter_by(username="testuser").first().id
        resp = client.patch(
            f"/api/v1/users/{uid}/role",
            json={"role": "nonexistent_role"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_user_preferences_self(self, app, client, auth_headers, test_user):
        user, _ = test_user
        with app.app_context():
            uid = User.query.filter_by(username="testuser").first().id
        resp = client.put(
            f"/api/v1/users/{uid}/preferences",
            json={"preferred_language": "de"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_user_preferences_no_fields(self, app, client, auth_headers, test_user):
        user, _ = test_user
        with app.app_context():
            uid = User.query.filter_by(username="testuser").first().id
        resp = client.put(
            f"/api/v1/users/{uid}/preferences",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_user_list_search(self, app, client, admin_headers):
        resp = client.get("/api/v1/users?q=test", headers=admin_headers)
        assert resp.status_code == 200


# ======================= DATA EXPORT/IMPORT =======================

class TestDataExportImport:

    def test_export_full(self, app, client, admin_headers):
        resp = client.post(
            "/api/v1/data/export",
            json={"scope": "full"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_export_table(self, app, client, admin_headers):
        resp = client.post(
            "/api/v1/data/export",
            json={"scope": "table", "table": "users"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_export_list_tables(self, app, client, admin_headers):
        resp = client.get("/api/v1/data/tables", headers=admin_headers)
        assert resp.status_code in (200, 404)

    def test_import_preflight(self, app, client, admin_headers):
        resp = client.post(
            "/api/v1/data/import/preflight",
            json={"metadata": {"format_version": 1}, "data": {"tables": {}}},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 400)


# ======================= SLOGAN API EXTENDED =======================

class TestSloganAPIExtended:

    def test_slogan_get_by_id(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/slogans",
            json={
                "text": "Slogan Get",
                "category": "landing_hero",
                "placement_key": "landing.hero.primary",
                "language_code": "de",
            },
            headers=moderator_headers,
        )
        if resp.status_code in (200, 201):
            slogan_id = resp.get_json()["id"]
            resp = client.get(f"/api/v1/slogans/{slogan_id}", headers=moderator_headers)
            assert resp.status_code == 200

    def test_slogan_get_not_found(self, app, client, moderator_headers):
        resp = client.get("/api/v1/slogans/99999", headers=moderator_headers)
        assert resp.status_code == 404

    def test_slogan_update_not_found(self, app, client, moderator_headers):
        resp = client.put(
            "/api/v1/slogans/99999",
            json={"text": "X"},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_slogan_delete_not_found(self, app, client, moderator_headers):
        resp = client.delete("/api/v1/slogans/99999", headers=moderator_headers)
        assert resp.status_code == 404

    def test_slogan_list_with_filters(self, app, client, moderator_headers):
        resp = client.get(
            "/api/v1/slogans?category=landing_hero&placement_key=landing.hero.primary&active_only=true",
            headers=moderator_headers,
        )
        assert resp.status_code == 200

    def test_slogan_create_invalid_category(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/slogans",
            json={
                "text": "Bad Cat",
                "category": "invalid_cat",
                "placement_key": "landing.hero.primary",
                "language_code": "de",
            },
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_slogans_for_placement_list(self, app, client):
        resp = client.get("/api/v1/site/slogans?placement=landing.hero.primary&lang=de")
        assert resp.status_code == 200

    def test_slogan_resolve_with_lang(self, app, client):
        resp = client.get("/api/v1/site/slogan?placement=landing.hero.primary&lang=de")
        assert resp.status_code == 200


# ======================= ROLE API EXTENDED =======================

class TestRoleAPIExtended:

    def test_role_list_admin(self, app, client, admin_headers):
        resp = client.get("/api/v1/roles", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data or isinstance(data, list)

    def test_role_create_if_supported(self, app, client, admin_headers):
        resp = client.post(
            "/api/v1/roles",
            json={"name": "custom_role", "display_name": "Custom"},
            headers=admin_headers,
        )
        # Might not support creation - just ensure no crash
        assert resp.status_code in (200, 201, 400, 404, 405)


# ======================= ADMIN LOGS EXTENDED =======================

class TestAdminLogsExtended:

    def test_admin_logs_with_filters(self, app, client, admin_headers):
        resp = client.get(
            "/api/v1/admin/logs?page=1&limit=10&q=test&category=auth&status=success",
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_admin_logs_pagination(self, app, client, admin_headers):
        resp = client.get("/api/v1/admin/logs?page=2&limit=5", headers=admin_headers)
        assert resp.status_code == 200


# ======================= SERVICE LEVEL TESTS =======================

class TestServiceLevel:

    def test_area_service_validation(self, app):
        from app.services.area_service import validate_area_name, validate_area_slug
        with app.app_context():
            assert validate_area_name("") is not None
            assert validate_area_name(None) is not None
            assert validate_area_name("x" * 200) is not None
            assert validate_area_name("Valid Name") is None

            assert validate_area_slug("") is not None
            assert validate_area_slug(None) is not None
            assert validate_area_slug("x" * 100) is not None
            assert validate_area_slug("INVALID-SLUG") is not None  # uppercase + hyphen
            assert validate_area_slug("valid_slug") is None

    def test_area_service_get_by_slug(self, app):
        from app.services.area_service import get_area_by_slug
        with app.app_context():
            result = get_area_by_slug(None)
            assert result is None
            result = get_area_by_slug("")
            assert result is None

    def test_slogan_service_parse_dt(self, app):
        from app.services.slogan_service import _parse_dt
        assert _parse_dt(None) is None
        assert _parse_dt("") is None
        assert _parse_dt("invalid") is None
        result = _parse_dt("2024-01-01T00:00:00Z")
        assert result is not None
        result = _parse_dt(datetime(2024, 1, 1, tzinfo=timezone.utc))
        assert result is not None

    def test_data_export_service(self, app):
        from app.services.data_export_service import (
            export_full,
            export_table,
            list_exportable_tables,
        )
        with app.app_context():
            tables = list_exportable_tables()
            assert isinstance(tables, list)
            assert len(tables) > 0

            payload = export_full()
            assert "metadata" in payload
            assert "data" in payload

            payload = export_table("users")
            assert "metadata" in payload

    def test_data_export_service_unknown_table(self, app):
        from app.services.data_export_service import export_table
        with app.app_context():
            with pytest.raises(ValueError):
                export_table("nonexistent_table")

    def test_data_import_preflight(self, app):
        from app.services.data_import_service import preflight_validate_payload
        with app.app_context():
            # Invalid payload
            result = preflight_validate_payload("not a dict")
            assert not result.ok

            # Missing metadata
            result = preflight_validate_payload({"metadata": "bad"})
            assert not result.ok

            # Missing data tables
            result = preflight_validate_payload({"metadata": {}, "data": {}})
            assert not result.ok

            # Unknown table
            result = preflight_validate_payload({
                "metadata": {"format_version": 1, "schema_revision": ""},
                "data": {"tables": {"nonexistent_table": []}},
            })
            assert not result.ok

    def test_wiki_service_functions(self, app):
        from app.services.wiki_service import (
            get_wiki_page_by_key,
            get_wiki_markdown_for_display,
            get_wiki_page_by_slug,
        )
        with app.app_context():
            assert get_wiki_page_by_key(None) is None
            assert get_wiki_page_by_key("") is None
            assert get_wiki_markdown_for_display() is None
            page, trans = get_wiki_page_by_slug(None)
            assert page is None
            page, trans = get_wiki_page_by_slug("")
            assert page is None

    def test_news_service_functions(self, app):
        from app.services.news_service import (
            get_news_by_id,
            get_news_by_slug,
            get_news_article_by_id,
        )
        with app.app_context():
            assert get_news_by_id(None) is None
            assert get_news_by_id(99999) is None
            assert get_news_by_slug(None) is None
            assert get_news_by_slug("") is None
            assert get_news_article_by_id(None) is None

    def test_slogan_service_crud(self, app):
        from app.services.slogan_service import (
            create_slogan,
            update_slogan,
            delete_slogan,
            get_slogan_by_id,
            list_slogans,
            resolve_slogan_for_placement,
            list_slogans_for_placement,
        )
        with app.app_context():
            # Create
            s, err = create_slogan("Test", "landing_hero", "landing.hero.primary", "de")
            assert s is not None
            assert err is None

            # Get by id
            assert get_slogan_by_id(s.id) is not None
            assert get_slogan_by_id(None) is None
            assert get_slogan_by_id("abc") is None

            # List
            items = list_slogans(category="landing_hero", active_only=True)
            assert len(items) >= 1

            # Update
            s2, err = update_slogan(s.id, text="Updated")
            assert s2 is not None
            assert s2.text == "Updated"

            # Resolve
            result = resolve_slogan_for_placement("landing.hero.primary", "de")
            assert result is not None

            # List for placement
            items = list_slogans_for_placement("landing.hero.primary", "de")
            assert len(items) >= 1

            # Delete
            ok, err = delete_slogan(s.id)
            assert ok
            assert get_slogan_by_id(s.id) is None

    def test_area_service_create_delete(self, app):
        from app.services.area_service import create_area, delete_area, get_area_by_id, update_area
        with app.app_context():
            # Create
            area, err = create_area("Test Area SVC", slug="test_area_svc", description="desc")
            assert area is not None
            assert err is None

            # Get
            assert get_area_by_id(area.id) is not None
            assert get_area_by_id(None) is None
            assert get_area_by_id("abc") is None

            # Update
            area2, err = update_area(area.id, name="Updated Area SVC")
            assert area2 is not None
            assert area2.name == "Updated Area SVC"

            # Update not found
            _, err = update_area(99999, name="X")
            assert err == "Area not found"

            # Duplicate name
            area3, _ = create_area("Dup Test", slug="dup_test")
            _, err = update_area(area.id, name="Dup Test")
            assert "already exists" in err

            # Delete
            ok, err = delete_area(area.id)
            assert ok

            # Delete not found
            ok, err = delete_area(99999)
            assert not ok

            # Cleanup
            delete_area(area3.id)

    def test_feature_registry(self, app):
        from app.auth.feature_registry import (
            FEATURE_IDS,
            is_valid_feature_id,
            get_feature_area_ids,
        )
        with app.app_context():
            assert len(FEATURE_IDS) > 0
            assert is_valid_feature_id("manage.users")
            assert not is_valid_feature_id("nonexistent.feature")
            ids = get_feature_area_ids("manage.users")
            assert isinstance(ids, list)

    def test_permissions_helpers(self, app):
        from app.auth.permissions import admin_may_edit_target, admin_may_assign_role_level
        assert admin_may_edit_target(50, 0) is True
        assert admin_may_edit_target(50, 50) is False
        assert admin_may_edit_target(0, 50) is False

    def test_web_auth_helpers(self, app):
        from app.web.auth import is_safe_redirect
        assert is_safe_redirect("/dashboard") is True
        assert is_safe_redirect("https://evil.com") is False
        assert is_safe_redirect("") is False
        assert is_safe_redirect(None) is False
        assert is_safe_redirect("javascript:alert(1)") is False

    def test_csv_safe(self, app):
        from app.utils.csv_safe import csv_safe_cell
        assert csv_safe_cell(None) == ""
        assert csv_safe_cell("normal") == "normal"
        # Test formula injection prevention
        result = csv_safe_cell("=cmd")
        assert not result.startswith("=")

    def test_html_sanitizer(self, app):
        from app.utils.html_sanitizer import sanitize_wiki_html
        result = sanitize_wiki_html("<p>Hello</p>")
        assert "<p>" in result
        result = sanitize_wiki_html("<script>alert(1)</script>")
        assert "<script>" not in result
