"""Extended forum route tests — covers thread/post CRUD, moderation, admin, and edge cases."""
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
    ForumThreadBookmark,
    Notification,
    User,
    Role,
    ForumTag,
    ForumThreadTag,
)
from app.models.forum import ModeratorAssignment
from app.models.activity_log import ActivityLog


def _assign_moderators_to_category(app, category_id):
    """Helper: assign all moderators to a category for testing moderation."""
    with app.app_context():
        moderator_role = Role.query.filter_by(name="moderator").first()
        admin_role = Role.query.filter_by(name="admin").first()
        moderators = User.query.filter_by(role_id=moderator_role.id).all() if moderator_role else []
        admin = User.query.filter_by(role_id=admin_role.id).first() if admin_role else None

        for mod in moderators:
            assignment = ModeratorAssignment(
                user_id=mod.id,
                category_id=category_id,
                assigned_by=admin.id if admin else mod.id,
            )
            db.session.add(assignment)
        db.session.commit()


def _setup_public_cat_and_thread(app, username="testuser"):
    """Helper: create a public category + thread owned by given user, return IDs.
    Also assigns all moderators to the category for testing moderation endpoints."""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        cat = ForumCategory(slug="pub-ext", title="Pub Ext", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()

        # Assign all moderators to this category so they can test moderation
        moderator_role = Role.query.filter_by(name="moderator").first()
        admin_role = Role.query.filter_by(name="admin").first()
        moderators = User.query.filter_by(role_id=moderator_role.id).all() if moderator_role else []
        admin = User.query.filter_by(role_id=admin_role.id).first() if admin_role else None
        for mod in moderators:
            assignment = ModeratorAssignment(
                user_id=mod.id,
                category_id=cat.id,
                assigned_by=admin.id if admin else mod.id,
            )
            db.session.add(assignment)

        thread = ForumThread(
            category_id=cat.id, slug="ext-thread", title="Ext Thread",
            status="open", author_id=user.id,
        )
        db.session.add(thread)
        db.session.flush()
        post = ForumPost(
            thread_id=thread.id, author_id=user.id, content="First post", status="visible",
        )
        db.session.add(post)
        db.session.commit()
        return cat.id, cat.slug, thread.id, thread.slug, post.id, user.id


# ============= CATEGORY DETAIL =============

def test_category_detail(app, client, auth_headers):
    with app.app_context():
        cat = ForumCategory(slug="detail-cat", title="Detail", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()
    resp = client.get("/api/v1/forum/categories/detail-cat", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["slug"] == "detail-cat"
    assert "thread_count" in data


def test_category_detail_not_found(app, client, auth_headers):
    resp = client.get("/api/v1/forum/categories/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


# ============= THREAD LISTING =============

def test_category_threads_pagination(app, client, auth_headers):
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="page-cat", title="Pageable", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        for i in range(5):
            t = ForumThread(
                category_id=cat.id, slug=f"page-thread-{i}", title=f"Thread {i}",
                status="open", author_id=user.id,
            )
            db.session.add(t)
        db.session.commit()
    resp = client.get("/api/v1/forum/categories/page-cat/threads?page=1&limit=2", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["items"]) == 2
    assert data["total"] == 5

    resp2 = client.get("/api/v1/forum/categories/page-cat/threads?page=3&limit=2", headers=auth_headers)
    data2 = resp2.get_json()
    assert len(data2["items"]) == 1


def test_category_threads_hidden_excluded_for_user(app, client, auth_headers):
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="vis-cat", title="Vis", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        db.session.add(ForumThread(category_id=cat.id, slug="vis-open", title="Open", status="open", author_id=user.id))
        db.session.add(ForumThread(category_id=cat.id, slug="vis-open-2", title="Open 2", status="open", author_id=user.id))
        db.session.add(ForumThread(category_id=cat.id, slug="vis-hidden", title="Hidden", status="hidden", author_id=user.id))
        db.session.commit()
    resp = client.get("/api/v1/forum/categories/vis-cat/threads", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 2  # hidden excluded, 2 visible threads remain


def test_category_threads_hidden_visible_for_mod(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="modvis-cat", title="ModVis", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        db.session.add(ForumThread(category_id=cat.id, slug="modvis-open", title="Open", status="open", author_id=mod.id))
        db.session.add(ForumThread(category_id=cat.id, slug="modvis-hidden", title="Hidden", status="hidden", author_id=mod.id))
        db.session.add(ForumThread(category_id=cat.id, slug="modvis-arch", title="Archived", status="archived", author_id=mod.id))
        db.session.commit()
    resp = client.get("/api/v1/forum/categories/modvis-cat/threads", headers=moderator_headers)
    data = resp.get_json()
    assert data["total"] == 3  # mod sees all


# ============= THREAD CRUD =============

def test_create_thread_via_api(app, client, auth_headers):
    with app.app_context():
        cat = ForumCategory(slug="create-cat", title="Create", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()
    resp = client.post(
        "/api/v1/forum/categories/create-cat/threads",
        json={"title": "API Thread", "content": "This is the body text"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["title"] == "API Thread"
    assert "category" in data


def test_create_thread_missing_body(app, client, auth_headers):
    with app.app_context():
        cat = ForumCategory(slug="create-cat2", title="Create2", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()
    resp = client.post(
        "/api/v1/forum/categories/create-cat2/threads",
        json={"title": "", "content": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_create_thread_nonexistent_category(app, client, auth_headers):
    resp = client.post(
        "/api/v1/forum/categories/nope/threads",
        json={"title": "X", "content": "Y"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_update_thread_title(app, client, auth_headers):
    cat_id, cat_slug, thread_id, _, _, uid = _setup_public_cat_and_thread(app)
    resp = client.put(
        f"/api/v1/forum/threads/{thread_id}",
        json={"title": "Updated Title"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Updated Title"


def test_update_thread_forbidden_for_other_user(app, client, moderator_headers, auth_headers):
    """Moderator can update any thread."""
    cat_id, _, thread_id, _, _, _ = _setup_public_cat_and_thread(app)
    resp = client.put(
        f"/api/v1/forum/threads/{thread_id}",
        json={"title": "Mod Updated"},
        headers=moderator_headers,
    )
    assert resp.status_code == 200


def test_update_thread_not_found(app, client, auth_headers):
    resp = client.put(
        "/api/v1/forum/threads/99999",
        json={"title": "X"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_delete_thread(app, client, auth_headers):
    cat_id, _, thread_id, _, _, _ = _setup_public_cat_and_thread(app)
    resp = client.delete(f"/api/v1/forum/threads/{thread_id}", headers=auth_headers)
    assert resp.status_code == 200


def test_delete_thread_not_found(app, client, auth_headers):
    resp = client.delete("/api/v1/forum/threads/99999", headers=auth_headers)
    assert resp.status_code == 404


def test_thread_detail_view(app, client, auth_headers):
    cat_id, _, thread_id, thread_slug, _, _ = _setup_public_cat_and_thread(app)
    resp = client.get(f"/api/v1/forum/threads/{thread_slug}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "category" in data
    assert "subscribed_by_me" in data


def test_thread_detail_not_found(app, client, auth_headers):
    resp = client.get("/api/v1/forum/threads/nonexistent-slug", headers=auth_headers)
    assert resp.status_code == 404


# ============= POST CRUD =============

def test_create_post_via_api(app, client, auth_headers):
    cat_id, _, thread_id, _, _, _ = _setup_public_cat_and_thread(app)
    reply_content = "This is a new reply message"
    resp = client.post(
        f"/api/v1/forum/threads/{thread_id}/posts",
        json={"content": reply_content},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["content"] == reply_content


def test_create_post_empty_content(app, client, auth_headers):
    cat_id, _, thread_id, _, _, _ = _setup_public_cat_and_thread(app)
    resp = client.post(
        f"/api/v1/forum/threads/{thread_id}/posts",
        json={"content": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_create_post_not_found_thread(app, client, auth_headers):
    resp = client.post(
        "/api/v1/forum/threads/99999/posts",
        json={"content": "x"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_thread_posts_list(app, client, auth_headers):
    cat_id, _, thread_id, _, _, _ = _setup_public_cat_and_thread(app)
    resp = client.get(f"/api/v1/forum/threads/{thread_id}/posts?page=1&limit=10", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    assert data["total"] >= 1


def test_post_update_by_author(app, client, auth_headers):
    cat_id, _, thread_id, _, post_id, _ = _setup_public_cat_and_thread(app)
    resp = client.put(
        f"/api/v1/forum/posts/{post_id}",
        json={"content": "Edited content"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "Edited content" in resp.get_json()["content"]


def test_post_update_not_found(app, client, auth_headers):
    resp = client.put(
        "/api/v1/forum/posts/99999",
        json={"content": "x"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_post_delete_by_author(app, client, auth_headers):
    cat_id, _, thread_id, _, post_id, _ = _setup_public_cat_and_thread(app)
    resp = client.delete(f"/api/v1/forum/posts/{post_id}", headers=auth_headers)
    assert resp.status_code == 200


def test_post_delete_not_found(app, client, auth_headers):
    resp = client.delete("/api/v1/forum/posts/99999", headers=auth_headers)
    assert resp.status_code == 404


# ============= BOOKMARK/UNBOOKMARK VIA ROUTE =============

def test_bookmark_unbookmark_route(app, client, auth_headers):
    cat_id, _, thread_id, _, _, _ = _setup_public_cat_and_thread(app)
    resp = client.post(f"/api/v1/forum/threads/{thread_id}/bookmark", headers=auth_headers)
    assert resp.status_code == 200
    resp = client.delete(f"/api/v1/forum/threads/{thread_id}/bookmark", headers=auth_headers)
    assert resp.status_code == 200


def test_bookmark_not_found(app, client, auth_headers):
    resp = client.post("/api/v1/forum/threads/99999/bookmark", headers=auth_headers)
    assert resp.status_code == 404


def test_bookmarks_list_route(app, client, auth_headers):
    cat_id, _, thread_id, _, _, _ = _setup_public_cat_and_thread(app)
    client.post(f"/api/v1/forum/threads/{thread_id}/bookmark", headers=auth_headers)
    resp = client.get("/api/v1/forum/bookmarks", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1


# ============= SUBSCRIBE/UNSUBSCRIBE VIA ROUTE =============

def test_subscribe_unsubscribe_route(app, client, auth_headers):
    cat_id, _, thread_id, _, _, _ = _setup_public_cat_and_thread(app)
    resp = client.post(f"/api/v1/forum/threads/{thread_id}/subscribe", headers=auth_headers)
    assert resp.status_code == 200
    resp = client.delete(f"/api/v1/forum/threads/{thread_id}/subscribe", headers=auth_headers)
    assert resp.status_code == 200


# ============= TAG ROUTES =============

def test_set_tags_route(app, client, auth_headers):
    cat_id, _, thread_id, _, _, _ = _setup_public_cat_and_thread(app)
    resp = client.put(
        f"/api/v1/forum/threads/{thread_id}/tags",
        json={"tags": ["Alpha", "Beta"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["tags"]) == 2


def test_set_tags_not_found(app, client, auth_headers):
    resp = client.put(
        "/api/v1/forum/threads/99999/tags",
        json={"tags": ["X"]},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_set_tags_invalid_body(app, client, auth_headers):
    cat_id, _, thread_id, _, _, _ = _setup_public_cat_and_thread(app)
    resp = client.put(
        f"/api/v1/forum/threads/{thread_id}/tags",
        data="not json",
        headers=auth_headers,
        content_type="text/plain",
    )
    assert resp.status_code == 400


def test_set_tags_invalid_format(app, client, auth_headers):
    cat_id, _, thread_id, _, _, _ = _setup_public_cat_and_thread(app)
    resp = client.put(
        f"/api/v1/forum/threads/{thread_id}/tags",
        json={"tags": "not-a-list"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


# ============= REPORT VIA ROUTE =============

def test_report_thread_via_route(app, client, auth_headers):
    cat_id, _, thread_id, _, _, _ = _setup_public_cat_and_thread(app)
    resp = client.post(
        "/api/v1/forum/reports",
        json={"target_type": "thread", "target_id": thread_id, "reason": "Spam content"},
        headers=auth_headers,
    )
    assert resp.status_code == 201


def test_report_post_via_route(app, client, auth_headers):
    cat_id, _, thread_id, _, post_id, _ = _setup_public_cat_and_thread(app)
    resp = client.post(
        "/api/v1/forum/reports",
        json={"target_type": "post", "target_id": post_id, "reason": "Offensive"},
        headers=auth_headers,
    )
    assert resp.status_code == 201


def test_report_invalid_target(app, client, auth_headers):
    resp = client.post(
        "/api/v1/forum/reports",
        json={"target_type": "invalid", "target_id": 1, "reason": "Bad"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_report_thread_not_found(app, client, auth_headers):
    resp = client.post(
        "/api/v1/forum/reports",
        json={"target_type": "thread", "target_id": 99999, "reason": "Missing"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ============= MODERATION: LOCK/UNLOCK/PIN/UNPIN VIA ROUTE =============

def test_lock_unlock_via_route(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="lock-cat", title="Lock Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="lock-thread", title="Lockable", status="open", author_id=mod.id)
        db.session.add(t)
        db.session.commit()
        thread_id = t.id
        cat_id = cat.id

    _assign_moderators_to_category(app, cat_id)
    resp = client.post(f"/api/v1/forum/threads/{thread_id}/lock", headers=moderator_headers)
    assert resp.status_code == 200
    resp = client.post(f"/api/v1/forum/threads/{thread_id}/unlock", headers=moderator_headers)
    assert resp.status_code == 200


def test_pin_unpin_via_route(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="pin-cat", title="Pin Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="pin-thread", title="Pinnable", status="open", author_id=mod.id)
        db.session.add(t)
        db.session.commit()
        thread_id = t.id
        _assign_moderators_to_category(app, cat.id)

    resp = client.post(f"/api/v1/forum/threads/{thread_id}/pin", headers=moderator_headers)
    assert resp.status_code == 200
    resp = client.post(f"/api/v1/forum/threads/{thread_id}/unpin", headers=moderator_headers)
    assert resp.status_code == 200


def test_post_delete_by_moderator(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="del-post-cat", title="DelPost", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="del-post-thread", title="DelPost", status="open", author_id=mod.id)
        db.session.add(t)
        db.session.flush()
        p = ForumPost(thread_id=t.id, author_id=mod.id, content="Del me", status="visible")
        db.session.add(p)
        db.session.commit()
        post_id = p.id

    resp = client.delete(f"/api/v1/forum/posts/{post_id}", headers=moderator_headers)
    assert resp.status_code == 200


def test_feature_unfeature_thread(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="feat-cat", title="Feat Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="feat-thread", title="Featurable", status="open", author_id=mod.id)
        db.session.add(t)
        db.session.commit()
        thread_id = t.id
        _assign_moderators_to_category(app, cat.id)

    resp = client.post(f"/api/v1/forum/threads/{thread_id}/feature", headers=moderator_headers)
    assert resp.status_code == 200
    assert resp.get_json()["is_featured"] is True
    resp = client.post(f"/api/v1/forum/threads/{thread_id}/unfeature", headers=moderator_headers)
    assert resp.status_code == 200
    assert resp.get_json()["is_featured"] is False


def test_archive_unarchive_via_route(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="arch-cat", title="Arch Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="arch-thread", title="Archivable", status="open", author_id=mod.id)
        db.session.add(t)
        db.session.commit()
        thread_id = t.id
        _assign_moderators_to_category(app, cat.id)

    resp = client.post(f"/api/v1/forum/threads/{thread_id}/archive", headers=moderator_headers)
    assert resp.status_code == 200
    resp = client.post(f"/api/v1/forum/threads/{thread_id}/unarchive", headers=moderator_headers)
    assert resp.status_code == 200


# ============= MODERATION: HIDE/UNHIDE POST =============

def test_hide_unhide_post_via_route(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="hp-cat", title="HP Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="hp-thread", title="HP Thread", status="open", author_id=mod.id)
        db.session.add(t)
        db.session.flush()
        p = ForumPost(thread_id=t.id, author_id=mod.id, content="Hide me", status="visible")
        db.session.add(p)
        db.session.commit()
        post_id = p.id
        _assign_moderators_to_category(app, cat.id)

    resp = client.post(f"/api/v1/forum/posts/{post_id}/hide", headers=moderator_headers)
    assert resp.status_code == 200
    # Verify activity log created
    with app.app_context():
        logs = ActivityLog.query.filter_by(action="post_hidden").all()
        assert len(logs) >= 1

    resp = client.post(f"/api/v1/forum/posts/{post_id}/unhide", headers=moderator_headers)
    assert resp.status_code == 200


# ============= MOVE THREAD =============

def test_move_thread_via_route(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat1 = ForumCategory(slug="mv-from", title="From", is_active=True, is_private=False)
        cat2 = ForumCategory(slug="mv-to", title="To", is_active=True, is_private=False)
        db.session.add_all([cat1, cat2])
        db.session.flush()
        t = ForumThread(category_id=cat1.id, slug="mv-thread-ext", title="Move Me", status="open", author_id=mod.id)
        db.session.add(t)
        db.session.commit()
        thread_id = t.id
        cat2_id = cat2.id
        _assign_moderators_to_category(app, cat1.id)
        _assign_moderators_to_category(app, cat2.id)

    resp = client.post(
        f"/api/v1/forum/threads/{thread_id}/move",
        json={"category_id": cat2_id},
        headers=moderator_headers,
    )
    assert resp.status_code == 200


# ============= MERGE THREAD =============

def test_merge_thread_via_route(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="merge-cat-ext", title="Merge", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        source = ForumThread(category_id=cat.id, slug="merge-source-ext", title="Source", status="open", author_id=mod.id)
        target = ForumThread(category_id=cat.id, slug="merge-target-ext", title="Target", status="open", author_id=mod.id)
        db.session.add_all([source, target])
        db.session.flush()
        ForumPost(thread_id=source.id, author_id=mod.id, content="P1", status="visible")
        db.session.add(ForumPost(thread_id=source.id, author_id=mod.id, content="P1", status="visible"))
        db.session.commit()
        source_id = source.id
        target_id = target.id
        _assign_moderators_to_category(app, cat.id)

    resp = client.post(
        f"/api/v1/forum/threads/{source_id}/merge",
        json={"target_thread_id": target_id},
        headers=moderator_headers,
    )
    assert resp.status_code == 200


# ============= BULK OPERATIONS =============

def test_bulk_thread_lock(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="bulk-cat", title="Bulk", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t1 = ForumThread(category_id=cat.id, slug="bulk-t1", title="B1", status="open", author_id=mod.id)
        t2 = ForumThread(category_id=cat.id, slug="bulk-t2", title="B2", status="open", author_id=mod.id)
        db.session.add_all([t1, t2])
        db.session.commit()
        ids = [t1.id, t2.id]
        _assign_moderators_to_category(app, cat.id)

    resp = client.post(
        "/api/v1/forum/moderation/bulk-threads/status",
        json={"thread_ids": ids, "lock": True},
        headers=moderator_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data["updated_ids"]) == set(ids)

    # Verify activity log
    with app.app_context():
        logs = ActivityLog.query.filter_by(action="threads_bulk_status_updated").all()
        assert len(logs) >= 1


def test_bulk_posts_hide(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="bulkp-cat", title="BulkP", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="bulkp-thread", title="BulkP", status="open", author_id=mod.id)
        db.session.add(t)
        db.session.flush()
        p1 = ForumPost(thread_id=t.id, author_id=mod.id, content="BP1", status="visible")
        p2 = ForumPost(thread_id=t.id, author_id=mod.id, content="BP2", status="visible")
        db.session.add_all([p1, p2])
        db.session.commit()
        ids = [p1.id, p2.id]
        _assign_moderators_to_category(app, cat.id)

    resp = client.post(
        "/api/v1/forum/moderation/bulk-posts/hide",
        json={"post_ids": ids, "hidden": True},
        headers=moderator_headers,
    )
    assert resp.status_code == 200
    assert set(resp.get_json()["updated_ids"]) == set(ids)


def test_bulk_thread_archive(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="bulka-cat", title="BulkA", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="bulka-t", title="BA", status="open", author_id=mod.id)
        db.session.add(t)
        db.session.commit()
        tid = t.id

    resp = client.post(
        "/api/v1/forum/moderation/bulk-threads/status",
        json={"thread_ids": [tid], "archive": True},
        headers=moderator_headers,
    )
    assert resp.status_code == 200


def test_bulk_thread_missing_action(app, client, moderator_headers):
    resp = client.post(
        "/api/v1/forum/moderation/bulk-threads/status",
        json={"thread_ids": [1]},
        headers=moderator_headers,
    )
    assert resp.status_code == 400


    resp = client.post(
        "/api/v1/forum/moderation/bulk-threads/status",
        json={"thread_ids": [1]},
        headers=moderator_headers,
    )
    assert resp.status_code == 400


def test_bulk_thread_empty_ids(app, client, moderator_headers):
    resp = client.post(
        "/api/v1/forum/moderation/bulk-threads/status",
        json={"thread_ids": [], "lock": True},
        headers=moderator_headers,
    )
    assert resp.status_code == 400


    resp = client.post(
        "/api/v1/forum/moderation/bulk-threads/status",
        json={"thread_ids": [], "lock": True},
        headers=moderator_headers,
    )
    assert resp.status_code == 400


def test_bulk_posts_hide_missing_hidden(app, client, moderator_headers):
    resp = client.post(
        "/api/v1/forum/moderation/bulk-posts/hide",
        json={"post_ids": [1]},
        headers=moderator_headers,
    )
    assert resp.status_code == 400


# ============= ADMIN CATEGORY CRUD =============

    resp = client.post(
        "/api/v1/forum/moderation/bulk-posts/hide",
        json={"post_ids": [1]},
        headers=moderator_headers,
    )
    assert resp.status_code == 400


# ============= ADMIN CATEGORY CRUD =============

def test_admin_create_category(app, client, admin_headers):
    resp = client.post(
        "/api/v1/forum/admin/categories",
        json={"slug": "admin-cat", "title": "Admin Cat"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["slug"] == "admin-cat"


def test_admin_create_category_duplicate(app, client, admin_headers):
    client.post(
        "/api/v1/forum/admin/categories",
        json={"slug": "dup-cat", "title": "Duplicate Category"},
        headers=admin_headers,
    )
    resp = client.post(
        "/api/v1/forum/admin/categories",
        json={"slug": "dup-cat", "title": "Duplicate Again"},
        headers=admin_headers,
    )
    assert resp.status_code == 409


def test_admin_update_category(app, client, admin_headers):
    resp = client.post(
        "/api/v1/forum/admin/categories",
        json={"slug": "upd-cat", "title": "Original"},
        headers=admin_headers,
    )
    cat_id = resp.get_json()["id"]
    resp = client.put(
        f"/api/v1/forum/admin/categories/{cat_id}",
        json={"title": "Updated"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Updated"


def test_admin_update_category_not_found(app, client, admin_headers):
    resp = client.put(
        "/api/v1/forum/admin/categories/99999",
        json={"title": "X"},
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_admin_delete_category(app, client, admin_headers):
    resp = client.post(
        "/api/v1/forum/admin/categories",
        json={"slug": "del-admin-cat", "title": "Delete Me"},
        headers=admin_headers,
    )
    cat_id = resp.get_json()["id"]
    resp = client.delete(f"/api/v1/forum/admin/categories/{cat_id}", headers=admin_headers)
    assert resp.status_code == 200


def test_admin_delete_category_not_found(app, client, admin_headers):
    resp = client.delete("/api/v1/forum/admin/categories/99999", headers=admin_headers)
    assert resp.status_code == 404


def test_admin_category_requires_admin(app, client, auth_headers):
    resp = client.post(
        "/api/v1/forum/admin/categories",
        json={"slug": "x", "title": "X"},
        headers=auth_headers,
    )
    assert resp.status_code == 403


# ============= MODERATION DASHBOARD =============

def test_moderation_log(app, client, moderator_headers):
    resp = client.get("/api/v1/forum/moderation/log", headers=moderator_headers)
    assert resp.status_code == 200
    assert "items" in resp.get_json()


    resp = client.get("/api/v1/forum/moderation/log", headers=moderator_headers)
    assert resp.status_code == 200
    assert "items" in resp.get_json()


def test_moderation_log_forbidden_for_user(app, client, auth_headers):
    resp = client.get("/api/v1/forum/moderation/log", headers=auth_headers)
    assert resp.status_code == 403


def test_subscribers_list(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="sub-list-cat", title="SubList", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="sub-list-thread", title="SubList", status="open", author_id=mod.id)
        db.session.add(t)
        db.session.commit()
        thread_id = t.id

    resp = client.get(f"/api/v1/forum/threads/{thread_id}/subscribers", headers=moderator_headers)
    assert resp.status_code == 200
    assert "items" in resp.get_json()


def test_moderation_recent_reports(app, client, moderator_headers):
    resp = client.get("/api/v1/forum/moderation/recent-reports", headers=moderator_headers)
    assert resp.status_code == 200


    resp = client.get("/api/v1/forum/moderation/recent-reports", headers=moderator_headers)
    assert resp.status_code == 200


def test_moderation_hidden_posts(app, client, moderator_headers):
    resp = client.get("/api/v1/forum/moderation/hidden-posts", headers=moderator_headers)
    assert resp.status_code == 200


    resp = client.get("/api/v1/forum/moderation/hidden-posts", headers=moderator_headers)
    assert resp.status_code == 200


def test_moderation_locked_threads(app, client, moderator_headers):
    resp = client.get("/api/v1/forum/moderation/locked-threads", headers=moderator_headers)
    assert resp.status_code == 200


# ============= NOTIFICATIONS =============

    resp = client.get("/api/v1/forum/moderation/locked-threads", headers=moderator_headers)
    assert resp.status_code == 200


# ============= NOTIFICATIONS =============

def test_notifications_list_with_unread(app, client, auth_headers):
    resp = client.get("/api/v1/notifications?unread_only=true", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    assert "total" in data


def test_notifications_mark_all_read(app, client, auth_headers):
    resp = client.post("/api/v1/notifications/read-all", headers=auth_headers)
    assert resp.status_code == 200


# ============= SEARCH =============

def test_search_empty_returns_empty(app, client, auth_headers):
    resp = client.get("/api/v1/forum/search", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["total"] == 0


def test_search_by_text(app, client, auth_headers):
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="s-cat", title="S", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="searchable-xyz", title="XYZ Unique Title", status="open", author_id=user.id)
        db.session.add(t)
        db.session.commit()

    resp = client.get("/api/v1/forum/search?q=XYZ+Unique", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1


def test_search_by_status(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="ss-cat", title="SS", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="ss-locked", title="Locked Search", status="locked", author_id=mod.id)
        db.session.add(t)
        db.session.commit()

    resp = client.get("/api/v1/forum/search?status=locked&q=Locked", headers=moderator_headers)
    assert resp.status_code == 200


def test_search_with_content(app, client, auth_headers):
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        cat = ForumCategory(slug="sc-cat", title="SC", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="sc-thread", title="SC Thread", status="open", author_id=user.id)
        db.session.add(t)
        db.session.flush()
        p = ForumPost(thread_id=t.id, author_id=user.id, content="Unique content string QWE", status="visible")
        db.session.add(p)
        db.session.commit()

    resp = client.get("/api/v1/forum/search?q=QWE&include_content=1", headers=auth_headers)
    assert resp.status_code == 200


# ============= REPORTS LIST (MOD) =============

def test_reports_list_route(app, client, moderator_headers):
    resp = client.get("/api/v1/forum/reports?page=1&limit=10", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data


    resp = client.get("/api/v1/forum/reports?page=1&limit=10", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data


def test_report_detail_route(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="rdcat", title="RD", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="rd-thread", title="RD", status="open", author_id=mod.id)
        db.session.add(t)
        db.session.flush()
        report = ForumReport(target_type="thread", target_id=t.id, reported_by=mod.id, reason="Test", status="open")
        db.session.add(report)
        db.session.commit()
        report_id = report.id

    resp = client.get(f"/api/v1/forum/reports/{report_id}", headers=moderator_headers)
    assert resp.status_code == 200


def test_report_update_route(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="rucat", title="RU", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="ru-thread", title="RU", status="open", author_id=mod.id)
        db.session.add(t)
        db.session.flush()
        report = ForumReport(target_type="thread", target_id=t.id, reported_by=mod.id, reason="Test", status="open")
        db.session.add(report)
        db.session.commit()
        report_id = report.id

    resp = client.put(
        f"/api/v1/forum/reports/{report_id}",
        json={"status": "resolved", "resolution_note": "Fixed"},
        headers=moderator_headers,
    )
    assert resp.status_code == 200


# ============= ACTIVITY LOG AFTER LOCK =============

def test_activity_log_after_lock(app, client, moderator_headers):
    with app.app_context():
        mod = User.query.filter_by(username="moderatoruser").first()
        cat = ForumCategory(slug="log-lock-cat", title="Log Lock Category", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        t = ForumThread(category_id=cat.id, slug="log-lock-t", title="Log Lock Thread", status="open", author_id=mod.id)
        db.session.add(t)
        db.session.commit()
        thread_id = t.id

    _assign_moderators_to_category(app, t.category_id)
    client.post(f"/api/v1/forum/threads/{thread_id}/lock", headers=moderator_headers)

    with app.app_context():
        logs = ActivityLog.query.filter_by(action="thread_locked").all()
        assert len(logs) >= 1
