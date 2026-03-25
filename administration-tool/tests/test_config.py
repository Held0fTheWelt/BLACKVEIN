import pytest
import sys
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import validate_secret_key, validate_service_url


class TestConfigValidation:
    """Unit tests for configuration validation functions."""

    @pytest.mark.unit
    def test_validate_secret_key_rejects_empty(self):
        """Test that empty or None secret keys raise ValueError."""
        # Test with empty string
        with pytest.raises(ValueError, match="secret_key"):
            validate_secret_key("", is_production=True)

        # Test with None
        with pytest.raises(ValueError, match="secret_key"):
            validate_secret_key(None, is_production=True)

    @pytest.mark.unit
    def test_validate_secret_key_accepts_long_in_production(self):
        """Test that long secret keys (32+ chars) are accepted in production."""
        # Valid 32-character key
        valid_key = "a" * 32
        result = validate_secret_key(valid_key, is_production=True)
        assert result is True

        # Valid 64-character key
        valid_key_long = "b" * 64
        result = validate_secret_key(valid_key_long, is_production=True)
        assert result is True

        # Valid key with mixed characters
        valid_key_mixed = "AbCdEfGhIjKlMnOpQrStUvWxYz12345678"
        result = validate_secret_key(valid_key_mixed, is_production=True)
        assert result is True

    @pytest.mark.unit
    def test_validate_secret_key_accepts_short_in_test(self):
        """Test that short secret keys are accepted when not in production."""
        # Short key should be accepted in test mode
        short_key = "test"
        result = validate_secret_key(short_key, is_production=False)
        assert result is True

        # Even a single character should work in test mode
        single_char = "x"
        result = validate_secret_key(single_char, is_production=False)
        assert result is True

        # Empty string should still fail even in test mode
        with pytest.raises(ValueError, match="secret_key"):
            validate_secret_key("", is_production=False)

    @pytest.mark.unit
    def test_validate_service_url_rejects_invalid_scheme(self):
        """Test that URLs with invalid schemes raise ValueError."""
        # FTP scheme should be rejected
        with pytest.raises(ValueError, match="service_url"):
            validate_service_url("ftp://example.com", required=True)

        # HTTP without proper format should be rejected
        with pytest.raises(ValueError, match="service_url"):
            validate_service_url("http://", required=True)

        # Invalid scheme should be rejected
        with pytest.raises(ValueError, match="service_url"):
            validate_service_url("mailto://example.com", required=True)

        # Only scheme without host should be rejected
        with pytest.raises(ValueError, match="service_url"):
            validate_service_url("https://", required=True)

    @pytest.mark.unit
    def test_validate_service_url_rejects_missing_required(self):
        """Test that missing required URLs raise ValueError."""
        # None value with required=True should raise
        with pytest.raises(ValueError, match="service_url"):
            validate_service_url(None, required=True)

        # Empty string with required=True should raise
        with pytest.raises(ValueError, match="service_url"):
            validate_service_url("", required=True)

        # Whitespace only with required=True should raise
        with pytest.raises(ValueError, match="service_url"):
            validate_service_url("   ", required=True)

        # Empty string with required=False should not raise
        result = validate_service_url("", required=False)
        assert result is True

        # None with required=False should not raise
        result = validate_service_url(None, required=False)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
