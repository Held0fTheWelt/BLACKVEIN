"""Tests for app.i18n language helpers."""
import pytest

from app.i18n import (
    get_default_language,
    get_supported_languages,
    is_supported_language,
    normalize_language,
    validate_language_code,
)


def test_is_supported_language_rejects_empty_and_non_string(app):
    with app.app_context():
        assert is_supported_language(None) is False
        assert is_supported_language("") is False
        assert is_supported_language(42) is False
        assert is_supported_language("DE") is True


def test_get_supported_and_default_language(app):
    with app.app_context():
        app.config["SUPPORTED_LANGUAGES"] = ["de", "fr"]
        app.config["DEFAULT_LANGUAGE"] = "fr"
        assert get_supported_languages() == ["de", "fr"]
        assert get_default_language() == "fr"


def test_normalize_language_invalid(app):
    with app.app_context():
        assert normalize_language(None) is None
        assert normalize_language("") is None
        assert normalize_language("xx") is None


def test_validate_language_code_all_branches(app):
    with app.app_context():
        app.config["SUPPORTED_LANGUAGES"] = ["de", "en"]

        assert validate_language_code(None) == (None, "language_code is required")
        assert validate_language_code("") == (None, "language_code is required")

        assert validate_language_code(123) == (None, "language_code must be a string")

        assert validate_language_code("a" * 11) == (None, "language_code is invalid")

        assert validate_language_code("de!") == (
            None,
            "language_code contains invalid characters",
        )

        assert "Unsupported language" in validate_language_code("fr")[1]

        assert validate_language_code(" EN ") == ("en", None)
