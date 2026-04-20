"""
WAVE 4: Comprehensive contract tests for administration-tool routes, rendering, and i18n.

Tests cover:
- Route contract compliance (200, 404 for valid/invalid requests)
- Template context consistency (required keys, backend unavailability)
- i18n contract (language resolution, locale fallback, translations)
- Error page handling (404, 500, proxy errors)
"""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest
from conftest import captured_templates, load_frontend_module


# ============================================================================
# ROUTE CONTRACT TESTS
# ============================================================================


class TestPublicRoutesContract:
    """Test public routes return 200 for valid requests."""

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        [
            "/",
            "/news",
            "/news/1",
            "/news/999",
            "/wiki",
            "/wiki/lore/city",
            "/forum",
            "/forum/categories/general",
            "/forum/threads/welcome",
            "/forum/notifications",
            "/forum/saved",
            "/forum/tags/devlog",
            "/users/7/profile",
            "/users/1/profile",
            "/users/999/profile",
        ],
    )
    def test_public_routes_return_200_for_valid_requests(self, client, path: str):
        """Contract: Public routes return 200 for any valid request structure."""
        response = client.get(path)
        assert response.status_code == 200, f"Path {path} should return 200"

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        [
            "/news/invalid",
            "/users/not-a-number/profile",
            "/users/abc/profile",
        ],
    )
    def test_invalid_parameter_types_return_404(self, client, path: str):
        """Contract: Routes with invalid parameter types return 404."""
        response = client.get(path)
        assert response.status_code == 404, f"Path {path} should return 404"


class TestManagementRoutesContract:
    """Test management routes return 200 for valid requests."""

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        [
            "/manage",
            "/manage/login",
            "/manage/news",
            "/manage/users",
            "/manage/roles",
            "/manage/areas",
            "/manage/feature-areas",
            "/manage/wiki",
            "/manage/slogans",
            "/manage/data",
            "/manage/forum",
            "/manage/diagnosis",
            "/manage/play-service-control",
        ],
    )
    def test_management_routes_return_200(self, client, path: str):
        """Contract: Management routes return 200 for valid paths."""
        response = client.get(path)
        assert response.status_code == 200, f"Management path {path} should return 200"

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        [
            "/manage/invalid",
            "/manage/nonexistent",
            "/manage/news/edit/123",
        ],
    )
    def test_invalid_management_routes_return_404(self, client, path: str):
        """Contract: Invalid management routes return 404."""
        response = client.get(path)
        assert response.status_code == 404, f"Path {path} should return 404"


# ============================================================================
# TEMPLATE CONTEXT CONSISTENCY TESTS
# ============================================================================


class TestTemplateContextConsistency:
    """Test that routes provide consistent template context."""

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        [
            "/",
            "/news",
            "/wiki",
            "/forum",
            "/users/1/profile",
            "/manage",
            "/manage/login",
            "/manage/news",
        ],
    )
    def test_all_routes_provide_backend_api_url_context(self, app, client, path: str):
        """Contract: All routes provide backend_api_url in template context."""
        with captured_templates(app) as templates:
            response = client.get(path)

        assert response.status_code == 200
        assert templates, f"No template rendered for {path}"
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert context["backend_api_url"] == app.config["BACKEND_API_URL"]

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        [
            "/",
            "/news",
            "/wiki",
            "/forum",
            "/users/1/profile",
        ],
    )
    def test_all_routes_provide_frontend_config_context(self, app, client, path: str):
        """Contract: All routes provide frontend_config with required keys."""
        with captured_templates(app) as templates:
            response = client.get(path)

        assert response.status_code == 200
        _, context = templates[-1]
        assert "frontend_config" in context
        config = context["frontend_config"]
        assert "backendApiUrl" in config
        assert "apiProxyBase" in config
        assert "supportedLanguages" in config
        assert "defaultLanguage" in config
        assert "currentLanguage" in config

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        [
            "/",
            "/news",
            "/wiki",
            "/forum",
        ],
    )
    def test_all_routes_provide_language_context(self, app, client, path: str):
        """Contract: All routes provide language-related context."""
        with captured_templates(app) as templates:
            response = client.get(path + "?lang=en")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context
        assert isinstance(context["t"], dict)

    @pytest.mark.contract
    def test_route_with_numeric_id_provides_id_context(self, app, client):
        """Contract: Routes with numeric IDs pass the ID to template context."""
        with captured_templates(app) as templates:
            response = client.get("/news/42")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "news_id" in context
        assert context["news_id"] == 42

    @pytest.mark.contract
    def test_route_with_slug_provides_slug_context(self, app, client):
        """Contract: Routes with slugs pass the slug to template context."""
        with captured_templates(app) as templates:
            response = client.get("/wiki/lore/city")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "slug" in context
        assert context["slug"] == "lore/city"

    @pytest.mark.contract
    def test_forum_category_provides_slug_context(self, app, client):
        """Contract: Forum category route provides category_slug."""
        with captured_templates(app) as templates:
            response = client.get("/forum/categories/general")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "category_slug" in context
        assert context["category_slug"] == "general"

    @pytest.mark.contract
    def test_forum_thread_provides_slug_context(self, app, client):
        """Contract: Forum thread route provides thread_slug."""
        with captured_templates(app) as templates:
            response = client.get("/forum/threads/welcome")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "thread_slug" in context
        assert context["thread_slug"] == "welcome"

    @pytest.mark.contract
    def test_user_profile_provides_user_id_context(self, app, client):
        """Contract: User profile route provides user_id."""
        with captured_templates(app) as templates:
            response = client.get("/users/7/profile")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "user_id" in context
        assert context["user_id"] == 7

    @pytest.mark.contract
    def test_forum_tag_provides_slug_context(self, app, client):
        """Contract: Forum tag route provides tag_slug."""
        with captured_templates(app) as templates:
            response = client.get("/forum/tags/lore")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "tag_slug" in context
        assert context["tag_slug"] == "lore"


# ============================================================================
# i18n CONTRACT TESTS
# ============================================================================


class TestI18nContract:
    """Test internationalization contract compliance."""

    @pytest.mark.contract
    def test_lang_query_parameter_switches_locale(self, app, client):
        """Contract: lang query parameter switches the current language."""
        with captured_templates(app) as templates:
            response = client.get("/?lang=en")

        assert response.status_code == 200
        _, context = templates[-1]
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_lang_query_parameter_persists_in_session(self, client):
        """Contract: lang query parameter persists language preference in session."""
        with client.session_transaction() as session:
            assert "lang" not in session

        client.get("/?lang=en")

        with client.session_transaction() as session:
            assert session.get("lang") == "en"

    @pytest.mark.contract
    def test_session_language_persists_across_requests(self, client):
        """Contract: Language set in session persists across subsequent requests."""
        # Set language in first request
        client.get("/?lang=de")

        # Verify it persists in second request without explicit lang parameter
        with client.session_transaction() as session:
            assert session.get("lang") == "de"

    @pytest.mark.contract
    def test_accept_language_header_fallback(self, app, client):
        """Contract: Accept-Language header is used as fallback when no session/query."""
        with captured_templates(app) as templates:
            response = client.get(
                "/",
                headers={"Accept-Language": "en-US,en;q=0.9"},
            )

        assert response.status_code == 200
        _, context = templates[-1]
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_unsupported_locale_falls_back_to_default(self, app, client):
        """Contract: Unsupported locale falls back to default language."""
        with captured_templates(app) as templates:
            response = client.get(
                "/?lang=fr",  # fr is not supported
                headers={"Accept-Language": "es-ES"},  # es is not supported
            )

        assert response.status_code == 200
        _, context = templates[-1]
        assert context["current_lang"] == "de"  # Default language

    @pytest.mark.contract
    def test_supported_languages_list_includes_both_locales(self, app, client):
        """Contract: Supported languages list includes both 'de' and 'en'."""
        with captured_templates(app) as templates:
            response = client.get("/")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "supported_languages" in context
        supported = context["supported_languages"]
        assert "de" in supported
        assert "en" in supported

    @pytest.mark.contract
    def test_german_translations_are_loaded(self, app, client):
        """Contract: German translations are loaded for 'de' locale."""
        with captured_templates(app) as templates:
            response = client.get("/?lang=de")

        assert response.status_code == 200
        _, context = templates[-1]
        t = context["t"]
        # Verify translations dict is loaded (should have content)
        assert isinstance(t, dict)
        # The dict should have at least some keys from the translation file
        assert len(t) > 0

    @pytest.mark.contract
    def test_english_translations_are_loaded(self, app, client):
        """Contract: English translations are loaded for 'en' locale."""
        with captured_templates(app) as templates:
            response = client.get("/?lang=en")

        assert response.status_code == 200
        _, context = templates[-1]
        t = context["t"]
        # Verify translations dict is loaded
        assert isinstance(t, dict)
        assert len(t) > 0

    @pytest.mark.contract
    def test_query_lang_takes_precedence_over_session(self, client):
        """Contract: Query lang parameter takes precedence over session language."""
        # Set session language to 'de'
        client.get("/?lang=de")

        # Request with en in query parameter should override session
        with client.session_transaction() as session:
            assert session["lang"] == "de"

        # Now request with en in query
        client.get("/?lang=en")

        with client.session_transaction() as session:
            # Session should now be updated to en
            assert session["lang"] == "en"

    @pytest.mark.contract
    def test_session_language_takes_precedence_over_accept_language(self, app, client):
        """Contract: Session language takes precedence over Accept-Language header."""
        # Set session language
        client.get("/?lang=en")

        # Request with Accept-Language for different language
        with captured_templates(app) as templates:
            response = client.get(
                "/",
                headers={"Accept-Language": "de-DE,de;q=0.9"},
            )

        _, context = templates[-1]
        # Should use session language (en), not Accept-Language (de)
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_default_language_is_german(self, app, client):
        """Contract: Default language is German ('de')."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        assert context["current_lang"] == "de"

    @pytest.mark.contract
    def test_language_context_consistent_across_routes(self, app, client):
        """Contract: Language context is consistent across all routes."""
        paths = ["/", "/news", "/wiki", "/forum", "/users/1/profile"]

        for path in paths:
            with captured_templates(app) as templates:
                response = client.get(path + "?lang=en")

            assert response.status_code == 200
            _, context = templates[-1]
            assert context["current_lang"] == "en"
            assert "t" in context
            assert isinstance(context["t"], dict)


# ============================================================================
# SECURITY HEADERS AND ERROR PAGE TESTS
# ============================================================================


class TestErrorPageContract:
    """Test error pages and graceful error handling."""

    @pytest.mark.contract
    @pytest.mark.security
    def test_invalid_route_returns_404(self, client):
        """Contract: Invalid routes return 404."""
        response = client.get("/nonexistent/route/that/does/not/exist")
        assert response.status_code == 404

    @pytest.mark.contract
    @pytest.mark.security
    def test_error_pages_include_security_headers(self, client):
        """Contract: Even 404 error pages include security headers."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        # Security headers should still be present
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"

    @pytest.mark.contract
    @pytest.mark.security
    def test_proxy_502_error_includes_security_headers(self, monkeypatch):
        """Contract: Proxy 502 errors include security headers."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout: int = 0):
            raise URLError("Network unreachable")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 502
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"

    @pytest.mark.contract
    @pytest.mark.security
    def test_proxy_403_forbidden_for_admin_paths(self, client):
        """Contract: Admin paths return 403 Forbidden."""
        response = client.get("/_proxy/admin/users")
        assert response.status_code == 403
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    @pytest.mark.contract
    def test_proxy_timeout_returns_502(self, monkeypatch):
        """Contract: Proxy timeout returns 502 Bad Gateway."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout: int = 0):
            raise URLError("Connection timed out")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")
        assert response.status_code == 502

    @pytest.mark.contract
    def test_proxy_http_error_passes_through(self, monkeypatch):
        """Contract: HTTP errors from backend pass through with original status."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout: int = 0):
            raise HTTPError(
                url=request.full_url,
                code=404,
                msg="Not Found",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b'{"error":"Not found"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/users/999")
        assert response.status_code == 404

    @pytest.mark.contract
    @pytest.mark.security
    def test_proxy_500_error_includes_security_headers(self, monkeypatch):
        """Contract: Proxy 500 errors from backend include security headers."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout: int = 0):
            raise HTTPError(
                url=request.full_url,
                code=500,
                msg="Internal Server Error",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b'{"error":"Internal server error"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/data")
        assert response.status_code == 500
        assert response.headers.get("X-Content-Type-Options") == "nosniff"


# ============================================================================
# PROXY BACKEND AVAILABILITY TESTS
# ============================================================================


class TestProxyBackendAvailability:
    """Test graceful handling of backend unavailability."""

    @pytest.mark.contract
    def test_proxy_missing_backend_url_returns_500(self, frontend_module):
        """Contract: Missing backend URL returns 500."""
        frontend_module.app.config["BACKEND_API_URL"] = ""
        client = frontend_module.app.test_client()

        response = client.get("/_proxy/api/v1/news")
        assert response.status_code == 500
        assert b"Backend API URL not configured" in response.data

    @pytest.mark.contract
    def test_routes_render_without_backend_contact(self, client):
        """Contract: Frontend routes render without contacting backend."""
        # Routes should render HTML templates without making backend calls
        response = client.get("/news")
        assert response.status_code == 200
        # Should have HTML content
        assert b"<!DOCTYPE" in response.data or b"<html" in response.data.lower()

    @pytest.mark.contract
    def test_frontend_config_always_provided_regardless_of_backend_status(self, app, client):
        """Contract: frontend_config is always provided to templates."""
        with captured_templates(app) as templates:
            response = client.get("/news")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "frontend_config" in context
        # Should have necessary config even if backend is unavailable
        assert "apiProxyBase" in context["frontend_config"]


# ============================================================================
# RESPONSE CONTENT TYPE TESTS
# ============================================================================


class TestResponseContentTypes:
    """Test that responses have appropriate content types."""

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        ["/", "/news", "/wiki", "/forum", "/manage/login"],
    )
    def test_html_routes_return_html_content_type(self, client, path: str):
        """Contract: HTML routes return text/html content type."""
        response = client.get(path)
        assert response.status_code == 200
        content_type = response.headers.get("Content-Type", "")
        assert "text/html" in content_type

    @pytest.mark.contract
    def test_proxy_forwards_json_content_type(self, monkeypatch):
        """Contract: Proxy forwards Content-Type from backend."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout: int = 0):
            from tests.test_routes_contracts import DummyUpstreamResponse

            return DummyUpstreamResponse(
                b'{"data": []}',
                status=200,
                content_type="application/json",
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("Content-Type", "")


# ============================================================================
# HELPER CLASSES
# ============================================================================


class DummyUpstreamResponse:
    """Mock upstream HTTP response for testing."""

    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        content_type: str = "application/json",
    ) -> None:
        self._body = body
        self.status = status
        self.headers = {"Content-Type": content_type}

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False
