"""Cross-Service Contract Tests: Backend-to-WorldEngine Bridge.

WAVE 9 FINAL: Cross-service integration contracts and execution profiles.
Tests ensure backend-issued tickets are valid and verifiable by world-engine.

Mark: @pytest.mark.contract, @pytest.mark.security, @pytest.mark.integration
"""

from __future__ import annotations

import hmac
import hashlib
import base64
import json
import time
from typing import Any
from unittest.mock import patch

import pytest

from app.auth.tickets import TicketManager, TicketError


class TestBackendIssuedTicketsAreValidByWorldEngine:
    """Test that backend-issued tickets are valid and verifiable by world-engine."""

    @pytest.mark.contract
    @pytest.mark.security
    def test_backend_issued_ticket_with_shared_secret_is_valid(self):
        """Backend ticket issued with correct secret must be verifiable by world-engine."""
        # Simulate backend issuing ticket with shared secret
        shared_secret = "backend-world-engine-shared-secret"
        backend_manager = TicketManager(shared_secret)

        # Backend issues ticket with required fields
        payload = {
            "run_id": "run-001",
            "participant_id": "p-001",
            "account_id": "backend-account-123",
            "character_id": "char-456",
            "display_name": "BackendUser",
            "role_id": "citizen",
        }
        ticket = backend_manager.issue(payload, ttl_seconds=3600)

        # World-engine verifies with same secret
        world_engine_manager = TicketManager(shared_secret)
        verified_payload = world_engine_manager.verify(ticket)

        # All fields must be preserved
        assert verified_payload["run_id"] == "run-001"
        assert verified_payload["participant_id"] == "p-001"
        assert verified_payload["account_id"] == "backend-account-123"
        assert verified_payload["character_id"] == "char-456"
        assert verified_payload["display_name"] == "BackendUser"
        assert verified_payload["role_id"] == "citizen"

    @pytest.mark.contract
    def test_backend_ticket_structure_contains_required_fields(self):
        """Backend ticket payload must include all required identity mapping fields."""
        shared_secret = "shared-secret-for-contracts"
        manager = TicketManager(shared_secret)

        # Required fields from backend perspective
        payload = {
            "run_id": "run-uuid-backend",
            "participant_id": "p-uuid-backend",
            "account_id": "account-uuid-backend",
            "character_id": "character-uuid-backend",
            "display_name": "PlayerName",
            "role_id": "narrator",
        }
        ticket = manager.issue(payload)

        # Verify structure
        verified = manager.verify(ticket)
        required_fields = [
            "run_id",
            "participant_id",
            "account_id",
            "character_id",
            "display_name",
            "role_id",
            "iat",
            "exp",
        ]
        for field in required_fields:
            assert field in verified, f"Missing required field: {field}"

    @pytest.mark.contract
    def test_backend_ticket_preserves_field_types(self):
        """Backend ticket must preserve field data types during round-trip."""
        shared_secret = "test-secret"
        manager = TicketManager(shared_secret)

        payload = {
            "run_id": "string-run-id",
            "participant_id": "string-pid",
            "account_id": "string-acct",
            "character_id": "string-char",
            "display_name": "StringDisplay",
            "role_id": "string-role",
            "custom_numeric": 42,
            "custom_bool": True,
        }
        ticket = manager.issue(payload)
        verified = manager.verify(ticket)

        # Verify all fields maintain their types
        assert isinstance(verified["run_id"], str)
        assert isinstance(verified["participant_id"], str)
        assert isinstance(verified["account_id"], str)
        assert isinstance(verified["character_id"], str)
        assert isinstance(verified["display_name"], str)
        assert isinstance(verified["role_id"], str)
        assert verified["custom_numeric"] == 42
        assert isinstance(verified["custom_numeric"], int)
        assert verified["custom_bool"] is True
        assert isinstance(verified["custom_bool"], bool)


class TestWrongSecretRejection:
    """Test that tickets with wrong secret are rejected."""

    @pytest.mark.contract
    @pytest.mark.security
    def test_ticket_with_wrong_secret_is_rejected(self):
        """Ticket signed with different secret must be rejected by world-engine."""
        backend_secret = "backend-secret-abc123"
        wrong_secret = "different-secret-xyz789"

        backend_manager = TicketManager(backend_secret)
        world_engine_manager = TicketManager(wrong_secret)

        payload = {
            "run_id": "run-456",
            "participant_id": "p-456",
            "account_id": "acc-456",
            "character_id": "char-456",
            "display_name": "TestUser",
            "role_id": "citizen",
        }

        # Backend issues with its secret
        ticket = backend_manager.issue(payload)

        # World-engine with wrong secret should reject
        with pytest.raises(TicketError, match="Invalid signature"):
            world_engine_manager.verify(ticket)

    @pytest.mark.contract
    @pytest.mark.security
    def test_ticket_with_api_key_mismatch_rejected(self):
        """Credential mismatch between backend and world-engine must be detected."""
        backend_api_key = "backend-api-key-v1-secure"
        world_engine_api_key = "world-engine-api-key-v1-secure"

        # These represent different credentials
        assert backend_api_key != world_engine_api_key

        backend_manager = TicketManager(backend_api_key)
        world_engine_manager = TicketManager(world_engine_api_key)

        payload = {"run_id": "r1", "participant_id": "p1"}
        ticket = backend_manager.issue(payload)

        # Verification fails with mismatched key
        with pytest.raises(TicketError):
            world_engine_manager.verify(ticket)

    @pytest.mark.contract
    @pytest.mark.security
    def test_malformed_ticket_rejected(self):
        """Malformed or corrupted tickets must be rejected."""
        manager = TicketManager("test-secret")

        # Various malformed tickets
        malformed_tickets = [
            "not-base64-safe",
            "YWJjZGVmZ2g=",  # Invalid base64
            "",  # Empty
            "YWJj" * 100,  # Truncated
        ]

        for malformed in malformed_tickets:
            with pytest.raises(TicketError):
                manager.verify(malformed)


class TestExpiredArtifactsHandling:
    """Test that expired artifacts from backend are properly handled."""

    @pytest.mark.contract
    @pytest.mark.security
    def test_expired_ticket_from_backend_is_rejected(self):
        """Expired ticket issued by backend must be rejected by world-engine."""
        shared_secret = "shared-secret-expiry"
        backend_manager = TicketManager(shared_secret)
        world_engine_manager = TicketManager(shared_secret)

        payload = {
            "run_id": "run-expired",
            "participant_id": "p-expired",
            "account_id": "acc-expired",
            "character_id": "char-expired",
            "display_name": "ExpiredUser",
            "role_id": "citizen",
        }

        # Mock time to issue ticket at time T=100
        with patch("time.time", return_value=100):
            ticket = backend_manager.issue(payload, ttl_seconds=10)

        # Move time forward past expiration (T=111)
        with patch("time.time", return_value=111):
            # World-engine should reject as expired
            with pytest.raises(TicketError, match="Expired ticket"):
                world_engine_manager.verify(ticket)

    @pytest.mark.contract
    def test_old_backend_issued_ticket_with_past_iat_is_rejected_if_expired(self):
        """Old tickets from backend with past issuance time are rejected if expired."""
        shared_secret = "shared-for-old-tickets"
        manager = TicketManager(shared_secret)

        # Create a payload with past issuance time
        past_time = int(time.time()) - 7200  # 2 hours ago
        payload = {
            "run_id": "run-old",
            "participant_id": "p-old",
            "iat": past_time,
            "exp": past_time + 3600,  # Expired 1 hour ago
        }

        # Manually create expired ticket (simulate old backend-issued)
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        sig = hmac.new(manager.secret, raw, hashlib.sha256).hexdigest().encode("ascii")
        ticket = base64.urlsafe_b64encode(raw + b"." + sig).decode("ascii")

        # Should be rejected as expired
        with pytest.raises(TicketError, match="Expired ticket"):
            manager.verify(ticket)

    @pytest.mark.contract
    def test_newly_issued_backend_ticket_with_valid_ttl_is_accepted(self):
        """Recently issued backend tickets with valid TTL are accepted."""
        shared_secret = "shared-for-valid-ttl"
        manager = TicketManager(shared_secret)

        payload = {
            "run_id": "run-valid",
            "participant_id": "p-valid",
            "account_id": "acc-valid",
            "character_id": "char-valid",
            "display_name": "ValidUser",
            "role_id": "citizen",
        }

        # Issue with long TTL
        ticket = manager.issue(payload, ttl_seconds=3600)

        # Should be verifiable
        verified = manager.verify(ticket)
        assert verified["run_id"] == "run-valid"
        assert verified["exp"] > int(time.time())  # Not expired


class TestFieldMappingCompatibility:
    """Test field name and structure compatibility between services."""

    @pytest.mark.contract
    def test_backend_to_worldengine_field_mapping(self):
        """Backend field names must map correctly to world-engine expectations."""
        shared_secret = "field-mapping-secret"
        manager = TicketManager(shared_secret)

        # Backend uses these field names
        backend_payload = {
            "run_id": "run-mapping-test",
            "participant_id": "participant-id-value",
            "account_id": "account-id-value",
            "character_id": "character-id-value",
            "display_name": "DisplayNameValue",
            "role_id": "role-id-value",
        }

        ticket = manager.issue(backend_payload)
        verified = manager.verify(ticket)

        # World-engine expects these exact field names
        assert verified["run_id"] == "run-mapping-test"
        assert verified["participant_id"] == "participant-id-value"
        assert verified["account_id"] == "account-id-value"
        assert verified["character_id"] == "character-id-value"
        assert verified["display_name"] == "DisplayNameValue"
        assert verified["role_id"] == "role-id-value"

    @pytest.mark.contract
    def test_ticket_with_missing_optional_fields_still_valid(self):
        """Tickets with missing optional fields should still be valid."""
        shared_secret = "optional-fields-secret"
        manager = TicketManager(shared_secret)

        # Minimal required fields only
        minimal_payload = {
            "run_id": "run-minimal",
            "participant_id": "p-minimal",
        }

        ticket = manager.issue(minimal_payload)
        verified = manager.verify(ticket)

        assert verified["run_id"] == "run-minimal"
        assert verified["participant_id"] == "p-minimal"
        assert "iat" in verified
        assert "exp" in verified

    @pytest.mark.contract
    def test_identity_format_compatibility_uuid_style(self):
        """Backend and world-engine must handle UUID-style identity fields."""
        shared_secret = "uuid-format-secret"
        manager = TicketManager(shared_secret)

        # UUID-formatted identities
        payload = {
            "run_id": "550e8400-e29b-41d4-a716-446655440000",
            "participant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "account_id": "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
            "character_id": "6ba7b812-9dad-11d1-80b4-00c04fd430c8",
            "display_name": "UUIDPlayer",
            "role_id": "citizen",
        }

        ticket = manager.issue(payload)
        verified = manager.verify(ticket)

        assert verified["run_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert verified["participant_id"] == "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

    @pytest.mark.contract
    def test_identity_format_compatibility_alphanumeric_style(self):
        """Backend and world-engine must handle alphanumeric identity fields."""
        shared_secret = "alphanumeric-secret"
        manager = TicketManager(shared_secret)

        payload = {
            "run_id": "run_abc123def456",
            "participant_id": "participant_xyz789_ABC",
            "account_id": "acct_001_test",
            "character_id": "char_final_v2",
            "display_name": "TestPlayer123",
            "role_id": "role_citizen_v1",
        }

        ticket = manager.issue(payload)
        verified = manager.verify(ticket)

        assert verified["run_id"] == "run_abc123def456"
        assert verified["character_id"] == "char_final_v2"

    @pytest.mark.contract
    def test_display_name_with_special_characters_preserved(self):
        """Display names with special characters must be preserved correctly."""
        shared_secret = "special-chars-secret"
        manager = TicketManager(shared_secret)

        payload = {
            "run_id": "run-special",
            "participant_id": "p-special",
            "display_name": "Player-Name_123 (Test)",
            "role_id": "citizen",
        }

        ticket = manager.issue(payload)
        verified = manager.verify(ticket)

        assert verified["display_name"] == "Player-Name_123 (Test)"


class TestTicketSignatureValidation:
    """Test HMAC signature validation between backend and world-engine."""

    @pytest.mark.contract
    @pytest.mark.security
    def test_signature_validation_uses_shared_secret(self):
        """Ticket signature must be validated using shared secret."""
        shared_secret = "sig-validation-secret"
        manager = TicketManager(shared_secret)

        payload = {
            "run_id": "run-sig",
            "participant_id": "p-sig",
        }
        ticket = manager.issue(payload)

        # Should verify successfully
        verified = manager.verify(ticket)
        assert verified["run_id"] == "run-sig"

    @pytest.mark.contract
    @pytest.mark.security
    def test_ticket_signature_tampering_detected(self):
        """Any tampering with ticket signature must be detected."""
        shared_secret = "tamper-detection-secret"
        manager = TicketManager(shared_secret)

        payload = {
            "run_id": "run-tamper",
            "participant_id": "p-tamper",
        }
        ticket = manager.issue(payload)

        # Tamper with the ticket signature
        parts = ticket.split(".")
        if len(parts) == 2:
            # Flip one character in the signature
            tampered_sig = parts[1][:-1] + ("a" if parts[1][-1] != "a" else "b")
            tampered_ticket = parts[0] + "." + tampered_sig
            tampered_ticket = base64.urlsafe_b64encode(
                base64.urlsafe_b64decode(parts[0]) + b"." + tampered_sig.encode()
            ).decode()

            with pytest.raises(TicketError, match="Invalid signature"):
                manager.verify(tampered_ticket)

    @pytest.mark.contract
    @pytest.mark.security
    def test_hmac_sha256_ensures_integrity(self):
        """Signature must use HMAC-SHA256 for integrity."""
        shared_secret = "integrity-secret"
        manager = TicketManager(shared_secret)

        payload = {
            "run_id": "run-integrity",
            "participant_id": "p-integrity",
        }
        ticket = manager.issue(payload)

        # Decode to inspect structure
        decoded = base64.urlsafe_b64decode(ticket.encode())
        raw, sig = decoded.rsplit(b".", 1)

        # Verify signature was computed correctly
        expected_sig = hmac.new(
            manager.secret, raw, hashlib.sha256
        ).hexdigest().encode("ascii")
        assert sig == expected_sig


class TestJoinContextAuthenticationRequirement:
    """Test that join context operations require proper authentication."""

    @pytest.mark.contract
    @pytest.mark.security
    def test_join_context_ticket_must_have_run_id(self):
        """Join context ticket must include run_id field."""
        shared_secret = "joinctx-secret"
        manager = TicketManager(shared_secret)

        # Valid join context ticket
        payload = {
            "run_id": "run-join",
            "participant_id": "p-join",
            "display_name": "JoinUser",
            "role_id": "citizen",
        }
        ticket = manager.issue(payload)
        verified = manager.verify(ticket)

        assert "run_id" in verified
        assert verified["run_id"] == "run-join"

    @pytest.mark.contract
    @pytest.mark.security
    def test_join_context_ticket_must_have_participant_id(self):
        """Join context ticket must include participant_id for identity."""
        shared_secret = "joinctx-pid-secret"
        manager = TicketManager(shared_secret)

        payload = {
            "run_id": "run-join-pid",
            "participant_id": "p-join-pid",
            "account_id": "acc-join",
            "display_name": "ParticipantUser",
            "role_id": "citizen",
        }
        ticket = manager.issue(payload)
        verified = manager.verify(ticket)

        assert "participant_id" in verified
        assert verified["participant_id"] == "p-join-pid"

    @pytest.mark.contract
    def test_join_context_ticket_may_include_optional_fields(self):
        """Join context ticket may optionally include account_id and character_id."""
        shared_secret = "joinctx-optional-secret"
        manager = TicketManager(shared_secret)

        payload = {
            "run_id": "run-join-opt",
            "participant_id": "p-join-opt",
            "account_id": "acc-optional",
            "character_id": "char-optional",
            "display_name": "OptionalUser",
            "role_id": "citizen",
        }
        ticket = manager.issue(payload)
        verified = manager.verify(ticket)

        # All fields should be present
        assert verified["account_id"] == "acc-optional"
        assert verified["character_id"] == "char-optional"

    @pytest.mark.contract
    def test_join_context_ticket_with_role_id_enables_role_assignment(self):
        """Join context ticket with role_id enables proper role assignment."""
        shared_secret = "joinctx-role-secret"
        manager = TicketManager(shared_secret)

        payload = {
            "run_id": "run-join-role",
            "participant_id": "p-join-role",
            "display_name": "RoleUser",
            "role_id": "narrator",  # Specific role
        }
        ticket = manager.issue(payload)
        verified = manager.verify(ticket)

        assert verified["role_id"] == "narrator"


class TestBackendWorldEngineVersionCompatibility:
    """Test version compatibility between backend and world-engine."""

    @pytest.mark.contract
    def test_ticket_format_version_compatibility(self):
        """Ticket format must remain compatible across versions."""
        shared_secret = "version-compat-secret"
        manager = TicketManager(shared_secret)

        # Standard ticket format
        payload = {
            "run_id": "run-v1",
            "participant_id": "p-v1",
            "account_id": "acc-v1",
            "character_id": "char-v1",
            "display_name": "VersionedUser",
            "role_id": "citizen",
            "version": "1.0",  # Optional version marker
        }
        ticket = manager.issue(payload)
        verified = manager.verify(ticket)

        # All fields preserved
        assert verified["version"] == "1.0"
        assert verified["run_id"] == "run-v1"

    @pytest.mark.contract
    def test_forward_compatible_extra_fields_preserved(self):
        """Extra fields in ticket payload are preserved for forward compatibility."""
        shared_secret = "forward-compat-secret"
        manager = TicketManager(shared_secret)

        payload = {
            "run_id": "run-compat",
            "participant_id": "p-compat",
            "display_name": "CompatUser",
            "role_id": "citizen",
            "extra_field_v2": "new-feature-data",
            "another_extension": {"nested": "value"},
        }
        ticket = manager.issue(payload)
        verified = manager.verify(ticket)

        assert verified["extra_field_v2"] == "new-feature-data"
        assert verified["another_extension"] == {"nested": "value"}

    @pytest.mark.contract
    def test_timestamp_fields_iat_exp_always_present(self):
        """Timestamp fields iat and exp must always be present for version compatibility."""
        shared_secret = "timestamp-secret"
        manager = TicketManager(shared_secret)

        payload = {
            "run_id": "run-ts",
            "participant_id": "p-ts",
        }
        ticket = manager.issue(payload)
        verified = manager.verify(ticket)

        # Timestamps always present
        assert "iat" in verified
        assert "exp" in verified
        assert isinstance(verified["iat"], int)
        assert isinstance(verified["exp"], int)
        assert verified["exp"] > verified["iat"]
