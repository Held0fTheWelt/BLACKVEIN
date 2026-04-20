"""Registration, forum, and news constraint validation tests (split from former test_coverage_expansion)."""


class TestConstraintValidation:
    """Test database constraints and validation rules."""

    def test_duplicate_username_rejected(self, client, test_user, app):
        """Registering with duplicate username fails."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "password": "NewPass1",
                "email": "new@example.com",
            },
        )
        assert response.status_code == 409
        assert "username" in response.get_json().get("error", "").lower()

    def test_duplicate_email_rejected(self, client, test_user_with_email, app):
        """Registering with duplicate email fails."""
        user, _ = test_user_with_email
        with app.app_context():
            existing_email = user.email

        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser2",
                "password": "NewPass1",
                "email": existing_email,
            },
        )
        assert response.status_code == 409

    def test_invalid_email_format_rejected(self, client):
        """Invalid email formats rejected during registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "validuser",
                "password": "ValidPass1",
                "email": "not-an-email",
            },
        )
        assert response.status_code == 400
        assert "email" in response.get_json().get("error", "").lower()

    def test_weak_password_rejected(self, client):
        """Weak passwords rejected."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "validuser",
                "password": "weak",
                "email": "user@example.com",
            },
        )
        assert response.status_code == 400
        assert "password" in response.get_json().get("error", "").lower()

    def test_forum_thread_requires_category(self, client, admin_headers, app):
        """Forum thread must reference valid category."""
        response = client.post(
            "/api/v1/forum/categories/999/threads",
            headers=admin_headers,
            json={"title": "Test", "content": "Test content"},
        )
        assert response.status_code == 404

    def test_news_duplicate_slug_rejected(self, client, admin_headers, app):
        """News articles with duplicate slugs rejected."""
        response1 = client.post(
            "/api/v1/news",
            headers=admin_headers,
            json={
                "title": "Unique Article",
                "content": "Content",
                "slug": "unique-article",
            },
        )
        assert response1.status_code == 201

        response2 = client.post(
            "/api/v1/news",
            headers=admin_headers,
            json={
                "title": "Another Article",
                "content": "Content",
                "slug": "unique-article",
            },
        )
        assert response2.status_code == 409
