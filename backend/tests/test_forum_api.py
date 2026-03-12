"""Forum API tests: comprehensive coverage of visibility, permissions, counters, reports, moderation, and search."""
from datetime import datetime, timezone

import pytest

from app.extensions import db
from app.models import ForumCategory, ForumThread, ForumPost, ForumPostLike, ForumReport, User


# ============= CATEGORY VISIBILITY & ACCESS TESTS =============

@pytest.mark.usefixtures("app")
def test_public_category_visible_to_all(client):
    """Public categories are visible to all users (with or without JWT)."""
    with client.application.app_context():
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    resp = client.get("/api/v1/forum/categories")
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(c["slug"] == "public" for c in data["items"])


@pytest.mark.usefixtures("app")
def test_private_category_hidden_from_normal_users(client, auth_headers):
    """Private categories are hidden from non-moderator users."""
    with client.application.app_context():
        cat = ForumCategory(slug="private", title="Private", is_active=True, is_private=True)
        db.session.add(cat)
        db.session.commit()

    # Normal user cannot see private category
    resp = client.get("/api/v1/forum/categories", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert not any(c["slug"] == "private" for c in data["items"])


def test_inactive_category_only_visible_to_admins(app, client, admin_headers):
    """Inactive categories only visible to admins."""
    with app.app_context():
        cat = ForumCategory(slug="inactive", title="Inactive", is_active=False, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # Admin can see
    resp = client.get("/api/v1/forum/categories", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(c["slug"] == "inactive" for c in data["items"])


def test_category_with_required_role(app, client, auth_headers):
    """Categories with required_role block users with lower role."""
    with app.app_context():
        # Create moderator-only category
        cat = ForumCategory(
            slug="mod-only",
            title="Mod Only",
            is_active=True,
            is_private=False,
            required_role="moderator"
        )
        db.session.add(cat)
        db.session.commit()

    # Normal user cannot see
    resp = client.get("/api/v1/forum/categories", headers=auth_headers)
    data = resp.get_json()
    assert not any(c["slug"] == "mod-only" for c in data["items"])


# ============= THREAD CREATION & VISIBILITY TESTS =============

def test_thread_creation_requires_auth(app, client):
    """Creating a thread requires authentication."""
    with app.app_context():
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    resp = client.post(
        "/api/v1/forum/categories/public/threads",
        json={"title": "Test", "content": "Content"},
    )
    assert resp.status_code == 401


def test_thread_creation_sets_author(app, client, auth_headers):
    """Created thread has correct author_username in response."""
    with app.app_context():
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    resp = client.post(
        "/api/v1/forum/categories/public/threads",
        json={"title": "My Thread", "content": "Content here"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["title"] == "My Thread"
    assert data["author_username"] == "testuser"
    assert data["reply_count"] == 0  # Initial post not counted in reply_count


def test_hidden_threads_not_listed_for_normal_user(client):
    """Hidden/archived threads must not appear in category listings for normal users."""
    with client.application.app_context():
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        visible_thread = ForumThread(category_id=cat.id, slug="visible", title="Visible", status="open")
        hidden_thread = ForumThread(category_id=cat.id, slug="hidden", title="Hidden", status="hidden")
        db.session.add_all([visible_thread, hidden_thread])
        db.session.commit()

    resp = client.get("/api/v1/forum/categories/public/threads")
    assert resp.status_code == 200
    data = resp.get_json()
    slugs = {t["slug"] for t in data["items"]}
    assert "visible" in slugs
    assert "hidden" not in slugs


def test_deleted_threads_not_visible_to_normal_users(client):
    """Soft-deleted threads are not visible to normal users."""
    with client.application.app_context():
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="deleted-thread", title="Will be deleted", status="deleted")
        db.session.add(thread)
        db.session.commit()

    resp = client.get(f"/api/v1/forum/threads/deleted-thread")
    assert resp.status_code == 404


# ============= POST CREATION & VISIBILITY TESTS =============

def test_post_creation_requires_auth(app, client):
    """Creating a post requires authentication."""
    with app.app_context():
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open")
        db.session.add(thread)
        db.session.commit()
        thread_id = thread.id

    resp = client.post(
        f"/api/v1/forum/threads/{thread_id}/posts",
        json={"content": "Reply"},
    )
    assert resp.status_code == 401


def test_post_author_username_in_response(app, client, auth_headers):
    """Post responses include author_username."""
    thread_id = None
    with app.app_context():
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open")
        db.session.add(thread)
        db.session.commit()
        thread_id = thread.id

    resp = client.post(
        f"/api/v1/forum/threads/{thread_id}/posts",
        json={"content": "My post"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["author_username"] == "testuser"


def test_hidden_posts_not_visible_to_normal_users(app, client, auth_headers):
    """Hidden posts should not appear in thread listings for normal users."""
    thread_id = None
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open")
        db.session.add(thread)
        db.session.flush()

        visible_post = ForumPost(thread_id=thread.id, author_id=user.id, content="visible", status="visible")
        hidden_post = ForumPost(thread_id=thread.id, author_id=user.id, content="hidden", status="hidden")
        db.session.add_all([visible_post, hidden_post])
        db.session.commit()
        thread_id = thread.id

    resp = client.get(f"/api/v1/forum/threads/{thread_id}/posts", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    contents = {p["content"] for p in data["items"]}
    assert "visible" in contents
    assert "hidden" not in contents


# ============= LIKE/UNLIKE TESTS =============

def test_like_requires_visibility(app, client, auth_headers):
    """Users cannot like posts in categories they cannot access."""
    with app.app_context():
        cat = ForumCategory(slug="private", title="Private", is_active=True, is_private=True)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="private-thread", title="Private", status="open")
        db.session.add(thread)
        db.session.flush()
        user = User.query.filter_by(username="testuser").first()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="secret", status="visible")
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    resp = client.post(f"/api/v1/forum/posts/{post_id}/like", headers=auth_headers)
    assert resp.status_code in (403, 404)


def test_like_post_increments_counter(app, client, auth_headers):
    """Liking a post increments like_count and sets liked_by_me."""
    post_id = None
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open")
        db.session.add(thread)
        db.session.flush()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="post", status="visible", like_count=0)
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    resp = client.post(f"/api/v1/forum/posts/{post_id}/like", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["like_count"] == 1
    assert data["liked_by_me"] is True


def test_unlike_post_decrements_counter(app, client, auth_headers):
    """Unliking a post decrements like_count."""
    post_id = None
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open")
        db.session.add(thread)
        db.session.flush()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="post", status="visible", like_count=1)
        db.session.add(post)
        db.session.flush()
        like = ForumPostLike(post_id=post.id, user_id=user.id)
        db.session.add(like)
        db.session.commit()
        post_id = post.id

    resp = client.delete(f"/api/v1/forum/posts/{post_id}/like", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["like_count"] == 0
    assert data["liked_by_me"] is False


def test_duplicate_like_prevention(app, client, auth_headers):
    """Liking same post twice should not increment counter twice."""
    post_id = None
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open")
        db.session.add(thread)
        db.session.flush()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="post", status="visible", like_count=0)
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    # First like
    resp1 = client.post(f"/api/v1/forum/posts/{post_id}/like", headers=auth_headers)
    assert resp1.status_code == 200
    assert resp1.get_json()["like_count"] == 1

    # Second like attempt (should fail or idempotent)
    resp2 = client.post(f"/api/v1/forum/posts/{post_id}/like", headers=auth_headers)
    assert resp2.status_code in (200, 409)  # 409 if conflict, 200 if idempotent


def test_liked_by_me_flag_in_post_list(app, client, auth_headers):
    """Post list includes liked_by_me flag."""
    thread_id = None
    post_id = None
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open")
        db.session.add(thread)
        db.session.flush()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="post", status="visible", like_count=0)
        db.session.add(post)
        db.session.commit()

        # Like the post
        client.post(f"/api/v1/forum/posts/{post.id}/like", headers=auth_headers)
        thread_id = thread.id
        post_id = post.id

    # Fetch post list and check flag
    resp = client.get(f"/api/v1/forum/threads/{thread_id}/posts", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    posts = {p["id"]: p for p in data["items"]}
    assert post_id in posts
    assert posts[post_id]["liked_by_me"] is True


# ============= REPORT TESTS =============

def test_report_submission(app, client, auth_headers):
    """Users can submit reports on posts."""
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open")
        db.session.add(thread)
        db.session.flush()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="post", status="visible")
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    resp = client.post(
        "/api/v1/forum/reports",
        json={"target_type": "post", "target_id": post_id, "reason": "Spam"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["target_type"] == "post"
    assert data["target_id"] == post_id
    assert data["reason"] == "Spam"
    assert data["status"] == "open"


def test_report_status_update(app, client, test_user, moderator_headers):
    """Moderators can update report status."""
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open")
        db.session.add(thread)
        db.session.flush()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="post", status="visible")
        db.session.add(post)
        db.session.flush()
        report = ForumReport(target_type="post", target_id=post.id, reported_by=user.id, reason="Spam", status="open")
        db.session.add(report)
        db.session.commit()
        report_id = report.id

    resp = client.put(
        f"/api/v1/forum/reports/{report_id}",
        json={"status": "resolved"},
        headers=moderator_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "resolved"


# ============= MODERATION ACTION TESTS =============

def test_lock_unlock_thread(app, client, moderator_headers):
    """Moderators can lock/unlock threads."""
    thread_id = None
    with app.app_context():
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open", is_locked=False)
        db.session.add(thread)
        db.session.commit()
        thread_id = thread.id

    # Lock
    resp = client.post(f"/api/v1/forum/threads/{thread_id}/lock", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_locked"] is True

    # Unlock
    resp = client.post(f"/api/v1/forum/threads/{thread_id}/unlock", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_locked"] is False


def test_pin_unpin_thread(app, client, moderator_headers):
    """Moderators can pin/unpin threads."""
    thread_id = None
    with app.app_context():
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open", is_pinned=False)
        db.session.add(thread)
        db.session.commit()
        thread_id = thread.id

    # Pin
    resp = client.post(f"/api/v1/forum/threads/{thread_id}/pin", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_pinned"] is True

    # Unpin
    resp = client.post(f"/api/v1/forum/threads/{thread_id}/unpin", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_pinned"] is False


def test_hide_unhide_post(app, client, test_user, moderator_headers):
    """Moderators can hide/unhide posts."""
    post_id = None
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open")
        db.session.add(thread)
        db.session.flush()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="post", status="visible")
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    # Hide
    resp = client.post(f"/api/v1/forum/posts/{post_id}/hide", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "hidden"

    # Unhide
    resp = client.post(f"/api/v1/forum/posts/{post_id}/unhide", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "visible"


def test_own_post_edit(app, client, auth_headers):
    """Authors can edit their own posts."""
    post_id = None
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open")
        db.session.add(thread)
        db.session.flush()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="original", status="visible")
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    resp = client.put(
        f"/api/v1/forum/posts/{post_id}",
        json={"content": "edited"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["content"] == "edited"
    assert data["edited_at"] is not None


def test_own_post_delete(app, client, auth_headers):
    """Authors can soft-delete their own posts."""
    post_id = None
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="test", title="Test", status="open")
        db.session.add(thread)
        db.session.flush()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="post", status="visible")
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    resp = client.delete(f"/api/v1/forum/posts/{post_id}", headers=auth_headers)
    assert resp.status_code == 200


# ============= COUNTER & METADATA TESTS =============

def test_counters_after_hide_unhide(app, client, test_user, moderator_headers):
    """reply_count and last_post metadata follow visible posts when hiding/unhiding."""
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(
            category_id=cat.id,
            slug="counter-thread",
            title="Counter",
            status="open",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(thread)
        db.session.flush()
        p1 = ForumPost(thread_id=thread.id, author_id=user.id, content="first", status="visible")
        p2 = ForumPost(thread_id=thread.id, author_id=user.id, content="second", status="visible")
        db.session.add_all([p1, p2])
        db.session.commit()

        from app.services.forum_service import recalc_thread_counters, hide_post, unhide_post

        recalc_thread_counters(thread)
        db.session.refresh(thread)
        assert thread.reply_count == 1
        assert thread.last_post_id == p2.id

        hide_post(p2)
        recalc_thread_counters(thread)
        db.session.refresh(thread)
        assert thread.last_post_id == p1.id

        unhide_post(p2)
        recalc_thread_counters(thread)
        db.session.refresh(thread)
        assert thread.last_post_id == p2.id


def test_parent_post_validation_same_thread_only(app, client, auth_headers):
    """parent_post_id must belong to same thread."""
    t1_id = None
    t2_id = None
    p1_id = None
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t1 = ForumThread(category_id=cat.id, slug="t1", title="T1", status="open")
        t2 = ForumThread(category_id=cat.id, slug="t2", title="T2", status="open")
        db.session.add_all([t1, t2])
        db.session.flush()
        p1 = ForumPost(thread_id=t1.id, author_id=user.id, content="p1", status="visible")
        db.session.add(p1)
        db.session.commit()
        t1_id = t1.id
        t2_id = t2.id
        p1_id = p1.id

    resp = client.post(
        f"/api/v1/forum/threads/{t2_id}/posts",
        json={"content": "reply", "parent_post_id": p1_id},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "same thread" in resp.get_json().get("error", "").lower()


# ============= SEARCH TESTS =============

def test_forum_search_returns_visible_threads(app, client):
    """Forum search returns only visible threads."""
    with app.app_context():
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        visible = ForumThread(category_id=cat.id, slug="visible-search", title="Findme", status="open")
        hidden = ForumThread(category_id=cat.id, slug="hidden-search", title="Findme Hidden", status="hidden")
        db.session.add_all([visible, hidden])
        db.session.commit()

    resp = client.get("/api/v1/forum/search?q=Findme")
    assert resp.status_code == 200
    data = resp.get_json()
    slugs = {t["slug"] for t in data["items"]}
    assert "visible-search" in slugs
    assert "hidden-search" not in slugs


def test_forum_search_includes_author_username(app, client, test_user):
    """Search results include author_username."""
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="search-test", title="Searchable", status="open", author_id=user.id)
        db.session.add(thread)
        db.session.commit()

    resp = client.get("/api/v1/forum/search?q=Searchable")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["items"]) > 0
    assert data["items"][0]["author_username"] == "testuser"
