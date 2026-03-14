"""Forum API tests: comprehensive coverage of visibility, permissions, counters, reports, moderation, and search."""
from datetime import datetime, timezone

import pytest

from app.extensions import db
from app.models import (
    ForumCategory,
    ForumThread,
    ForumPost,
    ForumPostLike,
    ForumReport,
    ForumThreadSubscription,
    ForumTag,
    ForumThreadTag,
    ForumThreadBookmark,
    Notification,
    User,
    Role,
)


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


@pytest.mark.usefixtures("app")
def test_thread_bookmark_create_and_list(client, auth_headers):
    """User can bookmark a thread and see it in /forum/bookmarks."""
    with client.application.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="public", title="Public", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="bookmark-me", title="Bookmark me", status="open")
        db.session.add(thread)
        db.session.commit()
        thread_id = thread.id

    # Bookmark thread
    resp = client.post(f"/api/v1/forum/threads/{thread_id}/bookmark", headers=auth_headers)
    assert resp.status_code == 200

    # List bookmarks
    resp2 = client.get("/api/v1/forum/bookmarks", headers=auth_headers)
    assert resp2.status_code == 200
    data = resp2.get_json()
    slugs = {t["slug"] for t in data["items"]}
    assert "bookmark-me" in slugs


@pytest.mark.usefixtures("app")
def test_reports_bulk_status_update(app, client, admin_headers):
    """Bulk status update moves multiple reports to resolved."""
    with app.app_context():
        cat = ForumCategory(slug="rep-cat", title="RepCat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="rep-thread", title="Reported thread", status="open")
        db.session.add(thread)
        db.session.flush()
        # Create two open reports on the thread
        r1 = ForumReport(target_type="thread", target_id=thread.id, reported_by=None, reason="R1", status="open")
        r2 = ForumReport(target_type="thread", target_id=thread.id, reported_by=None, reason="R2", status="open")
        db.session.add_all([r1, r2])
        db.session.commit()
        ids = [r1.id, r2.id]

    resp = client.post(
        "/api/v1/forum/reports/bulk-status",
        json={"report_ids": ids, "status": "resolved"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data["updated_ids"]) == set(ids)
    assert data["status"] == "resolved"


def test_forum_search_filter_by_tag_and_category(app, client, auth_headers):
    """Forum search can filter by tag and category, even without a text query."""
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="search-cat", title="SearchCat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="search-thread", title="Searchable Thread", status="open", author_id=user.id)
        db.session.add(thread)
        db.session.commit()
        thread_id = thread.id

    # Set tag via API as thread author (testuser)
    resp_tags = client.put(
        f"/api/v1/forum/threads/{thread_id}/tags",
        json={"tags": ["Feature"]},
        headers=auth_headers,
    )
    assert resp_tags.status_code == 200
    tags_payload = resp_tags.get_json()
    assert any(t["slug"] == "feature" for t in tags_payload["tags"])

    # Search by category + tag without q
    resp = client.get("/api/v1/forum/search?category=search-cat&tag=feature&page=1&limit=20")
    assert resp.status_code == 200
    data = resp.get_json()
    slugs = {t["slug"] for t in data["items"]}
    assert "search-thread" in slugs


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


# ============= SUBSCRIBE / UNSUBSCRIBE =============


def test_subscribe_unsubscribe_flow(app, client, auth_headers):
    """User can subscribe to a thread and then unsubscribe; thread detail returns subscribed_by_me."""
    with app.app_context():
        cat = ForumCategory(slug="sub-cat", title="Sub Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="sub-thread", title="Sub Thread", status="open")
        db.session.add(thread)
        db.session.commit()
        thread_id = thread.id

    # Not subscribed initially
    resp = client.get("/api/v1/forum/threads/sub-thread", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json().get("subscribed_by_me") is False

    # Subscribe
    resp = client.post("/api/v1/forum/threads/{}/subscribe".format(thread_id), headers=auth_headers)
    assert resp.status_code == 200
    resp = client.get("/api/v1/forum/threads/sub-thread", headers=auth_headers)
    assert resp.get_json().get("subscribed_by_me") is True

    # Unsubscribe
    resp = client.delete("/api/v1/forum/threads/{}/subscribe".format(thread_id), headers=auth_headers)
    assert resp.status_code == 200
    resp = client.get("/api/v1/forum/threads/sub-thread", headers=auth_headers)
    assert resp.get_json().get("subscribed_by_me") is False


# ============= NOTIFICATIONS =============


def test_notification_created_on_reply_for_subscribers(app, client, auth_headers, moderator_headers):
    """When a user posts a reply in a thread, other subscribers (not the author) receive a notification."""
    with app.app_context():
        cat = ForumCategory(slug="notif-cat", title="Notif Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="notif-thread", title="Notif Thread", status="open")
        db.session.add(thread)
        db.session.commit()
        # Test user (subscriber) and moderator (will post)
        subscriber = User.query.filter_by(username="testuser").first()
        sub1 = ForumThreadSubscription(thread_id=thread.id, user_id=subscriber.id)
        db.session.add(sub1)
        db.session.commit()
        thread_id = thread.id
        subscriber_id = subscriber.id

    # Moderator posts a reply; subscriber (testuser) should get a notification, not the author
    resp = client.post(
        "/api/v1/forum/threads/{}/posts".format(thread_id),
        headers=moderator_headers,
        json={"content": "A reply"},
        content_type="application/json",
    )
    assert resp.status_code == 201

    with app.app_context():
        notifications = Notification.query.filter_by(target_type="forum_thread", target_id=thread_id).all()
        assert len(notifications) == 1
        assert notifications[0].user_id == subscriber_id
        assert notifications[0].message


def test_notifications_list_and_mark_read(app, client, auth_headers):
    """User can list notifications and mark one as read."""
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        n = Notification(
            user_id=user.id,
            event_type="thread_reply",
            target_type="forum_thread",
            target_id=99,
            message="Test notification",
            is_read=False,
        )
        db.session.add(n)
        db.session.commit()
        nid = n.id

    resp = client.get("/api/v1/notifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    items = [i for i in data["items"] if i["id"] == nid]
    assert len(items) == 1
    assert items[0]["is_read"] is False

    resp = client.patch("/api/v1/notifications/{}/read".format(nid), headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json().get("is_read") is True

    resp = client.get("/api/v1/notifications", headers=auth_headers)
    items2 = [i for i in resp.get_json()["items"] if i["id"] == nid]
    assert len(items2) == 1
    assert items2[0]["is_read"] is True


# ============= MODERATION DASHBOARD =============


def test_moderation_metrics_includes_pinned_threads(app, client, moderator_headers):
    """Moderation metrics returns open_reports, hidden_posts, locked_threads, pinned_threads."""
    with app.app_context():
        cat = ForumCategory(slug="mcat", title="M Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="pinned-t", title="Pinned", status="open", is_pinned=True)
        db.session.add(t)
        db.session.commit()

    resp = client.get("/api/v1/forum/moderation/metrics", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "pinned_threads" in data
    assert data["pinned_threads"] >= 1
    assert "open_reports" in data
    assert "locked_threads" in data
    assert "hidden_posts" in data


def test_moderation_recently_handled(app, client, test_user, moderator_headers):
    """Recently handled reports endpoint returns reports with status reviewed/resolved/dismissed."""
    with app.app_context():
        cat = ForumCategory(slug="rcat", title="R Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="rthread", title="R Thread", status="open")
        db.session.add(thread)
        db.session.commit()
        reporter, _ = test_user
        report = ForumReport(
            target_type="thread",
            target_id=thread.id,
            reported_by=reporter.id,
            reason="test",
            status="resolved",
            handled_by=User.query.filter_by(username="moderatoruser").first().id,
            handled_at=datetime.now(timezone.utc),
        )
        db.session.add(report)
        db.session.commit()

    resp = client.get("/api/v1/forum/moderation/recently-handled?limit=5", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    assert len(data["items"]) >= 1
    assert data["items"][0].get("status") in ("reviewed", "resolved", "dismissed")
    assert "thread_slug" in data["items"][0]


def test_moderation_locked_pinned_hidden_lists(app, client, moderator_headers):
    """Locked threads, pinned threads, and hidden posts list endpoints return 200 and items array."""
    with app.app_context():
        cat = ForumCategory(slug="lcat", title="L Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="locked-t", title="Locked", status="open", is_locked=True)
        db.session.add(t)
        db.session.commit()

    for path in ["/api/v1/forum/moderation/locked-threads", "/api/v1/forum/moderation/pinned-threads", "/api/v1/forum/moderation/hidden-posts"]:
        resp = client.get(path + "?limit=5", headers=moderator_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert isinstance(data["items"], list)


def test_move_thread(app, client, moderator_headers):
    """Moderator can move a thread to another category."""
    with app.app_context():
        c1 = ForumCategory(slug="move-from", title="From", is_active=True, is_private=False)
        c2 = ForumCategory(slug="move-to", title="To", is_active=True, is_private=False)
        db.session.add_all([c1, c2])
        db.session.flush()
        t = ForumThread(category_id=c1.id, slug="move-thread", title="Move Me", status="open")
        db.session.add(t)
        db.session.commit()
        thread_id, cat2_id = t.id, c2.id

    resp = client.post(
        "/api/v1/forum/threads/{}/move".format(thread_id),
        headers=moderator_headers,
        json={"category_id": cat2_id},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["category_id"] == cat2_id
    assert data["slug"] == "move-thread"

    with app.app_context():
        t = ForumThread.query.get(thread_id)
        assert t.category_id == cat2_id


def test_archive_unarchive_thread(app, client, moderator_headers):
    """Moderator can archive and unarchive a thread."""
    with app.app_context():
        cat = ForumCategory(slug="arch-cat", title="Arch Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="arch-thread", title="Archive Me", status="open")
        db.session.add(t)
        db.session.commit()
        thread_id = t.id

    resp = client.post("/api/v1/forum/threads/{}/archive".format(thread_id), headers=moderator_headers, json={})
    assert resp.status_code == 200
    assert resp.get_json().get("status") == "archived"

    resp = client.post("/api/v1/forum/threads/{}/unarchive".format(thread_id), headers=moderator_headers, json={})
    assert resp.status_code == 200
    assert resp.get_json().get("status") == "open"


def test_thread_merge_moves_posts_and_updates_counters(app, client, moderator_headers):
    """Merging a source thread into a target moves posts, updates counters, and archives source."""
    with app.app_context():
        cat = ForumCategory(slug="merge-cat", title="Merge Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        source = ForumThread(category_id=cat.id, slug="source-thread", title="Source", status="open")
        target = ForumThread(category_id=cat.id, slug="target-thread", title="Target", status="open")
        db.session.add_all([source, target])
        db.session.flush()
        # Two posts in source (first + reply), one post in target
        src_p1 = ForumPost(thread_id=source.id, author_id=None, content="S1", status="visible")
        src_p2 = ForumPost(thread_id=source.id, author_id=None, content="S2", parent_post_id=None, status="visible")
        tgt_p1 = ForumPost(thread_id=target.id, author_id=None, content="T1", status="visible")
        db.session.add_all([src_p1, src_p2, tgt_p1])
        db.session.commit()
        source_id = source.id
        target_id = target.id

    resp = client.post(
        f"/api/v1/forum/threads/{source_id}/merge",
        headers=moderator_headers,
        json={"target_thread_id": target_id},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == target_id
    # All posts should now belong to target thread
    with app.app_context():
        posts_in_target = ForumPost.query.filter_by(thread_id=target_id).all()
        assert len(posts_in_target) == 3
        src_thread = ForumThread.query.get(source_id)
        tgt_thread = ForumThread.query.get(target_id)
        assert src_thread.status == "archived"
        # reply_count: total visible posts - 1
        assert tgt_thread.reply_count == max(0, len(posts_in_target) - 1)
        assert tgt_thread.last_post_id is not None


def test_thread_merge_requires_moderator_permissions(app, client, auth_headers):
    """Non-moderator cannot merge threads."""
    with app.app_context():
        cat = ForumCategory(slug="merge-cat2", title="Merge Cat 2", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        source = ForumThread(category_id=cat.id, slug="source-thread2", title="Source2", status="open")
        target = ForumThread(category_id=cat.id, slug="target-thread2", title="Target2", status="open")
        db.session.add_all([source, target])
        db.session.commit()
        source_id = source.id
        target_id = target.id

    resp = client.post(
        f"/api/v1/forum/threads/{source_id}/merge",
        headers=auth_headers,
        json={"target_thread_id": target_id},
        content_type="application/json",
    )
    assert resp.status_code in (401, 403)


def test_thread_merge_merges_subscriptions(app, client, moderator_headers):
    """Subscriptions from source are merged into target without duplicates."""
    with app.app_context():
        cat = ForumCategory(slug="merge-cat3", title="Merge Cat 3", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        source = ForumThread(category_id=cat.id, slug="source-thread3", title="Source3", status="open")
        target = ForumThread(category_id=cat.id, slug="target-thread3", title="Target3", status="open")
        db.session.add_all([source, target])
        db.session.flush()
        user1 = User(username="merge_user1", password_hash="x", role_id=Role.query.filter_by(name=Role.NAME_USER).first().id)
        user2 = User(username="merge_user2", password_hash="x", role_id=Role.query.filter_by(name=Role.NAME_USER).first().id)
        db.session.add_all([user1, user2])
        db.session.flush()
        sub_source = ForumThreadSubscription(thread_id=source.id, user_id=user1.id)
        sub_target = ForumThreadSubscription(thread_id=target.id, user_id=user2.id)
        db.session.add_all([sub_source, sub_target])
        db.session.commit()
        source_id = source.id
        target_id = target.id
        user1_id = user1.id
        user2_id = user2.id

    resp = client.post(
        f"/api/v1/forum/threads/{source_id}/merge",
        headers=moderator_headers,
        json={"target_thread_id": target_id},
        content_type="application/json",
    )
    assert resp.status_code == 200
    with app.app_context():
        subs_source = ForumThreadSubscription.query.filter_by(thread_id=source_id).all()
        subs_target = ForumThreadSubscription.query.filter_by(thread_id=target_id).all()
        assert len(subs_source) == 0
        user_ids = {s.user_id for s in subs_target}
        assert user1_id in user_ids
        assert user2_id in user_ids


def test_thread_split_creates_new_thread_and_moves_posts(app, client, moderator_headers):
    """Splitting from a top-level post creates a new thread and moves the root + direct replies."""
    with app.app_context():
        cat = ForumCategory(slug="split-cat", title="Split Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        source = ForumThread(category_id=cat.id, slug="split-source", title="SourceThread", status="open")
        db.session.add(source)
        db.session.flush()
        # Top-level root post and its direct reply, plus another independent top-level post.
        root = ForumPost(thread_id=source.id, author_id=None, content="Root", status="visible")
        db.session.add(root)
        db.session.flush()
        reply = ForumPost(
            thread_id=source.id,
            author_id=None,
            parent_post_id=root.id,
            content="Reply to root",
            status="visible",
        )
        other = ForumPost(thread_id=source.id, author_id=None, content="Other top-level", status="visible")
        db.session.add_all([reply, other])
        db.session.commit()
        source_id = source.id
        root_id = root.id
        reply_id = reply.id
        other_id = other.id
        cat_id = cat.id

    resp = client.post(
        f"/api/v1/forum/threads/{source_id}/split",
        headers=moderator_headers,
        json={"root_post_id": root_id, "title": "Split thread"},
        content_type="application/json",
    )
    assert resp.status_code == 201
    data = resp.get_json()
    new_thread_id = data["id"]
    assert new_thread_id != source_id
    assert data["title"] == "Split thread"
    assert data.get("category_id", cat_id) == cat_id  # category stays consistent or is embedded

    with app.app_context():
        source = ForumThread.query.get(source_id)
        new_thread = ForumThread.query.get(new_thread_id)
        assert source is not None and new_thread is not None

        posts_in_source = ForumPost.query.filter_by(thread_id=source_id).all()
        posts_in_new = ForumPost.query.filter_by(thread_id=new_thread_id).all()

        # Root and its direct reply must be in the new thread; the other top-level post stays in source.
        source_ids = {p.id for p in posts_in_source}
        new_ids = {p.id for p in posts_in_new}
        assert root_id in new_ids
        assert reply_id in new_ids
        assert other_id in source_ids

        # Metadata: reply_count is total visible posts - 1; last_post_id is one of the visible posts.
        assert source.reply_count == max(0, len(posts_in_source) - 1)
        assert source.last_post_id in source_ids
        assert new_thread.reply_count == max(0, len(posts_in_new) - 1)
        assert new_thread.last_post_id in new_ids


def test_thread_split_requires_moderator_permissions(app, client, auth_headers):
    """Non-moderator users cannot split threads."""
    with app.app_context():
        cat = ForumCategory(slug="split-cat2", title="Split Cat 2", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="split-source2", title="Source2", status="open")
        db.session.add(thread)
        db.session.flush()
        root = ForumPost(thread_id=thread.id, author_id=None, content="Root", status="visible")
        db.session.add(root)
        db.session.commit()
        thread_id = thread.id
        root_id = root.id

    resp = client.post(
        f"/api/v1/forum/threads/{thread_id}/split",
        headers=auth_headers,
        json={"root_post_id": root_id, "title": "Split thread"},
        content_type="application/json",
    )
    assert resp.status_code in (401, 403)


def test_thread_split_rejects_non_top_level_root_post(app, client, moderator_headers):
    """Split from a non-top-level post is rejected to avoid broken reply chains."""
    with app.app_context():
        cat = ForumCategory(slug="split-cat3", title="Split Cat 3", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="split-source3", title="Source3", status="open")
        db.session.add(thread)
        db.session.flush()
        root = ForumPost(thread_id=thread.id, author_id=None, content="Root", status="visible")
        db.session.add(root)
        db.session.flush()
        child = ForumPost(
            thread_id=thread.id,
            author_id=None,
            parent_post_id=root.id,
            content="Child",
            status="visible",
        )
        db.session.add(child)
        db.session.commit()
        thread_id = thread.id
        child_id = child.id

    resp = client.post(
        f"/api/v1/forum/threads/{thread_id}/split",
        headers=moderator_headers,
        json={"root_post_id": child_id, "title": "Split child"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    # Service returns a clear error string; ensure we propagate a meaningful error.
    assert "top-level" in (data.get("error") or "").lower()

def test_notifications_mark_all_read(app, client, auth_headers):
    """User can mark all notifications as read."""
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        for _ in range(2):
            n = Notification(
                user_id=user.id,
                event_type="thread_reply",
                target_type="forum_thread",
                target_id=1,
                message="Test",
                is_read=False,
            )
            db.session.add(n)
        db.session.commit()

    resp = client.put("/api/v1/notifications/read-all", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("updated") >= 2

    resp = client.get("/api/v1/notifications?unread_only=1", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json().get("items", [])) == 0


def test_notifications_list_thread_slug_for_forum_post(app, client, auth_headers):
    """Notifications list includes thread_slug and target_post_id for forum_post targets."""
    with app.app_context():
        cat = ForumCategory(slug="ncat", title="N Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="notif-post-thread", title="T", status="open")
        db.session.add(thread)
        db.session.flush()
        post = ForumPost(thread_id=thread.id, author_id=User.query.filter_by(username="testuser").first().id, content="x", status="visible")
        db.session.add(post)
        db.session.commit()
        post_id = post.id
        user = User.query.filter_by(username="testuser").first()
        n = Notification(
            user_id=user.id,
            event_type="mention",
            target_type="forum_post",
            target_id=post_id,
            message="Mentioned",
            is_read=False,
        )
        db.session.add(n)
        db.session.commit()
        nid = n.id

    resp = client.get("/api/v1/notifications", headers=auth_headers)
    assert resp.status_code == 200
    items = [i for i in resp.get_json()["items"] if i["id"] == nid]
    assert len(items) == 1
    assert items[0]["thread_slug"] == "notif-post-thread"
    assert items[0]["target_post_id"] == post_id


def test_mention_creates_notification(app, client, moderator_headers, auth_headers):
    """Post containing @username creates a mention notification for that user (not for author)."""
    with app.app_context():
        cat = ForumCategory(slug="mention-cat", title="Mention Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(
            category_id=cat.id,
            slug="mention-thread",
            title="Mention Thread",
            status="open",
            author_id=User.query.filter_by(username="moderatoruser").first().id,
        )
        db.session.add(thread)
        db.session.commit()
        thread_id = thread.id
        testuser = User.query.filter_by(username="testuser").first()
        assert testuser

    # Moderator posts with @testuser
    resp = client.post(
        "/api/v1/forum/threads/{}/posts".format(thread_id),
        headers=moderator_headers,
        json={"content": "Hello @testuser, check this out."},
        content_type="application/json",
    )
    assert resp.status_code == 201

    with app.app_context():
        mention_notifications = Notification.query.filter_by(
            event_type="mention",
            target_type="forum_post",
            user_id=testuser.id,
        ).all()
        assert len(mention_notifications) == 1
        assert "mentioned you" in (mention_notifications[0].message or "")


def test_search_deleted_threads_hidden_from_moderator(app, client, moderator_headers):
    """Deleted threads are excluded from search results even for moderators."""
    with app.app_context():
        cat = ForumCategory(slug="del-search-cat", title="Del Search Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(
            category_id=cat.id,
            slug="deleted-search-thread",
            title="DeletedSearchTarget",
            status="deleted",
        )
        db.session.add(thread)
        db.session.commit()

    resp = client.get("/api/v1/forum/search?q=DeletedSearchTarget", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    slugs = {t["slug"] for t in data["items"]}
    assert "deleted-search-thread" not in slugs


# ============= PHASE 3: BOOKMARKED_BY_ME FLAG IN THREAD LIST =============


def test_bookmarked_by_me_in_thread_list(app, client, auth_headers):
    """Thread list includes bookmarked_by_me=True for bookmarked threads, False for others."""
    with app.app_context():
        cat = ForumCategory(slug="bm-cat", title="BM Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t1 = ForumThread(category_id=cat.id, slug="bm-thread-1", title="BM Thread 1", status="open")
        t2 = ForumThread(category_id=cat.id, slug="bm-thread-2", title="BM Thread 2", status="open")
        db.session.add_all([t1, t2])
        db.session.commit()
        t1_id = t1.id

    # Bookmark only the first thread
    resp = client.post(f"/api/v1/forum/threads/{t1_id}/bookmark", headers=auth_headers)
    assert resp.status_code == 200

    # List threads for category
    resp = client.get("/api/v1/forum/categories/bm-cat/threads", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    thread_map = {t["slug"]: t for t in data["items"]}
    assert thread_map["bm-thread-1"]["bookmarked_by_me"] is True
    assert thread_map["bm-thread-2"]["bookmarked_by_me"] is False


def test_bookmarked_by_me_false_for_anonymous(app, client):
    """Thread list returns bookmarked_by_me=False for anonymous users."""
    with app.app_context():
        cat = ForumCategory(slug="anon-bm-cat", title="Anon BM", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="anon-bm-thread", title="Anon Thread", status="open")
        db.session.add(t)
        db.session.commit()

    resp = client.get("/api/v1/forum/categories/anon-bm-cat/threads")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["items"]) >= 1
    for item in data["items"]:
        assert item["bookmarked_by_me"] is False


# ============= PHASE 3: TAGS IN THREAD LIST =============


def test_tags_in_thread_list(app, client, auth_headers):
    """Thread list includes tags array for each thread."""
    with app.app_context():
        cat = ForumCategory(slug="tags-cat", title="Tags Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="tags-thread", title="Tags Thread", status="open", author_id=User.query.filter_by(username="testuser").first().id)
        db.session.add(t)
        db.session.commit()
        t_id = t.id

    # Set tags via API
    resp = client.put(
        f"/api/v1/forum/threads/{t_id}/tags",
        json={"tags": ["Bug", "Help"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # List threads
    resp = client.get("/api/v1/forum/categories/tags-cat/threads", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    thread = next(t for t in data["items"] if t["slug"] == "tags-thread")
    assert "tags" in thread
    tag_slugs = {t["slug"] for t in thread["tags"]}
    assert "bug" in tag_slugs
    assert "help" in tag_slugs


# ============= PHASE 3: TAG ADMIN ENDPOINTS =============


def test_list_tags_requires_moderator(app, client, auth_headers):
    """GET /api/v1/forum/tags requires moderator or admin role."""
    resp = client.get("/api/v1/forum/tags", headers=auth_headers)
    assert resp.status_code == 403


def test_list_tags_moderator(app, client, moderator_headers):
    """Moderator can list all tags."""
    with app.app_context():
        tag = ForumTag(slug="mod-list-tag", label="ModListTag")
        db.session.add(tag)
        db.session.commit()

    resp = client.get("/api/v1/forum/tags", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    slugs = {t["slug"] for t in data["items"]}
    assert "mod-list-tag" in slugs


def test_list_tags_with_search(app, client, moderator_headers):
    """Tags list can be filtered by q parameter."""
    with app.app_context():
        t1 = ForumTag(slug="alpha-tag", label="Alpha")
        t2 = ForumTag(slug="beta-tag", label="Beta")
        db.session.add_all([t1, t2])
        db.session.commit()

    resp = client.get("/api/v1/forum/tags?q=alpha", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    slugs = {t["slug"] for t in data["items"]}
    assert "alpha-tag" in slugs
    assert "beta-tag" not in slugs


def test_delete_unused_tag(app, client, admin_headers):
    """Admin can delete a tag that has no thread associations."""
    with app.app_context():
        tag = ForumTag(slug="unused-tag", label="Unused")
        db.session.add(tag)
        db.session.commit()
        tag_id = tag.id

    resp = client.delete(f"/api/v1/forum/tags/{tag_id}", headers=admin_headers)
    assert resp.status_code == 200

    # Verify deleted
    with app.app_context():
        assert ForumTag.query.get(tag_id) is None


def test_delete_tag_in_use_rejected(app, client, admin_headers):
    """Deleting a tag with thread associations returns 409."""
    with app.app_context():
        tag = ForumTag(slug="in-use-tag", label="InUse")
        db.session.add(tag)
        db.session.flush()
        cat = ForumCategory(slug="tag-del-cat", title="TagDelCat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="tag-del-thread", title="Tag Thread", status="open")
        db.session.add(t)
        db.session.flush()
        link = ForumThreadTag(thread_id=t.id, tag_id=tag.id)
        db.session.add(link)
        db.session.commit()
        tag_id = tag.id

    resp = client.delete(f"/api/v1/forum/tags/{tag_id}", headers=admin_headers)
    assert resp.status_code == 409
    assert "in use" in resp.get_json()["error"].lower()


def test_delete_tag_requires_admin(app, client, moderator_headers):
    """Moderator cannot delete tags (admin only)."""
    with app.app_context():
        tag = ForumTag(slug="mod-del-tag", label="ModDel")
        db.session.add(tag)
        db.session.commit()
        tag_id = tag.id

    resp = client.delete(f"/api/v1/forum/tags/{tag_id}", headers=moderator_headers)
    assert resp.status_code == 403


# ============= PHASE 3: SEARCH HARDENING =============


def test_search_hidden_threads_not_visible_to_regular_users(app, client, auth_headers):
    """Search results exclude hidden threads for regular users at SQL level."""
    with app.app_context():
        cat = ForumCategory(slug="search-vis-cat", title="SearchVis", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t_open = ForumThread(category_id=cat.id, slug="search-vis-open", title="SearchOpen", status="open")
        t_hidden = ForumThread(category_id=cat.id, slug="search-vis-hidden", title="SearchHidden", status="hidden")
        db.session.add_all([t_open, t_hidden])
        db.session.commit()

    resp = client.get("/api/v1/forum/search?q=Search&category=search-vis-cat", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    slugs = {t["slug"] for t in data["items"]}
    assert "search-vis-open" in slugs
    assert "search-vis-hidden" not in slugs


def test_search_hidden_threads_visible_to_moderator(app, client, moderator_headers):
    """Moderators can see hidden threads in search when filtering by hidden status."""
    with app.app_context():
        cat = ForumCategory(slug="search-mod-cat", title="SearchMod", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t_hidden = ForumThread(category_id=cat.id, slug="search-mod-hidden", title="ModHidden", status="hidden")
        db.session.add(t_hidden)
        db.session.commit()

    resp = client.get("/api/v1/forum/search?q=ModHidden&category=search-mod-cat&status=hidden", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    slugs = {t["slug"] for t in data["items"]}
    assert "search-mod-hidden" in slugs


def test_search_private_category_excluded_for_regular_users(app, client, auth_headers):
    """Search excludes threads in private categories for regular users."""
    with app.app_context():
        cat = ForumCategory(slug="search-priv-cat", title="SearchPriv", is_active=True, is_private=True)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="search-priv-thread", title="PrivateThread", status="open")
        db.session.add(t)
        db.session.commit()

    resp = client.get("/api/v1/forum/search?q=PrivateThread", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    slugs = {t["slug"] for t in data["items"]}
    assert "search-priv-thread" not in slugs


# ============= PHASE 3: BOOKMARK REMOVAL =============


def test_bookmark_removal(app, client, auth_headers):
    """DELETE /api/v1/forum/threads/<id>/bookmark removes a bookmark."""
    with app.app_context():
        cat = ForumCategory(slug="bm-rm-cat", title="BM RM Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="bm-rm-thread", title="BM RM Thread", status="open")
        db.session.add(t)
        db.session.commit()
        t_id = t.id

    # Bookmark
    resp = client.post(f"/api/v1/forum/threads/{t_id}/bookmark", headers=auth_headers)
    assert resp.status_code == 200

    # Verify in list
    resp = client.get("/api/v1/forum/bookmarks", headers=auth_headers)
    assert any(b["slug"] == "bm-rm-thread" for b in resp.get_json()["items"])

    # Remove bookmark
    resp = client.delete(f"/api/v1/forum/threads/{t_id}/bookmark", headers=auth_headers)
    assert resp.status_code == 200

    # Verify removed from list
    resp = client.get("/api/v1/forum/bookmarks", headers=auth_headers)
    assert not any(b["slug"] == "bm-rm-thread" for b in resp.get_json()["items"])


@pytest.mark.usefixtures("app")
def test_saved_threads_list_requires_auth(client):
    """GET /api/v1/forum/bookmarks requires authentication (401)."""
    resp = client.get("/api/v1/forum/bookmarks")
    assert resp.status_code == 401


@pytest.mark.usefixtures("app")
def test_saved_threads_list_pagination(app, client, auth_headers):
    """Saved threads list respects pagination (page, limit, total, per_page)."""
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="test-cat", title="Test", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        # Create 25 threads and bookmark them all
        threads = []
        for i in range(25):
            t = ForumThread(
                category_id=cat.id,
                slug=f"paginated-thread-{i}",
                title=f"Paginated Thread {i}",
                status="open"
            )
            db.session.add(t)
            db.session.flush()
            threads.append(t)
        db.session.commit()
        # Bookmark all threads
        for t in threads:
            bookmark = ForumThreadBookmark(user_id=user.id, thread_id=t.id)
            db.session.add(bookmark)
        db.session.commit()

    # Page 1 (default limit 20)
    resp = client.get("/api/v1/forum/bookmarks", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["page"] == 1
    assert data["per_page"] == 20
    assert data["total"] == 25
    assert len(data["items"]) == 20

    # Page 2 with custom limit
    resp = client.get("/api/v1/forum/bookmarks?page=2&limit=10", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["page"] == 2
    assert data["per_page"] == 10
    assert data["total"] == 25
    assert len(data["items"]) == 10


@pytest.mark.usefixtures("app")
def test_unbookmark_from_saved_threads(app, client, auth_headers):
    """Unbooking (DELETE) removes thread from saved list."""
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="del-cat", title="Delete Test", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="del-thread", title="Delete Thread", status="open")
        db.session.add(thread)
        db.session.flush()
        bookmark = ForumThreadBookmark(user_id=user.id, thread_id=thread.id)
        db.session.add(bookmark)
        db.session.commit()
        thread_id = thread.id

    # Verify thread in saved list
    resp = client.get("/api/v1/forum/bookmarks", headers=auth_headers)
    assert resp.status_code == 200
    assert any(t["slug"] == "del-thread" for t in resp.get_json()["items"])

    # Delete bookmark
    resp = client.delete(f"/api/v1/forum/threads/{thread_id}/bookmark", headers=auth_headers)
    assert resp.status_code == 200

    # Verify thread removed from saved list
    resp = client.get("/api/v1/forum/bookmarks", headers=auth_headers)
    assert resp.status_code == 200
    assert not any(t["slug"] == "del-thread" for t in resp.get_json()["items"])
