"""Tests for config and startup behavior."""
import pytest

from app import create_app
from app.config import TestingConfig


def test_create_app_raises_when_secret_key_missing():
    """create_app with config that has no SECRET_KEY and not TESTING raises ValueError."""
    class NoSecretConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = None

    with pytest.raises(ValueError, match="SECRET_KEY must be set"):
        create_app(NoSecretConfig)


def test_create_app_accepts_testing_config():
    """create_app(TestingConfig) does not raise; testing config has fixed SECRET_KEY."""
    app = create_app(TestingConfig)
    assert app.config["TESTING"] is True
    assert app.config["SECRET_KEY"] is not None


def test_create_app_raises_when_secret_key_empty_and_not_testing():
    """Regression: empty SECRET_KEY with TESTING=False must raise (no insecure fallback)."""
    class EmptySecretConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = ""

    with pytest.raises(ValueError, match="SECRET_KEY must be set"):
        create_app(EmptySecretConfig)


def test_create_app_raises_when_jwt_secret_key_empty():
    """Startup validation: empty JWT_SECRET_KEY raises ValueError."""
    class NoJWTSecretConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = "valid-secret-key-for-testing-purposes"
        JWT_SECRET_KEY = ""

    with pytest.raises(ValueError, match="JWT_SECRET_KEY must be at least 32 bytes"):
        create_app(NoJWTSecretConfig)


def test_create_app_raises_when_jwt_secret_key_too_short():
    """Startup validation: JWT_SECRET_KEY < 32 bytes raises ValueError."""
    class ShortJWTSecretConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = "valid-secret-key-for-testing-purposes"
        JWT_SECRET_KEY = "weak"

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
