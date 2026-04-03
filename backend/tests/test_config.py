"""Tests for config and startup behavior."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from app import create_app
from app.config import TestingConfig


def test_create_app_raises_when_secret_key_missing():
    """create_app with config that has no SECRET_KEY and TESTING=False in production raises ValueError."""
    class NoSecretConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = None
        ENV = "production"

    with pytest.raises(ValueError, match="SECRET_KEY must be set in environment"):
        create_app(NoSecretConfig)


def test_create_app_accepts_testing_config():
    """create_app(TestingConfig) does not raise; testing config has fixed SECRET_KEY."""
    app = create_app(TestingConfig)
    assert app.config["TESTING"] is True
    assert app.config["SECRET_KEY"] is not None


def test_create_app_raises_when_secret_key_empty_and_not_testing():
    """Regression: empty SECRET_KEY with TESTING=False in production must raise (no insecure fallback)."""
    class EmptySecretConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = ""
        ENV = "production"

    with pytest.raises(ValueError, match="SECRET_KEY must be set in environment"):
        create_app(EmptySecretConfig)


def test_create_app_raises_when_jwt_secret_key_empty():
    """Startup validation: empty JWT_SECRET_KEY in production raises ValueError."""
    class NoJWTSecretConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = "valid-secret-key-for-testing-purposes"
        JWT_SECRET_KEY = ""
        ENV = "production"

    with pytest.raises(ValueError, match="JWT_SECRET_KEY must be at least 32 bytes"):
        create_app(NoJWTSecretConfig)


def test_create_app_raises_when_jwt_secret_key_too_short():
    """Startup validation: JWT_SECRET_KEY < 32 bytes in production raises ValueError."""
    class ShortJWTSecretConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = "valid-secret-key-for-testing-purposes"
        JWT_SECRET_KEY = "weak"
        ENV = "production"

    with pytest.raises(ValueError, match="JWT_SECRET_KEY must be at least 32 bytes"):
        create_app(ShortJWTSecretConfig)


def test_create_app_accepts_valid_jwt_secret_key():
    """Startup validation: JWT_SECRET_KEY with 32+ bytes is accepted."""
    class ValidJWTSecretConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = "valid-secret-key-for-testing-purposes"
        JWT_SECRET_KEY = "valid-jwt-secret-key-at-least-32-bytes-long"

    app = create_app(ValidJWTSecretConfig)
    assert app.config["JWT_SECRET_KEY"] == "valid-jwt-secret-key-at-least-32-bytes-long"


def test_create_app_raises_when_play_service_public_url_without_shared_secret():
    """Validates PLAY_SERVICE_SHARED_SECRET when PLAY_SERVICE_PUBLIC_URL is set."""
    class PlayServiceMissingSecretConfig(TestingConfig):
        PLAY_SERVICE_PUBLIC_URL = "https://play-service.example.com"
        PLAY_SERVICE_SHARED_SECRET = None

    with pytest.raises(ValueError, match="PLAY_SERVICE_SHARED_SECRET must be configured"):
        create_app(PlayServiceMissingSecretConfig)


def test_create_app_raises_when_play_service_public_url_empty_shared_secret():
    """Validates PLAY_SERVICE_SHARED_SECRET when PLAY_SERVICE_PUBLIC_URL is set (empty string)."""
    class PlayServiceEmptySecretConfig(TestingConfig):
        PLAY_SERVICE_PUBLIC_URL = "https://play-service.example.com"
        PLAY_SERVICE_SHARED_SECRET = ""

    with pytest.raises(ValueError, match="PLAY_SERVICE_SHARED_SECRET must be configured"):
        create_app(PlayServiceEmptySecretConfig)


def test_create_app_raises_when_play_service_public_url_whitespace_only_shared_secret():
    """Validates PLAY_SERVICE_SHARED_SECRET when PLAY_SERVICE_PUBLIC_URL is set (whitespace only)."""
    class PlayServiceWhitespaceSecretConfig(TestingConfig):
        PLAY_SERVICE_PUBLIC_URL = "https://play-service.example.com"
        PLAY_SERVICE_SHARED_SECRET = "   "

    with pytest.raises(ValueError, match="PLAY_SERVICE_SHARED_SECRET must be configured"):
        create_app(PlayServiceWhitespaceSecretConfig)


def test_create_app_succeeds_when_play_service_both_configured():
    """Succeeds when both PLAY_SERVICE_PUBLIC_URL and PLAY_SERVICE_SHARED_SECRET are set."""
    class PlayServiceFullConfig(TestingConfig):
        PLAY_SERVICE_PUBLIC_URL = "https://play-service.example.com"
        PLAY_SERVICE_SHARED_SECRET = "my-secret-key"

    app = create_app(PlayServiceFullConfig)
    assert app.config["PLAY_SERVICE_PUBLIC_URL"] == "https://play-service.example.com"
    assert app.config["PLAY_SERVICE_SHARED_SECRET"] == "my-secret-key"


def test_create_app_succeeds_when_play_service_public_url_not_set():
    """Succeeds when PLAY_SERVICE_PUBLIC_URL is not set (optional feature)."""
    class PlayServiceOptionalConfig(TestingConfig):
        PLAY_SERVICE_PUBLIC_URL = None
        PLAY_SERVICE_SHARED_SECRET = "my-secret-key"

    app = create_app(PlayServiceOptionalConfig)
    assert app.config["PLAY_SERVICE_SHARED_SECRET"] == "my-secret-key"


def test_create_app_succeeds_when_play_service_not_configured():
    """Succeeds when neither PLAY_SERVICE_PUBLIC_URL nor PLAY_SERVICE_SHARED_SECRET are set."""
    class NoPlayServiceConfig(TestingConfig):
        PLAY_SERVICE_PUBLIC_URL = None
        PLAY_SERVICE_SHARED_SECRET = None

    app = create_app(NoPlayServiceConfig)
    assert app.config.get("PLAY_SERVICE_PUBLIC_URL") is None or app.config.get("PLAY_SERVICE_PUBLIC_URL") == ""
    assert app.config.get("PLAY_SERVICE_SHARED_SECRET") is None or app.config.get("PLAY_SERVICE_SHARED_SECRET") == ""


# ============================================================================
# Email Verification Bypass Prevention Tests
# ============================================================================

def test_create_app_raises_when_prod_env_email_verification_disabled():
    """Production env with REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN=False raises ValueError."""
    class ProductionNoEmailVerificationConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = "valid-secret-key-for-testing-purposes"
        JWT_SECRET_KEY = "valid-jwt-secret-key-at-least-32-bytes-long"
        ENV = "production"
        REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN = False

    with pytest.raises(ValueError, match="Email verification MUST be enforced in production"):
        create_app(ProductionNoEmailVerificationConfig)


def test_create_app_raises_when_mail_enabled_email_verification_disabled():
    """Non-testing config with MAIL_ENABLED=True and email verification disabled raises."""
    class MailEnabledNoVerificationConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = "valid-secret-key-for-testing-purposes"
        JWT_SECRET_KEY = "valid-jwt-secret-key-at-least-32-bytes-long"
        ENV = "production"
        MAIL_ENABLED = True
        REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN = False

    with pytest.raises(ValueError, match="Email verification MUST be enforced in production"):
        create_app(MailEnabledNoVerificationConfig)


def test_create_app_succeeds_prod_with_email_verification_enabled():
    """Production env with REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN=True succeeds."""
    class ProductionWithEmailVerificationConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = "valid-secret-key-for-testing-purposes"
        JWT_SECRET_KEY = "valid-jwt-secret-key-at-least-32-bytes-long"
        ENV = "production"
        REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN = True

    app = create_app(ProductionWithEmailVerificationConfig)
    assert app.config["REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN"] is True


def test_create_app_succeeds_mail_enabled_with_email_verification():
    """Non-testing config with MAIL_ENABLED=True and verification enabled succeeds."""
    class MailEnabledWithVerificationConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = "valid-secret-key-for-testing-purposes"
        JWT_SECRET_KEY = "valid-jwt-secret-key-at-least-32-bytes-long"
        MAIL_ENABLED = True
        REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN = True

    app = create_app(MailEnabledWithVerificationConfig)
    assert app.config["REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN"] is True


def test_create_app_testing_config_allows_email_verification_disabled():
    """TestingConfig with REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN=False is allowed."""
    class TestingNoVerificationConfig(TestingConfig):
        TESTING = True
        REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN = False

    app = create_app(TestingNoVerificationConfig)
    assert app.config["TESTING"] is True
    assert app.config["REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN"] is False


def test_create_app_dev_mail_disabled_allows_verification_disabled():
    """Non-testing config with MAIL_ENABLED=False allows email verification disabled."""
    class DevNoMailConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = "valid-secret-key-for-testing-purposes"
        JWT_SECRET_KEY = "valid-jwt-secret-key-at-least-32-bytes-long"
        MAIL_ENABLED = False
        REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN = False

    app = create_app(DevNoMailConfig)
    assert app.config["MAIL_ENABLED"] is False
    assert app.config["REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN"] is False


# --- Config helpers & env-driven class body (subprocess for fresh import) ---


def test_env_bool_truthy_and_falsy():
    from app.config import env_bool

    assert env_bool("__ENV_BOOL_MISSING_XYZ__") is False
    assert env_bool("__ENV_BOOL_MISSING_XYZ__", default=True) is True
    for val in ("1", "true", "yes", "on"):
        with patch.dict(os.environ, {"ENV_BOOL_T": val}):
            assert env_bool("ENV_BOOL_T") is True
    for val in ("0", "false", "no", "off", ""):
        with patch.dict(os.environ, {"ENV_BOOL_F": val}):
            assert env_bool("ENV_BOOL_F") is False


def test_parse_cors_origins_empty_and_list():
    from app.config import _parse_cors_origins

    with patch.dict(os.environ, {"CORS_ORIGINS": ""}, clear=False):
        assert _parse_cors_origins() is None
    with patch.dict(os.environ, {"CORS_ORIGINS": " https://a.test , ,https://b.test "}, clear=False):
        assert _parse_cors_origins() == ["https://a.test", "https://b.test"]


def test_validate_service_url_accepts_rejects_and_warns():
    from app.config import _validate_service_url

    assert _validate_service_url(None) is None
    assert _validate_service_url("") is None
    assert _validate_service_url("  ") is None  # whitespace-only after strip => None, no warning
    assert _validate_service_url("http://internal:8080") == "http://internal:8080"
    assert _validate_service_url(" https://x.test/path ") == "https://x.test/path"
    with pytest.warns(UserWarning, match=r"Invalid service URL .*ftp://bad"):
        assert _validate_service_url("ftp://bad") is None


def _run_fresh_config(extra_env: dict[str, str], assertion_src: str) -> None:
    backend = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    for k in (
        "GAME_TICKET_TTL_SECONDS",
        "DEV_SECRETS_OK",
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "DATABASE_URI",
    ):
        env.pop(k, None)
    env.update(extra_env)
    env["PYTHONPATH"] = str(backend)
    code = "import app.config as cfg\n" + assertion_src + "\n"
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(backend),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)


def test_config_game_ticket_ttl_invalid_defaults():
    _run_fresh_config(
        {"GAME_TICKET_TTL_SECONDS": "not-an-int"},
        "assert cfg.Config.GAME_TICKET_TTL_SECONDS == 300",
    )


def test_config_game_ticket_ttl_clamped_high():
    _run_fresh_config(
        {"GAME_TICKET_TTL_SECONDS": "999999"},
        "assert cfg.Config.GAME_TICKET_TTL_SECONDS == 86400",
    )


def test_development_config_dev_secrets_fallback():
    _run_fresh_config(
        {
            "DEV_SECRETS_OK": "1",
            "SECRET_KEY": "",
            "JWT_SECRET_KEY": "",
        },
        "assert cfg.DevelopmentConfig.SECRET_KEY == 'dev-secret-do-not-use-in-production'\n"
        "assert 'dev' in cfg.DevelopmentConfig.JWT_SECRET_KEY.lower()\n",
    )


def test_play_service_internal_api_key_module_default():
    _run_fresh_config(
        {"PLAY_SERVICE_INTERNAL_API_KEY": "  key-from-env  "},
        "import app.config as c2\n"
        "assert c2.PLAY_SERVICE_INTERNAL_API_KEY == 'key-from-env'\n",
    )
