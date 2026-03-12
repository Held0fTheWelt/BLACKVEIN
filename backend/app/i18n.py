"""Language and translation constants. Backend validates language codes against config."""

from flask import current_app


def get_supported_languages():
    """Return list of supported language codes from config."""
    return list(current_app.config.get("SUPPORTED_LANGUAGES", ["de", "en"]))


def get_default_language():
    """Return default language code from config."""
    return current_app.config.get("DEFAULT_LANGUAGE", "de")


def is_supported_language(code):
    """Return True if code is a supported language code."""
    if not code or not isinstance(code, str):
        return False
    return code.strip().lower() in get_supported_languages()


def normalize_language(code):
    """Return normalized language code if supported, else None."""
    if not code or not isinstance(code, str):
        return None
    normalized = code.strip().lower()
    return normalized if normalized in get_supported_languages() else None


# Translation status values for content (news, wiki). Do not auto-publish machine_draft.
TRANSLATION_STATUS_MISSING = "missing"
TRANSLATION_STATUS_MACHINE_DRAFT = "machine_draft"
TRANSLATION_STATUS_REVIEW_REQUIRED = "review_required"
TRANSLATION_STATUS_APPROVED = "approved"
TRANSLATION_STATUS_PUBLISHED = "published"
TRANSLATION_STATUS_OUTDATED = "outdated"

TRANSLATION_STATUSES = frozenset({
    TRANSLATION_STATUS_MACHINE_DRAFT,
    TRANSLATION_STATUS_REVIEW_REQUIRED,
    TRANSLATION_STATUS_APPROVED,
    TRANSLATION_STATUS_PUBLISHED,
    TRANSLATION_STATUS_OUTDATED,
})
