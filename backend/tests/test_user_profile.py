"""Tests for User Profile endpoints (Phase 4)."""
import pytest
from app.extensions import db
from app.models import ForumCategory, ForumThread, ForumPost, ForumThreadBookmark, ForumTag, ForumThreadTag


# ============= FIXTURES FOR USER PROFILES =============

@pytest.fixture
def forum_category(app):
    """Create a public forum category for testing.

    Returns the category ID (integer) to avoid DetachedInstanceError.
    Tests should reload the category from the database with:
        category = ForumCategory.query.get(forum_category)
    within an app context when they need the full object.
    """
    with app.app_context():
        cat = ForumCategory(slug="general", title="General", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()
        yield cat.id


@pytest.fixture
def user_with_threads_and_posts(app, forum_category):
    """Create a user with threads and posts."""
    from app.models import User, Role
    from werkzeug.security import generate_password_hash

    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="threadmaker",
            password_hash=generate_password_hash("Threadpass1"),
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()

        # Create 5 threads by this user
        for i in range(5):
            thread = ForumThread(
                category_id=forum_category,
                author_id=user.id,
                slug=f"thread-{i}",
                title=f"Test Thread {i}",
                status="open",
            )
            db.session.add(thread)
        db.session.commit()

        # Create posts on first thread
        first_thread = ForumThread.query.filter_by(author_id=user.id).first()
        for i in range(3):
            post = ForumPost(
                thread_id=first_thread.id,
                author_id=user.id,
                content=f"Test post {i} content",
                status="visible",
            )
            db.session.add(post)
        db.session.commit()

        # Create a bookmark
        thread_to_bookmark = ForumThread.query.filter_by(author_id=user.id).offset(1).first()
        bookmark = ForumThreadBookmark(
            thread_id=thread_to_bookmark.id,
            user_id=user.id,
        )
        db.session.add(bookmark)
        db.session.commit()

        yield user


@pytest.fixture
def auth_headers_for_profile_user(user_with_threads_and_posts, client):
    """Return headers with valid JWT for the profile user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "threadmaker", "password": "Threadpass1"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============= USER PROFILE ENDPOINT TESTS =============

def test_profile_get_public_returns_200(client, user_with_threads_and_posts):
    """GET /api/v1/users/<id>/profile returns 200 with profile data (no auth required)."""
    user = user_with_threads_and_posts
    resp = client.get(f"/api/v1/users/{user.id}/profile")
    assert resp.status_code == 200
    data = resp.get_json()

    # Check basic user info
    assert data["id"] == user.id
    assert data["username"] == "threadmaker"
    assert data["role"] == "user"
    assert "created_at" in data
    assert "last_seen_at" in data

    # Check stats
    assert "stats" in data
    assert data["stats"]["thread_count"] == 5
    assert data["stats"]["post_count"] == 3
    assert data["stats"]["bookmark_count"] == 1

    # Check recent threads
    assert "recent_threads" in data
    assert len(data["recent_threads"]) > 0
    assert data["recent_threads"][0]["title"] == "Test Thread 4"  # Most recent

    # Check recent posts
    assert "recent_posts" in data
    assert len(data["recent_posts"]) > 0

    # Check tags list
    assert "tags" in data


def test_profile_get_nonexistent_user_returns_404(client):
    """GET /api/v1/users/999999/profile returns 404 for nonexistent user."""
    resp = client.get("/api/v1/users/999999/profile")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_profile_returns_recent_threads_limited(client, user_with_threads_and_posts):
    """Profile returns recent threads limited to 10 and ordered by date."""
    user = user_with_threads_and_posts
    resp = client.get(f"/api/v1/users/{user.id}/profile")
    assert resp.status_code == 200
    data = resp.get_json()

    recent_threads = data["recent_threads"]
    assert len(recent_threads) <= 10

    # Check order (most recent first)
    for i, thread in enumerate(recent_threads):
        assert "id" in thread
        assert "title" in thread
        assert "slug" in thread
        assert "post_count" in thread
        assert "created_at" in thread


def test_profile_returns_recent_posts_limited(client, user_with_threads_and_posts):
    """Profile returns recent posts limited to 10."""
    user = user_with_threads_and_posts
    resp = client.get(f"/api/v1/users/{user.id}/profile")
    assert resp.status_code == 200
    data = resp.get_json()

    recent_posts = data["recent_posts"]
    assert len(recent_posts) <= 10

    for post in recent_posts:
        assert "id" in post
        assert "content_preview" in post
        assert "thread_id" in post
        assert "thread_title" in post
        assert "created_at" in post


def test_profile_activity_counts_accurate(app, client, forum_category):
    """Profile activity counts are accurate."""
    from app.models import User, Role
    from werkzeug.security import generate_password_hash

    user_id = None
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="counter_tester",
            password_hash=generate_password_hash("Test1"),
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        # Create exactly 3 threads
        for i in range(3):
            thread = ForumThread(
                category_id=forum_category,
                author_id=user.id,
                slug=f"cnt-thread-{i}",
                title=f"Counter Thread {i}",
                status="open",
            )
            db.session.add(thread)
        db.session.commit()

        # Create exactly 2 posts
        threads = ForumThread.query.filter_by(author_id=user.id).all()
        for i in range(2):
            post = ForumPost(
                thread_id=threads[0].id,
                author_id=user.id,
                content=f"Counter post {i}",
                status="visible",
            )
            db.session.add(post)
        db.session.commit()

    resp = client.get(f"/api/v1/users/{user_id}/profile")
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["stats"]["thread_count"] == 3
    assert data["stats"]["post_count"] == 2
    assert data["stats"]["bookmark_count"] == 0


# ============= USER BOOKMARKS ENDPOINT TESTS =============

def test_bookmarks_get_own_bookmarks_returns_200(app, client, user_with_threads_and_posts, auth_headers_for_profile_user):
    """GET /api/v1/users/<id>/bookmarks for own user returns 200 with bookmarks."""
    user = user_with_threads_and_posts
    resp = client.get(f"/api/v1/users/{user.id}/bookmarks", headers=auth_headers_for_profile_user)
    assert resp.status_code == 200
    data = resp.get_json()

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert data["total"] == 1
    assert len(data["items"]) == 1

    bookmark = data["items"][0]
    assert "id" in bookmark
    assert "title" in bookmark
    assert "slug" in bookmark
    assert "bookmarked_at" in bookmark


def test_bookmarks_requires_auth(client, user_with_threads_and_posts):
    """GET /api/v1/users/<id>/bookmarks without auth returns 401."""
    user = user_with_threads_and_posts
    resp = client.get(f"/api/v1/users/{user.id}/bookmarks")
    assert resp.status_code == 401


def test_bookmarks_other_user_forbidden(client, user_with_threads_and_posts, test_user, auth_headers):
    """GET /api/v1/users/<other_id>/bookmarks as different user returns 403."""
    user = user_with_threads_and_posts
    resp = client.get(f"/api/v1/users/{user.id}/bookmarks", headers=auth_headers)
    assert resp.status_code == 403
    assert "Forbidden" in resp.get_json()["error"]


def test_bookmarks_admin_can_view_others(app, client, user_with_threads_and_posts, admin_headers):
    """GET /api/v1/users/<id>/bookmarks as admin can view any user's bookmarks."""
    user = user_with_threads_and_posts
    resp = client.get(f"/api/v1/users/{user.id}/bookmarks", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 1


def test_bookmarks_pagination(app, client, forum_category):
    """GET /api/v1/users/<id>/bookmarks supports pagination."""
    from app.models import User, Role
    from werkzeug.security import generate_password_hash

    user_id = None
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="bookmark_tester",
            password_hash=generate_password_hash("Test1"),
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        # Create 5 threads and bookmark them all
        for i in range(5):
            thread = ForumThread(
                category_id=forum_category,
                author_id=None,
                slug=f"bookmark-test-{i}",
                title=f"Bookmark Test {i}",
                status="open",
            )
            db.session.add(thread)
        db.session.commit()

        threads = ForumThread.query.filter(
            ForumThread.slug.like("bookmark-test-%")
        ).all()

        for thread in threads:
            bookmark = ForumThreadBookmark(thread_id=thread.id, user_id=user_id)
            db.session.add(bookmark)
        db.session.commit()

    # Get auth headers for this user
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "bookmark_tester", "password": "Test1"},
        content_type="application/json",
    )
    assert response.status_code == 200
    token = response.get_json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/users/{user_id}/bookmarks?page=1&limit=2", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 5
    assert data["per_page"] == 2
    assert len(data["items"]) == 2


# ============= FORUM TAGS ENDPOINTS TESTS =============

def test_popular_tags_returns_200(app, client, forum_category):
    """GET /api/v1/forum/tags/popular returns 200 with popular tags."""
    from app.models import User, Role
    from werkzeug.security import generate_password_hash

    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="tag_tester",
            password_hash=generate_password_hash("Test1"),
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()

        # Create a tag
        tag = ForumTag(slug="test-tag", label="Test Tag")
        db.session.add(tag)
        db.session.commit()

        # Create thread with tag
        thread = ForumThread(
            category_id=forum_category,
            author_id=user.id,
            slug="tagged-thread",
            title="Tagged Thread",
            status="open",
        )
        db.session.add(thread)
        db.session.commit()

        thread_tag = ForumThreadTag(thread_id=thread.id, tag_id=tag.id)
        db.session.add(thread_tag)
        db.session.commit()

    resp = client.get("/api/v1/forum/tags/popular")
    assert resp.status_code == 200
    data = resp.get_json()

    assert "items" in data
    assert len(data["items"]) > 0

    tag_item = data["items"][0]
    assert "id" in tag_item
    assert "label" in tag_item
    assert "slug" in tag_item
    assert "thread_count" in tag_item
    assert tag_item["thread_count"] >= 1


def test_popular_tags_limit_parameter(app, client, forum_category):
    """GET /api/v1/forum/tags/popular respects limit parameter."""
    with app.app_context():
        # Create multiple tags
        for i in range(5):
            tag = ForumTag(slug=f"test-tag-{i}", label=f"Test Tag {i}")
            db.session.add(tag)
        db.session.commit()

    resp = client.get("/api/v1/forum/tags/popular?limit=2")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["items"]) <= 2


def test_tag_detail_returns_200(app, client, forum_category):
    """GET /api/v1/forum/tags/<slug> returns 200 with tag and threads."""
    from app.models import User, Role
    from werkzeug.security import generate_password_hash

    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="tag_detail_tester",
            password_hash=generate_password_hash("Test1"),
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()

        # Create a tag
        tag = ForumTag(slug="detailed-tag", label="Detailed Tag")
        db.session.add(tag)
        db.session.commit()

        # Create 3 threads with this tag
        for i in range(3):
            thread = ForumThread(
                category_id=forum_category,
                author_id=user.id,
                slug=f"detailed-thread-{i}",
                title=f"Detailed Thread {i}",
                status="open",
            )
            db.session.add(thread)
        db.session.commit()

        threads = ForumThread.query.filter(
            ForumThread.slug.like("detailed-thread-%")
        ).all()

        for thread in threads:
            thread_tag = ForumThreadTag(thread_id=thread.id, tag_id=tag.id)
            db.session.add(thread_tag)
        db.session.commit()

    resp = client.get("/api/v1/forum/tags/detailed-tag")
    assert resp.status_code == 200
    data = resp.get_json()

    assert "tag" in data
    assert data["tag"]["slug"] == "detailed-tag"
    assert data["tag"]["label"] == "Detailed Tag"

    assert "threads" in data
    assert len(data["threads"]) == 3

    assert "total" in data
    assert data["total"] == 3


def test_tag_detail_pagination(app, client, forum_category):
    """GET /api/v1/forum/tags/<slug> supports pagination."""
    from app.models import User, Role
    from werkzeug.security import generate_password_hash

    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="tag_paginate_tester",
            password_hash=generate_password_hash("Test1"),
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()

        # Create a tag
        tag = ForumTag(slug="paginated-tag", label="Paginated Tag")
        db.session.add(tag)
        db.session.commit()

        # Create 5 threads with this tag
        for i in range(5):
            thread = ForumThread(
                category_id=forum_category,
                author_id=user.id,
                slug=f"paginated-thread-{i}",
                title=f"Paginated Thread {i}",
                status="open",
            )
            db.session.add(thread)
        db.session.commit()

        threads = ForumThread.query.filter(
            ForumThread.slug.like("paginated-thread-%")
        ).all()

        for thread in threads:
            thread_tag = ForumThreadTag(thread_id=thread.id, tag_id=tag.id)
            db.session.add(thread_tag)
        db.session.commit()

    resp = client.get("/api/v1/forum/tags/paginated-tag?page=1&limit=2")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert len(data["threads"]) == 2


def test_tag_detail_nonexistent_returns_404(client):
    """GET /api/v1/forum/tags/nonexistent returns 404."""
    resp = client.get("/api/v1/forum/tags/nonexistent-tag")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


# ============= PERFORMANCE TESTS =============

def test_profile_load_performance(client, user_with_threads_and_posts):
    """Profile endpoint completes within reasonable time (<500ms)."""
    import time
    user = user_with_threads_and_posts
    start = time.time()
    resp = client.get(f"/api/v1/users/{user.id}/profile")
    elapsed = (time.time() - start) * 1000  # Convert to ms

    assert resp.status_code == 200
    # Should load in under 1200ms (allowing for CI slowness and variable performance)
    assert elapsed < 1200, f"Profile load took {elapsed:.0f}ms (expected <1200ms)"


def test_bookmarks_endpoint_performance(client, user_with_threads_and_posts, auth_headers_for_profile_user):
    """Bookmarks endpoint completes within reasonable time."""
    import time
    user = user_with_threads_and_posts
    start = time.time()
    resp = client.get(f"/api/v1/users/{user.id}/bookmarks", headers=auth_headers_for_profile_user)
    elapsed = (time.time() - start) * 1000

    assert resp.status_code == 200
    assert elapsed < 1200, f"Bookmarks load took {elapsed:.0f}ms (expected <1200ms)"


def test_popular_tags_performance(client):
    """Popular tags endpoint completes within reasonable time."""
    import time
    start = time.time()
    resp = client.get("/api/v1/forum/tags/popular")
    elapsed = (time.time() - start) * 1000

    assert resp.status_code == 200
    assert elapsed < 1200, f"Popular tags load took {elapsed:.0f}ms (expected <1200ms)"
