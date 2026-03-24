"""Test password complexity validation."""
import pytest
from app.services.user_service import validate_password_complexity


class TestPasswordComplexityValidation:
    """Test the validate_password_complexity function."""

    def test_valid_password(self):
        """Test that a valid password passes validation."""
        is_valid, error_msg = validate_password_complexity("ValidPass123!")
        assert is_valid is True
        assert error_msg == ""

    def test_too_short(self):
        """Test that passwords shorter than 12 characters fail."""
        is_valid, error_msg = validate_password_complexity("Short1!")
        assert is_valid is False
        assert "at least 12 characters" in error_msg

    def test_no_uppercase(self):
        """Test that passwords without uppercase fail."""
        is_valid, error_msg = validate_password_complexity("nouppercase123!")
        assert is_valid is False
        assert "uppercase letter" in error_msg

    def test_no_lowercase(self):
        """Test that passwords without lowercase fail."""
        is_valid, error_msg = validate_password_complexity("NOLOWERCASE123!")
        assert is_valid is False
        assert "lowercase letter" in error_msg

    def test_no_number(self):
        """Test that passwords without a number fail."""
        is_valid, error_msg = validate_password_complexity("NoNumbersHere!")
        assert is_valid is False
        assert "digit" in error_msg

    def test_no_special_character(self):
        """Test that passwords without special characters fail."""
        is_valid, error_msg = validate_password_complexity("NoSpecial123")
        assert is_valid is False
        assert "special character" in error_msg

    def test_empty_password(self):
        """Test that empty password fails."""
        is_valid, error_msg = validate_password_complexity("")
        assert is_valid is False
        assert "required" in error_msg

    def test_none_password(self):
        """Test that None password fails."""
        is_valid, error_msg = validate_password_complexity(None)
        assert is_valid is False
        assert "required" in error_msg

    def test_special_char_exclamation(self):
        """Test with exclamation mark special character."""
        is_valid, error_msg = validate_password_complexity("ValidPass123!")
        assert is_valid is True

    def test_special_char_at(self):
        """Test with @ special character."""
        is_valid, error_msg = validate_password_complexity("ValidPass123@")
        assert is_valid is True

    def test_special_char_hash(self):
        """Test with # special character."""
        is_valid, error_msg = validate_password_complexity("ValidPass123#")
        assert is_valid is True

    def test_special_char_dollar(self):
        """Test with $ special character."""
        is_valid, error_msg = validate_password_complexity("ValidPass123$")
        assert is_valid is True

    def test_special_char_percent(self):
        """Test with % special character."""
        is_valid, error_msg = validate_password_complexity("ValidPass123%")
        assert is_valid is True

    def test_special_char_caret(self):
        """Test with ^ special character."""
        is_valid, error_msg = validate_password_complexity("ValidPass123^")
        assert is_valid is True

    def test_special_char_ampersand(self):
        """Test with & special character."""
        is_valid, error_msg = validate_password_complexity("ValidPass123&")
        assert is_valid is True

    def test_special_char_asterisk(self):
        """Test with * special character."""
        is_valid, error_msg = validate_password_complexity("ValidPass123*")
        assert is_valid is True

    def test_special_char_dash(self):
        """Test with - special character."""
        is_valid, error_msg = validate_password_complexity("ValidPass123-")
        assert is_valid is True

    def test_too_long(self):
        """Test that passwords longer than 128 characters fail."""
        long_password = "ValidPass123!" + "A" * 120
        is_valid, error_msg = validate_password_complexity(long_password)
        assert is_valid is False
        assert "at most 128 characters" in error_msg

    def test_exactly_12_characters(self):
        """Test that passwords with exactly 12 characters pass."""
        is_valid, error_msg = validate_password_complexity("ValidPass12!")
        assert is_valid is True

    def test_multiple_special_chars(self):
        """Test password with multiple special characters."""
        is_valid, error_msg = validate_password_complexity("ValidPass123!@#")
        assert is_valid is True


class TestPasswordComplexityIntegration:
    """Integration tests for password complexity in auth endpoints."""

    def test_registration_with_weak_password(self, client):
        """Test that registration fails with weak password."""
        response = client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "weak",
            "email": "test@example.com"
        })
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data.get("code") == "PASSWORD_WEAK"

    def test_registration_with_strong_password(self, client):
        """Test that registration succeeds with strong password."""
        response = client.post("/api/v1/auth/register", json={
            "username": "testuser123",
            "password": "ValidPass123!",
            "email": "test@example.com"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert "id" in data
        assert "username" in data

    def test_password_change_with_weak_password(self, client, auth_user):
        """Test that password change fails with weak password."""
        user, password = auth_user
        # Login first
        login_response = client.post("/api/v1/auth/login", json={
            "username": user.username,
            "password": password
        })
        assert login_response.status_code == 200
        token = login_response.get_json()["access_token"]

        # Try to change password with weak one
        response = client.put(
            f"/api/v1/users/{user.id}/password",
            json={
                "current_password": password,
                "new_password": "weak"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data.get("code") == "PASSWORD_WEAK"

    def test_password_change_with_strong_password(self, client, auth_user):
        """Test that password change succeeds with strong password."""
        user, password = auth_user
        # Login first
        login_response = client.post("/api/v1/auth/login", json={
            "username": user.username,
            "password": password
        })
        assert login_response.status_code == 200
        token = login_response.get_json()["access_token"]

        # Change password with strong one
        response = client.put(
            f"/api/v1/users/{user.id}/password",
            json={
                "current_password": password,
                "new_password": "NewValidPass123!"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data

    def test_reset_password_with_weak_password(self, client, auth_user):
        """Test that password reset fails with weak password."""
        from app.services.user_service import create_password_reset_token

        user, _ = auth_user
        # Create reset token
        token = create_password_reset_token(user)

        # Try to reset with weak password
        response = client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "new_password": "weak"
        })
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data.get("code") == "PASSWORD_WEAK"

    def test_reset_password_with_strong_password(self, client, auth_user):
        """Test that password reset succeeds with strong password."""
        from app.services.user_service import create_password_reset_token

        user, _ = auth_user
        # Create reset token
        token = create_password_reset_token(user)

        # Reset with strong password
        response = client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "new_password": "NewValidPass123!"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
