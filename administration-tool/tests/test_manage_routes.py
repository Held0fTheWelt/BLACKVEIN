"""
WAVE 4: Comprehensive tests for management routes rendering and context validation.

Tests cover:
- Management route rendering with correct templates
- Template context (backend_api_url, frontend_config, language metadata)
- user_id parameter passed correctly to user profile route
- All management area routes (dashboard, login, news, users, roles, etc.)
- Security headers on management routes
- Graceful degradation when backend data unavailable
- Template rendering without exceptions
"""
from __future__ import annotations

import pytest

from conftest import captured_templates


class TestManagementDashboardRoute:
    """Test GET /manage route (management area entry point)."""

    @pytest.mark.unit
    def test_manage_dashboard_returns_200(self, client):
        """GET /manage should return 200 OK."""
        response = client.get("/manage")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_manage_dashboard_renders_correct_template(self, app, client):
        """GET /manage should render manage/dashboard.html template."""
        with captured_templates(app) as templates:
            response = client.get("/manage")

        assert response.status_code == 200
        assert templates, "No template rendered for /manage"
        assert templates[-1][0] == "manage/dashboard.html"

    @pytest.mark.contract
    def test_manage_dashboard_provides_required_context(self, app, client):
        """GET /manage should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/manage")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestManagementLoginRoute:
    """Test GET /manage/login route."""

    @pytest.mark.unit
    def test_manage_login_returns_200(self, client):
        """GET /manage/login should return 200 OK."""
        response = client.get("/manage/login")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_manage_login_renders_correct_template(self, app, client):
        """GET /manage/login should render manage/login.html template."""
        with captured_templates(app) as templates:
            response = client.get("/manage/login")

        assert response.status_code == 200
        assert templates, "No template rendered for /manage/login"
        assert templates[-1][0] == "manage/login.html"

    @pytest.mark.contract
    def test_manage_login_provides_required_context(self, app, client):
        """GET /manage/login should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/manage/login")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestManagementNewsRoute:
    """Test GET /manage/news route."""

    @pytest.mark.unit
    def test_manage_news_returns_200(self, client):
        """GET /manage/news should return 200 OK."""
        response = client.get("/manage/news")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_manage_news_renders_correct_template(self, app, client):
        """GET /manage/news should render manage/news.html template."""
        with captured_templates(app) as templates:
            response = client.get("/manage/news")

        assert response.status_code == 200
        assert templates, "No template rendered for /manage/news"
        assert templates[-1][0] == "manage/news.html"

    @pytest.mark.contract
    def test_manage_news_provides_required_context(self, app, client):
        """GET /manage/news should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/manage/news")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestManagementUsersRoute:
    """Test GET /manage/users route."""

    @pytest.mark.unit
    def test_manage_users_returns_200(self, client):
        """GET /manage/users should return 200 OK."""
        response = client.get("/manage/users")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_manage_users_renders_correct_template(self, app, client):
        """GET /manage/users should render manage/users.html template."""
        with captured_templates(app) as templates:
            response = client.get("/manage/users")

        assert response.status_code == 200
        assert templates, "No template rendered for /manage/users"
        assert templates[-1][0] == "manage/users.html"

    @pytest.mark.contract
    def test_manage_users_provides_required_context(self, app, client):
        """GET /manage/users should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/manage/users")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestManagementRolesRoute:
    """Test GET /manage/roles route."""

    @pytest.mark.unit
    def test_manage_roles_returns_200(self, client):
        """GET /manage/roles should return 200 OK."""
        response = client.get("/manage/roles")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_manage_roles_renders_correct_template(self, app, client):
        """GET /manage/roles should render manage/roles.html template."""
        with captured_templates(app) as templates:
            response = client.get("/manage/roles")

        assert response.status_code == 200
        assert templates, "No template rendered for /manage/roles"
        assert templates[-1][0] == "manage/roles.html"

    @pytest.mark.contract
    def test_manage_roles_provides_required_context(self, app, client):
        """GET /manage/roles should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/manage/roles")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestManagementAreasRoute:
    """Test GET /manage/areas route."""

    @pytest.mark.unit
    def test_manage_areas_returns_200(self, client):
        """GET /manage/areas should return 200 OK."""
        response = client.get("/manage/areas")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_manage_areas_renders_correct_template(self, app, client):
        """GET /manage/areas should render manage/areas.html template."""
        with captured_templates(app) as templates:
            response = client.get("/manage/areas")

        assert response.status_code == 200
        assert templates, "No template rendered for /manage/areas"
        assert templates[-1][0] == "manage/areas.html"

    @pytest.mark.contract
    def test_manage_areas_provides_required_context(self, app, client):
        """GET /manage/areas should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/manage/areas")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestManagementFeatureAreasRoute:
    """Test GET /manage/feature-areas route."""

    @pytest.mark.unit
    def test_manage_feature_areas_returns_200(self, client):
        """GET /manage/feature-areas should return 200 OK."""
        response = client.get("/manage/feature-areas")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_manage_feature_areas_renders_correct_template(self, app, client):
        """GET /manage/feature-areas should render manage/feature_areas.html template."""
        with captured_templates(app) as templates:
            response = client.get("/manage/feature-areas")

        assert response.status_code == 200
        assert templates, "No template rendered for /manage/feature-areas"
        assert templates[-1][0] == "manage/feature_areas.html"

    @pytest.mark.contract
    def test_manage_feature_areas_provides_required_context(self, app, client):
        """GET /manage/feature-areas should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/manage/feature-areas")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestManagementWikiRoute:
    """Test GET /manage/wiki route."""

    @pytest.mark.unit
    def test_manage_wiki_returns_200(self, client):
        """GET /manage/wiki should return 200 OK."""
        response = client.get("/manage/wiki")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_manage_wiki_renders_correct_template(self, app, client):
        """GET /manage/wiki should render manage/wiki.html template."""
        with captured_templates(app) as templates:
            response = client.get("/manage/wiki")

        assert response.status_code == 200
        assert templates, "No template rendered for /manage/wiki"
        assert templates[-1][0] == "manage/wiki.html"

    @pytest.mark.contract
    def test_manage_wiki_provides_required_context(self, app, client):
        """GET /manage/wiki should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/manage/wiki")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestManagementForumRoute:
    """Test GET /manage/forum route."""

    @pytest.mark.unit
    def test_manage_forum_returns_200(self, client):
        """GET /manage/forum should return 200 OK."""
        response = client.get("/manage/forum")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_manage_forum_renders_correct_template(self, app, client):
        """GET /manage/forum should render manage/forum.html template."""
        with captured_templates(app) as templates:
            response = client.get("/manage/forum")

        assert response.status_code == 200
        assert templates, "No template rendered for /manage/forum"
        assert templates[-1][0] == "manage/forum.html"

    @pytest.mark.contract
    def test_manage_forum_provides_required_context(self, app, client):
        """GET /manage/forum should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/manage/forum")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestUserProfileRoute:
    """Test GET /users/<int:user_id>/profile route."""

    @pytest.mark.unit
    @pytest.mark.parametrize("user_id", [1, 7, 42, 999])
    def test_user_profile_returns_200(self, client, user_id):
        """GET /users/<int:user_id>/profile should return 200 OK for valid integer IDs."""
        response = client.get(f"/users/{user_id}/profile")
        assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.parametrize("user_id", [1, 7, 42])
    def test_user_profile_renders_correct_template(self, app, client, user_id):
        """GET /users/<int:user_id>/profile should render user/profile.html template."""
        with captured_templates(app) as templates:
            response = client.get(f"/users/{user_id}/profile")

        assert response.status_code == 200
        assert templates, f"No template rendered for /users/{user_id}/profile"
        assert templates[-1][0] == "user/profile.html"

    @pytest.mark.contract
    @pytest.mark.parametrize("user_id", [1, 7, 42])
    def test_user_profile_provides_user_id_context(self, app, client, user_id):
        """GET /users/<int:user_id>/profile should pass user_id to template context."""
        with captured_templates(app) as templates:
            response = client.get(f"/users/{user_id}/profile")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "user_id" in context
        assert context["user_id"] == user_id

    @pytest.mark.contract
    @pytest.mark.parametrize("user_id", [1, 7, 42])
    def test_user_profile_provides_required_context(self, app, client, user_id):
        """GET /users/<int:user_id>/profile should provide standard context keys."""
        with captured_templates(app) as templates:
            response = client.get(f"/users/{user_id}/profile")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context

    @pytest.mark.unit
    @pytest.mark.parametrize("invalid_id", ["abc", "invalid", "12.34"])
    def test_user_profile_rejects_invalid_ids(self, client, invalid_id):
        """GET /users/<invalid>/profile should return 404 for non-integer IDs."""
        response = client.get(f"/users/{invalid_id}/profile")
        assert response.status_code == 404


class TestManagementRoutesLanguageVariants:
    """Test management routes with language parameters."""

    @pytest.mark.integration
    @pytest.mark.parametrize("lang", ["de", "en"])
    def test_management_routes_respond_to_lang_parameter(self, client, lang):
        """Management routes should respond to ?lang parameter."""
        for path in ["/manage", "/manage/login", "/manage/news", "/manage/users"]:
            response = client.get(f"{path}?lang={lang}")
            assert response.status_code == 200

    @pytest.mark.integration
    def test_user_profile_with_lang_parameter(self, app, client):
        """GET /users/<id>/profile?lang=en should work and respect language."""
        with captured_templates(app) as templates:
            response = client.get("/users/42/profile?lang=en")

        assert response.status_code == 200
        _, context = templates[-1]
        assert context["current_lang"] == "en"
        assert context["user_id"] == 42


class TestManagementRoutesContextConsistency:
    """Test context consistency across all management routes."""

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
            "/manage/forum",
            "/manage/diagnosis",
            "/manage/play-service-control",
            "/manage/inspector-workbench",
            "/users/1/profile",
        ],
    )
    def test_all_management_routes_provide_backend_api_url(self, app, client, path):
        """All management routes should provide backend_api_url."""
        with captured_templates(app) as templates:
            response = client.get(path)

        assert response.status_code == 200
        assert templates
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert context["backend_api_url"] == app.config["BACKEND_API_URL"]

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
            "/manage/forum",
            "/manage/diagnosis",
            "/manage/play-service-control",
            "/manage/inspector-workbench",
            "/users/1/profile",
        ],
    )
    def test_all_management_routes_provide_frontend_config(self, app, client, path):
        """All management routes should provide frontend_config with all required keys."""
        with captured_templates(app) as templates:
            response = client.get(path)

        assert response.status_code == 200
        assert templates
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
            "/manage",
            "/manage/login",
            "/manage/news",
            "/manage/users",
            "/manage/roles",
            "/users/1/profile",
        ],
    )
    def test_all_management_routes_provide_language_metadata(self, app, client, path):
        """All management routes should provide language-related context."""
        with captured_templates(app) as templates:
            response = client.get(path)

        assert response.status_code == 200
        assert templates
        _, context = templates[-1]
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context
        assert isinstance(context["t"], dict)


class TestManagementRoutesSecurityHeaders:
    """Test that management routes include proper security headers."""

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        [
            "/manage",
            "/manage/login",
            "/manage/news",
            "/manage/users",
            "/manage/roles",
        ],
    )
    def test_management_routes_have_security_headers(self, client, path):
        """Management routes should include X-Content-Type-Options, X-Frame-Options, etc."""
        response = client.get(path)

        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "Referrer-Policy" in response.headers
        assert "Content-Security-Policy" in response.headers

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        [
            "/manage",
            "/manage/login",
            "/manage/news",
        ],
    )
    def test_management_routes_have_csp_header(self, client, path):
        """Management routes should include Content-Security-Policy header."""
        response = client.get(path)

        assert response.status_code == 200
        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src" in csp
        assert "script-src" in csp
        assert "style-src" in csp


class TestManagementRoutesGracefulDegradation:
    """Test that management routes render gracefully even without backend data."""

    @pytest.mark.integration
    def test_manage_routes_render_without_backend_errors(self, client):
        """Management routes should render templates even if backend is unavailable."""
        # Routes should render templates without making errors, leaving data loading to JS
        for path in ["/manage", "/manage/news", "/manage/users", "/manage/roles"]:
            response = client.get(path)
            assert response.status_code == 200
            assert response.content_type == "text/html; charset=utf-8"

    @pytest.mark.integration
    def test_user_profile_renders_without_backend_errors(self, client):
        """User profile route should render template without backend errors."""
        response = client.get("/users/42/profile")
        assert response.status_code == 200
        assert response.content_type == "text/html; charset=utf-8"


class TestManagementRoutesProxyAccess:
    """Test that management templates can access API proxy configuration."""

    @pytest.mark.contract
    def test_manage_routes_have_proxy_config(self, app, client):
        """Management routes should provide /_proxy in apiProxyBase."""
        with captured_templates(app) as templates:
            response = client.get("/manage")

        _, context = templates[-1]
        assert context["frontend_config"]["apiProxyBase"] == "/_proxy"

    @pytest.mark.contract
    def test_manage_routes_have_correct_backend_url(self, app, client):
        """Management routes should provide correct backend API URL."""
        with captured_templates(app) as templates:
            response = client.get("/manage/login")

        _, context = templates[-1]
        assert context["frontend_config"]["backendApiUrl"] == app.config["BACKEND_API_URL"]


class TestManagementGameContentRoute:
    @pytest.mark.unit
    def test_manage_game_content_returns_200(self, client):
        response = client.get("/manage/game-content")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_manage_game_content_renders_correct_template(self, app, client):
        with captured_templates(app) as templates:
            response = client.get("/manage/game-content")
        assert response.status_code == 200
        assert templates[-1][0] == "manage/game_content.html"


class TestManagementGameOperationsRoute:
    @pytest.mark.unit
    def test_manage_game_operations_returns_200(self, client):
        response = client.get("/manage/game-operations")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_manage_game_operations_renders_correct_template(self, app, client):
        with captured_templates(app) as templates:
            response = client.get("/manage/game-operations")
        assert response.status_code == 200
        assert templates[-1][0] == "manage/game_operations.html"
