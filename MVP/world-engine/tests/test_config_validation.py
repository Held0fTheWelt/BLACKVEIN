"""Tests for configuration validation functions."""
import pytest
from urllib.parse import urlparse

from app.config import (
    validate_play_service_secret,
    validate_database_url,
    validate_redis_url,
    validate_cors_origins,
)


class TestValidatePlayServiceSecret:
    """Tests for validate_play_service_secret."""

    @pytest.mark.unit
    def test_validate_play_service_secret_rejects_empty(self):
        """Test that empty or None secret raises ValueError."""
        # Test with empty string
        with pytest.raises(ValueError, match="play_service_secret"):
            validate_play_service_secret("", is_production=True)

        # Test with None
        with pytest.raises(ValueError, match="play_service_secret"):
            validate_play_service_secret(None, is_production=True)

        # Test with whitespace only
        with pytest.raises(ValueError, match="play_service_secret"):
            validate_play_service_secret("   ", is_production=True)

    @pytest.mark.unit
    def test_validate_play_service_secret_requires_32_bytes_in_production(self):
        """Test that 32+ byte secrets are required in production."""
        # Too short in production should raise
        with pytest.raises(ValueError, match="play_service_secret"):
            validate_play_service_secret("short_secret", is_production=True)

        # Exactly 32 bytes should pass
        valid_secret_32 = "a" * 32
        result = validate_play_service_secret(valid_secret_32, is_production=True)
        assert result is True

        # 64 bytes should pass
        valid_secret_64 = "b" * 64
        result = validate_play_service_secret(valid_secret_64, is_production=True)
        assert result is True

        # Mixed characters with 32+ bytes should pass
        valid_secret_mixed = "SecretKey1234567890ABCDEFGHIJKLMN"
        result = validate_play_service_secret(valid_secret_mixed, is_production=True)
        assert result is True

    @pytest.mark.unit
    def test_validate_play_service_secret_accepts_short_in_test(self):
        """Test that short secrets are accepted in test mode."""
        # Short secret in test mode should pass
        short_secret = "test"
        result = validate_play_service_secret(short_secret, is_production=False)
        assert result is True

        # Single character in test mode should pass
        single_char = "x"
        result = validate_play_service_secret(single_char, is_production=False)
        assert result is True

        # Empty string should still fail even in test mode
        with pytest.raises(ValueError, match="play_service_secret"):
            validate_play_service_secret("", is_production=False)


class TestValidateDatabaseUrl:
    """Tests for validate_database_url."""

    @pytest.mark.unit
    def test_validate_database_url_requires_valid_scheme(self):
        """Test that database URLs must have valid schemes."""
        # Valid PostgreSQL URL
        result = validate_database_url("postgresql://user:pass@localhost/db")
        assert result is True

        # Valid SQLite URL
        result = validate_database_url("sqlite:///path/to/db.sqlite")
        assert result is True

        # Valid MySQL URL
        result = validate_database_url("mysql+pymysql://user:pass@localhost/db")
        assert result is True

    @pytest.mark.unit
    def test_validate_database_url_rejects_invalid_schemes(self):
        """Test that invalid database schemes raise ValueError."""
        # FTP scheme should be rejected
        with pytest.raises(ValueError, match="database_url"):
            validate_database_url("ftp://example.com/db")

        # HTTP scheme should be rejected
        with pytest.raises(ValueError, match="database_url"):
            validate_database_url("http://example.com/db")

        # No scheme should be rejected
        with pytest.raises(ValueError, match="database_url"):
            validate_database_url("localhost/db")

        # Missing host (just scheme)
        with pytest.raises(ValueError, match="database_url"):
            validate_database_url("postgresql://")

    @pytest.mark.unit
    def test_validate_database_url_required_parameter(self):
        """Test required parameter behavior for database_url."""
        # required=True with None should raise
        with pytest.raises(ValueError, match="database_url"):
            validate_database_url(None, required=True)

        # required=True with empty string should raise
        with pytest.raises(ValueError, match="database_url"):
            validate_database_url("", required=True)

        # required=False with None should return True
        result = validate_database_url(None, required=False)
        assert result is True

        # required=False with empty string should return True
        result = validate_database_url("", required=False)
        assert result is True


class TestValidateRedisUrl:
    """Tests for validate_redis_url."""

    @pytest.mark.unit
    def test_validate_redis_url_accepts_valid_formats(self):
        """Test that valid Redis URLs are accepted."""
        # Standard redis:// URL
        result = validate_redis_url("redis://localhost:6379/0")
        assert result is True

        # Redis with password
        result = validate_redis_url("redis://:password@localhost:6379/0")
        assert result is True

        # rediss:// (Redis with TLS)
        result = validate_redis_url("rediss://localhost:6379/0")
        assert result is True

        # Different host and port
        result = validate_redis_url("redis://redis.example.com:6380/1")
        assert result is True

    @pytest.mark.unit
    def test_validate_redis_url_allows_none_when_not_required(self):
        """Test that None is allowed when not required."""
        # None with required=False should pass
        result = validate_redis_url(None, required=False)
        assert result is True

        # Empty string with required=False should pass
        result = validate_redis_url("", required=False)
        assert result is True

        # Whitespace with required=False should pass
        result = validate_redis_url("   ", required=False)
        assert result is True

    @pytest.mark.unit
    def test_validate_redis_url_rejects_invalid_when_required(self):
        """Test that invalid URLs raise when required."""
        # Invalid scheme when required=True
        with pytest.raises(ValueError, match="redis_url"):
            validate_redis_url("http://localhost:6379", required=True)

        # None when required=True should raise
        with pytest.raises(ValueError, match="redis_url"):
            validate_redis_url(None, required=True)

        # Empty when required=True should raise
        with pytest.raises(ValueError, match="redis_url"):
            validate_redis_url("", required=True)


class TestValidateCorsOrigins:
    """Tests for validate_cors_origins."""

    @pytest.mark.unit
    def test_validate_cors_origins_rejects_wildcards(self):
        """Test that wildcard origins are rejected."""
        with pytest.raises(ValueError, match="cors_origins"):
            validate_cors_origins(["*"], is_production=True)

        with pytest.raises(ValueError, match="cors_origins"):
            validate_cors_origins(["https://*"], is_production=True)

        with pytest.raises(ValueError, match="cors_origins"):
            validate_cors_origins(["https://example.com", "*"], is_production=True)

    @pytest.mark.unit
    def test_validate_cors_origins_requires_https_in_production(self):
        """Test that HTTP origins are rejected in production."""
        # HTTP should be rejected in production
        with pytest.raises(ValueError, match="cors_origins"):
            validate_cors_origins(["http://example.com"], is_production=True)

        # HTTPS should be accepted in production
        result = validate_cors_origins(["https://example.com"], is_production=True)
        assert result is True

        # Multiple HTTPS origins should be accepted
        result = validate_cors_origins(
            ["https://example.com", "https://app.example.com"],
            is_production=True,
        )
        assert result is True

    @pytest.mark.unit
    def test_validate_cors_origins_allows_localhost_in_dev(self):
        """Test that localhost is allowed in development."""
        # HTTP localhost should be rejected in production
        with pytest.raises(ValueError, match="cors_origins"):
            validate_cors_origins(["http://localhost:3000"], is_production=True)

        # HTTP localhost should be accepted in dev
        result = validate_cors_origins(["http://localhost:3000"], is_production=False)
        assert result is True

        # 127.0.0.1 should be accepted in dev
        result = validate_cors_origins(["http://127.0.0.1:3000"], is_production=False)
        assert result is True

        # HTTPS localhost should be accepted in both
        result = validate_cors_origins(["https://localhost:3000"], is_production=True)
        assert result is True

        result = validate_cors_origins(["https://localhost:3000"], is_production=False)
        assert result is True

    @pytest.mark.unit
    def test_validate_cors_origins_rejects_invalid_urls(self):
        """Test that invalid URLs are rejected."""
        # Missing scheme
        with pytest.raises(ValueError, match="cors_origins"):
            validate_cors_origins(["example.com"], is_production=True)

        # Invalid characters
        with pytest.raises(ValueError, match="cors_origins"):
            validate_cors_origins(["https://exa mple.com"], is_production=True)

        # Just a scheme
        with pytest.raises(ValueError, match="cors_origins"):
            validate_cors_origins(["https://"], is_production=True)

    @pytest.mark.unit
    def test_validate_cors_origins_allows_empty_list(self):
        """Test that empty list is allowed."""
        result = validate_cors_origins([])
        assert result is True
