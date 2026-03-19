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


class Config:
    """Base config for production. SECRET_KEY must be set via environment."""

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.environ.get("SECRET_KEY")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or os.environ.get("SECRET_KEY")

    _instance_path = Path(__file__).resolve().parent.parent / "instance"
    _default_db = _instance_path / "wos.db"
    _uri = os.environ.get("DATABASE_URI")
    if not _uri:
        _instance_path.mkdir(parents=True, exist_ok=True)
        _uri = "sqlite:///" + str(_default_db).replace("\\", "/")
    SQLALCHEMY_DATABASE_URI = _uri

    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 86400))
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    CORS_ORIGINS = _parse_cors_origins()

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_bool("PREFER_HTTPS", False)
    ENFORCE_HTTPS = env_bool("PREFER_HTTPS", False)

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

    REGISTRATION_REQUIRE_EMAIL = env_bool("REGISTRATION_REQUIRE_EMAIL", False)
    APP_PUBLIC_BASE_URL = os.environ.get("APP_PUBLIC_BASE_URL", "").strip() or None
    EMAIL_VERIFICATION_TTL_HOURS = int(os.environ.get("EMAIL_VERIFICATION_TTL_HOURS", "24"))
    EMAIL_VERIFICATION_ENABLED = env_bool("EMAIL_VERIFICATION_ENABLED", False)

    FRONTEND_URL = os.environ.get("FRONTEND_URL", "").strip() or None

    SUPPORTED_LANGUAGES = ["de", "en"]
    DEFAULT_LANGUAGE = "de"

    N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "").strip() or None
    N8N_WEBHOOK_SECRET = os.environ.get("N8N_WEBHOOK_SECRET", "").strip() or None
    N8N_SERVICE_TOKEN = os.environ.get("N8N_SERVICE_TOKEN", "").strip() or None

    # Play service bridge configuration.
    PLAY_SERVICE_PUBLIC_URL = os.environ.get("PLAY_SERVICE_PUBLIC_URL", "").strip() or None
    PLAY_SERVICE_INTERNAL_URL = os.environ.get("PLAY_SERVICE_INTERNAL_URL", "").strip() or None
    PLAY_SERVICE_SHARED_SECRET = (
        os.environ.get("PLAY_SERVICE_SHARED_SECRET")
        or os.environ.get("PLAY_SERVICE_SECRET")
        or ""
    ).strip() or None
    PLAY_SERVICE_INTERNAL_API_KEY = os.environ.get("PLAY_SERVICE_INTERNAL_API_KEY", "").strip() or None
    GAME_TICKET_TTL_SECONDS = int(os.environ.get("GAME_TICKET_TTL_SECONDS", "300"))


class DevelopmentConfig(Config):
    """Dev-only: fallback secrets when DEV_SECRETS_OK is explicitly enabled."""

    if env_bool("DEV_SECRETS_OK", False):
        SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-do-not-use-in-production"
        JWT_SECRET_KEY = (
            os.environ.get("JWT_SECRET_KEY")
            or os.environ.get("SECRET_KEY")
            or "dev-jwt-secret-do-not-use-in-production"
        )


class TestingConfig(Config):
    """Config for tests only: in-memory DB, fixed secrets, CSRF disabled, high rate limit."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key"
    JWT_SECRET_KEY = "test-jwt-secret-key-at-least-32-bytes-long"
    RATELIMIT_DEFAULT = "1000 per minute"
    WTF_CSRF_ENABLED = False
    CORS_ORIGINS = None
    PLAY_SERVICE_PUBLIC_URL = "http://play.example.test"
    PLAY_SERVICE_INTERNAL_URL = "http://play.example.test"
    PLAY_SERVICE_SHARED_SECRET = "test-play-secret"
    PLAY_SERVICE_INTERNAL_API_KEY = "test-play-key"
