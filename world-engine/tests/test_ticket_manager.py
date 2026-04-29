"""Comprehensive ticket manager tests for World Engine.

WAVE 5: Comprehensive ticket handling and validation.
Tests ensure TicketManager correctly issues, verifies, and rejects tickets.

Mark: @pytest.mark.unit, @pytest.mark.contract, @pytest.mark.security
"""

from __future__ import annotations

import base64
import json
import time
from unittest.mock import patch

import pytest

from app.auth.tickets import TicketManager, TicketError


class TestTicketManagerBasicContract:
    """Test basic ticket manager contract."""

    @pytest.mark.unit
    def test_ticket_manager_instantiation_with_secret(self):
        """TicketManager should accept custom secret during instantiation."""
        manager = TicketManager("custom-secret")
        assert manager.secret == b"custom-secret"

    @pytest.mark.unit
    def test_ticket_manager_uses_global_secret_when_none_provided(self):
        """TicketManager should use global PLAY_SERVICE_SECRET when not provided."""
        # When global secret is available, it should be used
        with patch("app.auth.tickets.PLAY_SERVICE_SECRET", "global-test-secret"):
            manager = TicketManager()
            assert manager.secret is not None
            assert isinstance(manager.secret, bytes)
            assert manager.secret == b"global-test-secret"

    @pytest.mark.unit
    def test_ticket_manager_with_explicit_secret_overrides_global(self):
        """Explicit secret should override global PLAY_SERVICE_SECRET."""
        manager1 = TicketManager("secret1")
        manager2 = TicketManager("secret2")

        # They should have different secrets
        assert manager1.secret != manager2.secret

    @pytest.mark.contract
    def test_ticket_issue_and_verify_roundtrip(self):
        """Valid ticket should be issued and verified successfully."""
        manager = TicketManager("test-secret-for-roundtrip")

        payload = {
            "run_id": "run-123",
            "participant_id": "p-456",
            "account_id": "acct-789",
            "character_id": "char-999",
            "display_name": "TestPlayer",
            "role_id": "citizen",
        }

        token = manager.issue(payload, ttl_seconds=3600)

        # Token should be a string
        assert isinstance(token, str)
        assert len(token) > 0

        # Should be verifiable
        verified_payload = manager.verify(token)

        # All original fields should be present
        for key, value in payload.items():
            assert verified_payload[key] == value

        # Should have iat and exp
        assert "iat" in verified_payload
        assert "exp" in verified_payload
        assert verified_payload["exp"] > verified_payload["iat"]


class TestTicketPayloadPreservation:
    """Test that ticket payloads are correctly preserved."""

    @pytest.mark.unit
    @pytest.mark.parametrize("payload_data", [
        {"run_id": "r1", "participant_id": "p1"},
        {"run_id": "r1", "participant_id": "p1", "account_id": "a1", "display_name": "User"},
        {"run_id": "r1", "participant_id": "p1", "extra_field": "should-be-preserved"},
        {"run_id": "r1", "participant_id": "p1", "numeric_field": 42, "bool_field": True},
    ])
    def test_various_payloads_preserved(self, payload_data):
        """Various payload structures should be correctly preserved."""
        manager = TicketManager("test-secret")
        token = manager.issue(payload_data, ttl_seconds=3600)
        verified = manager.verify(token)

        for key, value in payload_data.items():
            assert verified[key] == value, f"Field {key} not preserved"

    @pytest.mark.unit
    def test_payload_with_unicode_preserved(self):
        """Payloads with unicode characters should be preserved."""
        manager = TicketManager("test-secret")

        payload = {
            "run_id": "r1",
            "participant_id": "p1",
            "display_name": "Тестовый Игрок",  # Russian characters
        }

        token = manager.issue(payload)
        verified = manager.verify(token)

        assert verified["display_name"] == "Тестовый Игрок"

    @pytest.mark.unit
    def test_payload_with_special_characters_preserved(self):
        """Payloads with special JSON characters should be preserved."""
        manager = TicketManager("test-secret")

        payload = {
            "run_id": "r1",
            "participant_id": "p1",
            "notes": "Test with \"quotes\" and \\backslashes\\ and \nnewlines",
        }

        token = manager.issue(payload)
        verified = manager.verify(token)

        assert verified["notes"] == payload["notes"]


class TestTicketMalformedHandling:
    """Test that malformed tickets are handled cleanly."""

    @pytest.mark.unit
    @pytest.mark.security
    @pytest.mark.parametrize("malformed_token", [
        "not-a-valid-ticket",
        "aW52YWxpZA==",  # base64 "invalid" without signature
        "",  # empty
        "!!!invalid-base64!!!",
        "." * 100,  # just dots
        "missingdot",  # no dot separator
        "nodotshere",  # no signature separator
        "single.dot",  # just one dot - incomplete
        b"not-a-string",  # not string type
    ])
    def test_malformed_token_raises_ticket_error(self, malformed_token):
        """Malformed tokens should raise TicketError with 'Malformed' message."""
        manager = TicketManager("test-secret")

        with pytest.raises(TicketError, match="Malformed ticket"):
            manager.verify(malformed_token)

    @pytest.mark.unit
    @pytest.mark.security
    def test_token_without_base64_encoding_rejected(self):
        """Token not in base64 format should be rejected."""
        manager = TicketManager("test-secret")

        # Random bytes that aren't valid base64
        with pytest.raises(TicketError, match="Malformed ticket"):
            manager.verify("@#$%^&*()")

    @pytest.mark.unit
    @pytest.mark.security
    def test_token_with_no_dot_separator_rejected(self):
        """Token without dot separator should be rejected."""
        manager = TicketManager("test-secret")

        # Valid base64 but no signature separator
        valid_base64_no_sig = base64.urlsafe_b64encode(b"test data").decode("ascii")

        with pytest.raises(TicketError, match="Malformed ticket"):
            manager.verify(valid_base64_no_sig)


class TestTicketSignatureValidation:
    """Test that signatures are properly validated."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_invalid_signature_rejected(self):
        """Token with invalid signature should be rejected."""
        manager = TicketManager("test-secret")

        # Create a valid token
        token = manager.issue({"run_id": "r1", "participant_id": "p1"})

        # Tamper with the signature
        decoded = base64.urlsafe_b64decode(token.encode("ascii"))
        raw, sig = decoded.rsplit(b".", 1)

        # Change the signature
        tampered_sig = b"deadbeef" * 8  # 64 hex chars (256-bit hash)
        tampered_decoded = raw + b"." + tampered_sig
        tampered_token = base64.urlsafe_b64encode(tampered_decoded).decode("ascii")

        with pytest.raises(TicketError, match="Invalid signature"):
            manager.verify(tampered_token)

    @pytest.mark.unit
    @pytest.mark.security
    def test_wrong_secret_rejects_token(self):
        """Token signed with different secret should be rejected."""
        manager1 = TicketManager("secret1")
        manager2 = TicketManager("secret2")

        token = manager1.issue({"run_id": "r1", "participant_id": "p1"})

        # Different secret should fail verification
        with pytest.raises(TicketError, match="Invalid signature"):
            manager2.verify(token)

    @pytest.mark.unit
    @pytest.mark.security
    def test_modified_payload_rejects_token(self):
        """Token with modified payload should be rejected."""
        manager = TicketManager("test-secret")

        token = manager.issue({"run_id": "r1", "participant_id": "p1"})

        # Decode, modify payload, re-encode with same signature
        decoded = base64.urlsafe_b64decode(token.encode("ascii"))
        raw, sig = decoded.rsplit(b".", 1)

        # Parse and modify payload
        payload = json.loads(raw.decode("utf-8"))
        payload["participant_id"] = "p-modified"

        # Re-encode with modified payload but original signature
        modified_raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        modified_token = base64.urlsafe_b64encode(modified_raw + b"." + sig).decode("ascii")

        with pytest.raises(TicketError, match="Invalid signature"):
            manager.verify(modified_token)


class TestTicketExpiration:
    """Test ticket expiration validation."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_expired_ticket_rejected(self):
        """Ticket past expiration time should be rejected."""
        manager = TicketManager("test-secret")

        # Issue with -1 second TTL (already expired)
        token = manager.issue({"run_id": "r1", "participant_id": "p1"}, ttl_seconds=-1)

        with pytest.raises(TicketError, match="Expired ticket"):
            manager.verify(token)

    @pytest.mark.unit
    def test_ticket_with_zero_ttl_expires_immediately(self):
        """Ticket with 0 second TTL should expire as soon as time advances."""
        manager = TicketManager("test-secret")

        with patch("app.auth.tickets.time.time") as mock_time:
            # Set initial time
            mock_time.return_value = 1000.0

            token = manager.issue({"run_id": "r1", "participant_id": "p1"}, ttl_seconds=0)
            # Token exp will be 1000 + 0 = 1000, iat will be 1000

            # At time 1000, exp (1000) is not < 1000, so still valid
            payload = manager.verify(token)
            assert payload is not None

            # At time 1001, exp (1000) < 1001, so expired
            mock_time.return_value = 1001.0
            with pytest.raises(TicketError, match="Expired ticket"):
                manager.verify(token)

    @pytest.mark.unit
    @pytest.mark.parametrize("ttl_seconds", [1, 10, 100, 3600])
    def test_valid_ttl_ticket_verified(self, ttl_seconds):
        """Tickets with valid TTL should be verified successfully."""
        manager = TicketManager("test-secret")

        token = manager.issue({"run_id": "r1", "participant_id": "p1"}, ttl_seconds=ttl_seconds)

        # Should not raise
        payload = manager.verify(token)
        assert payload["run_id"] == "r1"

    @pytest.mark.unit
    def test_ticket_expiration_uses_time_for_comparison(self):
        """Ticket expiration should use time.time() for comparison."""
        manager = TicketManager("test-secret")

        with patch("app.auth.tickets.time.time") as mock_time:
            # Set initial time
            mock_time.return_value = 1000.0

            # Issue ticket with 100 second TTL
            token = manager.issue({"run_id": "r1", "participant_id": "p1"}, ttl_seconds=100)

            # Verify should work at issue time
            payload = manager.verify(token)
            assert payload is not None

            # Advance time past expiration
            mock_time.return_value = 1101.0

            # Now should be expired
            with pytest.raises(TicketError, match="Expired ticket"):
                manager.verify(token)


class TestTicketMissingFields:
    """Test handling of missing required fields in payload."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_token_missing_exp_field_raises_error(self):
        """Token missing 'exp' field should raise error during verification."""
        manager = TicketManager("test-secret")

        # Manually construct token without exp field
        payload = {"run_id": "r1", "participant_id": "p1", "iat": int(time.time())}
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

        import hmac
        import hashlib
        sig = hmac.new(manager.secret, raw, hashlib.sha256).hexdigest().encode("ascii")
        token = base64.urlsafe_b64encode(raw + b"." + sig).decode("ascii")

        # Should fail when trying to check expiration
        with pytest.raises((TicketError, KeyError)):
            manager.verify(token)

    @pytest.mark.unit
    @pytest.mark.security
    def test_token_missing_iat_field_accepted(self):
        """Token missing 'iat' field should still be verifiable (iat not checked)."""
        manager = TicketManager("test-secret")

        # iat is issued but not required for verification
        payload = {"run_id": "r1", "participant_id": "p1", "exp": int(time.time()) + 3600}
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

        import hmac
        import hashlib
        sig = hmac.new(manager.secret, raw, hashlib.sha256).hexdigest().encode("ascii")
        token = base64.urlsafe_b64encode(raw + b"." + sig).decode("ascii")

        # Should verify successfully
        verified = manager.verify(token)
        assert verified["run_id"] == "r1"


class TestTicketWrongClaimStructure:
    """Test handling of wrongly structured claims."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_token_with_non_dict_payload_raises_error(self):
        """Token with non-dict payload should raise error."""
        manager = TicketManager("test-secret")

        # Create token with non-dict payload (list instead)
        payload = ["not", "a", "dict"]
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

        import hmac
        import hashlib
        sig = hmac.new(manager.secret, raw, hashlib.sha256).hexdigest().encode("ascii")
        token = base64.urlsafe_b64encode(raw + b"." + sig).decode("ascii")

        # Should fail when trying to access dict keys
        with pytest.raises((TicketError, KeyError, TypeError)):
            manager.verify(token)

    @pytest.mark.unit
    @pytest.mark.security
    def test_token_with_invalid_json_raises_error(self):
        """Token with invalid JSON should raise error during parsing."""
        manager = TicketManager("test-secret")

        # Raw bytes that aren't valid JSON
        raw = b"not valid json {"

        import hmac
        import hashlib
        sig = hmac.new(manager.secret, raw, hashlib.sha256).hexdigest().encode("ascii")
        token = base64.urlsafe_b64encode(raw + b"." + sig).decode("ascii")

        # Should fail on JSON parsing - either as JSONDecodeError or TicketError
        with pytest.raises((TicketError, json.JSONDecodeError)):
            manager.verify(token)

    @pytest.mark.unit
    @pytest.mark.security
    def test_token_with_exp_not_integer_fails(self):
        """Token with exp as non-integer should fail gracefully."""
        manager = TicketManager("test-secret")

        # Create token with exp as string instead of int
        payload = {"run_id": "r1", "exp": "not-an-integer"}
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

        import hmac
        import hashlib
        sig = hmac.new(manager.secret, raw, hashlib.sha256).hexdigest().encode("ascii")
        token = base64.urlsafe_b64encode(raw + b"." + sig).decode("ascii")

        # Should fail when converting exp to int
        with pytest.raises((TicketError, ValueError, TypeError)):
            manager.verify(token)


class TestTicketMultipleIndependent:
    """Test multiple independent tickets."""

    @pytest.mark.unit
    def test_multiple_tickets_coexist_independently(self):
        """Multiple issued tickets should be independent."""
        manager = TicketManager("test-secret")

        payload1 = {"run_id": "r1", "participant_id": "p1"}
        payload2 = {"run_id": "r2", "participant_id": "p2"}
        payload3 = {"run_id": "r3", "participant_id": "p3"}

        token1 = manager.issue(payload1)
        token2 = manager.issue(payload2)
        token3 = manager.issue(payload3)

        # All should verify independently
        verified1 = manager.verify(token1)
        assert verified1["run_id"] == "r1"

        verified2 = manager.verify(token2)
        assert verified2["run_id"] == "r2"

        verified3 = manager.verify(token3)
        assert verified3["run_id"] == "r3"

        # Swapping signatures should fail
        decoded1 = base64.urlsafe_b64decode(token1.encode("ascii"))
        decoded2 = base64.urlsafe_b64decode(token2.encode("ascii"))

        raw1, sig1 = decoded1.rsplit(b".", 1)
        raw2, sig2 = decoded2.rsplit(b".", 1)

        # Token1 raw with token2 signature
        mixed = base64.urlsafe_b64encode(raw1 + b"." + sig2).decode("ascii")

        with pytest.raises(TicketError, match="Invalid signature"):
            manager.verify(mixed)


class TestTicketTtlParameter:
    """Test TTL parameter controls expiration correctly."""

    @pytest.mark.unit
    @pytest.mark.parametrize("ttl_seconds", [1, 10, 60, 3600, 86400])
    def test_ttl_controls_expiration_time(self, ttl_seconds):
        """Different TTL values should result in different expiration times."""
        manager = TicketManager("test-secret")

        with patch("app.auth.tickets.time.time") as mock_time:
            mock_time.return_value = 1000.0

            token = manager.issue({"run_id": "r1", "participant_id": "p1"}, ttl_seconds=ttl_seconds)

            # Decode and check exp
            decoded = base64.urlsafe_b64decode(token.encode("ascii"))
            raw, sig = decoded.rsplit(b".", 1)
            payload = json.loads(raw.decode("utf-8"))

            # exp should be iat + ttl
            expected_exp = 1000 + ttl_seconds
            assert payload["exp"] == expected_exp

    @pytest.mark.unit
    def test_default_ttl_is_3600_seconds(self):
        """Default TTL should be 3600 seconds (1 hour)."""
        manager = TicketManager("test-secret")

        with patch("app.auth.tickets.time.time") as mock_time:
            mock_time.return_value = 1000.0

            # Issue without specifying TTL
            token = manager.issue({"run_id": "r1", "participant_id": "p1"})

            decoded = base64.urlsafe_b64decode(token.encode("ascii"))
            raw, sig = decoded.rsplit(b".", 1)
            payload = json.loads(raw.decode("utf-8"))

            # Should be 1000 + 3600 = 4600
            assert payload["exp"] == 4600


class TestTicketDeterminism:
    """Test ticket generation and verification determinism."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_same_payload_twice_with_different_times_gives_different_tokens(self):
        """Same payload issued at different times should give different tokens (due to iat/exp)."""
        manager = TicketManager("test-secret")

        payload = {"run_id": "r1", "participant_id": "p1"}

        with patch("app.auth.tickets.time.time") as mock_time:
            # Issue at time 1000
            mock_time.return_value = 1000.0
            token1 = manager.issue(payload, ttl_seconds=100)

            # Issue at time 1001 (different iat)
            mock_time.return_value = 1001.0
            token2 = manager.issue(payload, ttl_seconds=100)

            # Tokens should be different (iat/exp will differ)
            assert token1 != token2

            # Both should verify
            mock_time.return_value = 1002.0
            verified1 = manager.verify(token1)
            verified2 = manager.verify(token2)

            assert verified1["run_id"] == verified2["run_id"]
            # iat/exp will be different
            assert verified1["iat"] < verified2["iat"]  # Second issued later

    @pytest.mark.unit
    def test_identical_payload_with_same_time_gives_same_token(self):
        """With same iat/exp, identical payloads should give same signature."""
        manager = TicketManager("test-secret")

        payload = {"run_id": "r1", "participant_id": "p1"}

        with patch("app.auth.tickets.time.time") as mock_time:
            mock_time.return_value = 1000.0

            token1 = manager.issue(payload, ttl_seconds=100)
            token2 = manager.issue(payload, ttl_seconds=100)

            # With same time and ttl, tokens should be identical
            assert token1 == token2


class TestTicketCustomSecret:
    """Test custom secret handling."""

    @pytest.mark.unit
    def test_custom_secret_in_constructor(self):
        """Custom secret passed to constructor should be used."""
        manager = TicketManager("my-custom-secret")

        token = manager.issue({"run_id": "r1", "participant_id": "p1"})

        # Should verify with same manager
        payload = manager.verify(token)
        assert payload["run_id"] == "r1"

    @pytest.mark.unit
    def test_custom_secret_not_interchangeable(self):
        """Tokens signed with one secret should not verify with another."""
        manager1 = TicketManager("secret1")
        manager2 = TicketManager("secret2")

        token = manager1.issue({"run_id": "r1", "participant_id": "p1"})

        with pytest.raises(TicketError, match="Invalid signature"):
            manager2.verify(token)

    @pytest.mark.unit
    @pytest.mark.security
    def test_none_secret_uses_global_when_available(self):
        """Passing None as secret should use global PLAY_SERVICE_SECRET if valid."""
        with patch("app.auth.tickets.PLAY_SERVICE_SECRET", "fallback-secret"):
            manager = TicketManager(None)

            # Should not raise during construction
            assert manager.secret is not None
            assert isinstance(manager.secret, bytes)
            assert manager.secret == b"fallback-secret"

    @pytest.mark.unit
    @pytest.mark.security
    def test_none_secret_with_missing_global_fails(self):
        """Passing None as secret should fail if global PLAY_SERVICE_SECRET is missing."""
        with patch("app.auth.tickets.PLAY_SERVICE_SECRET", None):
            with pytest.raises(TicketError, match="PLAY_SERVICE_SECRET is required and cannot be empty"):
                TicketManager(None)

    @pytest.mark.unit
    @pytest.mark.security
    def test_none_secret_with_blank_global_fails(self):
        """Passing None as secret should fail if global PLAY_SERVICE_SECRET is blank."""
        with patch("app.auth.tickets.PLAY_SERVICE_SECRET", ""):
            with pytest.raises(TicketError, match="PLAY_SERVICE_SECRET is required and cannot be empty"):
                TicketManager(None)

    @pytest.mark.unit
    @pytest.mark.security
    def test_none_secret_with_whitespace_global_fails(self):
        """Passing None as secret should fail if global PLAY_SERVICE_SECRET is whitespace-only."""
        with patch("app.auth.tickets.PLAY_SERVICE_SECRET", "   \t\n  "):
            with pytest.raises(TicketError, match="PLAY_SERVICE_SECRET is required and cannot be empty"):
                TicketManager(None)

    @pytest.mark.unit
    @pytest.mark.security
    def test_empty_string_secret_fails(self):
        """Passing empty string as secret should fail explicitly."""
        with pytest.raises(TicketError, match="Secret cannot be None or blank"):
            TicketManager("")

    @pytest.mark.unit
    @pytest.mark.security
    def test_blank_secret_fails(self):
        """Passing whitespace-only string as secret should fail explicitly."""
        with pytest.raises(TicketError, match="Secret cannot be None or blank"):
            TicketManager("   \t\n  ")

    @pytest.mark.unit
    @pytest.mark.security
    def test_explicit_secret_overrides_missing_global(self):
        """Explicit secret should be used even if global secret is missing."""
        with patch("app.auth.tickets.PLAY_SERVICE_SECRET", None):
            # Should not raise because explicit secret is provided
            manager = TicketManager("explicit-secret")
            assert manager.secret == b"explicit-secret"

    @pytest.mark.unit
    @pytest.mark.security
    def test_explicit_secret_overrides_blank_global(self):
        """Explicit secret should be used even if global secret is blank."""
        with patch("app.auth.tickets.PLAY_SERVICE_SECRET", ""):
            # Should not raise because explicit secret is provided
            manager = TicketManager("explicit-secret")
            assert manager.secret == b"explicit-secret"


class TestTicketSecurityIsolation:
    """Test security isolation between ticket operations."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_private_data_not_leaked_in_tokens(self):
        """Sensitive data should not be exposed in token structure."""
        manager = TicketManager("test-secret-12345")

        token = manager.issue({"run_id": "r1", "participant_id": "p1"})

        # Token is base64-encoded, so raw secret shouldn't appear
        assert "test-secret-12345" not in token

        # Even if we decode the base64, secret shouldn't be there
        decoded = base64.urlsafe_b64decode(token.encode("ascii"))
        assert b"test-secret-12345" not in decoded

    @pytest.mark.unit
    @pytest.mark.security
    def test_signature_is_hmac_sha256(self):
        """Token signature should use HMAC-SHA256."""
        manager = TicketManager("test-secret")

        token = manager.issue({"run_id": "r1", "participant_id": "p1"})

        decoded = base64.urlsafe_b64decode(token.encode("ascii"))
        raw, sig = decoded.rsplit(b".", 1)

        # SHA256 produces 64 hex characters (32 bytes * 2 hex chars)
        assert len(sig) == 64  # 256-bit hash in hex = 64 chars
        # All characters should be valid hex
        assert all(c in b"0123456789abcdef" for c in sig)
