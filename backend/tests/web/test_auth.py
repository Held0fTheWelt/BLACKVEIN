"""Tests for web/auth.py authentication helpers and decorators."""
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest

from app.web.auth import (
    is_safe_redirect,
    require_web_admin,
    require_web_login,
    _user_is_banned,
    _user_needs_verification,
)


class TestIsSafeRedirect:
    """Tests for is_safe_redirect function."""

    def test_safe_redirect_root_path(self):
        """Test that root path is safe."""
        assert is_safe_redirect("/") is True

    def test_safe_redirect_nested_path(self):
        """Test that nested paths are safe."""
        assert is_safe_redirect("/dashboard") is True
        assert is_safe_redirect("/admin/users") is True
        assert is_safe_redirect("/page?query=value") is True

    def test_safe_redirect_with_query_string(self):
        """Test that paths with query strings are safe."""
        assert is_safe_redirect("/login?next=/dashboard") is True

    def test_unsafe_redirect_external_url(self):
        """Test that external URLs are not safe."""
        assert is_safe_redirect("https://evil.com") is False
        assert is_safe_redirect("http://attacker.com/path") is False

    def test_unsafe_redirect_protocol_only(self):
        """Test that URLs with scheme are not safe."""
        assert is_safe_redirect("//evil.com") is False
        assert is_safe_redirect("javascript:alert('xss')") is False

    def test_unsafe_redirect_empty_string(self):
        """Test that empty string is not safe."""
        assert is_safe_redirect("") is False

    def test_unsafe_redirect_whitespace_only(self):
        """Test that whitespace-only string is not safe."""
        assert is_safe_redirect("   ") is False

    def test_unsafe_redirect_none(self):
        """Test that None is not safe."""
        assert is_safe_redirect(None) is False

    def test_unsafe_redirect_relative_with_scheme(self):
        """Test relative URLs with scheme are unsafe."""
        assert is_safe_redirect("http://") is False

    def test_safe_redirect_with_fragment(self):
        """Test paths with fragments are safe."""
        assert is_safe_redirect("/page#section") is True


class TestUserNeedsVerification:
    """Tests for _user_needs_verification function."""

    def test_verification_disabled(self):
        """Test when email verification is disabled."""
        user = MagicMock(email="user@example.com", email_verified_at=None)

        with patch("app.web.auth.current_app") as mock_app:
            mock_config = MagicMock()
            mock_config.get.return_value = False
            mock_app.config = mock_config

            result = _user_needs_verification(user)

            assert result is False

    def test_verification_enabled_user_verified(self):
        """Test when verification is enabled and user is verified."""
        from datetime import datetime

        user = MagicMock(
            email="user@example.com",
            email_verified_at=datetime.now(),
        )

        with patch("app.web.auth.current_app") as mock_app:
            mock_config = MagicMock()
            mock_config.get.return_value = True
            mock_app.config = mock_config

            result = _user_needs_verification(user)

            assert result is False

    def test_verification_enabled_user_unverified(self):
        """Test when verification is enabled and user is unverified."""
        user = MagicMock(email="user@example.com", email_verified_at=None)

        with patch("app.web.auth.current_app") as mock_app:
            mock_config = MagicMock()
            mock_config.get.return_value = True
            mock_app.config = mock_config

            result = _user_needs_verification(user)

            assert result is True

    def test_verification_enabled_no_email(self):
        """Test when verification is enabled but user has no email."""
        user = MagicMock(email=None, email_verified_at=None)

        with patch("app.web.auth.current_app") as mock_app:
            mock_config = MagicMock()
            mock_config.get.return_value = True
            mock_app.config = mock_config

            result = _user_needs_verification(user)

            assert result is False

    def test_verification_enabled_none_user(self):
        """Test when user is None."""
        with patch("app.web.auth.current_app") as mock_app:
            mock_config = MagicMock()
            mock_config.get.return_value = True
            mock_app.config = mock_config

            result = _user_needs_verification(None)

            assert result is False


class TestUserIsBanned:
    """Tests for _user_is_banned function."""

    def test_user_not_banned(self):
        """Test when user is not banned."""
        user = MagicMock(is_banned=False)

        result = _user_is_banned(user)

        assert result is False

    def test_user_is_banned(self):
        """Test when user is banned."""
        user = MagicMock(is_banned=True)

        result = _user_is_banned(user)

        assert result is True

    def test_user_without_is_banned_attribute(self):
        """Test when user doesn't have is_banned attribute."""
        user = MagicMock(spec=[])

        result = _user_is_banned(user)

        assert result is False

    def test_none_user(self):
        """Test when user is None."""
        result = _user_is_banned(None)

        assert result is False


class TestRequireWebLogin:
    """Tests for require_web_login decorator."""

    def test_decorator_preserves_function_name(self):
        """Test that decorator preserves function metadata using wraps."""
        def my_view():
            """Original docstring."""
            return "result"

        decorated = require_web_login(my_view)

        assert decorated.__name__ == "my_view"
        assert decorated.__doc__ == "Original docstring."

    def test_decorator_is_callable(self):
        """Test that decorator returns a callable."""
        def my_view():
            return "result"

        decorated = require_web_login(my_view)

        assert callable(decorated)

    def test_missing_session_redirects_to_frontend_login(self, app):
        """Decorator must not depend on removed backend web auth endpoints."""
        app.config["FRONTEND_URL"] = "https://frontend.example"

        @require_web_login
        def my_view():
            return "result"

        with app.test_request_context("/protected"):
            response = my_view()

        assert response.status_code == 302
        assert response.headers["Location"] == "https://frontend.example/login"


class TestRequireWebAdmin:
    """Tests for require_web_admin decorator."""

    def test_decorator_preserves_function_name(self):
        """Test that decorator preserves function metadata using wraps."""
        def admin_view():
            """Admin view docstring."""
            return "admin result"

        decorated = require_web_admin(admin_view)

        assert decorated.__name__ == "admin_view"
        assert decorated.__doc__ == "Admin view docstring."

    def test_decorator_is_callable(self):
        """Test that decorator returns a callable."""
        def admin_view():
            return "admin result"

        decorated = require_web_admin(admin_view)

        assert callable(decorated)

    def test_missing_session_redirects_to_frontend_login(self, app):
        """Decorator must not depend on removed backend web auth endpoints."""
        app.config["FRONTEND_URL"] = "https://frontend.example"

        @require_web_admin
        def admin_view():
            return "admin result"

        with app.test_request_context("/admin-only"):
            response = admin_view()

        assert response.status_code == 302
        assert response.headers["Location"] == "https://frontend.example/login"
