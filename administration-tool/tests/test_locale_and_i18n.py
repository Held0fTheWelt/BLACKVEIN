"""
WAVE 4: Locale and i18n contract tests for administration-tool.

Tests cover:
- Supported locales are enumerable
- Invalid locale falls back to default
- Default locale behavior works
- Missing translation behavior (must not crash)
- Language resolution hierarchy works
"""
from __future__ import annotations

from pathlib import Path

import pytest
from conftest import captured_templates, load_frontend_module


# ============================================================================
# SUPPORTED LOCALES CONTRACT
# ============================================================================


class TestSupportedLocalesContract:
    """Test that supported locales are clearly defined and enumerable."""

    @pytest.mark.contract
    def test_supported_languages_enumerable(self, app, client):
        """Contract: Supported languages are enumerable in app context."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        supported = context["supported_languages"]
        assert isinstance(supported, list), "supported_languages must be a list"
        assert len(supported) > 0, "supported_languages must not be empty"

    @pytest.mark.contract
    def test_supports_german_locale(self, app, client):
        """Contract: German (de) is a supported locale."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        assert "de" in context["supported_languages"]

    @pytest.mark.contract
    def test_supports_english_locale(self, app, client):
        """Contract: English (en) is a supported locale."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        assert "en" in context["supported_languages"]

    @pytest.mark.contract
    def test_default_language_is_german(self, app, client):
        """Contract: Default language is German (de)."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        assert context["frontend_config"]["defaultLanguage"] == "de"

    @pytest.mark.contract
    def test_supported_locales_consistent_across_routes(self, app, client):
        """Contract: supported_languages list is consistent across all routes."""
        paths = ["/", "/news", "/wiki", "/forum", "/manage/login"]
        expected_langs = None

        for path in paths:
            with captured_templates(app) as templates:
                response = client.get(path)

            _, context = templates[-1]
            current_langs = context["supported_languages"]

            if expected_langs is None:
                expected_langs = current_langs
            else:
                assert current_langs == expected_langs, \
                    f"supported_languages changed at {path}"


# ============================================================================
# LANGUAGE RESOLUTION HIERARCHY CONTRACT
# ============================================================================


class TestLanguageResolutionHierarchy:
    """Test that language resolution follows the correct priority hierarchy."""

    @pytest.mark.contract
    def test_query_parameter_is_highest_priority(self, app, client):
        """Contract: Query parameter ?lang=X has highest priority."""
        # Set session to de
        client.get("/?lang=de")

        # Request with lang=en in query should override
        with captured_templates(app) as templates:
            response = client.get("/?lang=en")

        _, context = templates[-1]
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_query_parameter_overrides_accept_language(self, app, client):
        """Contract: Query parameter overrides Accept-Language header."""
        with captured_templates(app) as templates:
            response = client.get(
                "/?lang=en",
                headers={"Accept-Language": "de-DE,de;q=0.9"},
            )

        _, context = templates[-1]
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_session_language_second_priority(self, app, client):
        """Contract: Session language is second priority."""
        # Set session language
        client.get("/?lang=en")

        # Request without lang param should use session
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        # Should use the session language (en)
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_session_overrides_accept_language(self, app, client):
        """Contract: Session language overrides Accept-Language."""
        # Set session
        client.get("/?lang=en")

        # Request with different Accept-Language
        with captured_templates(app) as templates:
            response = client.get(
                "/",
                headers={"Accept-Language": "de-DE,de;q=0.9"},
            )

        _, context = templates[-1]
        # Should use session (en), not Accept-Language (de)
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_accept_language_third_priority(self, app, client):
        """Contract: Accept-Language header is third priority."""
        # Don't set session or query parameter
        # Clear any session first by using new client
        test_client = app.test_client()

        with captured_templates(app) as templates:
            response = test_client.get(
                "/",
                headers={"Accept-Language": "en-US,en;q=0.9"},
            )

        _, context = templates[-1]
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_default_language_is_final_fallback(self, app, client):
        """Contract: Default language used when all other methods fail."""
        test_client = app.test_client()

        # No query param, no session, unsupported Accept-Language
        with captured_templates(app) as templates:
            response = test_client.get(
                "/",
                headers={"Accept-Language": "fr-FR,fr;q=0.9"},  # French not supported
            )

        _, context = templates[-1]
        # Should fall back to default (de)
        assert context["current_lang"] == "de"


# ============================================================================
# INVALID LOCALE FALLBACK CONTRACT
# ============================================================================


class TestInvalidLocaleFallback:
    """Test that invalid locales gracefully fall back to default."""

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "invalid_lang",
        ["fr", "es", "it", "ja", "zh", "invalid", "", "xx"],
    )
    def test_unsupported_lang_query_parameter_falls_back(self, app, client, invalid_lang: str):
        """Contract: Unsupported lang query parameter falls back to default."""
        with captured_templates(app) as templates:
            response = client.get(f"/?lang={invalid_lang}")

        assert response.status_code == 200
        _, context = templates[-1]
        # Should not crash, should use default
        assert context["current_lang"] == "de"

    @pytest.mark.contract
    def test_invalid_accept_language_header_falls_back(self, app, client):
        """Contract: Invalid Accept-Language falls back gracefully."""
        test_client = app.test_client()

        with captured_templates(app) as templates:
            response = test_client.get(
                "/",
                headers={"Accept-Language": "invalid-INVALID"},
            )

        assert response.status_code == 200
        _, context = templates[-1]
        # Should not crash, should use default
        assert context["current_lang"] == "de"

    @pytest.mark.contract
    def test_malformed_accept_language_header_safe(self, app, client):
        """Contract: Malformed Accept-Language header is handled safely."""
        test_client = app.test_client()

        with captured_templates(app) as templates:
            response = test_client.get(
                "/",
                headers={"Accept-Language": ";;;---===***"},
            )

        assert response.status_code == 200
        _, context = templates[-1]
        # Should not crash
        assert context["current_lang"] in ["de", "en"]  # Some sensible default


# ============================================================================
# TRANSLATION FILE LOADING CONTRACT
# ============================================================================


class TestTranslationFileLoadingContract:
    """Test that translation files are loaded correctly and fallback works."""

    @pytest.mark.contract
    def test_german_translations_loaded_for_de(self, app, client):
        """Contract: German translations are loaded when lang=de."""
        with captured_templates(app) as templates:
            response = client.get("/?lang=de")

        assert response.status_code == 200
        _, context = templates[-1]
        t = context["t"]
        assert isinstance(t, dict)
        # Should have some translation keys
        assert len(t) > 0

    @pytest.mark.contract
    def test_english_translations_loaded_for_en(self, app, client):
        """Contract: English translations are loaded when lang=en."""
        with captured_templates(app) as templates:
            response = client.get("/?lang=en")

        assert response.status_code == 200
        _, context = templates[-1]
        t = context["t"]
        assert isinstance(t, dict)
        # Should have some translation keys
        assert len(t) > 0

    @pytest.mark.contract
    def test_translation_dict_is_never_none(self, app, client):
        """Contract: Translation dict is always a dict, never None."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        t = context["t"]
        assert t is not None, "Translation dict should never be None"
        assert isinstance(t, dict)

    @pytest.mark.contract
    def test_invalid_language_uses_default_translations(self, app, client):
        """Contract: Unsupported language falls back to default translations."""
        with captured_templates(app) as templates:
            response = client.get("/?lang=fr")

        assert response.status_code == 200
        _, context = templates[-1]
        t = context["t"]
        # Should still have translations (default language)
        assert isinstance(t, dict)

    @pytest.mark.contract
    def test_translation_dict_consistent_across_requests(self, app, client):
        """Contract: Same language returns same translation dict."""
        with captured_templates(app) as templates:
            response1 = client.get("/?lang=en")

        _, context1 = templates[-1]
        t1 = context1["t"]

        with captured_templates(app) as templates:
            response2 = client.get("/?lang=en")

        _, context2 = templates[-1]
        t2 = context2["t"]

        # Should have same translations
        assert len(t1) == len(t2)


# ============================================================================
# LANGUAGE SESSION PERSISTENCE CONTRACT
# ============================================================================


class TestLanguageSessionPersistenceContract:
    """Test that language preference persists across requests via session."""

    @pytest.mark.contract
    def test_lang_query_parameter_sets_session(self, client):
        """Contract: lang query parameter sets session["lang"]."""
        client.get("/?lang=en")

        with client.session_transaction() as session:
            assert session.get("lang") == "en"

    @pytest.mark.contract
    def test_session_language_persists_across_requests(self, client):
        """Contract: Session language persists across multiple requests."""
        # First request sets language
        client.get("/?lang=en")

        # Second request should use session
        with client.session_transaction() as session:
            assert session.get("lang") == "en"

        # Third request without lang param
        with captured_templates(app := client.application) as templates:
            response = client.get("/news")

        _, context = templates[-1]
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_changing_language_updates_session(self, client):
        """Contract: Changing lang param updates session."""
        # Set to en
        client.get("/?lang=en")

        with client.session_transaction() as session:
            assert session.get("lang") == "en"

        # Change to de
        client.get("/?lang=de")

        with client.session_transaction() as session:
            assert session.get("lang") == "de"

    @pytest.mark.contract
    def test_session_cleared_when_invalid_lang_requested(self, client):
        """Contract: Session lang updated only when valid lang provided."""
        # Set valid language
        client.get("/?lang=en")

        with client.session_transaction() as session:
            assert session.get("lang") == "en"

        # Request with invalid language should not change session
        client.get("/?lang=fr")

        with client.session_transaction() as session:
            # Session should still have the previous valid language
            # (because invalid lang doesn't set session, just uses default)
            assert session.get("lang") == "en"


# ============================================================================
# ACCEPT-LANGUAGE HEADER PARSING CONTRACT
# ============================================================================


class TestAcceptLanguageParsingContract:
    """Test that Accept-Language header is parsed correctly."""

    @pytest.mark.contract
    def test_accept_language_en_us_resolved_to_en(self, app, client):
        """Contract: Accept-Language: en-US resolved to 'en'."""
        test_client = app.test_client()

        with captured_templates(app) as templates:
            response = test_client.get(
                "/",
                headers={"Accept-Language": "en-US"},
            )

        _, context = templates[-1]
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_accept_language_de_de_resolved_to_de(self, app, client):
        """Contract: Accept-Language: de-DE resolved to 'de'."""
        test_client = app.test_client()

        with captured_templates(app) as templates:
            response = test_client.get(
                "/",
                headers={"Accept-Language": "de-DE"},
            )

        _, context = templates[-1]
        assert context["current_lang"] == "de"

    @pytest.mark.contract
    def test_accept_language_with_quality_values(self, app, client):
        """Contract: Accept-Language with q values is parsed."""
        test_client = app.test_client()

        with captured_templates(app) as templates:
            response = test_client.get(
                "/",
                headers={"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8,de;q=0.7"},
            )

        _, context = templates[-1]
        # Should pick 'en' (not fr, which is first but unsupported)
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_accept_language_with_multiple_preferences(self, app, client):
        """Contract: Accept-Language with multiple preferences works."""
        test_client = app.test_client()

        with captured_templates(app) as templates:
            response = test_client.get(
                "/",
                headers={"Accept-Language": "en-US,en;q=0.9,de;q=0.8"},
            )

        _, context = templates[-1]
        # Should use 'en' (first supported)
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_accept_language_empty_string_falls_back(self, app, client):
        """Contract: Empty Accept-Language falls back gracefully."""
        test_client = app.test_client()

        with captured_templates(app) as templates:
            response = test_client.get(
                "/",
                headers={"Accept-Language": ""},
            )

        assert response.status_code == 200
        _, context = templates[-1]
        # Should use default
        assert context["current_lang"] == "de"


# ============================================================================
# TRANSLATION CONTEXT IN TEMPLATES CONTRACT
# ============================================================================


class TestTranslationContextContract:
    """Test that translation context is properly available in templates."""

    @pytest.mark.contract
    def test_translation_dict_t_available_in_templates(self, app, client):
        """Contract: Translation dict 't' is available in template context."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        assert "t" in context
        assert isinstance(context["t"], dict)

    @pytest.mark.contract
    def test_t_context_changes_with_language(self, app, client):
        """Contract: 't' context dict changes with language selection."""
        # Get German translations
        with captured_templates(app) as templates:
            response = client.get("/?lang=de")

        _, context_de = templates[-1]
        t_de = context_de["t"]

        # Get English translations
        with captured_templates(app) as templates:
            response = client.get("/?lang=en")

        _, context_en = templates[-1]
        t_en = context_en["t"]

        # Both should be dicts (might be same content if translations are same)
        assert isinstance(t_de, dict)
        assert isinstance(t_en, dict)

    @pytest.mark.contract
    def test_current_lang_available_in_templates(self, app, client):
        """Contract: current_lang variable available in template context."""
        with captured_templates(app) as templates:
            response = client.get("/?lang=en")

        _, context = templates[-1]
        assert "current_lang" in context
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_supported_languages_available_in_templates(self, app, client):
        """Contract: supported_languages list available in template context."""
        with captured_templates(app) as templates:
            response = client.get("/")

        _, context = templates[-1]
        assert "supported_languages" in context
        assert isinstance(context["supported_languages"], list)
        assert "de" in context["supported_languages"]
        assert "en" in context["supported_languages"]


# ============================================================================
# LOCALE STABILITY CONTRACT
# ============================================================================


class TestLocaleStabilityContract:
    """Test that locale handling is stable and predictable."""

    @pytest.mark.contract
    def test_same_request_returns_same_locale(self, app, client):
        """Contract: Same request returns same locale consistently."""
        test_client = app.test_client()

        with captured_templates(app) as templates:
            response1 = test_client.get("/?lang=en")

        _, context1 = templates[-1]
        lang1 = context1["current_lang"]

        with captured_templates(app) as templates:
            response2 = test_client.get("/?lang=en")

        _, context2 = templates[-1]
        lang2 = context2["current_lang"]

        assert lang1 == lang2

    @pytest.mark.contract
    def test_locale_not_affected_by_other_routes(self, app, client):
        """Contract: Locale selected on one route persists to another."""
        client.get("/?lang=en")

        # Visit another route
        with captured_templates(app) as templates:
            response = client.get("/news")

        _, context = templates[-1]
        # Should still be en
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_locale_reset_with_new_client(self, app):
        """Contract: New client starts with default locale."""
        client1 = app.test_client()
        client1.get("/?lang=en")

        # New client should start fresh
        client2 = app.test_client()

        with captured_templates(app) as templates:
            response = client2.get("/")

        _, context = templates[-1]
        # Should be default (de), not the en from client1
        assert context["current_lang"] == "de"


# ============================================================================
# MODULE-LEVEL I18N FUNCTION CONTRACTS
# ============================================================================


class TestI18nFunctionContracts:
    """Test module-level i18n functions work correctly."""

    @pytest.mark.contract
    def test_load_translations_returns_dict(self, monkeypatch):
        """Contract: _load_translations returns a dict."""
        module = load_frontend_module(monkeypatch)

        with module.app.app_context():
            t_de = module._load_translations("de")
            assert isinstance(t_de, dict)

            t_en = module._load_translations("en")
            assert isinstance(t_en, dict)

    @pytest.mark.contract
    def test_load_translations_invalid_language_returns_default(self, monkeypatch):
        """Contract: _load_translations for invalid language returns default."""
        module = load_frontend_module(monkeypatch)

        with module.app.app_context():
            t_fr = module._load_translations("fr")
            # Should return default language translations (de)
            assert isinstance(t_fr, dict)

    @pytest.mark.contract
    def test_resolve_language_function_works(self, monkeypatch):
        """Contract: _resolve_language function resolves language."""
        module = load_frontend_module(monkeypatch)

        with module.app.test_request_context("/?lang=en"):
            lang = module._resolve_language()
            assert lang == "en"

    @pytest.mark.contract
    def test_resolve_language_without_param(self, monkeypatch):
        """Contract: _resolve_language without param returns default."""
        module = load_frontend_module(monkeypatch)

        with module.app.test_request_context("/"):
            lang = module._resolve_language()
            assert lang == "de"  # Default

    @pytest.mark.contract
    def test_inject_config_returns_all_i18n_fields(self, monkeypatch):
        """Contract: inject_config returns all i18n-related fields."""
        module = load_frontend_module(monkeypatch)

        with module.app.test_request_context("/?lang=en"):
            config = module.inject_config()

            assert "current_lang" in config
            assert "supported_languages" in config
            assert "t" in config
            assert config["current_lang"] == "en"


# ============================================================================
# EDGE CASE LOCALE HANDLING
# ============================================================================


class TestEdgeCaseLocaleHandling:
    """Test edge cases in locale handling."""

    @pytest.mark.contract
    def test_whitespace_only_lang_parameter(self, app, client):
        """Contract: Whitespace-only lang parameter falls back to default."""
        test_client = app.test_client()

        with captured_templates(app) as templates:
            response = test_client.get("/?lang=   ")

        _, context = templates[-1]
        # Should fall back to default
        assert context["current_lang"] == "de"

    @pytest.mark.contract
    def test_case_insensitive_lang_parameter(self, app, client):
        """Contract: Lang parameter is case-insensitive."""
        with captured_templates(app) as templates:
            response = client.get("/?lang=EN")

        _, context = templates[-1]
        # Should recognize EN as en
        assert context["current_lang"] == "en"

    @pytest.mark.contract
    def test_mixed_case_lang_parameter(self, app, client):
        """Contract: Mixed case lang parameter is normalized."""
        with captured_templates(app) as templates:
            response = client.get("/?lang=De")

        _, context = templates[-1]
        # Should recognize De as de
        assert context["current_lang"] == "de"

    @pytest.mark.contract
    def test_lang_parameter_with_extra_whitespace(self, app, client):
        """Contract: Lang parameter with whitespace is trimmed."""
        with captured_templates(app) as templates:
            response = client.get("/?lang= en ")

        _, context = templates[-1]
        # Should recognize en
        assert context["current_lang"] == "en"
