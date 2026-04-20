from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv()
    _config_dir = Path(__file__).resolve().parent
    _project_root = _config_dir.parent
    load_dotenv(_project_root / ".env")
except ImportError:  # pragma: no cover - optional in constrained environments
    pass


# Configuration validation functions
def validate_play_service_secret(secret, is_production=True):
    """Validate PLAY_SERVICE_SECRET configuration.

    Args:
        secret: The secret string to validate
        is_production: Whether this is a production environment

    Returns:
        True if validation passes

    Raises:
        ValueError: If validation fails
    """
    if not secret or (isinstance(secret, str) and not secret.strip()):
        raise ValueError("play_service_secret cannot be empty")
    if is_production and len(secret) < 32:
        raise ValueError("play_service_secret must be at least 32 bytes in production")
    return True


def validate_database_url(url, required=True):
    """Validate database URL configuration.

    Args:
        url: The database URL string to validate
        required: Whether the URL is required

    Returns:
        True if validation passes

    Raises:
        ValueError: If validation fails
    """
    if required and not url:
        raise ValueError("database_url is required")

    if url:
        # Check for valid SQLAlchemy URL schemes
        valid_schemes = {
            'postgresql', 'postgres', 'mysql', 'sqlite',
            'oracle', 'mssql', 'firebird', 'sybase',
            'mysql+pymysql', 'mysql+mysqlconnector', 'mysql+cymysql',
            'postgresql+psycopg2', 'postgresql+pg8000',
        }

        parsed = urlparse(url)
        scheme = parsed.scheme

        # Check if scheme is valid
        if not scheme or scheme not in valid_schemes:
            raise ValueError("database_url must have a valid SQLAlchemy scheme")

        # For non-sqlite, check that there's a netloc (host)
        if scheme != 'sqlite' and not parsed.netloc and not parsed.path:
            raise ValueError("database_url must have a valid host/path")

    return True


def validate_redis_url(url, required=False):
    """Validate Redis URL configuration.

    Args:
        url: The Redis URL string to validate
        required: Whether the URL is required

    Returns:
        True if validation passes

    Raises:
        ValueError: If validation fails
    """
    if required and not url:
        raise ValueError("redis_url is required")

    if url and url.strip():
        valid_schemes = {'redis', 'rediss'}
        parsed = urlparse(url)

        if not parsed.scheme or parsed.scheme not in valid_schemes:
            raise ValueError("redis_url must have redis:// or rediss:// scheme")

        if not parsed.netloc:
            raise ValueError("redis_url must have a valid host")

    return True


def validate_play_service_internal_api_key(key, is_required=False, is_production=True):
    """Validate PLAY_SERVICE_INTERNAL_API_KEY configuration.

    Args:
        key: The API key string to validate
        is_required: Whether the key is required (fail-fast if missing)
        is_production: Whether this is a production environment

    Returns:
        True if validation passes

    Raises:
        ValueError: If validation fails
    """
    if is_required and (not key or (isinstance(key, str) and not key.strip())):
        raise ValueError("play_service_internal_api_key cannot be empty when required")

    if key and isinstance(key, str) and not key.strip():
        raise ValueError("play_service_internal_api_key cannot be blank (whitespace-only)")

    return True


def validate_cors_origins(origins, is_production=True):
    """Validate CORS origins configuration.

    Args:
        origins: List of origin URLs to validate
        is_production: Whether this is a production environment

    Returns:
        True if validation passes

    Raises:
        ValueError: If validation fails
    """
    import re

    if not origins:
        return True  # Empty list is valid

    # Valid hostname pattern (alphanumeric, dots, hyphens, colons for port)
    valid_hostname_pattern = re.compile(r'^[a-zA-Z0-9.-:]+$')

    for origin in origins:
        # Reject wildcards
        if '*' in origin:
            raise ValueError("cors_origins cannot contain wildcards")

        # Parse the URL
        parsed = urlparse(origin)

        # Check for valid scheme
        if not parsed.scheme or parsed.scheme not in {'http', 'https'}:
            raise ValueError("cors_origins must use http:// or https:// scheme")

        # Check for valid netloc (hostname)
        if not parsed.netloc:
            raise ValueError("cors_origins must have a valid hostname")

        # Check for valid hostname format (no spaces or invalid characters)
        if not valid_hostname_pattern.match(parsed.netloc):
            raise ValueError("cors_origins must have a valid hostname")

        # Check for valid hostname (not just spaces or empty)
        hostname = parsed.hostname
        if not hostname or not hostname.strip():
            raise ValueError("cors_origins must have a valid hostname")

        # In production, enforce HTTPS for all non-localhost origins
        if is_production:
            is_localhost = hostname in {'localhost', '127.0.0.1', '::1'}
            if parsed.scheme == 'http' and not is_localhost:
                raise ValueError("cors_origins must use https:// in production (except localhost)")
            # In production, even HTTP localhost is discouraged but we reject it for now
            # to encourage HTTPS everywhere
            if is_localhost and parsed.scheme == 'http':
                raise ValueError("cors_origins must use https:// in production (except localhost)")

    return True

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "var"
RUN_STORE_DIR = DATA_DIR / "runs"
APP_TITLE = os.getenv("APP_TITLE", "World of Shadows Play Service Prototype")
APP_VERSION = "0.3.0"

# Determine if we're in production-like mode (explicit opt-in to lenient test mode)
_IS_PRODUCTION_MODE = os.getenv("FLASK_ENV") in {"production", "staging"} or \
                      os.getenv("ENV") in {"production", "staging"} or \
                      (os.getenv("PLAY_SERVICE_SECRET") is not None and
                       os.getenv("PLAY_SERVICE_SECRET", "").strip() != "" and
                       os.getenv("FLASK_ENV") not in {"test"})

# CRITICAL: Shared secret with backend. Must be configured via env var, never use defaults.
# Fail fast in production if missing or blank
PLAY_SERVICE_SECRET = (os.getenv("PLAY_SERVICE_SECRET") or os.getenv("PLAY_SERVICE_SHARED_SECRET") or "").strip() or None

if PLAY_SERVICE_SECRET is None:
    if _IS_PRODUCTION_MODE or os.getenv("FLASK_ENV") not in {"test"}:
        # In production or production-like mode, fail fast
        raise ValueError(
            "PLAY_SERVICE_SECRET is required and cannot be empty. "
            "Set PLAY_SERVICE_SECRET or PLAY_SERVICE_SHARED_SECRET environment variable. "
            "In test mode, set FLASK_ENV=test to use lenient defaults."
        )
    else:
        # In explicit test mode, issue warning for traceability
        import warnings
        warnings.warn(
            "PLAY_SERVICE_SECRET not configured - backend integration will fail in production. "
            "Set PLAY_SERVICE_SECRET or PLAY_SERVICE_SHARED_SECRET env var for production deployment.",
            stacklevel=2
        )

# PLAY_SERVICE_INTERNAL_API_KEY: optional in lenient mode, but when set must be non-blank
PLAY_SERVICE_INTERNAL_API_KEY = os.getenv("PLAY_SERVICE_INTERNAL_API_KEY", "").strip() or None
RUN_STORE_BACKEND = os.getenv("RUN_STORE_BACKEND", "json")
RUN_STORE_URL = os.getenv("RUN_STORE_URL", "")

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "").strip().rstrip("/")
BACKEND_CONTENT_FEED_URL = os.getenv("BACKEND_CONTENT_FEED_URL", (f"{BACKEND_API_URL}/api/v1/game/content/published" if BACKEND_API_URL else "")).strip()
BACKEND_CONTENT_SYNC_ENABLED = os.getenv("BACKEND_CONTENT_SYNC_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
BACKEND_CONTENT_SYNC_INTERVAL_SECONDS = float(os.getenv("BACKEND_CONTENT_SYNC_INTERVAL_SECONDS", "15"))
BACKEND_CONTENT_TIMEOUT_SECONDS = float(os.getenv("BACKEND_CONTENT_TIMEOUT_SECONDS", "10"))
