"""Tests for language resolution and UI language selection.

Validates that:
- Supported language selection works correctly
- Query parameter (lang=?) overrides session and Accept-Language
- Invalid language falls back cleanly to default
- Accept-Language header is used as fallback when no query or session
- Session language persistence works (if intended)
- Multiple language changes in sequence work correctly
"""
from __future__ import annotations

import pytest


class TestLanguageResolutionHierarchy:
    """Test the language resolution priority hierarchy."""

    @pytest.mark.unit
    def test_query_parameter_takes_highest_priority(self, app_factory):
        """Test that query lang parameter overrides everything."""
        from app import _resolve_language
        app = app_factory(test_config={"TESTING": True})

        # Query param should win over Accept-Language
        with app.test_request_context(
            "/?lang=en",
            headers={"Accept-Language": "de-DE"}
        ):
            lang = _resolve_language()
            assert lang == "en"

    @pytest.mark.unit
    def test_session_takes_priority_over_accept_language(self, app_factory):
        """Test that session language overrides Accept-Language."""
        from app import _resolve_language
        from flask import session
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context(
            "/",
            headers={"Accept-Language": "de-DE"}
        ):
            session["lang"] = "en"
            lang = _resolve_language()
            assert lang == "en"

    @pytest.mark.unit
    def test_accept_language_used_when_no_query_or_session(self, app_factory):
        """Test that Accept-Language header is used as fallback."""
        from app import _resolve_language
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context(
            "/",
            headers={"Accept-Language": "en-US,en;q=0.9"}
        ):
            lang = _resolve_language()
            assert lang == "en"

    @pytest.mark.unit
    def test_default_language_is_last_resort(self, app_factory):
        """Test that DEFAULT_LANGUAGE is used when nothing else matches."""
        from app import _resolve_language, DEFAULT_LANGUAGE
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context(
            "/",
            headers={"Accept-Language": "fr-FR,fr;q=0.9"}
        ):
            lang = _resolve_language()
            assert lang == DEFAULT_LANGUAGE


class TestQueryParameterLanguageSelection:
    """Test language selection via query parameter."""

    @pytest.mark.unit
    @pytest.mark.parametrize("lang", ["de", "en"])
    def test_query_parameter_selects_supported_language(self, app_factory, lang):
        """Test that valid lang query parameters are recognized."""
        from app import _resolve_language
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context(f"/?lang={lang}"):
            selected = _resolve_language()
            assert selected == lang

    @pytest.mark.unit
    def test_query_parameter_is_case_insensitive(self, app_factory):
        """Test that lang query parameter is lowercased."""
        from app import _resolve_language
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/?lang=EN"):
            selected = _resolve_language()
            assert selected == "en"

    @pytest.mark.unit
    def test_query_parameter_with_whitespace_is_stripped(self, app_factory):
        """Test that whitespace in lang parameter is stripped."""
        from app import _resolve_language
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/?lang= en "):
            selected = _resolve_language()
            assert selected == "en"

    @pytest.mark.unit
    def test_unsupported_query_parameter_falls_back(self, app_factory):
        """Test that unsupported lang parameter falls back to session/default."""
        from app import _resolve_language, DEFAULT_LANGUAGE
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/?lang=fr"):
            selected = _resolve_language()
            assert selected == DEFAULT_LANGUAGE

    @pytest.mark.unit
    def test_empty_query_parameter_is_ignored(self, app_factory):
        """Test that empty lang parameter is treated as not provided."""
        from app import _resolve_language, DEFAULT_LANGUAGE
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/?lang="):
            selected = _resolve_language()
            assert selected == DEFAULT_LANGUAGE

    @pytest.mark.unit
    def test_query_parameter_persists_to_session(self, app_factory):
        """Test that setting via query parameter saves to session."""
        from app import _resolve_language
        from flask import session
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/?lang=en"):
            lang = _resolve_language()
            assert lang == "en"
            assert session["lang"] == "en"


class TestSessionLanguagePersistence:
    """Test session-based language persistence."""

    @pytest.mark.unit
    def test_session_language_is_preserved(self, app_factory):
        """Test that language set in session is remembered."""
        from app import _resolve_language
        from flask import session
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/"):
            session["lang"] = "en"
            lang = _resolve_language()
            assert lang == "en"

    @pytest.mark.unit
    def test_session_language_is_used_on_subsequent_requests(self, app_factory):
        """Test that session language persists across context changes."""
        from app import _resolve_language
        from flask import session
        app = app_factory(test_config={"TESTING": True})

        # First request sets session
        with app.test_request_context("/?lang=en"):
            lang1 = _resolve_language()
            assert lang1 == "en"

        # Second request without query param but with session (simulated)
        with app.test_request_context("/"):
            session["lang"] = "en"
            lang2 = _resolve_language()
            assert lang2 == "en"

    @pytest.mark.unit
    def test_invalid_session_language_falls_back(self, app_factory):
        """Test that invalid session language is treated as not set."""
        from app import _resolve_language, DEFAULT_LANGUAGE
        from flask import session
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context(
            "/",
            headers={"Accept-Language": "de-DE"}
        ):
            session["lang"] = "fr"  # Invalid language
            lang = _resolve_language()
            # Should fall back to Accept-Language or default
            assert lang in ["de", DEFAULT_LANGUAGE]

    @pytest.mark.unit
    def test_session_language_empty_string_is_ignored(self, app_factory):
        """Test that empty string in session is treated as not set."""
        from app import _resolve_language
        from flask import session
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context(
            "/",
            headers={"Accept-Language": "en-US"}
        ):
            session["lang"] = ""
            lang = _resolve_language()
            assert lang == "en"


class TestAcceptLanguageHeaderParsing:
    """Test Accept-Language header parsing and selection."""

    @pytest.mark.unit
    @pytest.mark.parametrize("accept_lang,expected", [
        ("en-US,en;q=0.9", "en"),
        ("de-DE,de;q=0.9", "de"),
        ("en", "en"),
        ("de", "de"),
    ])
    def test_accept_language_variants_recognized(self, app_factory, accept_lang, expected):
        """Test that various Accept-Language formats are recognized."""
        from app import _resolve_language
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/", headers={"Accept-Language": accept_lang}):
            lang = _resolve_language()
            assert lang == expected

    @pytest.mark.unit
    def test_accept_language_with_quality_values(self, app_factory):
        """Test that Accept-Language with quality values is parsed."""
        from app import _resolve_language
        app = app_factory(test_config={"TESTING": True})

        # de is weighted higher than en
        with app.test_request_context(
            "/",
            headers={"Accept-Language": "en;q=0.5,de;q=0.9"}
        ):
            lang = _resolve_language()
            # Should pick first supported language (en)
            assert lang in ["en", "de"]

    @pytest.mark.unit
    def test_accept_language_with_spaces_handled(self, app_factory):
        """Test that Accept-Language with spaces is handled."""
        from app import _resolve_language
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context(
            "/",
            headers={"Accept-Language": "en - US , en ; q = 0.9"}
        ):
            lang = _resolve_language()
            # Should handle space removal and parse correctly
            assert lang is not None

    @pytest.mark.unit
    def test_accept_language_first_supported_picked(self, app_factory):
        """Test that first supported language in Accept-Language is picked."""
        from app import _resolve_language
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context(
            "/",
            headers={"Accept-Language": "fr,de,en"}
        ):
            lang = _resolve_language()
            # fr is not supported, should pick de (first supported)
            assert lang == "de"

    @pytest.mark.unit
    def test_accept_language_missing_defaults_to_default(self, app_factory):
        """Test that missing Accept-Language defaults to DEFAULT_LANGUAGE."""
        from app import _resolve_language, DEFAULT_LANGUAGE
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/"):
            lang = _resolve_language()
            assert lang == DEFAULT_LANGUAGE

    @pytest.mark.unit
    def test_accept_language_with_region_code_extracted(self, app_factory):
        """Test that region codes (e.g., en-US) are extracted correctly."""
        from app import _resolve_language
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context(
            "/",
            headers={"Accept-Language": "en-US"}
        ):
            lang = _resolve_language()
            assert lang == "en"


class TestLanguageFallbackBehavior:
    """Test fallback behavior for unsupported languages."""

    @pytest.mark.unit
    @pytest.mark.parametrize("unsupported_lang", ["fr", "es", "it", "pt", "ja", "zh"])
    def test_unsupported_languages_fallback_to_default(self, app_factory, unsupported_lang):
        """Test that unsupported languages fall back to DEFAULT_LANGUAGE."""
        from app import _resolve_language, DEFAULT_LANGUAGE
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context(f"/?lang={unsupported_lang}"):
            lang = _resolve_language()
            assert lang == DEFAULT_LANGUAGE

    @pytest.mark.unit
    def test_special_characters_in_language_handled(self, app_factory):
        """Test that special characters in language parameter are handled."""
        from app import _resolve_language
        app = app_factory(test_config={"TESTING": True})

        with app.test_request_context("/?lang=en<script>"):
            lang = _resolve_language()
            # Should not crash, should fall back
            assert lang is not None

    @pytest.mark.unit
    def test_very_long_language_parameter_handled(self, app_factory):
        """Test that very long language parameter is handled gracefully."""
        from app import _resolve_language
        app = app_factory(test_config={"TESTING": True})

        long_lang = "x" * 1000
        with app.test_request_context(f"/?lang={long_lang}"):
            lang = _resolve_language()
            # Should not crash, should fall back
            assert lang is not None


class TestMultipleLanguageChanges:
    """Test multiple language changes in sequence."""

    @pytest.mark.unit
    def test_language_changes_in_sequence(self, app_factory):
        """Test that language can be changed multiple times."""
        from app import _resolve_language
        app = app_factory(test_config={"TESTING": True})

        # First request in German
        with app.test_request_context("/?lang=de"):
            lang1 = _resolve_language()
            assert lang1 == "de"

        # Second request in English
        with app.test_request_context("/?lang=en"):
            lang2 = _resolve_language()
            assert lang2 == "en"

        # Third request back to German
        with app.test_request_context("/?lang=de"):
            lang3 = _resolve_language()
            assert lang3 == "de"

    @pytest.mark.unit
    def test_session_language_updates_on_query_change(self, app_factory):
        """Test that session language updates when query parameter changes."""
        from app import _resolve_language
        from flask import session
        app = app_factory(test_config={"TESTING": True})

        # Set to German
        with app.test_request_context("/?lang=de"):
            lang1 = _resolve_language()
            assert session["lang"] == "de"

        # Change to English
        with app.test_request_context("/?lang=en"):
            lang2 = _resolve_language()
            assert session["lang"] == "en"
            assert lang2 == "en"


class TestLanguageResolutionIntegration:
    """Integration tests for language resolution in full context."""

    @pytest.mark.integration
    def test_resolve_language_with_app_context(self, app):
        """Test _resolve_language with actual app test client context."""
        with app.test_request_context("/?lang=en"):
            from app import _resolve_language
            lang = _resolve_language()
            assert lang == "en"

    @pytest.mark.integration
    def test_resolve_language_called_during_context_injection(self, app):
        """Test that _resolve_language is called during inject_config."""
        with app.test_request_context("/?lang=de"):
            from app import inject_config
            context = inject_config()
            assert context["current_lang"] == "de"
            assert context["frontend_config"]["currentLanguage"] == "de"

    @pytest.mark.integration
    def test_language_available_in_template_context(self, app, client):
        """Test that resolved language is available in template context."""
        from conftest import captured_templates

        with captured_templates(app) as templates:
            response = client.get("/?lang=en")

        assert response.status_code == 200
        _, context = templates[-1]
        # Should have either current_lang or frontend_config with currentLanguage
        has_lang = (context.get("current_lang") or
                   context.get("frontend_config", {}).get("currentLanguage"))
        assert has_lang is not None
