"""Test forum moderator permissions: ensure moderators can only moderate assigned categories.

CRITICAL SECURITY TEST: Verify that moderators cannot perform cross-category moderation.
This test suite ensures that:
1. Moderators can only moderate posts/threads in their assigned categories
2. Moderators cannot delete/edit/hide content in unassigned categories
3. Admins can moderate any category
4. Category-scoped permission checks are enforced on all moderation endpoints
"""

import pytest
from werkzeug.security import generate_password_hash
from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import (
    User,
    Role,
    ForumCategory,
    ForumThread,
    ForumPost,
    ModeratorAssignment,
)


@pytest.fixture
def app():
    """Create app with test config."""
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def setup_data(app):
    """Set up test data: users, categories, threads, posts."""
    # Create roles
    user_role = Role.query.filter_by(name="user").first()
    if not user_role:
        user_role = Role(name="user")
        db.session.add(user_role)

    mod_role = Role.query.filter_by(name="moderator").first()
    if not mod_role:
        mod_role = Role(name="moderator")
        db.session.add(mod_role)

    admin_role = Role.query.filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin")
        db.session.add(admin_role)

    db.session.commit()

    # Create users with real passwords
    author_password = "Author1"
    mod_a_password = "ModA1"
    mod_b_password = "ModB1"
    admin_password = "Admin1"

    user_author = User(
        username="author",
        email="author@test.com",
        password_hash=generate_password_hash(author_password),
        role_id=user_role.id,
    )
    user_mod_a = User(
        username="mod_a",
        email="mod_a@test.com",
        password_hash=generate_password_hash(mod_a_password),
        role_id=mod_role.id,
    )
    user_mod_b = User(
        username="mod_b",
        email="mod_b@test.com",
        password_hash=generate_password_hash(mod_b_password),
        role_id=mod_role.id,
    )
    user_admin = User(
        username="admin",
        email="admin@test.com",
        password_hash=generate_password_hash(admin_password),
        role_id=admin_role.id,
    )

    db.session.add_all([user_author, user_mod_a, user_mod_b, user_admin])
    db.session.commit()

    # Create categories
    cat_a = ForumCategory(
        slug="category-a",
        title="Category A",
        description="First category",
        sort_order=1,
        is_active=True,
        is_private=False,
    )
    cat_b = ForumCategory(
        slug="category-b",
        title="Category B",
        description="Second category",
        sort_order=2,
        is_active=True,
        is_private=False,
    )

    db.session.add_all([cat_a, cat_b])
    db.session.commit()

    # Assign moderators to categories
    # mod_a assigned to cat_a
    assign_a = ModeratorAssignment(
        user_id=user_mod_a.id,
        category_id=cat_a.id,
        assigned_by=user_admin.id,
    )
    # mod_b assigned to cat_b
    assign_b = ModeratorAssignment(
        user_id=user_mod_b.id,
        category_id=cat_b.id,
        assigned_by=user_admin.id,
    )

    db.session.add_all([assign_a, assign_b])
    db.session.commit()

    # Create threads and posts
    thread_cat_a = ForumThread(
        category_id=cat_a.id,
        author_id=user_author.id,
        slug="thread-cat-a",
        title="Thread in Category A",
        status="open",
    )
    thread_cat_b = ForumThread(
        category_id=cat_b.id,
        author_id=user_author.id,
        slug="thread-cat-b",
        title="Thread in Category B",
        status="open",
    )

    db.session.add_all([thread_cat_a, thread_cat_b])
    db.session.commit()

    post_cat_a = ForumPost(
        thread_id=thread_cat_a.id,
        author_id=user_author.id,
        content="Post in Category A",
        status="visible",
    )
    post_cat_b = ForumPost(
        thread_id=thread_cat_b.id,
        author_id=user_author.id,
        content="Post in Category B",
        status="visible",
    )

    db.session.add_all([post_cat_a, post_cat_b])
    db.session.commit()

    return {
        "users": {
            "author": user_author,
            "mod_a": user_mod_a,
            "mod_b": user_mod_b,
            "admin": user_admin,
        },
        "passwords": {
            "author": author_password,
            "mod_a": mod_a_password,
            "mod_b": mod_b_password,
            "admin": admin_password,
        },
        "categories": {
            "cat_a": cat_a,
            "cat_b": cat_b,
        },
        "threads": {
            "cat_a": thread_cat_a,
            "cat_b": thread_cat_b,
        },
        "posts": {
            "cat_a": post_cat_a,
            "cat_b": post_cat_b,
        },
    }


class TestModeratorPermissions:
    """Test that moderators can only moderate their assigned categories."""

    def test_mod_a_cannot_delete_post_in_cat_b(self, client, setup_data):
        """CRITICAL: Moderator A should NOT be able to delete a post in Category B."""
        post_cat_b = setup_data["posts"]["cat_b"]
        mod_a = setup_data["users"]["mod_a"]

        response = client.delete(
            f"/api/v1/forum/posts/{post_cat_b.id}",
            headers={"Authorization": f"Bearer {self._get_jwt_token(mod_a, client, setup_data)}"},
        )

        # Expected: 403 Forbidden (not authorized for Category B)
        assert response.status_code == 403, (
            f"Moderator A should not be able to delete post in Category B. "
            f"Got {response.status_code}: {response.get_json()}"
        )

    def test_mod_a_can_delete_post_in_cat_a(self, client, setup_data):
        """Moderator A should be able to delete a post in Category A."""
        post_cat_a = setup_data["posts"]["cat_a"]
        mod_a = setup_data["users"]["mod_a"]

        response = client.delete(
            f"/api/v1/forum/posts/{post_cat_a.id}",
            headers={"Authorization": f"Bearer {self._get_jwt_token(mod_a, client, setup_data)}"},
        )

        # Expected: 200 OK
        assert response.status_code == 200, (
            f"Moderator A should be able to delete post in Category A. "
            f"Got {response.status_code}: {response.get_json()}"
        )

    def test_admin_can_delete_post_in_any_category(self, client, setup_data):
        """Admins should be able to delete posts in any category."""
        post_cat_b = setup_data["posts"]["cat_b"]
        admin = setup_data["users"]["admin"]

        response = client.delete(
            f"/api/v1/forum/posts/{post_cat_b.id}",
            headers={"Authorization": f"Bearer {self._get_jwt_token(admin, client, setup_data)}"},
        )

        # Expected: 200 OK
        assert response.status_code == 200, (
            f"Admin should be able to delete post in any category. "
            f"Got {response.status_code}: {response.get_json()}"
        )

    def test_mod_cannot_lock_thread_in_unassigned_category(self, client, setup_data):
        """CRITICAL: Moderator B should NOT be able to lock a thread in Category A."""
        thread_cat_a = setup_data["threads"]["cat_a"]
        mod_b = setup_data["users"]["mod_b"]

        response = client.post(
            f"/api/v1/forum/threads/{thread_cat_a.id}/lock",
            headers={"Authorization": f"Bearer {self._get_jwt_token(mod_b, client, setup_data)}"},
        )

        # Expected: 403 Forbidden
        assert response.status_code == 403, (
            f"Moderator B should not be able to lock thread in Category A. "
            f"Got {response.status_code}: {response.get_json()}"
        )

    def test_mod_can_lock_thread_in_assigned_category(self, client, setup_data):
        """Moderator B should be able to lock a thread in Category B."""
        thread_cat_b = setup_data["threads"]["cat_b"]
        mod_b = setup_data["users"]["mod_b"]

        response = client.post(
            f"/api/v1/forum/threads/{thread_cat_b.id}/lock",
            headers={"Authorization": f"Bearer {self._get_jwt_token(mod_b, client, setup_data)}"},
        )

        # Expected: 200 OK
        assert response.status_code == 200, (
            f"Moderator B should be able to lock thread in Category B. "
            f"Got {response.status_code}: {response.get_json()}"
        )

    def test_mod_cannot_hide_post_in_unassigned_category(self, client, setup_data):
        """CRITICAL: Moderator A should NOT be able to hide a post in Category B."""
        post_cat_b = setup_data["posts"]["cat_b"]
        mod_a = setup_data["users"]["mod_a"]

        response = client.post(
            f"/api/v1/forum/posts/{post_cat_b.id}/hide",
            headers={"Authorization": f"Bearer {self._get_jwt_token(mod_a, client, setup_data)}"},
        )

        # Expected: 403 Forbidden
        assert response.status_code == 403, (
            f"Moderator A should not be able to hide post in Category B. "
            f"Got {response.status_code}: {response.get_json()}"
        )

    def test_mod_can_hide_post_in_assigned_category(self, client, setup_data):
        """Moderator A should be able to hide a post in Category A."""
        post_cat_a = setup_data["posts"]["cat_a"]
        mod_a = setup_data["users"]["mod_a"]

        response = client.post(
            f"/api/v1/forum/posts/{post_cat_a.id}/hide",
            headers={"Authorization": f"Bearer {self._get_jwt_token(mod_a, client, setup_data)}"},
        )

        # Expected: 200 OK
        assert response.status_code == 200, (
            f"Moderator A should be able to hide post in Category A. "
            f"Got {response.status_code}: {response.get_json()}"
        )

    def test_author_can_delete_own_post_regardless_of_moderator_assignment(
        self, client, setup_data
    ):
        """Authors should be able to delete their own posts regardless of moderator assignment."""
        post_cat_b = setup_data["posts"]["cat_b"]
        author = setup_data["users"]["author"]

        response = client.delete(
            f"/api/v1/forum/posts/{post_cat_b.id}",
            headers={"Authorization": f"Bearer {self._get_jwt_token(author, client, setup_data)}"},
        )

        # Expected: 200 OK
        assert response.status_code == 200, (
            f"Author should be able to delete their own post. "
            f"Got {response.status_code}: {response.get_json()}"
        )

    def _get_jwt_token(self, user, client, setup_data):
        """Helper to generate JWT token for a user."""
        # Get the password for this user from setup_data
        user_key = None
        for key, u in setup_data["users"].items():
            if u.id == user.id:
                user_key = key
                break

        if not user_key:
            raise ValueError(f"User {user.id} not found in setup_data")

        password = setup_data["passwords"][user_key]

        # Login to get a JWT token
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )

        if response.status_code != 200:
            raise ValueError(f"Failed to login user {user.username}: {response.get_json()}")

        data = response.get_json()
        return data["access_token"]


class TestModeratorAssignmentModel:
    """Test the ModeratorAssignment model."""

    def test_moderator_assignment_creation(self, app, setup_data):
        """Test that moderator assignments are created correctly."""
        assignments = ModeratorAssignment.query.all()

        assert len(assignments) == 2, "Should have 2 moderator assignments"
        assert assignments[0].user_id == setup_data["users"]["mod_a"].id
        assert assignments[0].category_id == setup_data["categories"]["cat_a"].id
        assert assignments[1].user_id == setup_data["users"]["mod_b"].id
        assert assignments[1].category_id == setup_data["categories"]["cat_b"].id

    def test_moderator_assignment_uniqueness(self, app, setup_data):
        """Test that duplicate assignments are prevented."""
        cat_a = setup_data["categories"]["cat_a"]
        mod_a = setup_data["users"]["mod_a"]

        # Try to create a duplicate assignment
        duplicate = ModeratorAssignment(
            user_id=mod_a.id,
            category_id=cat_a.id,
            assigned_by=setup_data["users"]["admin"].id,
        )
        db.session.add(duplicate)

        with pytest.raises(Exception):  # Should raise IntegrityError
            db.session.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
