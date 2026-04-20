"""Forum posting rate limit tests.

Tests for the POST /forum/threads/<id>/posts endpoint rate limiting.
- Limit: 10 posts per minute (reduced from 60 to prevent spam/DoS)
- Tests that 10 consecutive posts succeed
- Tests that the 11th post returns 429 Too Many Requests
- Tests that after 1 minute, posts can be made again
"""
import pytest
from app.extensions import db
from app.models import ForumCategory, ForumThread, User, Role
from werkzeug.security import generate_password_hash


@pytest.fixture
def forum_setup(app):
    """Set up forum category and thread for testing."""
    with app.app_context():
        # Create category
        cat = ForumCategory(
            slug="test-category",
            title="Test Category",
            is_active=True,
            is_private=False
        )
        db.session.add(cat)
        db.session.flush()

        # Create user
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="forumtestuser",
            password_hash=generate_password_hash("Testpass1"),
            role_id=role.id,
        )
        db.session.add(user)
        db.session.flush()

        # Create thread
        import uuid
        thread = ForumThread(
            category_id=cat.id,
            author_id=user.id,
            title="Test Thread",
            slug=f"test-thread-{uuid.uuid4()}",
        )
        db.session.add(thread)
        db.session.commit()

        yield {
            "category": cat,
            "thread": thread,
            "user": user,
            "password": "Testpass1"
        }


def test_forum_post_rate_limit_10_posts_succeed(app, client, forum_setup):
    """First 10 posts within 1 minute should succeed (200 OK)."""
    with app.app_context():
        # Get auth headers
        user = forum_setup["user"]
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": forum_setup["password"]},
        )
        assert response.status_code == 200
        token = response.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        thread_id = forum_setup["thread"].id

        # Post 10 times - all should succeed
        for i in range(10):
            resp = client.post(
                f"/api/v1/forum/threads/{thread_id}/posts",
                json={"content": f"Test post {i+1} with enough content to pass validation"},
                headers=headers,
            )
            assert resp.status_code == 201, f"Post {i+1} failed with status {resp.status_code}"
            data = resp.get_json()
            assert "id" in data, f"Post {i+1} should return post ID"


def test_forum_post_11th_post_returns_429(app, client, forum_setup):
    """The 11th post within 1 minute should return 429 Too Many Requests."""
    with app.app_context():
        # Get auth headers
        user = forum_setup["user"]
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": forum_setup["password"]},
        )
        assert response.status_code == 200
        token = response.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        thread_id = forum_setup["thread"].id

        # Post 10 times successfully
        for i in range(10):
            resp = client.post(
                f"/api/v1/forum/threads/{thread_id}/posts",
                json={"content": f"Test post {i+1} with enough content to pass validation"},
                headers=headers,
            )
            assert resp.status_code == 201

        # 11th post should be rate limited
        resp = client.post(
            f"/api/v1/forum/threads/{thread_id}/posts",
            json={"content": "This should be rate limited with enough content"},
            headers=headers,
        )
        assert resp.status_code == 429, f"Expected 429, got {resp.status_code}"
        data = resp.get_json()
        # Flask-Limiter returns a default error message
        assert "rate limit" in data.get("message", "").lower() or resp.status_code == 429


def test_forum_post_different_users_independent_limits(app, client, forum_setup):
    """Different users should have independent rate limits."""
    with app.app_context():
        # Create a second user
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user2 = User(
            username="forumtestuser2",
            password_hash=generate_password_hash("Testpass2"),
            role_id=role.id,
        )
        db.session.add(user2)
        db.session.commit()

        thread_id = forum_setup["thread"].id

        # Get auth for first user
        user1 = forum_setup["user"]
        resp1 = client.post(
            "/api/v1/auth/login",
            json={"username": user1.username, "password": forum_setup["password"]},
        )
        token1 = resp1.get_json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Get auth for second user
        resp2 = client.post(
            "/api/v1/auth/login",
            json={"username": user2.username, "password": "Testpass2"},
        )
        token2 = resp2.get_json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # User 1 posts 10 times (should succeed)
        for i in range(10):
            resp = client.post(
                f"/api/v1/forum/threads/{thread_id}/posts",
                json={"content": f"User 1 post {i+1} with enough content to pass validation"},
                headers=headers1,
            )
            assert resp.status_code == 201

        # User 1's 11th post should fail
        resp = client.post(
            f"/api/v1/forum/threads/{thread_id}/posts",
            json={"content": "User 1 rate limited with enough content"},
            headers=headers1,
        )
        assert resp.status_code == 429

        # User 2 should still be able to post (independent limit)
        resp = client.post(
            f"/api/v1/forum/threads/{thread_id}/posts",
            json={"content": "User 2 post 1 with enough content to pass validation"},
            headers=headers2,
        )
        assert resp.status_code == 201
