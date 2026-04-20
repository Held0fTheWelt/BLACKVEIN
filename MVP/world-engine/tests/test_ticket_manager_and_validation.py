"""Comprehensive ticket manager and validation tests for World Engine.

WAVE 6: Ticket format, signature validation, expiration, and claim verification.
Tests ensure TicketManager correctly issues, verifies, and rejects tickets.
Covers all negative paths and security properties.

Mark: @pytest.mark.unit, @pytest.mark.contract, @pytest.mark.security
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest

from app.auth.tickets import TicketManager, TicketError


class TestTicketManagerBasics:
    """Test basic ticket manager contract and instantiation."""

    @pytest.mark.unit
    def test_ticket_manager_instantiation_with_secret(self):
        """TicketManager should accept custom secret during instantiation."""
        manager = TicketManager("custom-secret")
        assert manager.secret == b"custom-secret"

    @pytest.mark.unit
    def test_ticket_manager_uses_global_secret_when_none_provided(self):
        """TicketManager should use global PLAY_SERVICE_SECRET when not provided."""
        with patch("app.auth.tickets.PLAY_SERVICE_SECRET", "global-test-secret"):
            manager = TicketManager()
            assert manager.secret == b"global-test-secret"

    @pytest.mark.unit
    def test_ticket_manager_explicit_secret_overrides_global(self):
        """Explicit secret should override global PLAY_SERVICE_SECRET."""
        with patch("app.auth.tickets.PLAY_SERVICE_SECRET", "global-secret"):
            manager1 = TicketManager("secret1")
            manager2 = TicketManager("secret2")
            assert manager1.secret != manager2.secret
            assert manager1.secret == b"secret1"
            assert manager2.secret == b"secret2"

    @pytest.mark.unit
    def test_ticket_manager_with_empty_global_secret_fallback(self):
        """TicketManager should handle None global secret gracefully."""
        with patch("app.auth.tickets.PLAY_SERVICE_SECRET", None):
            manager = TicketManager("fallback-secret")
            assert manager.secret == b"fallback-secret"


class TestTicketIssuance:
    """Test ticket generation and format."""

    @pytest.mark.contract
    def test_issue_returns_base64_string(self):
        """Issued ticket should be a base64-encoded string."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123", "participant_id": "p-456"}
        token = manager.issue(payload)

        assert isinstance(token, str)
        assert len(token) > 0
        # Should be decodable as base64
        decoded = base64.urlsafe_b64decode(token.encode("ascii"))
        assert isinstance(decoded, bytes)

    @pytest.mark.contract
    def test_issue_includes_iat_claim(self):
        """Issued ticket should include 'iat' (issued at) timestamp claim."""
        manager = TicketManager("test-secret")
        before = int(time.time())
        payload = {"run_id": "run-123"}
        token = manager.issue(payload)
        after = int(time.time())

        verified = manager.verify(token)
        assert "iat" in verified
        assert before <= verified["iat"] <= after

    @pytest.mark.contract
    def test_issue_includes_exp_claim(self):
        """Issued ticket should include 'exp' (expiration) timestamp claim."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123"}
        token = manager.issue(payload, ttl_seconds=3600)

        verified = manager.verify(token)
        assert "exp" in verified
        assert verified["exp"] > verified["iat"]

    @pytest.mark.contract
    def test_issue_respects_ttl_parameter(self):
        """Issued ticket expiration should match ttl_seconds parameter."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123"}

        # Test different TTLs
        token_1h = manager.issue(payload, ttl_seconds=3600)
        token_1d = manager.issue(payload, ttl_seconds=86400)

        verified_1h = manager.verify(token_1h)
        verified_1d = manager.verify(token_1d)

        # 1-day ticket should expire much later than 1-hour
        assert verified_1d["exp"] > verified_1h["exp"]

    @pytest.mark.contract
    def test_issue_preserves_all_payload_fields(self):
        """Issued ticket should preserve all fields from payload."""
        manager = TicketManager("test-secret")
        payload = {
            "run_id": "run-123",
            "participant_id": "p-456",
            "account_id": "acct-789",
            "character_id": "char-999",
            "display_name": "TestPlayer",
            "role_id": "citizen",
            "custom_field": "custom_value",
            "number": 42,
        }
        token = manager.issue(payload)
        verified = manager.verify(token)

        for key, value in payload.items():
            assert verified[key] == value

    @pytest.mark.contract
    def test_issue_deterministic_payload_encoding(self):
        """Ticket payload should be JSON-encoded with sorted keys."""
        manager = TicketManager("test-secret")
        # Same payload, different field order
        payload1 = {"z": 3, "a": 1, "m": 2}
        payload2 = {"a": 1, "m": 2, "z": 3}

        token1 = manager.issue(payload1, ttl_seconds=3600)
        token2 = manager.issue(payload2, ttl_seconds=3600)

        # Extract raw JSON part (before signature)
        decoded1 = base64.urlsafe_b64decode(token1.encode("ascii")).split(b".")[0]
        decoded2 = base64.urlsafe_b64decode(token2.encode("ascii")).split(b".")[0]

        # JSON should be identical (deterministic encoding)
        assert decoded1 == decoded2

    @pytest.mark.contract
    def test_issue_default_ttl_is_3600(self):
        """Default TTL should be 3600 seconds (1 hour)."""
        manager = TicketManager("test-secret")
        before = int(time.time())
        payload = {"run_id": "run-123"}
        token = manager.issue(payload)  # No ttl_seconds specified
        after = int(time.time())

        verified = manager.verify(token)
        # Should be roughly 3600 seconds from now
        expected_exp_min = before + 3600
        expected_exp_max = after + 3600
        assert expected_exp_min <= verified["exp"] <= expected_exp_max


class TestTicketVerification:
    """Test ticket verification and validation."""

    @pytest.mark.contract
    def test_verify_valid_ticket_returns_payload(self):
        """Valid ticket should verify and return payload."""
        manager = TicketManager("test-secret")
        payload = {
            "run_id": "run-123",
            "participant_id": "p-456",
            "account_id": "acct-789",
        }
        token = manager.issue(payload)
        verified = manager.verify(token)

        assert verified["run_id"] == payload["run_id"]
        assert verified["participant_id"] == payload["participant_id"]
        assert verified["account_id"] == payload["account_id"]

    @pytest.mark.contract
    def test_verify_roundtrip_consistency(self):
        """Multiple verify calls on same token should return identical results."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123", "participant_id": "p-456"}
        token = manager.issue(payload)

        verified1 = manager.verify(token)
        verified2 = manager.verify(token)

        assert verified1 == verified2

    @pytest.mark.security
    def test_verify_requires_valid_signature(self):
        """Ticket with invalid signature should be rejected."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123"}
        token = manager.issue(payload)

        # Tamper with token (flip a bit in signature)
        decoded = base64.urlsafe_b64decode(token.encode("ascii"))
        raw, sig = decoded.rsplit(b".", 1)
        # Flip a bit in signature
        tampered_sig = bytes([sig[0] ^ 0xFF]) + sig[1:]
        tampered_token = base64.urlsafe_b64encode(raw + b"." + tampered_sig).decode("ascii")

        with pytest.raises(TicketError) as exc_info:
            manager.verify(tampered_token)
        assert "Invalid signature" in str(exc_info.value)

    @pytest.mark.security
    def test_verify_requires_correct_secret(self):
        """Ticket should only verify with correct secret."""
        manager1 = TicketManager("secret1")
        manager2 = TicketManager("secret2")

        payload = {"run_id": "run-123"}
        token = manager1.issue(payload)

        # Should verify with correct manager
        verified = manager1.verify(token)
        assert verified["run_id"] == payload["run_id"]

        # Should NOT verify with wrong manager
        with pytest.raises(TicketError) as exc_info:
            manager2.verify(token)
        assert "Invalid signature" in str(exc_info.value)

    @pytest.mark.security
    def test_verify_detects_tampered_payload(self):
        """Tampered payload should be detected by signature."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123", "participant_id": "p-456"}
        token = manager.issue(payload)

        # Decode and tamper with payload
        decoded = base64.urlsafe_b64decode(token.encode("ascii"))
        raw, sig = decoded.rsplit(b".", 1)

        # Change payload value
        malicious_payload = json.loads(raw.decode("utf-8"))
        malicious_payload["participant_id"] = "p-999"
        malicious_raw = json.dumps(malicious_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

        tampered_token = base64.urlsafe_b64encode(malicious_raw + b"." + sig).decode("ascii")

        with pytest.raises(TicketError) as exc_info:
            manager.verify(tampered_token)
        assert "Invalid signature" in str(exc_info.value)


class TestTicketExpiration:
    """Test ticket expiration behavior."""

    @pytest.mark.contract
    def test_ticket_expires_after_ttl(self):
        """Expired ticket should be rejected after TTL passes."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123"}

        # Use mocking for deterministic behavior
        with patch("time.time", return_value=1000.0):
            token = manager.issue(payload, ttl_seconds=1)  # expires at 1001

        # Verify at time 1000 - should work
        with patch("time.time", return_value=1000.0):
            verified = manager.verify(token)
            assert verified["run_id"] == "run-123"

        # Verify at time 1002 - should fail (past expiration)
        with patch("time.time", return_value=1002.0):
            with pytest.raises(TicketError) as exc_info:
                manager.verify(token)
            assert "Expired ticket" in str(exc_info.value)

    @pytest.mark.security
    def test_ticket_rejected_at_exact_exp_time(self):
        """Ticket should be rejected just after exp timestamp."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123"}

        # Issue with controlled timestamp
        with patch("time.time", return_value=1000.0):
            token = manager.issue(payload, ttl_seconds=100)  # exp=1100

        # Verify at time 1099 - should work
        with patch("time.time", return_value=1099.0):
            verified = manager.verify(token)
            assert verified["run_id"] == "run-123"

        # Verify at time 1101 - should fail (exp=1100 is expired)
        with patch("time.time", return_value=1101.0):
            with pytest.raises(TicketError) as exc_info:
                manager.verify(token)
            assert "Expired ticket" in str(exc_info.value)

    @pytest.mark.contract
    def test_expired_ticket_not_reused(self):
        """Expired ticket should not be usable even on second attempt."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123"}

        with patch("time.time", return_value=1000.0):
            token = manager.issue(payload, ttl_seconds=1)

        with patch("time.time", return_value=1002.0):
            # First attempt
            with pytest.raises(TicketError) as exc1:
                manager.verify(token)
            assert "Expired ticket" in str(exc1.value)

            # Second attempt - should also fail
            with pytest.raises(TicketError) as exc2:
                manager.verify(token)
            assert "Expired ticket" in str(exc2.value)


class TestTicketMalformedInput:
    """Test handling of malformed tickets."""

    @pytest.mark.security
    def test_malformed_ticket_invalid_base64(self):
        """Ticket with invalid base64 should be rejected."""
        manager = TicketManager("test-secret")

        with pytest.raises(TicketError) as exc_info:
            manager.verify("not-valid-base64!!!")
        assert "Malformed ticket" in str(exc_info.value)

    @pytest.mark.security
    def test_malformed_ticket_missing_separator(self):
        """Ticket without dot separator should be rejected."""
        manager = TicketManager("test-secret")

        # Encode without dot separator
        payload = json.dumps({"run_id": "run-123"}).encode("utf-8")
        invalid_token = base64.urlsafe_b64encode(payload).decode("ascii")

        with pytest.raises(TicketError) as exc_info:
            manager.verify(invalid_token)
        assert "Malformed ticket" in str(exc_info.value)

    @pytest.mark.security
    def test_malformed_ticket_empty_payload(self):
        """Ticket with empty payload should be rejected."""
        manager = TicketManager("test-secret")

        # Create token with empty payload
        token = base64.urlsafe_b64encode(b".signature").decode("ascii")

        with pytest.raises(TicketError):
            manager.verify(token)

    @pytest.mark.security
    def test_malformed_ticket_invalid_json_payload(self):
        """Ticket with invalid JSON payload should be rejected."""
        manager = TicketManager("test-secret")

        # Invalid JSON in payload (missing closing brace)
        token = base64.urlsafe_b64encode(b"{invalid json.signature").decode("ascii")

        with pytest.raises(TicketError):
            manager.verify(token)

    @pytest.mark.security
    def test_malformed_ticket_empty_string(self):
        """Empty ticket string should be rejected."""
        manager = TicketManager("test-secret")

        with pytest.raises(TicketError) as exc_info:
            manager.verify("")
        assert "Malformed ticket" in str(exc_info.value)

    @pytest.mark.security
    def test_malformed_ticket_none_input(self):
        """None as ticket should be rejected."""
        manager = TicketManager("test-secret")

        with pytest.raises((TicketError, AttributeError, TypeError)):
            manager.verify(None)


class TestRequiredClaims:
    """Test required claims in ticket payload."""

    @pytest.mark.contract
    def test_ticket_must_include_run_id(self):
        """Ticket should include run_id claim."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123", "participant_id": "p-456"}
        token = manager.issue(payload)
        verified = manager.verify(token)

        assert "run_id" in verified
        assert verified["run_id"] == "run-123"

    @pytest.mark.contract
    def test_ticket_must_include_participant_id(self):
        """Ticket should include participant_id claim."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123", "participant_id": "p-456"}
        token = manager.issue(payload)
        verified = manager.verify(token)

        assert "participant_id" in verified
        assert verified["participant_id"] == "p-456"

    @pytest.mark.contract
    def test_ticket_must_include_account_id(self):
        """Ticket should include account_id claim."""
        manager = TicketManager("test-secret")
        payload = {
            "run_id": "run-123",
            "participant_id": "p-456",
            "account_id": "acct-789",
        }
        token = manager.issue(payload)
        verified = manager.verify(token)

        assert "account_id" in verified
        assert verified["account_id"] == "acct-789"

    @pytest.mark.contract
    def test_ticket_must_include_character_id(self):
        """Ticket should include character_id claim."""
        manager = TicketManager("test-secret")
        payload = {
            "run_id": "run-123",
            "participant_id": "p-456",
            "character_id": "char-999",
        }
        token = manager.issue(payload)
        verified = manager.verify(token)

        assert "character_id" in verified
        assert verified["character_id"] == "char-999"

    @pytest.mark.contract
    def test_ticket_must_include_role_id(self):
        """Ticket should include role_id claim."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123", "role_id": "citizen"}
        token = manager.issue(payload)
        verified = manager.verify(token)

        assert "role_id" in verified
        assert verified["role_id"] == "citizen"

    @pytest.mark.contract
    def test_ticket_iat_before_exp(self):
        """Issued-at (iat) claim should always be before expiration (exp)."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123"}
        token = manager.issue(payload, ttl_seconds=3600)
        verified = manager.verify(token)

        assert verified["iat"] < verified["exp"]

    @pytest.mark.contract
    def test_ticket_with_all_required_claims(self):
        """Ticket with all required claims should verify correctly."""
        manager = TicketManager("test-secret")
        payload = {
            "run_id": "run-123",
            "participant_id": "p-456",
            "character_id": "char-999",
            "account_id": "acct-789",
            "role_id": "citizen",
        }
        token = manager.issue(payload)
        verified = manager.verify(token)

        # All claims should be present
        required_claims = [
            "run_id",
            "participant_id",
            "character_id",
            "account_id",
            "role_id",
            "iat",
            "exp",
        ]
        for claim in required_claims:
            assert claim in verified


class TestSignatureValidation:
    """Test HMAC-SHA256 signature validation."""

    @pytest.mark.security
    def test_signature_uses_hmac_sha256(self):
        """Signature should use HMAC-SHA256."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123"}
        token = manager.issue(payload)

        # Manually verify signature format
        decoded = base64.urlsafe_b64decode(token.encode("ascii"))
        raw, sig_hex = decoded.rsplit(b".", 1)

        # Signature should be valid hex string
        sig_bytes = bytes.fromhex(sig_hex.decode("ascii"))
        assert len(sig_bytes) == 32  # SHA256 produces 32 bytes

        # Should match HMAC-SHA256 calculation
        expected_sig = hmac.new(b"test-secret", raw, hashlib.sha256).hexdigest().encode("ascii")
        assert sig_hex == expected_sig

    @pytest.mark.security
    def test_signature_prevents_replay_attacks(self):
        """Different payloads should have different signatures."""
        manager = TicketManager("test-secret")

        token1 = manager.issue({"run_id": "run-123"})
        token2 = manager.issue({"run_id": "run-456"})

        # Signatures should be different
        assert token1 != token2

        # Swapping signatures should fail
        decoded1 = base64.urlsafe_b64decode(token1.encode("ascii"))
        decoded2 = base64.urlsafe_b64decode(token2.encode("ascii"))

        raw1, sig1 = decoded1.rsplit(b".", 1)
        raw2, sig2 = decoded2.rsplit(b".", 1)

        # Token1 raw with Token2 signature
        mixed_token = base64.urlsafe_b64encode(raw1 + b"." + sig2).decode("ascii")

        with pytest.raises(TicketError) as exc_info:
            manager.verify(mixed_token)
        assert "Invalid signature" in str(exc_info.value)

    @pytest.mark.security
    def test_signature_constant_time_comparison(self):
        """Signature comparison should be constant-time (HMAC.compare_digest)."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123"}
        token = manager.issue(payload)

        # Create token with wrong signature
        decoded = base64.urlsafe_b64decode(token.encode("ascii"))
        raw, sig = decoded.rsplit(b".", 1)
        wrong_sig = b"0" * len(sig)
        wrong_token = base64.urlsafe_b64encode(raw + b"." + wrong_sig).decode("ascii")

        # Should reject without timing leak (can't test timing directly, but can verify rejection)
        with pytest.raises(TicketError) as exc_info:
            manager.verify(wrong_token)
        assert "Invalid signature" in str(exc_info.value)


class TestTypeValidation:
    """Test type validation of ticket fields."""

    @pytest.mark.contract
    def test_ticket_fields_preserve_types(self):
        """Ticket should preserve field types through issue/verify."""
        manager = TicketManager("test-secret")
        payload = {
            "run_id": "run-123",  # string
            "count": 42,  # integer
            "enabled": True,  # boolean
            "score": 3.14,  # float
        }
        token = manager.issue(payload)
        verified = manager.verify(token)

        assert isinstance(verified["run_id"], str)
        assert isinstance(verified["count"], int)
        assert isinstance(verified["enabled"], bool)
        assert isinstance(verified["score"], float)

    @pytest.mark.contract
    def test_timestamp_claims_are_integers(self):
        """iat and exp claims should be integers (Unix timestamps)."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123"}
        token = manager.issue(payload)
        verified = manager.verify(token)

        assert isinstance(verified["iat"], int)
        assert isinstance(verified["exp"], int)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.contract
    def test_ticket_with_special_characters_in_payload(self):
        """Ticket should handle special characters in string fields."""
        manager = TicketManager("test-secret")
        payload = {
            "run_id": "run-123",
            "display_name": "Test Player with Special Chars: !@#$%^&*()",
        }
        token = manager.issue(payload)
        verified = manager.verify(token)

        assert verified["display_name"] == payload["display_name"]

    @pytest.mark.contract
    def test_ticket_with_unicode_characters(self):
        """Ticket should handle Unicode characters in payload."""
        manager = TicketManager("test-secret")
        payload = {
            "run_id": "run-123",
            "display_name": "Test Player 🎮 Émoji",
        }
        token = manager.issue(payload)
        verified = manager.verify(token)

        assert verified["display_name"] == payload["display_name"]

    @pytest.mark.contract
    def test_ticket_with_very_long_payload(self):
        """Ticket should handle reasonably large payloads."""
        manager = TicketManager("test-secret")
        payload = {
            "run_id": "run-123",
            "long_field": "x" * 10000,  # 10KB of data
        }
        token = manager.issue(payload)
        verified = manager.verify(token)

        assert verified["long_field"] == payload["long_field"]

    @pytest.mark.contract
    def test_ticket_with_nested_structures(self):
        """Ticket should handle nested JSON structures."""
        manager = TicketManager("test-secret")
        payload = {
            "run_id": "run-123",
            "metadata": {
                "level": 5,
                "inventory": ["sword", "shield"],
                "stats": {"health": 100, "mana": 50},
            },
        }
        token = manager.issue(payload)
        verified = manager.verify(token)

        assert verified["metadata"] == payload["metadata"]

    @pytest.mark.contract
    def test_ticket_with_negative_ttl(self):
        """Ticket with negative TTL should be expired immediately."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123"}
        # Use negative TTL to ensure it's already expired
        token = manager.issue(payload, ttl_seconds=-1)

        # Should be expired immediately
        with pytest.raises(TicketError) as exc_info:
            manager.verify(token)
        assert "Expired ticket" in str(exc_info.value)

    @pytest.mark.contract
    def test_ticket_with_very_long_ttl(self):
        """Ticket should support very long TTLs (e.g., 30 days)."""
        manager = TicketManager("test-secret")
        payload = {"run_id": "run-123"}
        ttl_30_days = 30 * 24 * 60 * 60
        token = manager.issue(payload, ttl_seconds=ttl_30_days)

        verified = manager.verify(token)
        # Should not be expired
        assert verified["exp"] > int(time.time())
