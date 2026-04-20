"""Tests for template context processor injection.

Validates that:
- inject_config() makes backend_api_url available in templates
- frontend_config is available in templates
- language metadata (current_lang, supported_languages) is available in templates
- Context processor runs without errors during render
"""
from __future__ import annotations

import pytest
from conftest import captured_templates


class TestContextProcessorInjection:
    """Test that inject_config context processor injects required variables."""

    @pytest.mark.unit
    def test_inject_config_returns_dict(self, app_factory):
        """Test that inject_config returns a dictionary."""
        from app import inject_config
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/"):
            context = inject_config()
            assert isinstance(context, dict)

    @pytest.mark.unit
    def test_inject_config_includes_backend_api_url(self, app_factory):
        """Test that inject_config includes backend_api_url."""
        from app import inject_config
        backend_url = "https://api.test.example.com"
        app = app_factory(test_config={
            "BACKEND_API_URL": backend_url,
            "TESTING": True,
        })

        with app.test_request_context("/"):
            context = inject_config()
            assert "backend_api_url" in context
            assert context["backend_api_url"] == backend_url

    @pytest.mark.unit
    def test_inject_config_includes_frontend_config_dict(self, app_factory):
        """Test that inject_config includes frontend_config."""
        from app import inject_config
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/"):
            context = inject_config()
            assert "frontend_config" in context
            assert isinstance(context["frontend_config"], dict)

    @pytest.mark.unit
    def test_frontend_config_has_backend_api_url(self, app_factory):
        """Test that frontend_config includes backendApiUrl."""
        from app import inject_config
        backend_url = "https://backend.example.com"
        app = app_factory(test_config={
            "BACKEND_API_URL": backend_url,
            "TESTING": True,
        })

        with app.test_request_context("/"):
            context = inject_config()
            assert context["frontend_config"]["backendApiUrl"] == backend_url

    @pytest.mark.unit
    def test_frontend_config_has_api_proxy_base(self, app_factory):
        """Test that frontend_config includes apiProxyBase."""
        from app import inject_config
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/"):
            context = inject_config()
            assert "apiProxyBase" in context["frontend_config"]
            assert context["frontend_config"]["apiProxyBase"] == "/_proxy"

    @pytest.mark.unit
    def test_frontend_config_has_supported_languages(self, app_factory):
        """Test that frontend_config includes supportedLanguages."""
        from app import inject_config
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/"):
            context = inject_config()
            assert "supportedLanguages" in context["frontend_config"]
            assert isinstance(context["frontend_config"]["supportedLanguages"], list)

    @pytest.mark.unit
    def test_frontend_config_has_default_language(self, app_factory):
        """Test that frontend_config includes defaultLanguage."""
        from app import inject_config
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/"):
            context = inject_config()
            assert "defaultLanguage" in context["frontend_config"]
            assert isinstance(context["frontend_config"]["defaultLanguage"], str)

    @pytest.mark.unit
    def test_frontend_config_has_current_language(self, app_factory):
        """Test that frontend_config includes currentLanguage."""
        from app import inject_config
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/?lang=en"):
            context = inject_config()
            assert "currentLanguage" in context["frontend_config"]
            assert context["frontend_config"]["currentLanguage"] == "en"


class TestLanguageMetadataInContext:
    """Test that language metadata is available in context."""

    @pytest.mark.unit
    def test_context_includes_current_lang(self, app_factory):
        """Test that current_lang is available in context."""
        from app import inject_config
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/?lang=de"):
            context = inject_config()
            assert "current_lang" in context
            assert context["current_lang"] == "de"

    @pytest.mark.unit
    def test_context_includes_supported_languages(self, app_factory):
        """Test that supported_languages is available in context."""
        from app import inject_config
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/"):
            context = inject_config()
            assert "supported_languages" in context
            assert isinstance(context["supported_languages"], list)

    @pytest.mark.unit
    def test_supported_languages_contains_de_and_en(self, app_factory):
        """Test that supported_languages contains at least de and en."""
        from app import inject_config
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/"):
            context = inject_config()
            langs = context["supported_languages"]
            assert "de" in langs
            assert "en" in langs

    @pytest.mark.unit
    def test_current_lang_defaults_to_default_language(self, app_factory):
        """Test that current_lang defaults to DEFAULT_LANGUAGE when no preference."""
        from app import inject_config, DEFAULT_LANGUAGE
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/"):
            context = inject_config()
            assert context["current_lang"] == DEFAULT_LANGUAGE


class TestTranslationsInContext:
    """Test that translations are available in context."""

    @pytest.mark.unit
    def test_context_includes_translations_dict(self, app_factory):
        """Test that translations dict (t) is available in context."""
        from app import inject_config
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/"):
            context = inject_config()
            assert "t" in context
            assert isinstance(context["t"], dict)

    @pytest.mark.unit
    def test_translations_dict_is_dict_for_valid_language(self, app_factory):
        """Test that translations dict is a dict (even if empty)."""
        from app import inject_config
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/?lang=de"):
            context = inject_config()
            t = context["t"]
            assert isinstance(t, dict)

    @pytest.mark.unit
    def test_translations_available_for_each_language(self, app_factory):
        """Test that translations can be loaded for each supported language."""
        from app import inject_config, SUPPORTED_LANGUAGES
        app = app_factory(test_config={"TESTING": True})

        for lang in SUPPORTED_LANGUAGES:
            with app.test_request_context(f"/?lang={lang}"):
                context = inject_config()
                assert context["current_lang"] == lang
                assert "t" in context


class TestContextProcessorIntegration:
    """Integration tests for context processor with template rendering."""

    @pytest.mark.integration
    def test_context_available_during_template_render(self, app, client):
        """Test that context processor data is available during template render."""
        with captured_templates(app) as templates:
            response = client.get("/")

        assert response.status_code == 200
        assert len(templates) > 0
        # Check that at least one template was rendered
        _, context = templates[-1]
        assert "backend_api_url" in context or "frontend_config" in context

    @pytest.mark.integration
    def test_frontend_config_available_in_all_routes(self, app, client):
        """Test that frontend_config is available in all routes."""
        routes = ["/", "/news", "/forum", "/manage"]
        for route in routes:
            with captured_templates(app) as templates:
                response = client.get(route)

            assert response.status_code == 200
            assert len(templates) > 0
            _, context = templates[-1]
            # At least frontend_config or current_lang should be present
            assert ("frontend_config" in context or "current_lang" in context
                   ), f"Context missing in {route}"

    @pytest.mark.integration
    def test_current_lang_changes_with_query_parameter(self, app, client):
        """Test that current_lang changes based on lang query parameter."""
        with captured_templates(app) as templates_de:
            response_de = client.get("/?lang=de")
        assert response_de.status_code == 200

        with captured_templates(app) as templates_en:
            response_en = client.get("/?lang=en")
        assert response_en.status_code == 200

        # Both should render successfully with different languages
        _, context_de = templates_de[-1]
        _, context_en = templates_en[-1]

        # The language in frontend_config should differ
        if "frontend_config" in context_de and "frontend_config" in context_en:
            assert (context_de["frontend_config"]["currentLanguage"] == "de" or
                   context_de["current_lang"] == "de")
            assert (context_en["frontend_config"]["currentLanguage"] == "en" or
                   context_en["current_lang"] == "en")

    @pytest.mark.integration
    def test_backend_api_url_consistent_across_requests(self, app, client):
        """Test that backend_api_url is consistent across multiple requests."""
        with captured_templates(app) as templates1:
            client.get("/")
        _, context1 = templates1[-1]
        backend_url1 = context1.get("backend_api_url")

        with captured_templates(app) as templates2:
            client.get("/news")
        _, context2 = templates2[-1]
        backend_url2 = context2.get("backend_api_url")

        if backend_url1 and backend_url2:
            assert backend_url1 == backend_url2

    @pytest.mark.integration
    def test_context_processor_does_not_raise_errors(self, app, client):
        """Test that context processor executes without raising errors."""
        # Make requests to various routes and verify no errors
        routes = ["/", "/news", "/wiki", "/forum", "/manage"]
        for route in routes:
            response = client.get(route)
            assert response.status_code == 200


class TestContextProcessorEdgeCases:
    """Test edge cases for context processor."""

    @pytest.mark.unit
    def test_inject_config_with_invalid_language_query(self, app_factory):
        """Test that inject_config handles invalid language gracefully."""
        from app import inject_config, DEFAULT_LANGUAGE
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/?lang=invalid"):
            context = inject_config()
            # Should fall back to default
            assert context["current_lang"] == DEFAULT_LANGUAGE

    @pytest.mark.unit
    def test_inject_config_with_empty_language_query(self, app_factory):
        """Test that inject_config handles empty lang parameter."""
        from app import inject_config
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/?lang="):
            context = inject_config()
            # Should fall back to default
            assert "current_lang" in context

    @pytest.mark.unit
    def test_inject_config_with_whitespace_language(self, app_factory):
        """Test that inject_config handles whitespace language."""
        from app import inject_config
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/?lang=   "):
            context = inject_config()
            # Should fall back to default
            assert "current_lang" in context

    @pytest.mark.unit
    def test_context_backend_url_matches_app_config(self, app_factory):
        """Test that context backend_api_url matches app.config BACKEND_API_URL."""
        from app import inject_config
        backend_url = "https://custom-backend.test"
        app = app_factory(test_config={
            "BACKEND_API_URL": backend_url,
            "TESTING": True,
        })

        with app.test_request_context("/"):
            context = inject_config()
            assert context["backend_api_url"] == app.config["BACKEND_API_URL"]
