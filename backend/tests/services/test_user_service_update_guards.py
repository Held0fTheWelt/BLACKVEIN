"""Tests for user_service_update_guards.py - User update validation."""
import re
from unittest.mock import MagicMock
import pytest

from app.services.identity.user_service_update_guards import (
    update_user_build_patch,
)
from app.models import User


class TestUpdateUserBuildPatch:
    """Tests for update_user_build_patch function."""

    @pytest.fixture
    def validators(self):
        """Create validator fixtures."""
        return {
            "username_pattern": re.compile(r"^[a-zA-Z0-9_-]{2,}$"),
            "username_max_length": 32,
            "current_user_id": 1,
            "get_user_by_username": MagicMock(return_value=None),
            "get_user_by_email": MagicMock(return_value=None),
            "validate_email_format": lambda e: (True, e),
            "get_role_by_name": MagicMock(return_value=MagicMock(id=2)),
            "supported_languages": ["en", "es", "fr"],
        }

    def test_patch_all_none(self, validators):
        """Test with all fields None."""
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch == {}
        assert error is None

    def test_patch_valid_username(self, validators):
        """Test with valid username."""
        patch, error = update_user_build_patch(
            username="newuser",
            email=None,
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch == {"username": "newuser"}
        assert error is None

    def test_username_empty(self, validators):
        """Test with empty username."""
        patch, error = update_user_build_patch(
            username="",
            email=None,
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch is None
        assert error == "Username cannot be empty"

    def test_username_whitespace_only(self, validators):
        """Test with whitespace-only username."""
        patch, error = update_user_build_patch(
            username="   ",
            email=None,
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch is None
        assert error == "Username cannot be empty"

    def test_username_too_short(self, validators):
        """Test with username too short."""
        patch, error = update_user_build_patch(
            username="a",
            email=None,
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch is None
        assert error == "Username must be at least 2 characters"

    def test_username_too_long(self, validators):
        """Test with username too long."""
        long_username = "a" * 33
        patch, error = update_user_build_patch(
            username=long_username,
            email=None,
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch is None
        assert "at most 32 characters" in error

    def test_username_invalid_characters(self, validators):
        """Test with invalid username characters."""
        patch, error = update_user_build_patch(
            username="user@name",
            email=None,
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch is None
        assert error == "Username contains invalid characters"

    def test_username_already_taken(self, validators):
        """Test with username already taken by another user."""
        other_user = MagicMock(id=2)
        validators["get_user_by_username"].return_value = other_user
        patch, error = update_user_build_patch(
            username="taken",
            email=None,
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch is None
        assert error == "Username already taken"

    def test_username_taken_by_self(self, validators):
        """Test with username taken by the current user (allowed)."""
        validators["get_user_by_username"].return_value = MagicMock(id=1)
        patch, error = update_user_build_patch(
            username="current",
            email=None,
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch == {"username": "current"}
        assert error is None

    def test_valid_email(self, validators):
        """Test with valid email."""
        patch, error = update_user_build_patch(
            username=None,
            email="user@example.com",
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch == {"email": "user@example.com"}
        assert error is None

    def test_email_empty_string(self, validators):
        """Test with empty email string."""
        patch, error = update_user_build_patch(
            username=None,
            email="",
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch == {"email": None}
        assert error is None

    def test_email_whitespace_only(self, validators):
        """Test with whitespace-only email."""
        patch, error = update_user_build_patch(
            username=None,
            email="   ",
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch == {"email": None}
        assert error is None

    def test_email_invalid_format(self, validators):
        """Test with invalid email format."""
        validators["validate_email_format"] = lambda e: (False, "Invalid email format")
        patch, error = update_user_build_patch(
            username=None,
            email="invalid-email",
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch is None
        assert error == "Invalid email format"

    def test_email_already_registered(self, validators):
        """Test with email already registered."""
        validators["get_user_by_email"].return_value = MagicMock(id=2)
        patch, error = update_user_build_patch(
            username=None,
            email="taken@example.com",
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch is None
        assert error == "Email already registered"

    def test_email_registered_by_self(self, validators):
        """Test with email registered by current user (allowed)."""
        validators["get_user_by_email"].return_value = MagicMock(id=1)
        patch, error = update_user_build_patch(
            username=None,
            email="user@example.com",
            role=None,
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch == {"email": "user@example.com"}
        assert error is None

    def test_valid_role(self, validators):
        """Test with valid role."""
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role="admin",
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert "role_id" in patch
        assert error is None

    def test_role_empty_defaults_to_user(self, validators):
        """Test that empty role defaults to USER role."""
        validators["get_role_by_name"].return_value = MagicMock(id=1)
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role="",
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert "role_id" in patch
        # Verify get_role_by_name was called with User.ROLE_USER
        validators["get_role_by_name"].assert_called_with(User.ROLE_USER)

    def test_role_invalid(self, validators):
        """Test with invalid role."""
        validators["get_role_by_name"].return_value = None
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role="invalid_role",
            role_level=None,
            preferred_language=None,
            **validators,
        )
        assert patch is None
        assert error == "Invalid role"

    def test_valid_role_level(self, validators):
        """Test with valid role level."""
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role=None,
            role_level=50,
            preferred_language=None,
            **validators,
        )
        assert patch == {"role_level": 50}
        assert error is None

    def test_role_level_zero(self, validators):
        """Test with role level 0."""
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role=None,
            role_level=0,
            preferred_language=None,
            **validators,
        )
        assert patch == {"role_level": 0}
        assert error is None

    def test_role_level_max(self, validators):
        """Test with max role level."""
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role=None,
            role_level=9999,
            preferred_language=None,
            **validators,
        )
        assert patch == {"role_level": 9999}
        assert error is None

    def test_role_level_negative(self, validators):
        """Test with negative role level."""
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role=None,
            role_level=-1,
            preferred_language=None,
            **validators,
        )
        assert patch is None
        assert "between 0 and 9999" in error

    def test_role_level_too_high(self, validators):
        """Test with role level too high."""
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role=None,
            role_level=10000,
            preferred_language=None,
            **validators,
        )
        assert patch is None
        assert "between 0 and 9999" in error

    def test_role_level_invalid_type(self, validators):
        """Test with invalid role level type."""
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role=None,
            role_level="not_a_number",
            preferred_language=None,
            **validators,
        )
        assert patch is None
        assert "must be an integer" in error

    def test_valid_language(self, validators):
        """Test with valid language."""
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role=None,
            role_level=None,
            preferred_language="en",
            **validators,
        )
        assert patch == {"preferred_language": "en"}
        assert error is None

    def test_language_empty(self, validators):
        """Test with empty language."""
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role=None,
            role_level=None,
            preferred_language="",
            **validators,
        )
        assert patch == {"preferred_language": None}
        assert error is None

    def test_language_unsupported(self, validators):
        """Test with unsupported language."""
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role=None,
            role_level=None,
            preferred_language="de",
            **validators,
        )
        assert patch is None
        assert error == "Unsupported language"

    def test_language_case_insensitive(self, validators):
        """Test that language check is case-insensitive."""
        patch, error = update_user_build_patch(
            username=None,
            email=None,
            role=None,
            role_level=None,
            preferred_language="EN",
            **validators,
        )
        assert patch == {"preferred_language": "en"}
        assert error is None

    def test_all_fields_valid(self, validators):
        """Test with all fields valid."""
        patch, error = update_user_build_patch(
            username="newuser",
            email="new@example.com",
            role="admin",
            role_level=100,
            preferred_language="es",
            **validators,
        )
        assert error is None
        assert "username" in patch
        assert "email" in patch
        assert "role_id" in patch
        assert "role_level" in patch
        assert "preferred_language" in patch

    def test_partial_update(self, validators):
        """Test with only some fields provided."""
        patch, error = update_user_build_patch(
            username="updated",
            email=None,
            role=None,
            role_level=75,
            preferred_language=None,
            **validators,
        )
        assert error is None
        assert patch == {"username": "updated", "role_level": 75}
        assert "email" not in patch
        assert "role_id" not in patch
