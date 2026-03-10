"""Configuration loaded from environment. No hardcoded secrets in production."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
    # When running from Backend/, also load repo-root .env so one file works for both
    _config_dir = Path(__file__).resolve().parent
    _backend_root = _config_dir.parent
    _repo_root = _backend_root.parent
    if _repo_root != _backend_root:
        load_dotenv(_repo_root / ".env")
except ImportError:
    pass


def env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean from environment. Only 1, true, yes, on (case-insensitive) are True.
    Merely being set to any other value is False, so DEV_SECRETS_OK=0 or DEV_SECRETS_OK=foo
    does not enable dev behavior."""
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _parse_cors_origins():
    """Parse CORS_ORIGINS env: comma-separated list, or None for same-origin only."""
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if not raw:
        return None
    return [o.strip() for o in raw.split(",") if o.strip()]


class Config:
    """Base config for production. SECRET_KEY must be set via environment.
    JWT_SECRET_KEY may fall back to SECRET_KEY if unset (documented single-secret option);
    for production, set both explicitly when possible."""

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Required from environment; no insecure defaults
    SECRET_KEY = os.environ.get("SECRET_KEY")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or os.environ.get("SECRET_KEY")

    # Database (instance path: Backend/instance when run from Backend/)
    _instance_path = Path(__file__).resolve().parent.parent / "instance"
    _default_db = _instance_path / "wos.db"
    _uri = os.environ.get("DATABASE_URI")
    if not _uri:
        _instance_path.mkdir(parents=True, exist_ok=True)
        _uri = "sqlite:///" + str(_default_db).replace("\\", "/")
    SQLALCHEMY_DATABASE_URI = _uri

    # JWT
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 86400))
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # CORS: configurable origins; None means same-origin only
    CORS_ORIGINS = _parse_cors_origins()

    # Session cookies: explicit and secure by default
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_bool("PREFER_HTTPS", False)

    # Rate limiting
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "100 per minute")
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    # Mail (password reset)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = env_bool("MAIL_USE_TLS", True)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "noreply@worldofshadows.local"
    )

    # Public frontend URL (no trailing slash). When set, GET / and GET /news redirect there.
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "").strip() or None


class DevelopmentConfig(Config):
    """Dev-only: fallback secrets when DEV_SECRETS_OK is explicitly 1/true/yes/on.
    Do not use in production."""

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
