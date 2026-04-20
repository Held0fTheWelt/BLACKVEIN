"""Regression tests for security and correctness fixes (0.0.12)."""
import logging
import pytest


def test_wiki_html_sanitizer_removes_script(app):
    """Wiki HTML sanitizer strips script tags."""
    from app.utils.html_sanitizer import sanitize_wiki_html
    dirty = "<p>Hello</p><script>alert(1)</script><p>World</p>"
    cleaned = sanitize_wiki_html(dirty)
    assert "script" not in cleaned.lower()
    assert "Hello" in cleaned
    assert "World" in cleaned


def test_wiki_html_sanitizer_removes_javascript_url(app):
    """Wiki HTML sanitizer strips javascript: in href."""
    from app.utils.html_sanitizer import sanitize_wiki_html
    dirty = '<p><a href="javascript:alert(1)">click</a></p>'
    cleaned = sanitize_wiki_html(dirty)
    assert "javascript:" not in cleaned.lower()


def test_wiki_html_sanitizer_guard_inputs(app):
    """sanitize_wiki_html short-circuits for None, non-str, or whitespace-only input."""
    from app.utils.html_sanitizer import sanitize_wiki_html

    assert sanitize_wiki_html(None) == ""
    assert sanitize_wiki_html(123) == ""
    assert sanitize_wiki_html([]) == ""

    ws_only = "  \n\t  "
    assert sanitize_wiki_html(ws_only) is ws_only

    assert "<p>" in sanitize_wiki_html("<p>Hello</p>")
    assert "<script>" not in sanitize_wiki_html("<script>alert(1)</script>").lower()


def test_password_change_requires_current_password(client, test_user):
    """PUT /users/<id>/password with wrong current_password fails."""
    user, password = test_user
    login = client.post("/api/v1/auth/login", json={"username": user.username, "password": password})
    assert login.status_code == 200
    token = login.get_json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    r = client.put(
        f"/api/v1/users/{user.id}/password",
        json={"current_password": "wrong", "new_password": "NewValid1"},
        headers=headers,
    )
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_password_change_without_current_password_fails(client, test_user):
    """PUT /users/<id>/password with new_password but no current_password returns 400 (regression)."""
    user, password = test_user
    login = client.post("/api/v1/auth/login", json={"username": user.username, "password": password})
    assert login.status_code == 200
    token = login.get_json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    r = client.put(
        f"/api/v1/users/{user.id}/password",
        json={"new_password": "NewValid123"},
        headers=headers,
    )
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data
    assert "current_password" in data["error"].lower()


def test_password_change_succeeds_with_correct_current_password(client, test_user):
    """PUT /users/<id>/password with correct current_password succeeds."""
    user, password = test_user
    login = client.post("/api/v1/auth/login", json={"username": user.username, "password": password})
    assert login.status_code == 200
    token = login.get_json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    r = client.put(
        f"/api/v1/users/{user.id}/password",
        json={"current_password": password, "new_password": "NewValid123"},
        headers=headers,
    )
    assert r.status_code == 200
    login2 = client.post("/api/v1/auth/login", json={"username": user.username, "password": "NewValid123"})
    assert login2.status_code == 200


def test_generic_user_update_rejects_password_field(client, admin_headers, test_user):
    """PUT /users/<id> with password or current_password in body returns 400 and points to password endpoint."""
    user, _ = test_user
    r = client.put(
        f"/api/v1/users/{user.id}",
        json={"username": user.username, "password": "AttemptedNew1"},
        headers=admin_headers,
    )
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data
    assert "password" in data["error"].lower()
    assert "/password" in data["error"]


def test_generic_user_update_rejects_current_password_field(client, admin_headers, test_user):
    """PUT /users/<id> with current_password in body returns 400."""
    user, _ = test_user
    r = client.put(
        f"/api/v1/users/{user.id}",
        json={"username": user.username, "current_password": "any", "new_password": "New1"},
        headers=admin_headers,
    )
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data
    assert "password" in data["error"].lower()


def test_news_detail_by_slug_returns_200(client, sample_news):
    """GET /api/v1/news/<slug>?lang= returns 200 for valid published slug."""
    pub1, _pub2, _draft = sample_news
    slug = "published-article"
    response = client.get(f"/api/v1/news/{slug}?lang=de")
    assert response.status_code == 200
    data = response.get_json()
    assert data["slug"] == slug
    assert data["title"] == "Published Article"


def test_news_detail_invalid_slug_returns_404(client):
    """GET /api/v1/news/nonexistent-slug returns 404."""
    response = client.get("/api/v1/news/nonexistent-slug")
    assert response.status_code == 404
    assert response.get_json().get("error") == "Not found"


def test_csv_export_neutralizes_formula(client, admin_headers):
    """CSV export prefixes formula-triggering cells so they are safe."""
    from app.utils.csv_safe import csv_safe_cell
    assert csv_safe_cell("=1+2").startswith("'")
    assert csv_safe_cell("+1").startswith("'")
    assert csv_safe_cell("-1").startswith("'")
    assert csv_safe_cell("@sum").startswith("'")
    assert not csv_safe_cell("hello").startswith("'")


def test_security_headers_present(client):
    """Responses include security headers and CSP is hardened (object-src 'none')."""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Referrer-Policy" in r.headers
    csp = r.headers.get("Content-Security-Policy", "")
    assert "Content-Security-Policy" in r.headers
    assert "object-src 'none'" in csp


def test_wiki_slug_unique_per_language(app, moderator_headers, client):
    """Duplicate wiki slug in same language is rejected."""
    r1 = client.post(
        "/api/v1/wiki-admin/pages",
        json={"key": "slug-test-page1"},
        headers=moderator_headers,
    )
    assert r1.status_code == 201
    page1_id = r1.get_json()["id"]
    r2 = client.post(
        "/api/v1/wiki-admin/pages",
        json={"key": "slug-test-page2"},
        headers=moderator_headers,
    )
    assert r2.status_code == 201
    page2_id = r2.get_json()["id"]
    r3 = client.put(
        f"/api/v1/wiki-admin/pages/{page1_id}/translations/de",
        json={"title": "Page One", "slug": "unique-slug-de", "content_markdown": "x"},
        headers=moderator_headers,
    )
    assert r3.status_code == 200
    r4 = client.put(
        f"/api/v1/wiki-admin/pages/{page2_id}/translations/de",
        json={"title": "Page Two", "slug": "unique-slug-de", "content_markdown": "y"},
        headers=moderator_headers,
    )
    assert r4.status_code in (400, 409)
    assert "slug" in (r4.get_json().get("error") or "").lower()


def test_news_update_marks_translations_outdated(app, moderator_headers, client, sample_news):
    """Updating source (default-language) news content marks other translations outdated."""
    from app.models import NewsArticleTranslation
    from app.extensions import db

    pub1, _pub2, _draft = sample_news
    with app.app_context():
        en_trans = NewsArticleTranslation.query.filter_by(
            article_id=pub1.id, language_code="en"
        ).first()
        if not en_trans:
            en_trans = NewsArticleTranslation(
                article_id=pub1.id,
                language_code="en",
                title="Published Article EN",
                slug="published-article-en",
                content="Body",
                translation_status="approved",
                source_language="de",
            )
            db.session.add(en_trans)
            db.session.commit()
    r = client.put(
        f"/api/v1/news/{pub1.id}",
        json={"title": "Updated Title", "slug": "published-article", "content": "Updated content."},
        headers=moderator_headers,
    )
    assert r.status_code == 200
    with app.app_context():
        en_trans = NewsArticleTranslation.query.filter_by(
            article_id=pub1.id, language_code="en"
        ).first()
        assert en_trans is not None
        assert en_trans.translation_status == "outdated"


def test_verification_email_does_not_log_token(app, caplog, test_user):
    """Regression: send_verification_email must not log raw token or usable activation URL."""
    from app.services.mail_service import send_verification_email
    user, _ = test_user
    raw_token = "regression-test-secret-token-xyz"
    with app.test_request_context("http://testserver/"):
        with caplog.at_level(logging.INFO, logger="app.services.mail_service"):
            send_verification_email(user, raw_token)
    log_text = caplog.text
    assert raw_token not in log_text
    assert "/activate/" + raw_token not in log_text


def test_password_reset_email_does_not_log_token_or_url(app, caplog, test_user):
    """Regression: send_password_reset_email must not log raw token or usable reset URL."""
    from app.services.mail_service import send_password_reset_email
    user, _ = test_user
    raw_token = "regression-reset-secret-abc"
    with app.test_request_context("http://testserver/"):
        with caplog.at_level(logging.INFO, logger="app.services.mail_service"):
            send_password_reset_email(user, raw_token)
    log_text = caplog.text
    assert raw_token not in log_text
    assert "reset" in log_text.lower() or "password" in log_text.lower()


def test_wiki_update_marks_other_translations_outdated(app, moderator_headers, client):
    """Updating one wiki translation (content/title/slug) marks other languages outdated and sets source_version."""
    r1 = client.post(
        "/api/v1/wiki-admin/pages",
        json={"key": "outdated-test-page"},
        headers=moderator_headers,
    )
    assert r1.status_code == 201
    page_id = r1.get_json()["id"]
    r2 = client.put(
        f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
        json={"title": "De Title", "slug": "outdated-test-de", "content_markdown": "De content."},
        headers=moderator_headers,
    )
    assert r2.status_code == 200
    r3 = client.put(
        f"/api/v1/wiki-admin/pages/{page_id}/translations/en",
        json={"title": "En Title", "slug": "outdated-test-en", "content_markdown": "En content."},
        headers=moderator_headers,
    )
    assert r3.status_code == 200
    r4 = client.put(
        f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
        json={"title": "De Title Updated", "slug": "outdated-test-de", "content_markdown": "De content updated."},
        headers=moderator_headers,
    )
    assert r4.status_code == 200
    with app.app_context():
        from app.models import WikiPageTranslation
        de_trans = WikiPageTranslation.query.filter_by(page_id=page_id, language_code="de").first()
        en_trans = WikiPageTranslation.query.filter_by(page_id=page_id, language_code="en").first()
        assert de_trans is not None
        assert en_trans is not None
        assert de_trans.source_version is not None
        assert en_trans.translation_status == "outdated"
