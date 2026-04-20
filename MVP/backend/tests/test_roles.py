"""Tests for Role CRUD API. Admin-only endpoints."""

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


def test_roles_list_page_below_min_defaults_to_one(client, admin_headers):
    """page < min_val falls back to default (1)."""
    r = client.get("/api/v1/roles?page=0&limit=10", headers=admin_headers)
    assert r.status_code == 200
    assert r.get_json()["page"] == 1


def test_roles_list_limit_above_max_capped_to_100(client, admin_headers):
    """limit > max_val is capped at 100."""
    r = client.get("/api/v1/roles?page=1&limit=200", headers=admin_headers)
    assert r.status_code == 200
    assert r.get_json()["per_page"] == 100


def test_roles_list_invalid_page_and_limit_strings_use_defaults(client, admin_headers):
    """Non-numeric page/limit query values use defaults (1 and 50)."""
    r = client.get("/api/v1/roles?page=abc&limit=xyz", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["page"] == 1
    assert data["per_page"] == 50


def test_roles_list_page_zero_and_high_limit_in_one_request(client, admin_headers):
    """Combined invalid page and over-max limit in one GET."""
    r = client.get("/api/v1/roles?page=0&limit=999", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["page"] == 1
    assert data["per_page"] == 100


def test_roles_list_without_page_limit_query_uses_defaults(client, admin_headers):
    """Omitted page/limit runs _parse_int(None, default)."""
    r = client.get("/api/v1/roles", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["page"] == 1
    assert data["per_page"] == 50


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


def test_roles_create_invalid_json_returns_400(client, admin_headers):
    """POST with invalid JSON body returns 400."""
    r = client.post(
        "/api/v1/roles",
        data="not json",
        content_type="application/json",
        headers=admin_headers,
    )
    assert r.status_code == 400
    assert "Invalid or missing JSON" in r.get_json().get("error", "")


def test_roles_create_empty_description_normalized_to_null(client, app, admin_headers):
    """description key with empty or whitespace becomes None (omitted in JSON)."""
    for idx, desc in enumerate(["", "   "]):
        name = f"role_empty_desc_{idx}"
        r = client.post(
            "/api/v1/roles",
            json={"name": name, "description": desc},
            headers=admin_headers,
            content_type="application/json",
        )
        assert r.status_code == 201, f"body description={desc!r}"
        data = r.get_json()
        assert "description" not in data
        with app.app_context():
            role = Role.query.filter_by(name=name).first()
            assert role is not None
            assert role.description is None


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


def test_roles_update_invalid_json_returns_400(client, app, admin_headers):
    """PUT with invalid JSON returns 400."""
    with app.app_context():
        from app.extensions import db
        role = Role.query.filter_by(name="role_put_json").first()
        if not role:
            role = Role(name="role_put_json")
            db.session.add(role)
            db.session.commit()
            db.session.refresh(role)
        rid = role.id
    r = client.put(
        f"/api/v1/roles/{rid}",
        data="not json",
        content_type="application/json",
        headers=admin_headers,
    )
    assert r.status_code == 400
    assert "Invalid or missing JSON" in r.get_json().get("error", "")


def test_roles_update_description_only(client, app, admin_headers):
    """PUT with only description does not require name; empty description clears."""
    with app.app_context():
        from app.extensions import db
        role = Role.query.filter_by(name="role_desc_only").first()
        if not role:
            role = Role(name="role_desc_only", description="old")
            db.session.add(role)
            db.session.commit()
            db.session.refresh(role)
        rid = role.id
    r = client.put(
        f"/api/v1/roles/{rid}",
        json={"description": "only_desc"},
        headers=admin_headers,
        content_type="application/json",
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("description") == "only_desc"
    assert body.get("name") == "role_desc_only"

    r2 = client.put(
        f"/api/v1/roles/{rid}",
        json={"description": ""},
        headers=admin_headers,
        content_type="application/json",
    )
    assert r2.status_code == 200
    assert "description" not in r2.get_json()

    r3 = client.put(
        f"/api/v1/roles/{rid}",
        json={"description": None},
        headers=admin_headers,
        content_type="application/json",
    )
    assert r3.status_code == 200
    assert "description" not in r3.get_json()


def test_roles_update_404(client, admin_headers):
    """PUT non-existent role returns 404."""
    r = client.put(
        "/api/v1/roles/99999",
        json={"name": "any_valid_name"},
        headers=admin_headers,
        content_type="application/json",
    )
    assert r.status_code == 404
    assert r.get_json().get("error") == "Role not found"


def test_roles_update_duplicate_name_returns_409(client, app, admin_headers):
    """PUT renaming to another role's name returns 409."""
    with app.app_context():
        from app.extensions import db
        a = Role.query.filter_by(name="role_dup_a").first()
        if not a:
            a = Role(name="role_dup_a")
            db.session.add(a)
        b = Role.query.filter_by(name="role_dup_b").first()
        if not b:
            b = Role(name="role_dup_b")
            db.session.add(b)
        db.session.commit()
        db.session.refresh(a)
        db.session.refresh(b)
        rid_a = a.id
        name_b = b.name
    r = client.put(
        f"/api/v1/roles/{rid_a}",
        json={"name": name_b},
        headers=admin_headers,
        content_type="application/json",
    )
    assert r.status_code == 409
    assert r.get_json().get("error") == "Role name already exists"


def test_roles_update_invalid_name_returns_400(client, app, admin_headers):
    """PUT with invalid name format returns 400 (non-404/409 branch)."""
    with app.app_context():
        from app.extensions import db
        role = Role.query.filter_by(name="role_bad_name_tgt").first()
        if not role:
            role = Role(name="role_bad_name_tgt")
            db.session.add(role)
            db.session.commit()
            db.session.refresh(role)
        rid = role.id
    r = client.put(
        f"/api/v1/roles/{rid}",
        json={"name": "bad-dash"},
        headers=admin_headers,
        content_type="application/json",
    )
    assert r.status_code == 400
    assert r.get_json().get("error")


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
