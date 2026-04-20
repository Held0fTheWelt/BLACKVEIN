"""
WAVE 4: Comprehensive tests for forum routes rendering and context validation.

Tests cover:
- Forum route rendering with correct templates
- Template context (backend_api_url, frontend_config, language metadata)
- Slug parameters passed correctly to templates (category_slug, thread_slug, tag_slug)
- Forum notification and saved threads routes
- Graceful behavior with different slug values
- Template rendering without exceptions
"""
from __future__ import annotations

import pytest

from conftest import captured_templates


class TestForumIndexRoute:
    """Test GET /forum route (forum categories list)."""

    @pytest.mark.unit
    def test_forum_index_returns_200(self, client):
        """GET /forum should return 200 OK."""
        response = client.get("/forum")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_forum_index_renders_correct_template(self, app, client):
        """GET /forum should render forum/index.html template."""
        with captured_templates(app) as templates:
            response = client.get("/forum")

        assert response.status_code == 200
        assert templates, "No template rendered for /forum"
        assert templates[-1][0] == "forum/index.html"

    @pytest.mark.contract
    def test_forum_index_provides_required_context(self, app, client):
        """GET /forum should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/forum")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestForumCategoryRoute:
    """Test GET /forum/categories/<slug> route."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "slug",
        [
            "general",
            "off-topic",
            "announcements",
            "rules",
            "lore-discussion",
        ],
    )
    def test_forum_category_returns_200(self, client, slug):
        """GET /forum/categories/<slug> should return 200 OK for any slug."""
        response = client.get(f"/forum/categories/{slug}")
        assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "slug",
        [
            "general",
            "announcements",
            "lore-discussion",
        ],
    )
    def test_forum_category_renders_correct_template(self, app, client, slug):
        """GET /forum/categories/<slug> should render forum/category.html template."""
        with captured_templates(app) as templates:
            response = client.get(f"/forum/categories/{slug}")

        assert response.status_code == 200
        assert templates, f"No template rendered for /forum/categories/{slug}"
        assert templates[-1][0] == "forum/category.html"

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "slug",
        [
            "general",
            "announcements",
            "lore-discussion",
        ],
    )
    def test_forum_category_provides_slug_context(self, app, client, slug):
        """GET /forum/categories/<slug> should pass category_slug to template context."""
        with captured_templates(app) as templates:
            response = client.get(f"/forum/categories/{slug}")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "category_slug" in context
        assert context["category_slug"] == slug

    @pytest.mark.contract
    @pytest.mark.parametrize("slug", ["general", "announcements"])
    def test_forum_category_provides_required_context(self, app, client, slug):
        """GET /forum/categories/<slug> should provide standard context keys."""
        with captured_templates(app) as templates:
            response = client.get(f"/forum/categories/{slug}")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestForumThreadRoute:
    """Test GET /forum/threads/<slug> route."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "slug",
        [
            "welcome",
            "rules-and-guidelines",
            "introduce-yourself",
            "game-updates",
            "bug-reports",
        ],
    )
    def test_forum_thread_returns_200(self, client, slug):
        """GET /forum/threads/<slug> should return 200 OK for any slug."""
        response = client.get(f"/forum/threads/{slug}")
        assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "slug",
        [
            "welcome",
            "introduce-yourself",
            "game-updates",
        ],
    )
    def test_forum_thread_renders_correct_template(self, app, client, slug):
        """GET /forum/threads/<slug> should render forum/thread.html template."""
        with captured_templates(app) as templates:
            response = client.get(f"/forum/threads/{slug}")

        assert response.status_code == 200
        assert templates, f"No template rendered for /forum/threads/{slug}"
        assert templates[-1][0] == "forum/thread.html"

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "slug",
        [
            "welcome",
            "introduce-yourself",
            "game-updates",
        ],
    )
    def test_forum_thread_provides_slug_context(self, app, client, slug):
        """GET /forum/threads/<slug> should pass thread_slug to template context."""
        with captured_templates(app) as templates:
            response = client.get(f"/forum/threads/{slug}")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "thread_slug" in context
        assert context["thread_slug"] == slug

    @pytest.mark.contract
    @pytest.mark.parametrize("slug", ["welcome", "game-updates"])
    def test_forum_thread_provides_required_context(self, app, client, slug):
        """GET /forum/threads/<slug> should provide standard context keys."""
        with captured_templates(app) as templates:
            response = client.get(f"/forum/threads/{slug}")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestForumNotificationsRoute:
    """Test GET /forum/notifications route (requires login)."""

    @pytest.mark.unit
    def test_forum_notifications_returns_200(self, client):
        """GET /forum/notifications should return 200 OK."""
        response = client.get("/forum/notifications")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_forum_notifications_renders_correct_template(self, app, client):
        """GET /forum/notifications should render forum/notifications.html template."""
        with captured_templates(app) as templates:
            response = client.get("/forum/notifications")

        assert response.status_code == 200
        assert templates, "No template rendered for /forum/notifications"
        assert templates[-1][0] == "forum/notifications.html"

    @pytest.mark.contract
    def test_forum_notifications_provides_required_context(self, app, client):
        """GET /forum/notifications should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/forum/notifications")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestForumSavedThreadsRoute:
    """Test GET /forum/saved route (saved threads/bookmarks)."""

    @pytest.mark.unit
    def test_forum_saved_returns_200(self, client):
        """GET /forum/saved should return 200 OK."""
        response = client.get("/forum/saved")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_forum_saved_renders_correct_template(self, app, client):
        """GET /forum/saved should render forum/saved_threads.html template."""
        with captured_templates(app) as templates:
            response = client.get("/forum/saved")

        assert response.status_code == 200
        assert templates, "No template rendered for /forum/saved"
        assert templates[-1][0] == "forum/saved_threads.html"

    @pytest.mark.contract
    def test_forum_saved_provides_required_context(self, app, client):
        """GET /forum/saved should provide backend_api_url, frontend_config, and language context."""
        with captured_templates(app) as templates:
            response = client.get("/forum/saved")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestForumTagRoute:
    """Test GET /forum/tags/<slug> route."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "slug",
        [
            "lore",
            "mechanics",
            "gameplay",
            "story",
            "worldbuilding",
        ],
    )
    def test_forum_tag_returns_200(self, client, slug):
        """GET /forum/tags/<slug> should return 200 OK for any slug."""
        response = client.get(f"/forum/tags/{slug}")
        assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "slug",
        [
            "lore",
            "gameplay",
            "story",
        ],
    )
    def test_forum_tag_renders_correct_template(self, app, client, slug):
        """GET /forum/tags/<slug> should render forum/tag_detail.html template."""
        with captured_templates(app) as templates:
            response = client.get(f"/forum/tags/{slug}")

        assert response.status_code == 200
        assert templates, f"No template rendered for /forum/tags/{slug}"
        assert templates[-1][0] == "forum/tag_detail.html"

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "slug",
        [
            "lore",
            "gameplay",
            "story",
        ],
    )
    def test_forum_tag_provides_slug_context(self, app, client, slug):
        """GET /forum/tags/<slug> should pass tag_slug to template context."""
        with captured_templates(app) as templates:
            response = client.get(f"/forum/tags/{slug}")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "tag_slug" in context
        assert context["tag_slug"] == slug

    @pytest.mark.contract
    @pytest.mark.parametrize("slug", ["lore", "gameplay"])
    def test_forum_tag_provides_required_context(self, app, client, slug):
        """GET /forum/tags/<slug> should provide standard context keys."""
        with captured_templates(app) as templates:
            response = client.get(f"/forum/tags/{slug}")

        assert response.status_code == 200
        _, context = templates[-1]
        assert "backend_api_url" in context
        assert "frontend_config" in context
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context


class TestForumRoutesLanguageVariants:
    """Test forum routes with language parameters."""

    @pytest.mark.integration
    @pytest.mark.parametrize("lang", ["de", "en"])
    def test_forum_routes_respond_to_lang_parameter(self, client, lang):
        """Forum routes should respond to ?lang parameter."""
        for path in ["/forum", "/forum/categories/general", "/forum/threads/welcome", "/forum/tags/lore"]:
            response = client.get(f"{path}?lang={lang}")
            assert response.status_code == 200

    @pytest.mark.integration
    def test_forum_category_with_lang_parameter(self, app, client):
        """GET /forum/categories/<slug>?lang=en should work and respect language."""
        with captured_templates(app) as templates:
            response = client.get("/forum/categories/general?lang=en")

        assert response.status_code == 200
        _, context = templates[-1]
        assert context["current_lang"] == "en"
        assert context["category_slug"] == "general"

    @pytest.mark.integration
    def test_forum_thread_with_lang_parameter(self, app, client):
        """GET /forum/threads/<slug>?lang=de should work and respect language."""
        with captured_templates(app) as templates:
            response = client.get("/forum/threads/welcome?lang=de")

        assert response.status_code == 200
        _, context = templates[-1]
        assert context["current_lang"] == "de"
        assert context["thread_slug"] == "welcome"

    @pytest.mark.integration
    def test_forum_tag_with_lang_parameter(self, app, client):
        """GET /forum/tags/<slug>?lang=en should work and respect language."""
        with captured_templates(app) as templates:
            response = client.get("/forum/tags/lore?lang=en")

        assert response.status_code == 200
        _, context = templates[-1]
        assert context["current_lang"] == "en"
        assert context["tag_slug"] == "lore"


class TestForumRoutesContextConsistency:
    """Test context consistency across all forum routes."""

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "path",
        [
            "/forum",
            "/forum/categories/general",
            "/forum/threads/welcome",
            "/forum/notifications",
            "/forum/saved",
            "/forum/tags/lore",
        ],
    )
    def test_all_forum_routes_provide_backend_api_url(self, app, client, path):
        """All forum routes should provide backend_api_url."""
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
            "/forum",
            "/forum/categories/general",
            "/forum/threads/welcome",
            "/forum/notifications",
            "/forum/saved",
            "/forum/tags/lore",
        ],
    )
    def test_all_forum_routes_provide_frontend_config(self, app, client, path):
        """All forum routes should provide frontend_config with all required keys."""
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
            "/forum",
            "/forum/categories/general",
            "/forum/threads/welcome",
            "/forum/tags/lore",
        ],
    )
    def test_all_forum_routes_provide_language_metadata(self, app, client, path):
        """All forum routes should provide language-related context."""
        with captured_templates(app) as templates:
            response = client.get(path)

        assert response.status_code == 200
        assert templates
        _, context = templates[-1]
        assert "current_lang" in context
        assert "supported_languages" in context
        assert "t" in context
        assert isinstance(context["t"], dict)


class TestForumRoutesSlugVariants:
    """Test forum routes with various slug formats."""

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "category",
        [
            "general",
            "off-topic",
            "announcements-and-updates",
        ],
    )
    def test_forum_category_with_varied_slugs(self, app, client, category):
        """Forum category route should handle varied slug formats."""
        with captured_templates(app) as templates:
            response = client.get(f"/forum/categories/{category}")

        assert response.status_code == 200
        assert templates
        _, context = templates[-1]
        assert context["category_slug"] == category

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "tag",
        [
            "lore",
            "lore-discussion",
            "mechanics-and-gameplay",
        ],
    )
    def test_forum_tag_with_varied_slugs(self, app, client, tag):
        """Forum tag route should handle varied slug formats."""
        with captured_templates(app) as templates:
            response = client.get(f"/forum/tags/{tag}")

        assert response.status_code == 200
        assert templates
        _, context = templates[-1]
        assert context["tag_slug"] == tag
