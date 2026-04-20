"""Configuration loaded from environment. No hardcoded secrets in production."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
    _config_dir = Path(__file__).resolve().parent
    _backend_root = _config_dir.parent
    _repo_root = _backend_root.parent
    if _repo_root != _backend_root:
        load_dotenv(_repo_root / ".env")
except ImportError:  # pragma: no cover - optional in constrained environments
    pass


def env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean from environment."""
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _parse_cors_origins():
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if not raw:
        return None
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _validate_service_url(url: str | None) -> str | None:
    """Validate internal service URL (must be valid http/https if provided)."""
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if url.startswith(("http://", "https://")):
        return url
    # If set but invalid, log warning and reject
    import warnings
    warnings.warn(f"Invalid service URL (must start with http:// or https://): {url}")
    return None


class Config:
    """Base config for production. SECRET_KEY must be set via environment."""

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max request body to prevent DoS attacks

    SECRET_KEY = os.environ.get("SECRET_KEY")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or os.environ.get("SECRET_KEY")

    _instance_path = Path(__file__).resolve().parent.parent / "instance"
    _default_db = _instance_path / "wos.db"
    _uri = os.environ.get("DATABASE_URI")
    if not _uri:
        _instance_path.mkdir(parents=True, exist_ok=True)
        _uri = "sqlite:///" + str(_default_db).replace("\\", "/")
    SQLALCHEMY_DATABASE_URI = _uri

    # Access token: 1 hour (3600 seconds) for short-lived sessions
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    # Refresh token: 7 days (604800 seconds) for long-lived refresh capability
    JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", 604800))
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    JWT_ALGORITHM = "HS256"

    CORS_ORIGINS = _parse_cors_origins()

    # Task 2: register MockStoryAIAdapter + AdapterModelSpec at app startup when true.
    ROUTING_REGISTRY_BOOTSTRAP = env_bool("ROUTING_REGISTRY_BOOTSTRAP", True)

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_bool("PREFER_HTTPS", False)
    ENFORCE_HTTPS = env_bool("PREFER_HTTPS", False)
    # Enforce SECURE flag for production deployments
    PREFER_HTTPS = env_bool("PREFER_HTTPS", False)

    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "100 per minute")
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = env_bool("MAIL_USE_TLS", False)
    MAIL_USE_SSL = env_bool("MAIL_USE_SSL", False)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@worldofshadows.local")
    MAIL_ENABLED = env_bool("MAIL_ENABLED", False)

    REGISTRATION_REQUIRE_EMAIL = env_bool("REGISTRATION_REQUIRE_EMAIL", True)
    APP_PUBLIC_BASE_URL = os.environ.get("APP_PUBLIC_BASE_URL", "").strip() or None
    EMAIL_VERIFICATION_TTL_HOURS = int(os.environ.get("EMAIL_VERIFICATION_TTL_HOURS", "24"))
    EMAIL_VERIFICATION_ENABLED = env_bool("EMAIL_VERIFICATION_ENABLED", False)
    # Require email verification before login (default: True in production, False in dev/testing)
    REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN = env_bool("REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN", True)

    # Compatibility redirect target for legacy /web routes.
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "").strip() or None

    # Optional: administration-tool base URL for operator links (e.g. backend /backend home page).
    ADMINISTRATION_TOOL_URL = os.environ.get("ADMINISTRATION_TOOL_URL", "").strip() or None

    # Supported languages: whitelisted codes only (ISO 639-1)
    SUPPORTED_LANGUAGES = ["en", "fr", "de", "es", "it", "pt", "ru", "zh", "ja", "ko"]
    DEFAULT_LANGUAGE = "de"

    N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "").strip() or None
    N8N_WEBHOOK_SECRET = os.environ.get("N8N_WEBHOOK_SECRET", "").strip() or None
    N8N_SERVICE_TOKEN = os.environ.get("N8N_SERVICE_TOKEN", "").strip() or None

    # Play service bridge configuration.
    PLAY_SERVICE_PUBLIC_URL = os.environ.get("PLAY_SERVICE_PUBLIC_URL", "").strip() or None
    PLAY_SERVICE_INTERNAL_URL = _validate_service_url(os.environ.get("PLAY_SERVICE_INTERNAL_URL", ""))

    # Timeout for internal service calls (in seconds).
    PLAY_SERVICE_REQUEST_TIMEOUT = int(os.environ.get("PLAY_SERVICE_REQUEST_TIMEOUT", "30"))

    # Prefer PLAY_SERVICE_SHARED_SECRET; PLAY_SERVICE_SECRET is deprecated but supported for migration.
    PLAY_SERVICE_SHARED_SECRET = (
        os.environ.get("PLAY_SERVICE_SHARED_SECRET")
        or os.environ.get("PLAY_SERVICE_SECRET")
        or ""
    ).strip() or None
    PLAY_SERVICE_INTERNAL_API_KEY = os.environ.get("PLAY_SERVICE_INTERNAL_API_KEY", "").strip() or None

    # Game ticket TTL with bounds validation (5 min to 24 hours).
    _ttl_raw = os.environ.get("GAME_TICKET_TTL_SECONDS", "300")
    try:
        _ttl_int = int(_ttl_raw)
        GAME_TICKET_TTL_SECONDS = max(300, min(86400, _ttl_int))  # Clamp to 5min-24h
        if _ttl_int != GAME_TICKET_TTL_SECONDS:
            import warnings
            warnings.warn(f"GAME_TICKET_TTL_SECONDS clamped from {_ttl_int} to {GAME_TICKET_TTL_SECONDS}")
    except (ValueError, TypeError):
        GAME_TICKET_TTL_SECONDS = 300  # Default to 5 minutes if invalid


class DevelopmentConfig(Config):
    """Dev-only: fallback secrets when DEV_SECRETS_OK is explicitly enabled.

    run.py selects this class only when DEV_SECRETS_OK=1. Never set that in production.
    """

    if env_bool("DEV_SECRETS_OK", False):
        SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-do-not-use-in-production"
        JWT_SECRET_KEY = (
            os.environ.get("JWT_SECRET_KEY")
            or os.environ.get("SECRET_KEY")
            or "dev-jwt-secret-do-not-use-in-production"
        )


class TestingConfig(Config):
    """Config for tests only: in-memory DB, fixed secrets, CSRF disabled by default (enabled separately for CSRF tests)."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key"
    JWT_SECRET_KEY = "test-jwt-secret-key-at-least-32-bytes-long"
    RATELIMIT_ENABLED = True  # Enable rate limiting so tests can verify it works
    RATELIMIT_DEFAULT = "10000 per minute"  # Allow reasonable default, endpoint-specific limits will be enforced
    RATELIMIT_STORAGE_URI = "memory://"  # In-memory storage for testing
    WTF_CSRF_ENABLED = False  # Disable CSRF for regular tests; use TestingConfigWithCSRF for CSRF tests
    CORS_ORIGINS = None
    PLAY_SERVICE_PUBLIC_URL = "http://play.example.test"
    PLAY_SERVICE_INTERNAL_URL = "http://play.example.test"
    PLAY_SERVICE_SHARED_SECRET = "test-play-secret"
    PLAY_SERVICE_INTERNAL_API_KEY = "test-play-key"
    REGISTRATION_REQUIRE_EMAIL = False  # Email optional in tests
    REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN = False  # Allow login without verification in tests
    PASSWORD_COMPLEXITY_MIN_LENGTH = 8  # Relaxed requirement for testing (normally 12)
    ROUTING_REGISTRY_BOOTSTRAP = False  # keep process-global registry isolated across tests

# Module-level defaults for runtime configuration (used by app.runtime.manager)
RUN_STORE_BACKEND = os.environ.get("RUN_STORE_BACKEND", "json")
RUN_STORE_URL = os.environ.get("RUN_STORE_URL")

# Internal API key for World Engine / play service (e.g. join-context); not used by removed backend FastAPI shadow router.
PLAY_SERVICE_INTERNAL_API_KEY = (os.environ.get("PLAY_SERVICE_INTERNAL_API_KEY", "").strip() or None)
