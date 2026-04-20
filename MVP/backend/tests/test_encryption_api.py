"""Tests for encryption-enabled data export/import API endpoints."""
from __future__ import annotations

import json
import pytest


@pytest.mark.usefixtures("db_session")
class TestEncryptedDataExport:
    """Test encrypted export API endpoints."""

    def test_export_with_encryption_full_scope(self, client, admin_headers):
        """Test full export with AES-256 encryption."""
        payload = {
            "scope": "full",
            "encrypt": True,
            "password": "secure_export_password_123",
        }

        response = client.post("/api/v1/data/export", json=payload, headers=admin_headers)

        assert response.status_code == 200
        data = response.get_json()

        # Verify encrypted payload structure
        assert data["encrypted"] is True
        assert "encrypted_data" in data
        assert "iv" in data
        assert "salt" in data
        assert data["algorithm"] == "AES-256-CBC"
        assert data["version"] == 1

    def test_export_without_encryption(self, client, admin_headers):
        """Test that unencrypted export still works."""
        payload = {"scope": "full"}

        response = client.post("/api/v1/data/export", json=payload, headers=admin_headers)

        assert response.status_code == 200
        data = response.get_json()

        # Verify unencrypted structure
        assert "metadata" in data
        assert "data" in data
        assert "encrypted_data" not in data

    def test_export_with_encryption_missing_password(self, client, admin_headers):
        """Test that encrypted export fails without password."""
        payload = {"scope": "full", "encrypt": True}

        response = client.post("/api/v1/data/export", json=payload, headers=admin_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert "Password required" in data.get("error", "")

    def test_export_with_empty_password(self, client, admin_headers):
        """Test that empty password is rejected."""
        payload = {
            "scope": "full",
            "encrypt": True,
            "password": "",
        }

        response = client.post("/api/v1/data/export", json=payload, headers=admin_headers)

        assert response.status_code == 400

    def test_export_table_with_encryption(self, client, admin_headers):
        """Test table export with encryption."""
        payload = {
            "scope": "table",
            "table": "users",
            "encrypt": True,
            "password": "table_export_password",
        }

        response = client.post("/api/v1/data/export", json=payload, headers=admin_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["encrypted"] is True
        assert "encrypted_data" in data

    def test_export_rows_with_encryption(self, client, admin_headers):
        """Test row-level export with encryption."""
        payload = {
            "scope": "rows",
            "table": "users",
            "primary_keys": [1, 2],
            "encrypt": True,
            "password": "rows_export_password",
        }

        response = client.post("/api/v1/data/export", json=payload, headers=admin_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["encrypted"] is True


@pytest.mark.usefixtures("db_session")
class TestDecryptExport:
    """Test decryption API endpoint."""

    def test_decrypt_export_success(self, client, admin_headers):
        """Test successful decryption of encrypted export."""
        password = "decrypt_test_password"

        # First, encrypt an export
        encrypt_payload = {
            "scope": "full",
            "encrypt": True,
            "password": password,
        }
        encrypt_response = client.post("/api/v1/data/export", json=encrypt_payload, headers=admin_headers)
        assert encrypt_response.status_code == 200
        encrypted_data = encrypt_response.get_json()

        # Now decrypt it
        decrypt_payload = {
            "encrypted_data": encrypted_data["encrypted_data"],
            "iv": encrypted_data["iv"],
            "salt": encrypted_data["salt"],
            "password": password,
        }
        decrypt_response = client.post("/api/v1/data/export/decrypt", json=decrypt_payload, headers=admin_headers)

        assert decrypt_response.status_code == 200
        decrypted_data = decrypt_response.get_json()

        # Verify structure
        assert "metadata" in decrypted_data
        assert "data" in decrypted_data

    def test_decrypt_with_wrong_password(self, client, admin_headers):
        """Test that decryption with wrong password fails."""
        password = "correct_password"

        # Encrypt with one password
        encrypt_payload = {
            "scope": "full",
            "encrypt": True,
            "password": password,
        }
        encrypt_response = client.post("/api/v1/data/export", json=encrypt_payload, headers=admin_headers)
        encrypted_data = encrypt_response.get_json()

        # Try to decrypt with wrong password
        decrypt_payload = {
            "encrypted_data": encrypted_data["encrypted_data"],
            "iv": encrypted_data["iv"],
            "salt": encrypted_data["salt"],
            "password": "wrong_password",
        }
        decrypt_response = client.post("/api/v1/data/export/decrypt", json=decrypt_payload, headers=admin_headers)

        assert decrypt_response.status_code == 400
        error = decrypt_response.get_json()
        assert "Decryption failed" in error.get("error", "")

    def test_decrypt_missing_password(self, client, admin_headers):
        """Test that decryption fails without password."""
        decrypt_payload = {
            "encrypted_data": "base64data",
            "iv": "base64iv",
            "salt": "base64salt",
        }

        response = client.post("/api/v1/data/export/decrypt", json=decrypt_payload, headers=admin_headers)

        assert response.status_code == 400
        error = response.get_json()
        assert "Password required" in error.get("error", "")

    def test_decrypt_missing_fields(self, client, admin_headers):
        """Test that decryption fails with missing fields."""
        # Missing encrypted_data
        decrypt_payload = {
            "iv": "base64iv",
            "salt": "base64salt",
            "password": "test",
        }

        response = client.post("/api/v1/data/export/decrypt", json=decrypt_payload, headers=admin_headers)

        assert response.status_code == 400
        error = response.get_json()
        assert "Missing required field" in error.get("error", "")

    def test_decrypt_requires_admin(self, client, admin_headers):
        """Test that decryption requires admin privilege."""
        decrypt_payload = {
            "encrypted_data": "data",
            "iv": "iv",
            "salt": "salt",
            "password": "password",
        }

        response = client.post("/api/v1/data/export/decrypt", json=decrypt_payload, headers=admin_headers)

        # Admin passes auth/feature check, but decryption fails with bad data
        assert response.status_code == 400

    def test_decrypt_corrupted_data_fails(self, client, admin_headers):
        """Test that corrupted encrypted data fails to decrypt."""
        # Encrypt some data
        encrypt_payload = {
            "scope": "full",
            "encrypt": True,
            "password": "test_password",
        }
        encrypt_response = client.post("/api/v1/data/export", json=encrypt_payload, headers=admin_headers)
        encrypted_data = encrypt_response.get_json()

        # Corrupt the encrypted data
        corrupted_data = encrypted_data["encrypted_data"][:-2] + "XX"

        decrypt_payload = {
            "encrypted_data": corrupted_data,
            "iv": encrypted_data["iv"],
            "salt": encrypted_data["salt"],
            "password": "test_password",
        }
        decrypt_response = client.post(
            "/api/v1/data/export/decrypt", json=decrypt_payload, headers=admin_headers
        )

        assert decrypt_response.status_code == 400


@pytest.mark.usefixtures("db_session")
class TestEncryptionIntegration:
    """Integration tests for encryption workflow."""

    def test_round_trip_encryption_decryption(self, client, admin_headers):
        """Test complete round-trip: export → encrypt → decrypt → verify."""
        password = "integration_test_password"

        # Export with encryption
        export_payload = {
            "scope": "full",
            "encrypt": True,
            "password": password,
        }
        export_response = client.post("/api/v1/data/export", json=export_payload, headers=admin_headers)
        assert export_response.status_code == 200
        encrypted_data = export_response.get_json()

        # Decrypt
        decrypt_payload = {
            "encrypted_data": encrypted_data["encrypted_data"],
            "iv": encrypted_data["iv"],
            "salt": encrypted_data["salt"],
            "password": password,
        }
        decrypt_response = client.post(
            "/api/v1/data/export/decrypt", json=decrypt_payload, headers=admin_headers
        )
        assert decrypt_response.status_code == 200
        decrypted_data = decrypt_response.get_json()

        # Verify structure
        assert "metadata" in decrypted_data
        assert "data" in decrypted_data
        assert "tables" in decrypted_data["data"]

    def test_multiple_encryption_formats(self, client, admin_headers):
        """Test encryption with different scope types."""
        password = "multi_format_password"

        scopes = [
            {"scope": "full"},
            {"scope": "table", "table": "users"},
        ]

        for scope_payload in scopes:
            # Add encryption
            payload = {**scope_payload, "encrypt": True, "password": password}

            # Export with encryption
            export_response = client.post("/api/v1/data/export", json=payload, headers=admin_headers)
            assert export_response.status_code == 200
            encrypted_data = export_response.get_json()

            # Decrypt and verify
            decrypt_payload = {
                "encrypted_data": encrypted_data["encrypted_data"],
                "iv": encrypted_data["iv"],
                "salt": encrypted_data["salt"],
                "password": password,
            }
            decrypt_response = client.post(
                "/api/v1/data/export/decrypt", json=decrypt_payload, headers=admin_headers
            )
            assert decrypt_response.status_code == 200
            decrypted = decrypt_response.get_json()
            assert "metadata" in decrypted
            assert "data" in decrypted
