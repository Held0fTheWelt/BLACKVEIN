"""
WAVE 4: Route and rendering contract tests for administration-tool.

Tests cover:
- Route contract compliance (200, 404 for valid/invalid requests)
- Template context consistency (required keys, backend unavailability)
- Rendering behavior with empty backend data
- Clean behavior on upstream partial failure
- Graceful rendering without backend
"""
from __future__ import annotations

import pytest
from conftest import captured_templates


# ============================================================================
# PUBLIC ROUTES RENDERING CONTRACTS
# ============================================================================


class TestPublicRoutesRenderingContract:
    """Test public routes render expected templates with proper context."""

    @pytest.mark.contract
    @pytest.mark.parametrize(
        ("path", "template_name"),
        [
            ("/", "index.html"),
            ("/news", "news.html"),
            ("/news/1", "news_detail.html"),
            ("/news/999", "news_detail.html"),
            ("/wiki", "wiki_public.html"),
            ("/wiki/lore/city", "wiki_public.html"),
            ("/wiki/history/past-civilizations", "wiki_public.html"),
            ("/forum", "forum/index.html"),
            ("/forum/categories/general", "forum/category.html"),
            ("/forum/categories/lore", "forum/category.html"),
            ("/forum/threads/welcome", "forum/thread.html"),
            ("/forum/threads/rules-and-guidelines", "forum/thread.html"),
            ("/forum/notifications", "forum/notifications.html"),
            ("/forum/saved", "forum/saved_threads.html"),
            ("/forum/tags/devlog", "forum/tag_detail.html"),
            ("/forum/tags/lore", "forum/tag_detail.html"),
            ("/users/1/profile", "user/profile.html"),
            ("/users/7/profile", "user/profile.html"),
            ("/users/999/profile", "user/profile.html"),
        ],
    )
    def test_public_route_renders_correct_template(self, app, client, path: str, template_name: str):
        """Contract: Public routes render the correct template."""
        with captured_templates(app) as templates:
            response = client.get(path)

        assert response.status_code == 200, f"Path {path} should return 200"
        assert templates, f"No template rendered for {path}"
        rendered_template_name = templates[-1][0]
        assert rendered_template_name == template_name, \
            f"Path {path} should render {template_name}, got {rendered_template_name}"

    @pytest.mark.contract
    @pytest.mark.parametrize("path", ["/", "/news", "/wiki", "/forum", "/users/1/profile"])
    def test_public_route_provides_required_context_keys(self, app, client, path: str):
        """Contract: All public routes provide backend_api_url and frontend_config."""
        with captured_templates(app) as templates:
            response = client.get(path)

        assert response.status_code == 200
        assert templates, f"No template rendered for {path}"
        _, context = templates[-1]

        # All routes must provide these context keys
        assert "backend_api_url" in context, f"{path} missing backend_api_url"
        assert "frontend_config" in context, f"{path} missing frontend_config"
        assert "current_lang" in context, f"{path} missing current_lang"
        assert "supported_languages" in context, f"{path} missing supported_languages"
        assert "t" in context, f"{path} missing translation dict (t)"

    @pytest.mark.contract
    def test_index_page_renders_html_with_hero_section(self, client):
        """Contract: Index page renders HTML with hero content."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"<!DOCTYPE" in response.data or b"<html" in response.data.lower()
        # Check for hero section in rendered HTML
        assert b"hero" in response.data.lower() or b"section" in response.data.lower()

    @pytest.mark.contract
    def test_news_list_page_renders_with_content(self, client):
        """Contract: News list page renders successfully."""
        response = client.get("/news")
        assert response.status_code == 200
        assert b"<!DOCTYPE" in response.data or b"<html" in response.data.lower()
        # Should have HTML structure, no traceback
        assert b"Traceback" not in response.data

    @pytest.mark.contract
    def test_news_detail_page_passes_news_id_to_template(self, app, client):
        """Contract: News detail route passes news_id to template context."""
        with captured_templates(app) as templates:
            response = client.get("/news/42")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "news_id" in context
        assert context["news_id"] == 42

    @pytest.mark.contract
    def test_wiki_page_with_slug_passes_slug_to_template(self, app, client):
        """Contract: Wiki route passes slug to template context."""
        with captured_templates(app) as templates:
            response = client.get("/wiki/lore/city")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "slug" in context
        assert context["slug"] == "lore/city"

    @pytest.mark.contract
    def test_wiki_default_slug_is_wiki(self, app, client):
        """Contract: Wiki default slug is 'wiki' when no slug provided."""
        with captured_templates(app) as templates:
            response = client.get("/wiki")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "slug" in context
        assert context["slug"] == "wiki"

    @pytest.mark.contract
    def test_forum_category_passes_category_slug(self, app, client):
        """Contract: Forum category route passes category_slug."""
        with captured_templates(app) as templates:
            response = client.get("/forum/categories/lore")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "category_slug" in context
        assert context["category_slug"] == "lore"

    @pytest.mark.contract
    def test_forum_thread_passes_thread_slug(self, app, client):
        """Contract: Forum thread route passes thread_slug."""
        with captured_templates(app) as templates:
            response = client.get("/forum/threads/story")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "thread_slug" in context
        assert context["thread_slug"] == "story"

    @pytest.mark.contract
    def test_forum_tag_passes_tag_slug(self, app, client):
        """Contract: Forum tag route passes tag_slug."""
        with captured_templates(app) as templates:
            response = client.get("/forum/tags/lore")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "tag_slug" in context
        assert context["tag_slug"] == "lore"

    @pytest.mark.contract
    def test_user_profile_passes_user_id(self, app, client):
        """Contract: User profile route passes user_id."""
        with captured_templates(app) as templates:
            response = client.get("/users/123/profile")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "user_id" in context
        assert context["user_id"] == 123


# ============================================================================
# MANAGEMENT ROUTES RENDERING CONTRACTS
# ============================================================================


class TestManagementRoutesRenderingContract:
    """Test management routes render expected templates."""

    @pytest.mark.contract
    @pytest.mark.parametrize(
        ("path", "template_name"),
        [
            ("/manage", "manage/dashboard.html"),
            ("/manage/login", "manage/login.html"),
            ("/manage/news", "manage/news.html"),
            ("/manage/users", "manage/users.html"),
            ("/manage/roles", "manage/roles.html"),
            ("/manage/areas", "manage/areas.html"),
            ("/manage/feature-areas", "manage/feature_areas.html"),
            ("/manage/wiki", "manage/wiki.html"),
            ("/manage/slogans", "manage/slogans.html"),
            ("/manage/data", "manage/data.html"),
            ("/manage/forum", "manage/forum.html"),
            ("/manage/inspector-workbench", "manage/inspector_workbench.html"),
            ("/manage/diagnosis", "manage/diagnosis.html"),
            ("/manage/play-service-control", "manage/play_service_control.html"),
            ("/manage/analytics", "manage_analytics.html"),
            ("/manage/moderator-dashboard", "manage_moderator_dashboard.html"),
        ],
    )
    def test_management_route_renders_correct_template(self, app, client, path: str, template_name: str):
        """Contract: Management routes render the correct template."""
        with captured_templates(app) as templates:
            response = client.get(path)

        assert response.status_code == 200
        assert templates, f"No template rendered for {path}"
        rendered_template_name = templates[-1][0]
        assert rendered_template_name == template_name, \
            f"Path {path} should render {template_name}, got {rendered_template_name}"

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        ["/manage", "/manage/login", "/manage/news", "/manage/users", "/manage/roles"],
    )
    def test_management_route_provides_context(self, app, client, path: str):
        """Contract: Management routes provide required context."""
        with captured_templates(app) as templates:
            response = client.get(path)

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context

    @pytest.mark.contract
    def test_manage_login_renders_html(self, client):
        """Contract: Management login page renders HTML."""
        response = client.get("/manage/login")
        assert response.status_code == 200
        assert b"<!DOCTYPE" in response.data or b"<html" in response.data.lower()


# ============================================================================
# TEMPLATE CONTEXT CONSISTENCY CONTRACTS
# ============================================================================


class TestTemplateContextConsistencyContracts:
    """Test that template context is consistent and complete."""

    @pytest.mark.contract
    def test_frontend_config_has_all_required_fields(self, app, client):
        """Contract: frontend_config has all required fields."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        config = context["frontend_config"]

        required_fields = [
            "backendApiUrl",
            "apiProxyBase",
            "supportedLanguages",
            "defaultLanguage",
            "currentLanguage",
        ]
        for field in required_fields:
            assert field in config, f"frontend_config missing required field: {field}"

    @pytest.mark.contract
    def test_frontend_config_api_proxy_base_is_correct(self, app, client):
        """Contract: frontend_config.apiProxyBase points to correct proxy endpoint."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        assert context["frontend_config"]["apiProxyBase"] == "/_proxy"

    @pytest.mark.contract
    def test_frontend_config_backend_url_matches_app_config(self, app, client):
        """Contract: frontend_config.backendApiUrl matches app config."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        assert context["frontend_config"]["backendApiUrl"] == app.config["BACKEND_API_URL"]
        assert context["backend_api_url"] == app.config["BACKEND_API_URL"]

    @pytest.mark.contract
    def test_translation_dict_is_dict_not_none(self, app, client):
        """Contract: Translation dict 't' is always a dict, never None."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        t = context["t"]
        assert isinstance(t, dict), f"Translation dict should be dict, got {type(t)}"
        assert t is not None

    @pytest.mark.contract
    def test_supported_languages_includes_de_and_en(self, app, client):
        """Contract: supported_languages includes both 'de' and 'en'."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        langs = context["supported_languages"]
        assert "de" in langs, "supported_languages must include 'de'"
        assert "en" in langs, "supported_languages must include 'en'"

    @pytest.mark.contract
    def test_current_lang_matches_frontend_config_current_language(self, app, client):
        """Contract: current_lang matches frontend_config.currentLanguage."""
        with captured_templates(app) as templates:
            response = client.get("/?lang=en")

        _, context = templates[-1]
        assert context["current_lang"] == context["frontend_config"]["currentLanguage"]

    @pytest.mark.contract
    def test_context_consistent_across_multiple_routes(self, app, client):
        """Contract: Essential context keys consistent across all routes."""
        paths = ["/", "/news", "/wiki", "/forum", "/users/1/profile", "/manage/login"]
        essential_keys = ["backend_api_url", "frontend_config", "current_lang", "t"]

        for path in paths:
            with captured_templates(app) as templates:
                response = client.get(path)

            assert response.status_code == 200
            _, context = templates[-1]
            for key in essential_keys:
                assert key in context, f"Context missing {key} on route {path}"


# ============================================================================
# RENDERING WITHOUT BACKEND DATA CONTRACTS
# ============================================================================


class TestRenderingWithoutBackendData:
    """Test pages render successfully even when backend data is unavailable."""

    @pytest.mark.contract
    def test_html_routes_return_html_status_200(self, client):
        """Contract: HTML routes return 200 even without backend contact."""
        response = client.get("/")
        assert response.status_code == 200
        # Should return HTML (frontend renders templates, not JS)
        assert response.content_type.startswith("text/html")

    @pytest.mark.contract
    def test_news_list_renders_without_backend(self, client):
        """Contract: News list page renders without backend."""
        response = client.get("/news")
        assert response.status_code == 200
        assert b"<!DOCTYPE" in response.data or b"<html" in response.data.lower()

    @pytest.mark.contract
    def test_forum_renders_without_backend(self, client):
        """Contract: Forum page renders without backend."""
        response = client.get("/forum")
        assert response.status_code == 200
        assert b"<!DOCTYPE" in response.data or b"<html" in response.data.lower()

    @pytest.mark.contract
    def test_wiki_renders_without_backend(self, client):
        """Contract: Wiki page renders without backend."""
        response = client.get("/wiki")
        assert response.status_code == 200
        assert b"<!DOCTYPE" in response.data or b"<html" in response.data.lower()

    @pytest.mark.contract
    def test_management_pages_render_without_backend(self, client):
        """Contract: Management pages render without backend."""
        paths = ["/manage", "/manage/login", "/manage/news", "/manage/users"]
        for path in paths:
            response = client.get(path)
            assert response.status_code == 200, f"{path} failed to render"
            assert b"<!DOCTYPE" in response.data or b"<html" in response.data.lower(), \
                f"{path} did not return HTML"

    @pytest.mark.contract
    def test_routes_dont_crash_on_empty_backend_response(self, app, client):
        """Contract: Routes render successfully (backend data loading is async in JS)."""
        # Frontend routes render HTML templates; data loading happens in JS via /_proxy calls.
        # This test verifies the HTML templates themselves render without requiring backend.
        response = client.get("/")
        assert response.status_code == 200
        assert b"<!DOCTYPE" in response.data or b"<html" in response.data.lower()


# ============================================================================
# RESPONSE CONTENT TYPE AND HEADERS CONTRACTS
# ============================================================================


class TestResponseContentTypeContracts:
    """Test that responses have appropriate content types and headers."""

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        ["/", "/news", "/wiki", "/forum", "/manage/login", "/manage/users"],
    )
    def test_html_routes_return_html_content_type(self, client, path: str):
        """Contract: HTML routes return text/html content type."""
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("Content-Type", "")

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        ["/", "/news", "/wiki", "/forum", "/manage/login"],
    )
    def test_html_routes_include_security_headers(self, client, path: str):
        """Contract: HTML routes include security headers."""
        response = client.get(path)
        assert response.status_code == 200

        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Content-Security-Policy",
            "Referrer-Policy",
        ]
        for header in required_headers:
            assert header in response.headers, \
                f"{header} missing from {path} response"

    @pytest.mark.contract
    def test_html_routes_have_x_content_type_options_nosniff(self, client):
        """Contract: HTML routes have X-Content-Type-Options: nosniff."""
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    @pytest.mark.contract
    def test_html_routes_have_x_frame_options_deny(self, client):
        """Contract: HTML routes have X-Frame-Options: DENY."""
        response = client.get("/")
        assert response.headers.get("X-Frame-Options") == "DENY"


# ============================================================================
# INVALID ROUTE CONTRACTS
# ============================================================================


class TestInvalidRoutesContract:
    """Test that invalid routes return appropriate error responses."""

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        [
            "/does-not-exist",
            "/nonexistent/route",
            "/invalid/path",
            "/manage/invalid",
        ],
    )
    def test_invalid_routes_return_404(self, client, path: str):
        """Contract: Invalid routes return 404."""
        response = client.get(path)
        assert response.status_code == 404

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        [
            "/news/invalid",
            "/news/abc",
            "/users/invalid/profile",
            "/users/abc/profile",
        ],
    )
    def test_invalid_route_parameters_return_404(self, client, path: str):
        """Contract: Routes with invalid parameter types return 404."""
        response = client.get(path)
        assert response.status_code == 404

    @pytest.mark.contract
    def test_404_response_has_security_headers(self, client):
        """Contract: 404 responses include security headers."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert response.headers.get("X-Frame-Options") == "DENY"


# ============================================================================
# TEMPLATE PARAMETER PASSING CONTRACTS
# ============================================================================


class TestTemplateParameterPassingContracts:
    """Test that routes correctly pass parameters to templates."""

    @pytest.mark.contract
    @pytest.mark.parametrize("news_id", [1, 42, 999, 100000])
    def test_news_detail_passes_various_ids(self, app, client, news_id: int):
        """Contract: News detail route passes various numeric IDs correctly."""
        with captured_templates(app) as templates:
            response = client.get(f"/news/{news_id}")

        assert response.status_code == 200
        _, context = templates[-1]
        assert context["news_id"] == news_id

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "slug",
        ["general", "lore", "off-topic", "rules-and-guidelines"],
    )
    def test_forum_category_passes_various_slugs(self, app, client, slug: str):
        """Contract: Forum category route passes various slugs correctly."""
        with captured_templates(app) as templates:
            response = client.get(f"/forum/categories/{slug}")

        assert response.status_code == 200
        _, context = templates[-1]
        assert context["category_slug"] == slug

    @pytest.mark.contract
    @pytest.mark.parametrize("user_id", [1, 7, 123, 9999])
    def test_user_profile_passes_various_ids(self, app, client, user_id: int):
        """Contract: User profile route passes various numeric IDs correctly."""
        with captured_templates(app) as templates:
            response = client.get(f"/users/{user_id}/profile")

        assert response.status_code == 200
        _, context = templates[-1]
        assert context["user_id"] == user_id

    @pytest.mark.contract
    def test_wiki_multi_level_slug_passed_correctly(self, app, client):
        """Contract: Wiki route with multi-level slug preserves slashes."""
        with captured_templates(app) as templates:
            response = client.get("/wiki/history/age-of-shadows/first-war")

        assert response.status_code == 200
        _, context = templates[-1]
        assert context["slug"] == "history/age-of-shadows/first-war"


# ============================================================================
# BACKEND URL HANDLING IN TEMPLATES
# ============================================================================


class TestBackendUrlHandling:
    """Test backend_api_url availability and correctness in templates."""

    @pytest.mark.contract
    def test_backend_url_available_in_all_routes(self, app, client):
        """Contract: backend_api_url is available in all route templates."""
        paths = ["/", "/news", "/wiki", "/forum", "/manage/login", "/users/1/profile"]

        for path in paths:
            with captured_templates(app) as templates:
                response = client.get(path)

            assert response.status_code == 200
            _, context = templates[-1]
            assert "backend_api_url" in context
            assert context["backend_api_url"] is not None
            assert isinstance(context["backend_api_url"], str)

    @pytest.mark.contract
    def test_backend_url_no_trailing_slash(self, app, client):
        """Contract: backend_api_url has no trailing slash."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        backend_url = context["backend_api_url"]
        assert not backend_url.endswith("/"), "backend_api_url should not have trailing slash"

    @pytest.mark.contract
    def test_backend_url_matches_config(self, app, client):
        """Contract: backend_api_url matches app configuration."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        assert context["backend_api_url"] == app.config["BACKEND_API_URL"]


# ============================================================================
# TEMPLATE RENDERING WITHOUT ERRORS
# ============================================================================


class TestTemplateRenderingStability:
    """Test that templates render without errors or exceptions."""

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        [
            "/",
            "/news",
            "/news/1",
            "/wiki",
            "/wiki/lore",
            "/forum",
            "/forum/categories/general",
            "/forum/threads/welcome",
            "/forum/notifications",
            "/forum/saved",
            "/forum/tags/devlog",
            "/users/1/profile",
            "/manage",
            "/manage/login",
            "/manage/news",
            "/manage/users",
        ],
    )
    def test_route_renders_without_traceback(self, client, path: str):
        """Contract: Routes render without Python tracebacks."""
        response = client.get(path)
        assert response.status_code == 200
        # Should not contain traceback
        assert b"Traceback" not in response.data
        assert b"File \"" not in response.data
        # Should be HTML
        assert b"<!DOCTYPE" in response.data or b"<html" in response.data.lower()

    @pytest.mark.contract
    def test_all_templates_render_valid_html(self, client):
        """Contract: All templates render valid HTML structure."""
        paths = ["/", "/news", "/wiki", "/forum", "/manage/login"]

        for path in paths:
            response = client.get(path)
            assert response.status_code == 200
            # Check for basic HTML structure
            data = response.get_data(as_text=True)
            assert "<" in data and ">" in data, f"{path} should have HTML tags"
