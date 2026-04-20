"""Tests for AES-256 encryption service."""
from __future__ import annotations

import json
import pytest

from app.services import encryption_service


class TestEncryptionService:
    """Test encryption and decryption functionality."""

    def test_encrypt_export_basic(self):
        """Test basic encryption of export data."""
        export_data = {
            "metadata": {
                "format_version": 1,
                "application_version": "1.0.0",
                "exported_at": "2025-03-22T10:30:00+00:00",
                "scope": {"type": "full"},
                "tables": [{"name": "users", "row_count": 5}],
            },
            "data": {
                "tables": {
                    "users": [
                        {"id": 1, "username": "alice", "email": "alice@example.com"},
                        {"id": 2, "username": "bob", "email": "bob@example.com"},
                    ]
                }
            },
        }
        password = "test_password_123"

        encrypted = encryption_service.encrypt_export(export_data, password)

        # Verify structure
        assert "encrypted_data" in encrypted
        assert "iv" in encrypted
        assert "salt" in encrypted
        assert "version" in encrypted
        assert "algorithm" in encrypted
        assert encrypted["version"] == 1
        assert encrypted["algorithm"] == "AES-256-CBC"
        assert "pbkdf2_iterations" in encrypted

    def test_decrypt_export_basic(self):
        """Test basic decryption of encrypted data."""
        export_data = {
            "metadata": {"format_version": 1, "scope": {"type": "full"}},
            "data": {"tables": {"users": [{"id": 1, "username": "alice"}]}},
        }
        password = "test_password_123"

        # Encrypt
        encrypted = encryption_service.encrypt_export(export_data, password)

        # Decrypt
        decrypted = encryption_service.decrypt_export(encrypted, password)

        # Verify content
        assert decrypted == export_data

    def test_decrypt_with_wrong_password_fails(self):
        """Test that decryption with wrong password fails."""
        export_data = {
            "metadata": {"format_version": 1},
            "data": {"tables": {}},
        }
        password = "correct_password"
        wrong_password = "wrong_password"

        encrypted = encryption_service.encrypt_export(export_data, password)

        with pytest.raises(ValueError):
            encryption_service.decrypt_export(encrypted, wrong_password)

    def test_encrypt_with_empty_password_fails(self):
        """Test that empty password is rejected."""
        export_data = {"metadata": {}, "data": {}}

        with pytest.raises(ValueError, match="Password must be a non-empty string"):
            encryption_service.encrypt_export(export_data, "")

        with pytest.raises(ValueError, match="Password must be a non-empty string"):
            encryption_service.encrypt_export(export_data, None)

    def test_decrypt_with_empty_password_fails(self):
        """Test that empty password is rejected for decryption."""
        encrypted = {
            "encrypted_data": "base64data",
            "iv": "base64iv",
            "salt": "base64salt",
        }

        with pytest.raises(ValueError, match="Password must be a non-empty string"):
            encryption_service.decrypt_export(encrypted, "")

        with pytest.raises(ValueError, match="Password must be a non-empty string"):
            encryption_service.decrypt_export(encrypted, None)

    def test_decrypt_missing_required_fields(self):
        """Test that decryption fails with missing fields."""
        encrypted_missing_data = {"iv": "base64iv", "salt": "base64salt"}
        encrypted_missing_iv = {"encrypted_data": "base64data", "salt": "base64salt"}
        encrypted_missing_salt = {"encrypted_data": "base64data", "iv": "base64iv"}

        with pytest.raises(ValueError, match="Missing required field"):
            encryption_service.decrypt_export(encrypted_missing_data, "password")

        with pytest.raises(ValueError, match="Missing required field"):
            encryption_service.decrypt_export(encrypted_missing_iv, "password")

        with pytest.raises(ValueError, match="Missing required field"):
            encryption_service.decrypt_export(encrypted_missing_salt, "password")

    def test_decrypt_invalid_base64(self):
        """Test that invalid base64 encoding is caught."""
        encrypted = {
            "encrypted_data": "!!!invalid base64!!!",
            "iv": "base64iv",
            "salt": "base64salt",
        }

        with pytest.raises(ValueError, match="Invalid base64 encoding"):
            encryption_service.decrypt_export(encrypted, "password")

    def test_encrypt_large_export(self):
        """Test encryption of large export with many rows."""
        users = [
            {"id": i, "username": f"user{i}", "email": f"user{i}@example.com"}
            for i in range(100)
        ]
        export_data = {
            "metadata": {
                "format_version": 1,
                "tables": [{"name": "users", "row_count": 100}],
            },
            "data": {"tables": {"users": users}},
        }
        password = "large_export_password"

        encrypted = encryption_service.encrypt_export(export_data, password)
        decrypted = encryption_service.decrypt_export(encrypted, password)

        assert decrypted == export_data

    def test_encrypt_complex_data_types(self):
        """Test encryption with complex data types (dates, nulls, etc)."""
        export_data = {
            "metadata": {
                "format_version": 1,
                "exported_at": "2025-03-22T10:30:00.123456+00:00",
            },
            "data": {
                "tables": {
                    "posts": [
                        {
                            "id": 1,
                            "title": "Test Post",
                            "content": "Some content",
                            "published": True,
                            "published_at": "2025-03-22T10:00:00+00:00",
                            "tags": None,
                            "view_count": 0,
                        }
                    ]
                }
            },
        }
        password = "complex_data_password"

        encrypted = encryption_service.encrypt_export(export_data, password)
        decrypted = encryption_service.decrypt_export(encrypted, password)

        assert decrypted == export_data

    def test_iv_and_salt_are_random(self):
        """Test that IV and salt are randomly generated for each encryption."""
        export_data = {"metadata": {}, "data": {}}
        password = "test_password"

        encrypted1 = encryption_service.encrypt_export(export_data, password)
        encrypted2 = encryption_service.encrypt_export(export_data, password)

        # IV and salt should be different for each encryption
        assert encrypted1["iv"] != encrypted2["iv"]
        assert encrypted1["salt"] != encrypted2["salt"]

        # But both should decrypt to same data
        decrypted1 = encryption_service.decrypt_export(encrypted1, password)
        decrypted2 = encryption_service.decrypt_export(encrypted2, password)
        assert decrypted1 == decrypted2 == export_data

    def test_encrypt_special_characters_in_password(self):
        """Test encryption with special characters in password."""
        export_data = {"metadata": {}, "data": {"tables": {}}}
        passwords = [
            "p@ssw0rd!",
            "パスワード",  # Japanese characters
            "Ñoño123",  # Spanish characters
            "🔒secure🔒",  # Emojis
        ]

        for password in passwords:
            encrypted = encryption_service.encrypt_export(export_data, password)
            decrypted = encryption_service.decrypt_export(encrypted, password)
            assert decrypted == export_data

    def test_decrypt_corrupted_ciphertext(self):
        """Test that corrupted ciphertext causes decryption failure."""
        export_data = {"metadata": {}, "data": {}}
        password = "test_password"

        encrypted = encryption_service.encrypt_export(export_data, password)

        # Corrupt the ciphertext by flipping bits
        corrupted_data = encrypted["encrypted_data"]
        # Change one character
        corrupted_data = corrupted_data[:-2] + "XX"

        encrypted["encrypted_data"] = corrupted_data

        with pytest.raises(ValueError, match="Decryption failed"):
            encryption_service.decrypt_export(encrypted, password)

    def test_json_serialization_stability(self):
        """Test that JSON serialization is stable across encryptions."""
        export_data = {
            "z_field": "last",
            "a_field": "first",
            "data": {
                "nested": {
                    "z": 1,
                    "a": 2,
                }
            },
        }
        password = "test_password"

        encrypted1 = encryption_service.encrypt_export(export_data, password)
        encrypted2 = encryption_service.encrypt_export(export_data, password)

        # Same data with different IVs/salts should decrypt identically
        decrypted1 = encryption_service.decrypt_export(encrypted1, password)
        decrypted2 = encryption_service.decrypt_export(encrypted2, password)

        # Both should match original (order preserved by json.dumps sort_keys)
        assert decrypted1 == decrypted2 == export_data
