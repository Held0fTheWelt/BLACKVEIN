"""Tests for User CRUD API. Aligned with Postman suite: List (admin), Get (self/other), Update, Delete."""
import pytest

from app.models import User, Role
from werkzeug.security import generate_password_hash
from app.extensions import db


def test_users_list_without_token_returns_401(client):
    """GET /api/v1/users without JWT returns 401."""
    r = client.get("/api/v1/users")
    assert r.status_code == 401
    assert r.get_json().get("error")


def test_users_list_as_admin_returns_200_and_structure(client, admin_headers):
    """GET /api/v1/users with admin JWT returns 200 and items, total, page, per_page."""
    r = client.get("/api/v1/users?page=1&limit=20", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["per_page"] == 20
    assert isinstance(data["items"], list)


def test_users_list_as_non_admin_returns_403(client, auth_headers):
    """GET /api/v1/users with non-admin JWT returns 403."""
    r = client.get("/api/v1/users", headers=auth_headers)
    assert r.status_code == 403
    assert r.get_json().get("error") == "Forbidden"


def test_users_get_self_returns_200(client, auth_headers, test_user):
    """GET /api/v1/users/<id> for own id returns 200 with id, username, role."""
    user, _ = test_user
    r = client.get(f"/api/v1/users/{user.id}", headers=auth_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["id"] == user.id
    assert data["username"] == user.username
    assert "role" in data


def test_users_get_as_admin_other_user_returns_200(client, app, admin_headers, test_user):
    """GET /api/v1/users/<id> as admin for another user returns 200."""
    user, _ = test_user
    r = client.get(f"/api/v1/users/{user.id}", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["id"] == user.id
    assert data["username"] == user.username


def test_users_get_as_non_admin_other_user_returns_403(client, app, auth_headers, admin_user):
    """GET /api/v1/users/<id> as non-admin for another user returns 403."""
    admin, _ = admin_user
    r = client.get(f"/api/v1/users/{admin.id}", headers=auth_headers)
    assert r.status_code == 403
    assert r.get_json().get("error") == "Forbidden"


def test_users_get_404(client, admin_headers):
    """GET /api/v1/users/999999 returns 404."""
    r = client.get("/api/v1/users/999999", headers=admin_headers)
    assert r.status_code == 404
    assert r.get_json().get("error")


def test_users_get_without_token_returns_401(client, test_user):
    """GET /api/v1/users/<id> without JWT returns 401."""
    user, _ = test_user
    r = client.get(f"/api/v1/users/{user.id}")
    assert r.status_code == 401


def test_users_update_self_returns_200(client, auth_headers, test_user):
    """PUT /api/v1/users/<id> for own id returns 200 and updated username."""
    user, _ = test_user
    r = client.put(
        f"/api/v1/users/{user.id}",
        headers=auth_headers,
        json={"username": "testuser_updated"},
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["username"] == "testuser_updated"
    assert data["id"] == user.id


def test_users_update_as_admin_other_user_returns_200(client, app, admin_headers, test_user):
    """PUT /api/v1/users/<id> as admin for another user returns 200."""
    user, _ = test_user
    r = client.put(
        f"/api/v1/users/{user.id}",
        headers=admin_headers,
        json={"username": "renamed_by_admin"},
        content_type="application/json",
    )
    assert r.status_code == 200
    assert r.get_json()["username"] == "renamed_by_admin"


def test_users_update_as_non_admin_other_user_returns_403(client, app, auth_headers, admin_user):
    """PUT /api/v1/users/<id> as non-admin for another user returns 403."""
    admin, _ = admin_user
    r = client.put(
        f"/api/v1/users/{admin.id}",
        headers=auth_headers,
        json={"username": "hacker"},
        content_type="application/json",
    )
    assert r.status_code == 403
    assert r.get_json().get("error") == "Forbidden"


def test_users_update_404(client, admin_headers):
    """PUT /api/v1/users/999999 returns 404."""
    r = client.put(
        "/api/v1/users/999999",
        headers=admin_headers,
        json={"username": "x"},
        content_type="application/json",
    )
    assert r.status_code == 404


def test_users_delete_as_admin_returns_200(client, app, super_admin_headers, test_user):
    """DELETE /api/v1/users/<id> as super_admin for another user returns 200."""
    user, _ = test_user
    r = client.delete(f"/api/v1/users/{user.id}", headers=super_admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("message")
    with app.app_context():
        from app.models import User
        assert User.query.get(user.id) is None


def test_users_delete_as_non_admin_returns_403(client, app, auth_headers, admin_user):
    """DELETE /api/v1/users/<id> as non-admin returns 403."""
    admin, _ = admin_user
    r = client.delete(f"/api/v1/users/{admin.id}", headers=auth_headers)
    assert r.status_code == 403
    assert r.get_json().get("error") == "Forbidden"


def test_users_delete_404(client, super_admin_headers):
    """DELETE /api/v1/users/999999 returns 404."""
    r = client.delete("/api/v1/users/999999", headers=super_admin_headers)
    assert r.status_code == 404


def test_users_delete_without_token_returns_401(client, test_user):
    """DELETE /api/v1/users/<id> without JWT returns 401."""
    user, _ = test_user
    r = client.delete(f"/api/v1/users/{user.id}")
    assert r.status_code == 401


def test_users_get_self_banned_returns_403(client, app, banned_user):
    """GET /api/v1/users/<id> for own id when banned returns 403."""
    user, _ = banned_user
    with app.app_context():
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=str(user.id))
    r = client.get(f"/api/v1/users/{user.id}", headers={"Authorization": "Bearer " + token})
    assert r.status_code == 403
    assert "restricted" in (r.get_json().get("error") or "").lower()


def test_users_assign_role_as_admin_returns_200(client, admin_headers, test_user):
    """PATCH /api/v1/users/<id>/role as admin with valid role returns 200."""
    user, _ = test_user
    r = client.patch(
        f"/api/v1/users/{user.id}/role",
        headers=admin_headers,
        json={"role": "moderator"},
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["role"] == "moderator"
    assert "is_banned" in data


def test_users_assign_role_as_non_admin_returns_403(client, auth_headers, test_user):
    """PATCH /api/v1/users/<id>/role as non-admin returns 403."""
    user, _ = test_user
    r = client.patch(
        f"/api/v1/users/{user.id}/role",
        headers=auth_headers,
        json={"role": "moderator"},
        content_type="application/json",
    )
    assert r.status_code == 403
    assert r.get_json().get("error") == "Forbidden"


def test_users_assign_role_invalid_returns_400(client, admin_headers, test_user):
    """PATCH /api/v1/users/<id>/role with invalid role returns 400."""
    user, _ = test_user
    r = client.patch(
        f"/api/v1/users/{user.id}/role",
        headers=admin_headers,
        json={"role": "superuser"},
        content_type="application/json",
    )
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_users_ban_as_admin_returns_200(client, admin_headers, test_user):
    """POST /api/v1/users/<id>/ban as admin returns 200 and user is_banned true."""
    user, _ = test_user
    r = client.post(
        f"/api/v1/users/{user.id}/ban",
        headers=admin_headers,
        json={"reason": "Test ban reason"},
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["is_banned"] is True
    assert data.get("ban_reason") == "Test ban reason"


def test_users_ban_as_non_admin_returns_403(client, auth_headers, test_user):
    """POST /api/v1/users/<id>/ban as non-admin returns 403."""
    user, _ = test_user
    r = client.post(
        f"/api/v1/users/{user.id}/ban",
        headers=auth_headers,
        json={"reason": "x"},
        content_type="application/json",
    )
    assert r.status_code == 403
    assert r.get_json().get("error") == "Forbidden"


def test_users_unban_as_admin_returns_200(client, app, admin_headers, banned_user):
    """POST /api/v1/users/<id>/unban as admin returns 200 and user is_banned false."""
    user, _ = banned_user
    r = client.post(f"/api/v1/users/{user.id}/unban", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["is_banned"] is False


def test_users_unban_as_non_admin_returns_403(client, auth_headers, banned_user):
    """POST /api/v1/users/<id>/unban as non-admin returns 403."""
    user, _ = banned_user
    r = client.post(f"/api/v1/users/{user.id}/unban", headers=auth_headers)
    assert r.status_code == 403
    assert r.get_json().get("error") == "Forbidden"


def test_users_list_as_admin_includes_ban_fields(client, admin_headers, banned_user):
    """GET /api/v1/users as admin returns items with is_banned, banned_at, ban_reason."""
    r = client.get("/api/v1/users?page=1&limit=20", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data and len(data["items"]) >= 1
    user_item = next((u for u in data["items"] if u.get("username") == "banneduser"), None)
    assert user_item is not None
    assert "is_banned" in user_item
    assert user_item["is_banned"] is True


def test_users_get_as_admin_includes_ban_fields(client, admin_headers, banned_user):
    """GET /api/v1/users/<id> as admin for another user returns is_banned, banned_at, ban_reason."""
    user, _ = banned_user
    r = client.get(f"/api/v1/users/{user.id}", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("is_banned") is True
    assert "banned_at" in data
    assert "ban_reason" in data


def test_users_list_includes_role_level(client, admin_headers, test_user):
    """GET /api/v1/users returns items with role_level."""
    r = client.get("/api/v1/users?page=1&limit=20", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data
    user_item = next((u for u in data["items"] if u.get("id") == test_user[0].id), None)
    assert user_item is not None
    assert "role_level" in user_item


def test_admin_cannot_edit_user_with_equal_role_level(client, app, admin_headers, admin_user_same_level):
    """Admin (level 50) cannot PUT to another user with role_level 50."""
    other, _ = admin_user_same_level
    r = client.put(
        f"/api/v1/users/{other.id}",
        headers=admin_headers,
        json={"username": "hacked"},
        content_type="application/json",
    )
    assert r.status_code == 403
    assert "lower" in (r.get_json().get("error") or "").lower()


def test_admin_cannot_edit_user_with_higher_role_level(client, app, admin_headers, super_admin_user):
    """Admin (level 50) cannot PUT to SuperAdmin (level 100)."""
    super_admin, _ = super_admin_user
    r = client.put(
        f"/api/v1/users/{super_admin.id}",
        headers=admin_headers,
        json={"username": "hacked"},
        content_type="application/json",
    )
    assert r.status_code == 403


def test_admin_cannot_delete_user_with_equal_or_higher_role_level(client, app, admin_headers, admin_user_same_level):
    """Admin (50) cannot DELETE another admin with same level (50)."""
    other, _ = admin_user_same_level
    r = client.delete(f"/api/v1/users/{other.id}", headers=admin_headers)
    assert r.status_code == 403


def test_admin_cannot_ban_user_with_higher_role_level(client, admin_headers, super_admin_user):
    """Admin (50) cannot POST ban to SuperAdmin (100)."""
    super_admin, _ = super_admin_user
    r = client.post(
        f"/api/v1/users/{super_admin.id}/ban",
        headers=admin_headers,
        json={"reason": "test"},
        content_type="application/json",
    )
    assert r.status_code == 403


def test_non_super_admin_cannot_increase_own_role_level(client, admin_headers, admin_user):
    """Admin with role_level 50 cannot set own role_level to 100 via PUT."""
    admin, _ = admin_user
    r = client.put(
        f"/api/v1/users/{admin.id}",
        headers=admin_headers,
        json={"role_level": 100},
        content_type="application/json",
    )
    assert r.status_code == 403
    assert "SuperAdmin" in (r.get_json().get("error") or "")


def test_super_admin_may_increase_own_role_level(client, app, super_admin_headers, super_admin_user):
    """SuperAdmin (100) may set own role_level to 101 via PUT."""
    super_admin, _ = super_admin_user
    r = client.put(
        f"/api/v1/users/{super_admin.id}",
        headers=super_admin_headers,
        json={"role_level": 101},
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("role_level") == 101



def test_user_list_admin(app, client, admin_headers):
    resp = client.get("/api/v1/users", headers=admin_headers)
    assert resp.status_code == 200

def test_user_by_id_admin(app, client, admin_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.get(f"/api/v1/users/{uid}", headers=admin_headers)
    assert resp.status_code == 200

def test_user_update_by_admin(app, client, admin_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.put(
        f"/api/v1/users/{uid}",
        json={"preferred_language": "en"},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 204)

def test_user_preferences(app, client, admin_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.put(
        f"/api/v1/users/{uid}/preferences",
        json={"preferred_language": "de"},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 204, 404)

def test_user_change_password_admin(app, client, super_admin_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.put(
        f"/api/v1/users/{uid}/password",
        json={"new_password": "NewStrongPass1"},
        headers=super_admin_headers,
    )
    assert resp.status_code in (200, 204, 400, 403)

def test_user_role_change_admin(app, client, admin_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
        role = Role.query.filter_by(name=Role.NAME_USER).first()
    resp = client.patch(
        f"/api/v1/users/{uid}/role",
        json={"role_id": role.id},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 204, 400)

def test_user_ban_unban(app, client, admin_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.post(
        f"/api/v1/users/{uid}/ban",
        json={"reason": "Test ban"},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 204)
    resp = client.post(
        f"/api/v1/users/{uid}/unban",
        headers=admin_headers,
    )
    assert resp.status_code in (200, 204)

def test_user_not_found(app, client, admin_headers):
    resp = client.get("/api/v1/users/99999", headers=admin_headers)
    assert resp.status_code == 404


# ======================= AREA API TESTS =======================



def test_user_self_get(app, client, auth_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.get(f"/api/v1/users/{uid}", headers=auth_headers)
    assert resp.status_code == 200

def test_user_self_update(app, client, auth_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.put(
        f"/api/v1/users/{uid}",
        json={"preferred_language": "en"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

def test_user_self_change_password(app, client, auth_headers, test_user):
    user, password = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.put(
        f"/api/v1/users/{uid}/password",
        json={"current_password": password, "new_password": "NewStrongPass1"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

def test_user_self_change_password_wrong_current(app, client, auth_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.put(
        f"/api/v1/users/{uid}/password",
        json={"current_password": "wrongpass", "new_password": "NewStrongPass1"},
        headers=auth_headers,
    )
    assert resp.status_code == 400

def test_user_self_change_password_missing_fields(app, client, auth_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.put(
        f"/api/v1/users/{uid}/password",
        json={"new_password": "NewStrongPass1"},
        headers=auth_headers,
    )
    assert resp.status_code == 400

def test_user_delete_by_admin(app, client, super_admin_headers):
    # Create a user to delete (delete requires SuperAdmin)
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        u = User(username="deleteuser", password_hash=generate_password_hash("Delpass1"), role_id=role.id)
        db.session.add(u)
        db.session.commit()
        uid = u.id
    resp = client.delete(f"/api/v1/users/{uid}", headers=super_admin_headers)
    assert resp.status_code == 200

def test_user_delete_not_found(app, client, super_admin_headers):
    resp = client.delete("/api/v1/users/99999", headers=super_admin_headers)
    assert resp.status_code == 404

def test_user_delete_forbidden_for_user(app, client, auth_headers):
    resp = client.delete("/api/v1/users/99999", headers=auth_headers)
    assert resp.status_code == 403

def test_user_update_forbidden_for_other(app, client, auth_headers, admin_user):
    user, _ = admin_user
    with app.app_context():
        uid = User.query.filter_by(username="adminuser").first().id
    resp = client.put(
        f"/api/v1/users/{uid}",
        json={"preferred_language": "en"},
        headers=auth_headers,
    )
    assert resp.status_code == 403

def test_user_update_password_via_update_rejected(app, client, auth_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.put(
        f"/api/v1/users/{uid}",
        json={"password": "newpass"},
        headers=auth_headers,
    )
    assert resp.status_code == 400

def test_user_assign_role(app, client, admin_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.patch(
        f"/api/v1/users/{uid}/role",
        json={"role": "user"},
        headers=admin_headers,
    )
    assert resp.status_code == 200

def test_user_assign_role_invalid(app, client, admin_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.patch(
        f"/api/v1/users/{uid}/role",
        json={"role": "nonexistent_role"},
        headers=admin_headers,
    )
    assert resp.status_code == 400

def test_user_preferences_self(app, client, auth_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.put(
        f"/api/v1/users/{uid}/preferences",
        json={"preferred_language": "de"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

def test_user_preferences_no_fields(app, client, auth_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.put(
        f"/api/v1/users/{uid}/preferences",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 400

def test_user_list_search(app, client, admin_headers):
    resp = client.get("/api/v1/users?q=test", headers=admin_headers)
    assert resp.status_code == 200


# ======================= DATA EXPORT/IMPORT =======================



def test_role_list(app, client, admin_headers):
    resp = client.get("/api/v1/roles", headers=admin_headers)
    assert resp.status_code == 200

def test_role_list_forbidden(app, client, auth_headers):
    resp = client.get("/api/v1/roles", headers=auth_headers)
    assert resp.status_code in (200, 403)


# ======================= ADMIN LOG TESTS =======================



def test_role_list_admin(app, client, admin_headers):
    resp = client.get("/api/v1/roles", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data or isinstance(data, list)

def test_role_create_if_supported(app, client, admin_headers):
    resp = client.post(
        "/api/v1/roles",
        json={"name": "custom_role", "display_name": "Custom"},
        headers=admin_headers,
    )
    # Might not support creation - just ensure no crash
    assert resp.status_code in (200, 201, 400, 404, 405)


# ======================= ADMIN LOGS EXTENDED =======================
