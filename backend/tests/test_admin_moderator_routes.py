"""Tests for /api/v1/admin/moderator-assignments (admin_routes)."""
from unittest.mock import patch

import pytest

from app.extensions import db
from app.models import ForumCategory, User
from app.models.forum import ModeratorAssignment


@pytest.fixture
def mod_cat_and_moderator(app, moderator_user):
    """Forum category and moderator user id for assignment tests."""
    with app.app_context():
        cat = ForumCategory(
            slug="mod-assign-cat",
            title="Mod Assign Cat",
            is_active=True,
            is_private=False,
        )
        db.session.add(cat)
        db.session.commit()
        db.session.refresh(cat)
        mod, _ = moderator_user
        return {"category_id": cat.id, "moderator_id": mod.id, "slug": cat.slug}


def test_moderator_assignments_list_parse_int_and_filters(
    client, admin_headers, app, mod_cat_and_moderator
):
    """List uses defaults/caps for bad query params; filters by user_id and category_id."""
    mid = mod_cat_and_moderator["moderator_id"]
    cid = mod_cat_and_moderator["category_id"]
    with app.app_context():
        db.session.add(
            ModeratorAssignment(user_id=mid, category_id=cid, assigned_by=mid)
        )
        db.session.commit()

    r = client.get(
        "/api/v1/admin/moderator-assignments?page=0&limit=999&user_id=notint&category_id=xx",
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["page"] == 1
    assert body["limit"] == 100

    r2 = client.get(
        f"/api/v1/admin/moderator-assignments?user_id={mid}",
        headers=admin_headers,
    )
    assert r2.status_code == 200
    assert r2.get_json()["total"] >= 1

    r3 = client.get(
        f"/api/v1/admin/moderator-assignments?category_id={cid}",
        headers=admin_headers,
    )
    assert r3.status_code == 200
    assert r3.get_json()["total"] >= 1


def test_moderator_assignments_post_validation_and_errors(
    client, admin_headers, app, mod_cat_and_moderator, test_user
):
    """POST: invalid JSON, bad ids, plain user, missing category, duplicate, success."""
    mid = mod_cat_and_moderator["moderator_id"]
    cid = mod_cat_and_moderator["category_id"]
    plain_uid, _ = test_user
    plain_uid = plain_uid.id

    assert client.post(
        "/api/v1/admin/moderator-assignments",
        data="not-json",
        headers={**admin_headers, "Content-Type": "application/json"},
    ).status_code == 400

    r_bad = client.post(
        "/api/v1/admin/moderator-assignments",
        json={"user_id": "x", "category_id": cid},
        headers=admin_headers,
    )
    assert r_bad.status_code == 400

    r_plain = client.post(
        "/api/v1/admin/moderator-assignments",
        json={"user_id": plain_uid, "category_id": cid},
        headers=admin_headers,
    )
    assert r_plain.status_code == 404

    r_nocat = client.post(
        "/api/v1/admin/moderator-assignments",
        json={"user_id": mid, "category_id": 999999},
        headers=admin_headers,
    )
    assert r_nocat.status_code == 404

    r_ok = client.post(
        "/api/v1/admin/moderator-assignments",
        json={"user_id": mid, "category_id": cid},
        headers=admin_headers,
    )
    assert r_ok.status_code == 201

    r_dup = client.post(
        "/api/v1/admin/moderator-assignments",
        json={"user_id": mid, "category_id": cid},
        headers=admin_headers,
    )
    assert r_dup.status_code == 409


def test_moderator_assignments_delete_and_user_list(
    client, admin_headers, app, admin_user, mod_cat_and_moderator
):
    """DELETE 404, DELETE success; GET user assignments 404 and 200."""
    admin, _ = admin_user
    mid = mod_cat_and_moderator["moderator_id"]
    cid = mod_cat_and_moderator["category_id"]

    r404 = client.delete(
        "/api/v1/admin/moderator-assignments/999999",
        headers=admin_headers,
    )
    assert r404.status_code == 404

    with app.app_context():
        a = ModeratorAssignment(user_id=mid, category_id=cid, assigned_by=admin.id)
        db.session.add(a)
        db.session.commit()
        db.session.refresh(a)
        aid = a.id

    r_del = client.delete(
        f"/api/v1/admin/moderator-assignments/{aid}",
        headers=admin_headers,
    )
    assert r_del.status_code == 200

    r_user_missing = client.get(
        "/api/v1/admin/moderator-assignments/user/999999",
        headers=admin_headers,
    )
    assert r_user_missing.status_code == 404

    with app.app_context():
        a2 = ModeratorAssignment(user_id=mid, category_id=cid, assigned_by=admin.id)
        db.session.add(a2)
        db.session.commit()

    r_user_ok = client.get(
        f"/api/v1/admin/moderator-assignments/user/{mid}",
        headers=admin_headers,
    )
    assert r_user_ok.status_code == 200
    data = r_user_ok.get_json()
    assert data["user_id"] == mid
    assert len(data["categories"]) >= 1


def test_moderator_assignments_delete_logs_unknown_user_and_category(
    client, admin_headers, app, admin_user, mod_cat_and_moderator, monkeypatch
):
    """DELETE success path when User or ForumCategory row is missing (message fallback)."""
    admin, _ = admin_user
    mid = mod_cat_and_moderator["moderator_id"]
    cid = mod_cat_and_moderator["category_id"]

    with app.app_context():
        a = ModeratorAssignment(user_id=mid, category_id=cid, assigned_by=admin.id)
        db.session.add(a)
        db.session.commit()
        db.session.refresh(a)
        aid = a.id

    real_user_get = User.query.get

    def user_get(uid):
        if uid == mid:
            return None
        return real_user_get(uid)

    with patch.object(User.query, "get", side_effect=user_get):
        r = client.delete(
            f"/api/v1/admin/moderator-assignments/{aid}",
            headers=admin_headers,
        )
    assert r.status_code == 200

    with app.app_context():
        a2 = ModeratorAssignment(user_id=mid, category_id=cid, assigned_by=admin.id)
        db.session.add(a2)
        db.session.commit()
        db.session.refresh(a2)
        aid2 = a2.id

    real_cat_get = ForumCategory.query.get

    def cat_get(cat_id):
        if cat_id == cid:
            return None
        return real_cat_get(cat_id)

    with patch.object(ForumCategory.query, "get", side_effect=cat_get):
        r2 = client.delete(
            f"/api/v1/admin/moderator-assignments/{aid2}",
            headers=admin_headers,
        )
    assert r2.status_code == 200


def test_admin_list_user_assignments_skips_orphan_category(
    client, admin_headers, app, admin_user, mod_cat_and_moderator
):
    """GET user assignments skips entries when ForumCategory row is missing."""
    admin, _ = admin_user
    mid = mod_cat_and_moderator["moderator_id"]
    cid = mod_cat_and_moderator["category_id"]
    with app.app_context():
        a = ModeratorAssignment(user_id=mid, category_id=cid, assigned_by=admin.id)
        db.session.add(a)
        db.session.commit()

    with patch.object(ForumCategory.query, "get", return_value=None):
        r = client.get(
            f"/api/v1/admin/moderator-assignments/user/{mid}",
            headers=admin_headers,
        )
    assert r.status_code == 200
    assert r.get_json()["categories"] == []
    assert r.get_json()["total"] == 0
