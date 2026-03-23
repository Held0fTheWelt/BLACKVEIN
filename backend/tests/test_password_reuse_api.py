"""
Integration tests for password reuse prevention via API endpoint.
Tests the password change endpoint with reuse prevention.
"""
import pytest
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import User


class TestPasswordReuseAPI:
    """Test password reuse prevention through the API endpoint."""

    def test_api_password_change_blocks_reuse(self, app, client):
        """Test that API endpoint blocks password reuse."""
        with app.app_context():
            # Create a test user with auth token
            from app.services.user_service import create_user
            user, err = create_user("apiuser", "InitPass123!", email="api@example.com")
            assert err is None

            # Login to get token
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "apiuser", "password": "InitPass123!"},
                content_type="application/json",
            )
            assert response.status_code == 200
            token = response.get_json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Change password successfully
            resp = client.put(
                f"/api/v1/users/{user.id}/password",
                json={
                    "current_password": "InitPass123!",
                    "new_password": "NewPass123456!",
                },
                headers=headers,
            )
            assert resp.status_code == 200, f"Password change failed: {resp.get_json()}"

            # Try to change back to old password - should be blocked
            resp = client.put(
                f"/api/v1/users/{user.id}/password",
                json={
                    "current_password": "NewPass123456!",
                    "new_password": "InitPass123!",
                },
                headers=headers,
            )
            assert resp.status_code == 400
            error = resp.get_json().get("error", "")
            assert "Cannot reuse" in error or "last 3" in error, f"Unexpected error: {error}"

    def test_api_password_change_allows_rotation(self, app, client):
        """Test that old passwords can be reused after rotation."""
        with app.app_context():
            from app.services.user_service import create_user
            user, err = create_user("rotationuser", "Pass1234567!", email="rot@example.com")
            assert err is None

            # Helper to change password and get new token
            def change_and_login(username, old_pass, new_pass):
                response = client.post(
                    "/api/v1/auth/login",
                    json={"username": username, "password": old_pass},
                    content_type="application/json",
                )
                assert response.status_code == 200
                token = response.get_json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                resp = client.put(
                    f"/api/v1/users/{user.id}/password",
                    json={
                        "current_password": old_pass,
                        "new_password": new_pass,
                    },
                    headers=headers,
                )
                assert resp.status_code == 200
                return new_pass

            # Cycle through 5 passwords to rotate out the original
            # History keeps last 3 old passwords, so after 5 changes original is gone
            current = change_and_login("rotationuser", "Pass1234567!", "Pass2New9999!")
            current = change_and_login("rotationuser", current, "Pass3New8888!")
            current = change_and_login("rotationuser", current, "Pass4New7777!")
            current = change_and_login("rotationuser", current, "Pass5New6666!")
            current = change_and_login("rotationuser", current, "Pass6New5555!")

            # Now try to go back to original password - should work
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "rotationuser", "password": current},
                content_type="application/json",
            )
            assert response.status_code == 200
            token = response.get_json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            resp = client.put(
                f"/api/v1/users/{user.id}/password",
                json={
                    "current_password": current,
                    "new_password": "Pass1234567!",  # Original password
                },
                headers=headers,
            )
            assert resp.status_code == 200, f"Original password should be allowed after rotation: {resp.get_json()}"
            assert "Password updated" in resp.get_json().get("message", "")
