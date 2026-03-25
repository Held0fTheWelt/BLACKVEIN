"""
WAVE 4: Comprehensive tests for public routes rendering and context validation.

Tests cover:
- Route rendering with correct templates
- Template context (backend_api_url, frontend_config, language metadata)
- Route parameters passed correctly to templates (news_id, slug)
- Graceful behavior with different parameter values
- Template rendering without exceptions
"""
from __future__ import annotations

import pytest

from conftest import captured_templates


class TestPublicIndexRoute:
    """Test GET / route (public home page)."""

    @pytest.mark.unit
    def test_index_route_returns_200(self, client):
        """GET / should return 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_index_route_renders_correct_template(self, app, client):
        """GET / should render index.html template."""
        with captured_templates(app) as templates:
            response = client.get("/")

        assert response.status_code == 200
        assert templates, "No template rendered for /"
        assert templates[-1][0] == "index.html"

    @pytest.mark.contract
    def test_index_route_provides_required_context(self, app, client):
        """GET / should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestPublicNewsRoutes:
    """Test /news and /news/<int:news_id> routes."""

    @pytest.mark.unit
    def test_news_list_route_returns_200(self, client):
        """GET /news should return 200 OK."""
        response = client.get("/news")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_news_list_route_renders_correct_template(self, app, client):
        """GET /news should render news.html template."""
        with captured_templates(app) as templates:
            response = client.get("/news")

        assert response.status_code == 200
        assert templates, "No template rendered for /news"
        assert templates[-1][0] == "news.html"

    @pytest.mark.contract
    def test_news_list_route_provides_required_context(self, app, client):
        """GET /news should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/news")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context

    @pytest.mark.unit
    @pytest.mark.parametrize("news_id", [1, 42, 999, 12345])
    def test_news_detail_route_returns_200(self, client, news_id):
        """GET /news/<int:news_id> should return 200 OK for valid integer IDs."""
        response = client.get(f"/news/{news_id}")
        assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.parametrize("news_id", [1, 42, 999])
    def test_news_detail_route_renders_correct_template(self, app, client, news_id):
        """GET /news/<int:news_id> should render news_detail.html template."""
        with captured_templates(app) as templates:
            response = client.get(f"/news/{news_id}")

        assert response.status_code == 200
        assert templates, f"No template rendered for /news/{news_id}"
        assert templates[-1][0] == "news_detail.html"

    @pytest.mark.contract
    @pytest.mark.parametrize("news_id", [1, 42, 999])
    def test_news_detail_route_provides_news_id_context(self, app, client, news_id):
        """GET /news/<int:news_id> should pass news_id to template context."""
        with captured_templates(app) as templates:
            response = client.get(f"/news/{news_id}")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "news_id" in context
        assert context["news_id"] == news_id

    @pytest.mark.contract
    @pytest.mark.parametrize("news_id", [1, 42, 999])
    def test_news_detail_route_provides_required_context(self, app, client, news_id):
        """GET /news/<int:news_id> should provide standard context keys."""
        with captured_templates(app) as templates:
            response = client.get(f"/news/{news_id}")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context

    @pytest.mark.unit
    @pytest.mark.parametrize("invalid_id", ["abc", "invalid", "12.34"])
    def test_news_detail_route_rejects_invalid_ids(self, client, invalid_id):
        """GET /news/<invalid> should return 404 for non-integer IDs."""
        response = client.get(f"/news/{invalid_id}")
        assert response.status_code == 404


class TestPublicWikiRoutes:
    """Test /wiki and /wiki/<slug> routes."""

    @pytest.mark.unit
    def test_wiki_index_returns_200(self, client):
        """GET /wiki should return 200 OK."""
        response = client.get("/wiki")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_wiki_index_renders_correct_template(self, app, client):
        """GET /wiki should render wiki_public.html template."""
        with captured_templates(app) as templates:
            response = client.get("/wiki")

        assert response.status_code == 200
        assert templates, "No template rendered for /wiki"
        assert templates[-1][0] == "wiki_public.html"

    @pytest.mark.contract
    def test_wiki_index_provides_default_slug_context(self, app, client):
        """GET /wiki should provide slug='wiki' as default in context."""
        with captured_templates(app) as templates:
            response = client.get("/wiki")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "slug" in context
        assert context["slug"] == "wiki"

    @pytest.mark.contract
    def test_wiki_index_provides_required_context(self, app, client):
        """GET /wiki should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/wiki")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "slug",
        [
            "lore",
            "lore/city",
            "lore/city/history",
            "factions",
            "mechanics",
            "rules/combat",
        ],
    )
    def test_wiki_slug_returns_200(self, client, slug):
        """GET /wiki/<slug> should return 200 OK for any slug."""
        response = client.get(f"/wiki/{slug}")
        assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "slug",
        [
            "lore",
            "lore/city",
            "lore/city/history",
            "factions",
        ],
    )
    def test_wiki_slug_renders_correct_template(self, app, client, slug):
        """GET /wiki/<slug> should render wiki_public.html template."""
        with captured_templates(app) as templates:
            response = client.get(f"/wiki/{slug}")

        assert response.status_code == 200
        assert templates, f"No template rendered for /wiki/{slug}"
        assert templates[-1][0] == "wiki_public.html"

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "slug",
        [
            "lore",
            "lore/city",
            "lore/city/history",
            "factions",
        ],
    )
    def test_wiki_slug_provides_slug_context(self, app, client, slug):
        """GET /wiki/<slug> should pass custom slug to template context."""
        with captured_templates(app) as templates:
            response = client.get(f"/wiki/{slug}")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "slug" in context
        assert context["slug"] == slug

    @pytest.mark.contract
    @pytest.mark.parametrize("slug", ["lore", "lore/city", "factions"])
    def test_wiki_slug_provides_required_context(self, app, client, slug):
        """GET /wiki/<slug> should provide standard context keys."""
        with captured_templates(app) as templates:
            response = client.get(f"/wiki/{slug}")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestPublicRoutesLanguageVariants:
    """Test public routes with language parameters."""

    @pytest.mark.integration
    @pytest.mark.parametrize("lang", ["de", "en"])
    def test_routes_respond_to_lang_parameter(self, client, lang):
        """Public routes should respond to ?lang parameter."""
        for path in ["/", "/news", "/wiki", "/forum"]:
            response = client.get(f"{path}?lang={lang}")
            assert response.status_code == 200

    @pytest.mark.integration
    def test_news_detail_with_lang_parameter(self, app, client):
        """GET /news/<id>?lang=en should work and respect language."""
        with captured_templates(app) as templates:
            response = client.get("/news/42?lang=en")

        assert response.status_code == 200
        _, context = templates[-1]
        assert context["current_lang"] == "en"
        assert context["news_id"] == 42

    @pytest.mark.integration
    def test_wiki_slug_with_lang_parameter(self, app, client):
        """GET /wiki/<slug>?lang=de should work and respect language."""
        with captured_templates(app) as templates:
            response = client.get("/wiki/lore/city?lang=de")

        assert response.status_code == 200
        _, context = templates[-1]
        assert context["current_lang"] == "de"
        assert context["slug"] == "lore/city"


class TestPublicRoutesContextConsistency:
    """Test context consistency across all public routes."""

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
        ],
    )
    def test_all_public_routes_provide_backend_api_url(self, app, client, path):
        """All public routes should provide backend_api_url."""
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
            "/",
            "/news",
            "/news/1",
            "/wiki",
            "/wiki/lore",
            "/forum",
        ],
    )
    def test_all_public_routes_provide_frontend_config(self, app, client, path):
        """All public routes should provide frontend_config with all required keys."""
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
            "/",
            "/news",
            "/news/1",
            "/wiki",
            "/wiki/lore",
        ],
    )
    def test_all_public_routes_provide_language_metadata(self, app, client, path):
        """All public routes should provide language-related context."""
        with captured_templates(app) as templates:
            response = client.get(path)

        assert response.status_code == 200
        assert templates
        _, context = templates[-1]
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context
        assert isinstance(context["t"], dict)


class TestPublicRoutesProxyConfig:
    """Test that API proxy configuration is correctly passed."""

    @pytest.mark.contract
    def test_api_proxy_base_is_correct(self, app, client):
        """frontend_config.apiProxyBase should be /_proxy."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        assert context["frontend_config"]["apiProxyBase"] == "/_proxy"

    @pytest.mark.contract
    def test_supported_languages_includes_de_and_en(self, app, client):
        """supported_languages in context should include both 'de' and 'en'."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        assert "de" in context["supported_languages"]
        assert "en" in context["supported_languages"]
