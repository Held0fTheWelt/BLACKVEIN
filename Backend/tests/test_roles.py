"""Tests for Role CRUD API. Admin-only endpoints."""
import pytest

from app.models import Role


def test_roles_list_as_admin(client, admin_headers):
    """List roles returns 200 with items, total, page, per_page."""
    r = client.get("/api/v1/roles?page=1&limit=10", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["per_page"] == 10
    assert isinstance(data["items"], list)
    for item in data["items"]:
        assert "id" in item
        assert "name" in item


def test_roles_list_as_non_admin_returns_403(client, auth_headers):
    """Non-admin gets 403 on list roles."""
    r = client.get("/api/v1/roles", headers=auth_headers)
    assert r.status_code == 403
    assert r.get_json().get("error") == "Forbidden"


def test_roles_list_unauthenticated_returns_401(client):
    """Unauthenticated request returns 401."""
    r = client.get("/api/v1/roles")
    assert r.status_code == 401


def test_roles_get_as_admin(client, app, admin_headers):
    """Get role by id returns 200 with id and name."""
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        assert role is not None
        rid = role.id
    r = client.get(f"/api/v1/roles/{rid}", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["id"] == rid
    assert data["name"] == Role.NAME_USER


def test_roles_get_404(client, admin_headers):
    """Get non-existent role returns 404."""
    r = client.get("/api/v1/roles/99999", headers=admin_headers)
    assert r.status_code == 404
    assert r.get_json().get("error") == "Role not found"


def test_roles_get_as_non_admin_returns_403(client, app, auth_headers):
    """Non-admin gets 403 on get role."""
    with client.application.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        rid = role.id if role else 1
    r = client.get(f"/api/v1/roles/{rid}", headers=auth_headers)
    assert r.status_code == 403


def test_roles_create_as_admin(client, app, admin_headers):
    """Create role returns 201 with id and name."""
    r = client.post(
        "/api/v1/roles",
        json={"name": "custom_role"},
        headers=admin_headers,
        content_type="application/json",
    )
    assert r.status_code == 201
    data = r.get_json()
    assert "id" in data
    assert data["name"] == "custom_role"
    with app.app_context():
        role = Role.query.filter_by(name="custom_role").first()
        assert role is not None


def test_roles_create_duplicate_returns_409(client, app, admin_headers):
    """Create role with existing name returns 409."""
    with app.app_context():
        Role.query.filter_by(name="user").first() or None  # ensure user exists
    r = client.post(
        "/api/v1/roles",
        json={"name": "user"},
        headers=admin_headers,
        content_type="application/json",
    )
    assert r.status_code == 409
    assert r.get_json().get("error") == "Role name already exists"


def test_roles_create_invalid_name_returns_400(client, admin_headers):
    """Create with invalid name returns 400. (Names are normalized to lowercase, so UPPER is valid.)"""
    for body in [
        {"name": ""},
        {"name": "a" * 21},
        {"name": "has-dash"},
        {},
    ]:
        r = client.post(
            "/api/v1/roles",
            json=body,
            headers=admin_headers,
            content_type="application/json",
        )
        assert r.status_code == 400, f"Expected 400 for body {body}"


def test_roles_create_as_non_admin_returns_403(client, auth_headers):
    """Non-admin gets 403 on create role."""
    r = client.post(
        "/api/v1/roles",
        json={"name": "custom"},
        headers=auth_headers,
        content_type="application/json",
    )
    assert r.status_code == 403


def test_roles_update_as_admin(client, app, admin_headers):
    """Update role name returns 200."""
    with app.app_context():
        from app.extensions import db
        role = Role.query.filter_by(name="role_to_update").first()
        if not role:
            role = Role(name="role_to_update")
            db.session.add(role)
            db.session.commit()
            db.session.refresh(role)
        rid = role.id
    r = client.put(
        f"/api/v1/roles/{rid}",
        json={"name": "role_updated"},
        headers=admin_headers,
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["name"] == "role_updated"


def test_roles_update_as_non_admin_returns_403(client, app, auth_headers):
    """Non-admin gets 403 on update role."""
    with client.application.app_context():
        role = Role.query.first()
        rid = role.id if role else 1
    r = client.put(
        f"/api/v1/roles/{rid}",
        json={"name": "updated"},
        headers=auth_headers,
        content_type="application/json",
    )
    assert r.status_code == 403


def test_roles_delete_as_admin(client, app, admin_headers):
    """Delete role with no users returns 200."""
    with app.app_context():
        from app.extensions import db
        role = Role.query.filter_by(name="deletable_role").first()
        if not role:
            role = Role(name="deletable_role")
            db.session.add(role)
            db.session.commit()
            db.session.refresh(role)
        rid = role.id
    r = client.delete(f"/api/v1/roles/{rid}", headers=admin_headers)
    assert r.status_code == 200
    assert r.get_json().get("message")


def test_roles_delete_when_users_have_role_returns_400(client, app, admin_headers, test_user):
    """Delete role that is assigned to users returns 400."""
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        rid = role.id
    r = client.delete(f"/api/v1/roles/{rid}", headers=admin_headers)
    assert r.status_code == 400
    err = r.get_json().get("error", "")
    assert "user" in err.lower() or "role" in err.lower()


def test_roles_delete_404(client, admin_headers):
    """Delete non-existent role returns 404."""
    r = client.delete("/api/v1/roles/99999", headers=admin_headers)
    assert r.status_code == 404


def test_roles_delete_as_non_admin_returns_403(client, app, auth_headers):
    """Non-admin gets 403 on delete role."""
    with client.application.app_context():
        role = Role.query.first()
        rid = role.id if role else 1
    r = client.delete(f"/api/v1/roles/{rid}", headers=auth_headers)
    assert r.status_code == 403
