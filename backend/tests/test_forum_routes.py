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
from app.api.v1.forum_routes import (
    _enrich_report_dict,
    _parse_int,
    _validate_category_title_length,
    _validate_content_length,
    _validate_title_length,
)


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


# --- forum_routes helpers and moderation-route coverage ---


def test_parse_int_variants():
    assert _parse_int(None, 7) == 7
    assert _parse_int("", 7) == 7
    assert _parse_int("3", 1, min_val=1, max_val=10) == 3
    assert _parse_int("0", 5, min_val=1) == 5
    assert _parse_int("99", 1, min_val=1, max_val=10) == 10
    assert _parse_int("x", 2) == 2


def test_validate_content_length():
    ok, err = _validate_content_length(123)
    assert ok is False and "string" in (err or "").lower()

    ok2, err2 = _validate_content_length("a")
    assert ok2 is False and "at least" in (err2 or "").lower()

    ok3, err3 = _validate_content_length("hello there")
    assert ok3 is True and err3 is None


def test_validate_title_and_category_title():
    ok, err = _validate_title_length(None)
    assert ok is False

    ok2, err2 = _validate_title_length("ab")
    assert ok2 is False

    ok3, _ = _validate_title_length("valid title here")
    assert ok3 is True

    ok4, err4 = _validate_category_title_length("x")
    assert ok4 is False
    ok5, _ = _validate_category_title_length("Category title ok")
    assert ok5 is True

    ok6, err6 = _validate_category_title_length(123)
    assert ok6 is False and "string" in (err6 or "").lower()
    long_cat = "x" * 201
    ok7, err7 = _validate_category_title_length(long_cat)
    assert ok7 is False and "200" in (err7 or "")


def test_enrich_report_dict_thread_and_post(app, test_user):
    with app.app_context():
        user, _ = test_user
        cat = ForumCategory(slug="rep-cat", title="RC", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(
            category_id=cat.id,
            slug="rep-thread",
            title="Thread Title",
            status="open",
            author_id=user.id,
        )
        db.session.add(thread)
        db.session.flush()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="Post body text here", status="visible")
        db.session.add(post)
        db.session.flush()

        rt = ForumReport(
            target_type="thread",
            target_id=thread.id,
            reported_by=user.id,
            reason="spam",
            status="open",
        )
        rp = ForumReport(
            target_type="post",
            target_id=post.id,
            reported_by=user.id,
            reason="abuse",
            status="open",
        )
        db.session.add_all([rt, rp])
        db.session.commit()

        dt = _enrich_report_dict(rt)
        assert dt.get("thread_slug") == "rep-thread"
        assert dt.get("target_title") == "Thread Title"

        dp = _enrich_report_dict(rp)
        assert dp.get("thread_slug") == "rep-thread"
        assert "Post body" in (dp.get("target_title") or "")


def test_moderation_recent_reports_and_locked_threads(app, client, moderator_headers, test_user):
    with app.app_context():
        user, _ = test_user
        cat = ForumCategory(slug="mod-api-cat", title="MAC", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(
            category_id=cat.id,
            slug="locked-slug",
            title="Locked",
            status="open",
            author_id=user.id,
            is_locked=True,
        )
        db.session.add(thread)
        db.session.flush()
        rep = ForumReport(
            target_type="thread",
            target_id=thread.id,
            reported_by=user.id,
            reason="test",
            status="open",
        )
        db.session.add(rep)
        db.session.commit()

    r1 = client.get("/api/v1/forum/moderation/recent-reports", headers=moderator_headers)
    assert r1.status_code == 200
    data = r1.get_json()
    assert "items" in data
    assert data["total"] >= 1

    r2 = client.get("/api/v1/forum/moderation/locked-threads", headers=moderator_headers)
    assert r2.status_code == 200
    items = r2.get_json().get("items", [])
    assert any(x.get("slug") == "locked-slug" for x in items)


def test_moderation_recently_handled(app, client, moderator_headers, test_user):
    with app.app_context():
        user, _ = test_user
        cat = ForumCategory(slug="handled-cat", title="HC", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(
            category_id=cat.id,
            slug="handled-thread",
            title="Handled T",
            status="open",
            author_id=user.id,
        )
        db.session.add(thread)
        db.session.flush()
        now = datetime.now(timezone.utc)
        rep = ForumReport(
            target_type="thread",
            target_id=thread.id,
            reported_by=user.id,
            reason="x",
            status="resolved",
            handled_at=now,
        )
        db.session.add(rep)
        db.session.commit()

    r = client.get("/api/v1/forum/moderation/recently-handled", headers=moderator_headers)
    assert r.status_code == 200
    assert r.get_json().get("total", 0) >= 1


def test_moderation_bulk_threads_invalid_json(client, moderator_headers):
    r = client.post(
        "/api/v1/forum/moderation/bulk-threads/status",
        headers={**moderator_headers, "Content-Type": "application/json"},
        data="not json",
    )
    assert r.status_code == 400


def test_forum_categories_survives_get_current_user_exception(client, monkeypatch):
    from app.api.v1 import forum_routes

    def _boom():
        raise RuntimeError("jwt")

    monkeypatch.setattr(forum_routes, "get_current_user", _boom)
    r = client.get("/api/v1/forum/categories")
    assert r.status_code == 200
    assert "items" in r.get_json()


def test_forum_category_unknown_slug_returns_404(client):
    r = client.get("/api/v1/forum/categories/does-not-exist-slug-99999")
    assert r.status_code == 404


def test_forum_category_threads_unknown_returns_404(client):
    r = client.get("/api/v1/forum/categories/missing-cat/threads")
    assert r.status_code == 404


def test_forum_thread_detail_unknown_slug_returns_404(client):
    r = client.get("/api/v1/forum/threads/no-such-thread-slug-ever-12345")
    assert r.status_code == 404


def test_forum_thread_posts_unknown_id_returns_404(client):
    r = client.get("/api/v1/forum/threads/999999999/posts")
    assert r.status_code == 404


def test_forum_search_no_filters_returns_empty(client):
    r = client.get("/api/v1/forum/search")
    assert r.status_code == 200
    body = r.get_json()
    assert body["items"] == []
    assert body["total"] == 0


def test_forum_search_short_query_returns_400(client):
    r = client.get("/api/v1/forum/search?q=ab")
    assert r.status_code == 400


def test_forum_search_invalid_status_returns_400(client):
    r = client.get("/api/v1/forum/search?q=hello&status=not_a_status")
    assert r.status_code == 400


# --- forum_routes coverage plan (target ~90% line coverage; not every duplicate JWT guard branch) ---


def test_require_user_returns_401_without_user(app, monkeypatch):
    from app.api.v1 import forum_routes as fr

    monkeypatch.setattr(fr, "get_current_user", lambda: None)
    with app.test_request_context():
        user, resp = fr._require_user()
    assert user is None
    assert resp[1] == 401


def test_require_user_returns_403_when_banned(app, monkeypatch):
    from app.api.v1 import forum_routes as fr

    banned = User()
    banned.is_banned = True
    monkeypatch.setattr(fr, "get_current_user", lambda: banned)
    with app.test_request_context():
        user, resp = fr._require_user()
    assert user is None
    assert resp[1] == 403


def test_forum_thread_create_without_jwt_returns_401(client):
    r = client.post(
        "/api/v1/forum/categories/any-slug/threads",
        json={"title": "valid title here", "content": "valid content here ok"},
    )
    assert r.status_code == 401


def test_forum_thread_create_banned_user_returns_403(app, client, test_user, auth_headers):
    """JWT was issued before ban; login after ban would be 403 — thread create must still return 403."""
    with app.app_context():
        u, _pwd = test_user
        user = db.session.get(User, u.id)
        cat = ForumCategory(slug="ban-thread-cat", title="Ban Thread Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        user.is_banned = True
        db.session.commit()
    r = client.post(
        "/api/v1/forum/categories/ban-thread-cat/threads",
        headers=auth_headers,
        json={"title": "hello thread title", "content": "enough content here for thread"},
    )
    assert r.status_code == 403


def test_forum_report_create_invalid_body_and_errors(app, client, auth_headers, test_user):
    r0 = client.post(
        "/api/v1/forum/reports",
        headers={**auth_headers, "Content-Type": "application/json"},
        data="not-json",
    )
    assert r0.status_code == 400

    r1 = client.post(
        "/api/v1/forum/reports",
        headers=auth_headers,
        json={"target_type": "nope", "target_id": 1, "reason": "spam here"},
    )
    assert r1.status_code == 400

    r2 = client.post(
        "/api/v1/forum/reports",
        headers=auth_headers,
        json={"target_type": "thread", "target_id": "x", "reason": "spam here"},
    )
    assert r2.status_code == 400

    with app.app_context():
        u, _ = test_user
        cat = ForumCategory(slug="rep-cov-cat", title="Rep Cov", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        th = ForumThread(
            category_id=cat.id,
            slug="rep-cov-th",
            title="Thread for report",
            status="open",
            author_id=u.id,
        )
        db.session.add(th)
        db.session.commit()
        tid = th.id

    r3 = client.post(
        "/api/v1/forum/reports",
        headers=auth_headers,
        json={"target_type": "thread", "target_id": tid, "reason": "   "},
    )
    assert r3.status_code == 400


def test_forum_report_get_not_found_returns_404(client, moderator_headers):
    r = client.get("/api/v1/forum/reports/999999999", headers=moderator_headers)
    assert r.status_code == 404


def test_forum_report_update_invalid_priority_and_valueerror(app, client, moderator_headers, test_user):
    with app.app_context():
        u, _ = test_user
        cat = ForumCategory(slug="put-rep-cat", title="Put Rep", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        th = ForumThread(
            category_id=cat.id,
            slug="put-rep-th",
            title="Thread",
            status="open",
            author_id=u.id,
        )
        db.session.add(th)
        db.session.flush()
        rep = ForumReport(
            target_type="thread",
            target_id=th.id,
            reported_by=u.id,
            reason="issue",
            status="open",
        )
        db.session.add(rep)
        db.session.commit()
        rid = rep.id

    r_bad_pri = client.put(
        f"/api/v1/forum/reports/{rid}",
        headers=moderator_headers,
        json={"status": "reviewed", "priority": "mega"},
    )
    assert r_bad_pri.status_code == 400

    r_val = client.put(
        f"/api/v1/forum/reports/{rid}",
        headers=moderator_headers,
        json={"status": "not_a_valid_status"},
    )
    assert r_val.status_code == 400


def test_forum_reports_bulk_status_validation_errors(client, moderator_headers):
    r_json = client.post(
        "/api/v1/forum/reports/bulk-status",
        headers={**moderator_headers, "Content-Type": "application/json"},
        data="not json",
    )
    assert r_json.status_code == 400

    r_empty = client.post(
        "/api/v1/forum/reports/bulk-status",
        headers=moderator_headers,
        json={"report_ids": [], "status": "reviewed"},
    )
    assert r_empty.status_code == 400

    r_not_list = client.post(
        "/api/v1/forum/reports/bulk-status",
        headers=moderator_headers,
        json={"report_ids": 1, "status": "reviewed"},
    )
    assert r_not_list.status_code == 400

    r_bad_id = client.post(
        "/api/v1/forum/reports/bulk-status",
        headers=moderator_headers,
        json={"report_ids": ["x"], "status": "reviewed"},
    )
    assert r_bad_id.status_code == 400

    r_bad_status = client.post(
        "/api/v1/forum/reports/bulk-status",
        headers=moderator_headers,
        json={"report_ids": [1], "status": "open"},
    )
    assert r_bad_status.status_code == 400

    r_bad_pri = client.post(
        "/api/v1/forum/reports/bulk-status",
        headers=moderator_headers,
        json={"report_ids": [1], "status": "reviewed", "priority": "invalid"},
    )
    assert r_bad_pri.status_code == 400


def test_forum_moderation_bulk_threads_missing_lock_archive(client, moderator_headers):
    r = client.post(
        "/api/v1/forum/moderation/bulk-threads/status",
        headers=moderator_headers,
        json={"thread_ids": [1]},
    )
    assert r.status_code == 400


def test_forum_moderation_bulk_threads_empty_and_bad_ids(client, moderator_headers):
    r0 = client.post(
        "/api/v1/forum/moderation/bulk-threads/status",
        headers=moderator_headers,
        json={"thread_ids": [], "lock": True},
    )
    assert r0.status_code == 400

    r1 = client.post(
        "/api/v1/forum/moderation/bulk-threads/status",
        headers=moderator_headers,
        json={"thread_ids": "1", "lock": True},
    )
    assert r1.status_code == 400

    r2 = client.post(
        "/api/v1/forum/moderation/bulk-threads/status",
        headers=moderator_headers,
        json={"thread_ids": ["n"], "lock": True},
    )
    assert r2.status_code == 400


def test_forum_moderation_bulk_threads_skips_without_category_assignment(
    app, client, moderator_headers, test_user
):
    with app.app_context():
        u, _ = test_user
        cat = ForumCategory(slug="no-assign-cat", title="No Assign", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        th = ForumThread(
            category_id=cat.id,
            slug="no-assign-th",
            title="No assign thread",
            status="open",
            author_id=u.id,
        )
        db.session.add(th)
        db.session.commit()
        tid = th.id

    r = client.post(
        "/api/v1/forum/moderation/bulk-threads/status",
        headers=moderator_headers,
        json={"thread_ids": [tid], "lock": True},
    )
    assert r.status_code == 200
    assert r.get_json()["updated_ids"] == []


def test_forum_moderation_bulk_posts_hide_validation(client, moderator_headers):
    r_json = client.post(
        "/api/v1/forum/moderation/bulk-posts/hide",
        headers={**moderator_headers, "Content-Type": "application/json"},
        data="not json",
    )
    assert r_json.status_code == 400

    r_empty = client.post(
        "/api/v1/forum/moderation/bulk-posts/hide",
        headers=moderator_headers,
        json={"post_ids": [], "hidden": True},
    )
    assert r_empty.status_code == 400

    r_no_hidden = client.post(
        "/api/v1/forum/moderation/bulk-posts/hide",
        headers=moderator_headers,
        json={"post_ids": [1]},
    )
    assert r_no_hidden.status_code == 400

    r_bad = client.post(
        "/api/v1/forum/moderation/bulk-posts/hide",
        headers=moderator_headers,
        json={"post_ids": ["z"], "hidden": True},
    )
    assert r_bad.status_code == 400


def test_forum_moderation_bulk_posts_skips_without_assignment(app, client, moderator_headers, test_user):
    with app.app_context():
        u, _ = test_user
        cat = ForumCategory(slug="post-no-asg", title="PNA", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        th = ForumThread(
            category_id=cat.id,
            slug="post-no-asg-th",
            title="Thread",
            status="open",
            author_id=u.id,
        )
        db.session.add(th)
        db.session.flush()
        po = ForumPost(thread_id=th.id, author_id=u.id, content="Post body text here ok", status="visible")
        db.session.add(po)
        db.session.commit()
        pid = po.id

    r = client.post(
        "/api/v1/forum/moderation/bulk-posts/hide",
        headers=moderator_headers,
        json={"post_ids": [pid], "hidden": True},
    )
    assert r.status_code == 200
    assert r.get_json()["updated_ids"] == []


def test_forum_moderation_log_forbidden_for_plain_user(client, auth_headers):
    r = client.get("/api/v1/forum/moderation/log", headers=auth_headers)
    assert r.status_code == 403


def test_forum_post_like_idempotent_branch_when_like_post_returns_error(
    app, client, auth_headers, test_user, monkeypatch
):
    """Route treats truthy err from like_post as duplicate (service normally returns err=None)."""
    from app.api.v1 import forum_routes as fr

    with app.app_context():
        u, _ = test_user
        cat = ForumCategory(slug="like-dup-cat", title="Like Dup", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        th = ForumThread(
            category_id=cat.id,
            slug="like-dup-th",
            title="Like dup thread",
            status="open",
            author_id=u.id,
        )
        db.session.add(th)
        db.session.flush()
        po = ForumPost(thread_id=th.id, author_id=u.id, content="Post for like dup", status="visible")
        db.session.add(po)
        db.session.commit()
        pid = po.id

    monkeypatch.setattr(fr, "like_post", lambda _u, _p: (None, "duplicate"))

    r = client.post(f"/api/v1/forum/posts/{pid}/like", headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json().get("message") == "Already liked"
