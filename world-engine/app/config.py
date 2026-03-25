from __future__ import annotations

import os
import re
import warnings
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "var"
RUN_STORE_DIR = DATA_DIR / "runs"
APP_TITLE = os.getenv("APP_TITLE", "World of Shadows Play Service Prototype")
APP_VERSION = "0.3.0"

# Configuration validation functions
def validate_play_service_secret(value: str | None, is_production: bool = False) -> bool:
    """Validate PLAY_SERVICE_SECRET value.

    Args:
        value: The secret value to validate
        is_production: Whether running in production mode

    Returns:
        True if valid

    Raises:
        ValueError: If validation fails
    """
    if not value or (isinstance(value, str) and not value.strip()):
        raise ValueError("play_service_secret cannot be empty")

    if isinstance(value, str):
        value = value.strip()

    if is_production and len(value) < 32:
        raise ValueError("play_service_secret must be at least 32 bytes in production")

    return True


def validate_play_service_internal_api_key(value: str | None, is_required: bool = False) -> bool:
    """Validate PLAY_SERVICE_INTERNAL_API_KEY value.

    Args:
        value: The API key to validate
        is_required: Whether the key is required

    Returns:
        True if valid

    Raises:
        ValueError: If validation fails
    """
    if value is None or value == "":
        if is_required:
            raise ValueError("play_service_internal_api_key cannot be empty when required")
        return True

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped and value != "":
            raise ValueError("play_service_internal_api_key cannot be blank")
        if not stripped and is_required:
            raise ValueError("play_service_internal_api_key cannot be empty when required")

    return True


def validate_database_url(value: str | None, required: bool = False) -> bool:
    """Validate database URL format.

    Args:
        value: The database URL to validate
        required: Whether the URL is required

    Returns:
        True if valid

    Raises:
        ValueError: If validation fails
    """
    if not value:
        if required:
            raise ValueError("database_url is required")
        return True

    parsed = urlparse(value)

    valid_schemes = {
        'postgresql', 'postgres', 'mysql', 'sqlite',
        'mysql+pymysql', 'postgresql+psycopg2', 'oracle'
    }

    # Must have a valid scheme
    if not parsed.scheme:
        raise ValueError("database_url must include a scheme")

    if parsed.scheme not in valid_schemes:
        raise ValueError(f"database_url must use one of: {', '.join(valid_schemes)}")

    # sqlite URLs use a file path, others need a host
    if parsed.scheme != 'sqlite' and not parsed.netloc:
        raise ValueError("database_url must include a host for non-sqlite databases")

    # sqlite URLs need a path
    if parsed.scheme == 'sqlite' and not parsed.path:
        raise ValueError("sqlite URLs must include a path")

    return True


def validate_redis_url(value: str | None, required: bool = False) -> bool:
    """Validate Redis URL format.

    Args:
        value: The Redis URL to validate
        required: Whether the URL is required

    Returns:
        True if valid

    Raises:
        ValueError: If validation fails
    """
    if not value or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValueError("redis_url is required")
        return True

    parsed = urlparse(value)

    # Must have a scheme and host
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("redis_url must include both scheme and host")

    valid_schemes = {'redis', 'rediss'}
    if parsed.scheme not in valid_schemes:
        raise ValueError(f"redis_url must use redis:// or rediss://")
    return True


def validate_cors_origins(origins: list[str] | None, is_production: bool = False) -> bool:
    """Validate CORS origins configuration.

    Args:
        origins: List of allowed CORS origins
        is_production: Whether running in production mode

    Returns:
        True if valid

    Raises:
        ValueError: If validation fails
    """
    if not origins:
        return True

    for origin in origins:
        # No wildcards allowed
        if '*' in origin:
            raise ValueError("cors_origins cannot contain wildcards")

        # No spaces allowed
        if ' ' in origin:
            raise ValueError("cors_origins cannot contain spaces")

        # Must have scheme
        if '://' not in origin:
            raise ValueError("cors_origins must include scheme (https://)")

        # Check for invalid characters (spaces, etc)
        try:
            parsed = urlparse(origin)
            if not parsed.netloc or not parsed.scheme:
                raise ValueError("cors_origins must be a valid URL with scheme and host")
        except Exception:
            raise ValueError("cors_origins must be a valid URL")

        # In production, enforce HTTPS
        if is_production and origin.startswith('http://'):
            raise ValueError("cors_origins must use HTTPS in production")

    return True


# Load and validate configuration
FLASK_ENV = os.getenv("FLASK_ENV", "development").strip().lower()
IS_PRODUCTION = FLASK_ENV == "production"

# PLAY_SERVICE_SECRET configuration
_pss_env = os.getenv("PLAY_SERVICE_SECRET", "").strip()
_pss_fallback = os.getenv("PLAY_SERVICE_SHARED_SECRET", "").strip()
PLAY_SERVICE_SECRET = _pss_env or _pss_fallback or "change-me-for-production"

# Validate secret based on environment
if IS_PRODUCTION and not _pss_env and not _pss_fallback:
    raise ValueError("PLAY_SERVICE_SECRET is required in production mode")
elif FLASK_ENV == "test" and not _pss_env and not _pss_fallback:
    warnings.warn("PLAY_SERVICE_SECRET not configured, using default insecure value", UserWarning)

# PLAY_SERVICE_INTERNAL_API_KEY configuration
_piak = os.getenv("PLAY_SERVICE_INTERNAL_API_KEY", "").strip()
PLAY_SERVICE_INTERNAL_API_KEY = _piak if _piak else None

GAME_CONTENT_SOURCE_URL = os.getenv("GAME_CONTENT_SOURCE_URL", "").strip()
