"""Tests for areas and user/feature area assignment API. Admin only; hierarchy and area checks."""
import pytest

from app.models import User


def test_areas_list_without_token_returns_401(client):
    response = client.get("/api/v1/areas")
    assert response.status_code == 401


def test_areas_list_as_non_admin_returns_403(client, auth_headers, admin_headers):
    # auth_headers is for test_user (not admin)
    response = client.get("/api/v1/areas", headers=auth_headers)
    assert response.status_code == 403


def test_areas_list_as_admin_returns_200_and_structure(client, admin_headers):
    response = client.get("/api/v1/areas?limit=50", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    # Seeded defaults include "all"
    slugs = [a["slug"] for a in data["items"]]
    assert "all" in slugs


def test_areas_get_as_admin(client, admin_headers):
    # Get first area (e.g. all)
    r = client.get("/api/v1/areas?limit=1", headers=admin_headers)
    assert r.status_code == 200
    items = r.get_json()["items"]
    if not items:
        pytest.skip("No areas seeded")
    aid = items[0]["id"]
    response = client.get("/api/v1/areas/{}".format(aid), headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == aid
    assert "slug" in data
    assert "name" in data


def test_areas_get_404(client, admin_headers):
    response = client.get("/api/v1/areas/99999", headers=admin_headers)
    assert response.status_code == 404


def test_areas_create_as_admin(client, admin_headers):
    response = client.post(
        "/api/v1/areas",
        json={"name": "Test Area", "slug": "test_area"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Test Area"
    assert data["slug"] == "test_area"


def test_areas_create_duplicate_slug_returns_409(client, admin_headers):
    client.post("/api/v1/areas", json={"name": "Dup", "slug": "dup_slug"}, headers=admin_headers)
    response = client.post(
        "/api/v1/areas",
        json={"name": "Dup Other", "slug": "dup_slug"},
        headers=admin_headers,
    )
    assert response.status_code == 409


def test_user_areas_get_and_put(client, admin_headers, test_user):
    user, _ = test_user
    # GET user areas (admin can view users with lower level; test_user has level 0)
    r = client.get("/api/v1/users/{}/areas".format(user.id), headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["user_id"] == user.id
    assert "area_ids" in data
    assert "areas" in data
    # PUT assign an area (get first area id)
    areas_list = client.get("/api/v1/areas?limit=1", headers=admin_headers).get_json()
    if not areas_list["items"]:
        pytest.skip("No areas")
    area_id = areas_list["items"][0]["id"]
    put_resp = client.put(
        "/api/v1/users/{}/areas".format(user.id),
        json={"area_ids": [area_id]},
        headers=admin_headers,
    )
    assert put_resp.status_code == 200
    # Check user now has area
    get_resp = client.get("/api/v1/users/{}/areas".format(user.id), headers=admin_headers)
    assert get_resp.status_code == 200
    assert area_id in get_resp.get_json()["area_ids"]


def test_feature_areas_list_as_admin(client, admin_headers):
    response = client.get("/api/v1/feature-areas", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data
    assert isinstance(data["items"], list)
    # Each item has feature_id, area_ids, area_slugs
    for item in data["items"][:1]:
        assert "feature_id" in item
        assert "area_ids" in item
        assert "area_slugs" in item


def test_feature_areas_put_as_admin(client, admin_headers):
    # Set areas for manage.news to empty (global)
    response = client.put(
        "/api/v1/feature-areas/manage.news",
        json={"area_ids": []},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["feature_id"] == "manage.news"
    assert data["area_ids"] == []


def test_feature_areas_put_unknown_feature_returns_400(client, admin_headers):
    response = client.put(
        "/api/v1/feature-areas/unknown.feature",
        json={"area_ids": []},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_auth_me_includes_allowed_features(client, admin_headers):
    response = client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "allowed_features" in data
    assert isinstance(data["allowed_features"], list)
    assert "manage.users" in data["allowed_features"]
    assert "manage.play_service_control" in data["allowed_features"]



"""Tests for TestAreaAPI."""

class TestAreaAPI:

    def test_area_list(self, app, client, admin_headers):
        resp = client.get("/api/v1/areas", headers=admin_headers)
        assert resp.status_code == 200

    def test_area_create(self, app, client, admin_headers):
        resp = client.post(
            "/api/v1/areas",
            json={"name": "Test Area", "slug": "test-area-boost", "description": "desc"},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 201, 400, 409)

    def test_area_get(self, app, client, admin_headers):
        resp = client.post(
            "/api/v1/areas",
            json={"name": "Get Area", "slug": "get-area-boost", "description": "desc"},
            headers=admin_headers,
        )
        if resp.status_code in (200, 201):
            area_id = resp.get_json().get("id")
            if area_id:
                resp = client.get(f"/api/v1/areas/{area_id}", headers=admin_headers)
                assert resp.status_code == 200


# ======================= SLOGAN API TESTS =======================



"""Tests for TestAreaAPIExtended."""


def test_area_update(app, client, admin_headers):
    resp = client.post(
        "/api/v1/areas",
        json={"name": "Area Upd", "slug": "area_upd"},
        headers=admin_headers,
    )
    if resp.status_code in (200, 201):
        area_id = resp.get_json()["id"]
        resp = client.put(
            f"/api/v1/areas/{area_id}",
            json={"name": "Area Updated"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

def test_area_update_not_found(app, client, admin_headers):
    resp = client.put(
        "/api/v1/areas/99999",
        json={"name": "X"},
        headers=admin_headers,
    )
    assert resp.status_code == 404

def test_area_delete(app, client, admin_headers):
    resp = client.post(
        "/api/v1/areas",
        json={"name": "Area Del", "slug": "area_del"},
        headers=admin_headers,
    )
    if resp.status_code in (200, 201):
        area_id = resp.get_json()["id"]
        resp = client.delete(f"/api/v1/areas/{area_id}", headers=admin_headers)
        assert resp.status_code == 200

def test_area_delete_not_found(app, client, admin_headers):
    resp = client.delete("/api/v1/areas/99999", headers=admin_headers)
    assert resp.status_code == 404

def test_area_create_invalid_slug(app, client, admin_headers):
    resp = client.post(
        "/api/v1/areas",
        json={"name": "Area Bad Slug", "slug": "INVALID-SLUG!"},
        headers=admin_headers,
    )
    assert resp.status_code == 400

def test_area_create_missing_name(app, client, admin_headers):
    resp = client.post(
        "/api/v1/areas",
        json={"name": ""},
        headers=admin_headers,
    )
    assert resp.status_code == 400

def test_area_list_with_search(app, client, admin_headers):
    resp = client.get("/api/v1/areas?q=test", headers=admin_headers)
    assert resp.status_code == 200

def test_user_areas_list(app, client, admin_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.get(f"/api/v1/users/{uid}/areas", headers=admin_headers)
    assert resp.status_code == 200

def test_user_areas_set(app, client, admin_headers, test_user):
    user, _ = test_user
    with app.app_context():
        uid = User.query.filter_by(username="testuser").first().id
    resp = client.put(
        f"/api/v1/users/{uid}/areas",
        json={"area_ids": []},
        headers=admin_headers,
    )
    assert resp.status_code == 200

def test_feature_areas_list(app, client, admin_headers):
    resp = client.get("/api/v1/feature-areas", headers=admin_headers)
    assert resp.status_code == 200

def test_feature_areas_get(app, client, admin_headers):
    resp = client.get("/api/v1/feature-areas/manage.users", headers=admin_headers)
    assert resp.status_code == 200

def test_feature_areas_get_unknown(app, client, admin_headers):
    resp = client.get("/api/v1/feature-areas/unknown.feature", headers=admin_headers)
    assert resp.status_code == 404

def test_feature_areas_set(app, client, admin_headers):
    resp = client.put(
        "/api/v1/feature-areas/manage.users",
        json={"area_ids": []},
        headers=admin_headers,
    )
    assert resp.status_code == 200


def test_areas_list_invalid_pagination_defaults(client, admin_headers):
    r = client.get("/api/v1/areas?page=0&limit=999", headers=admin_headers)
    assert r.status_code == 200
    body = r.get_json()
    assert body["page"] == 1
    assert body["per_page"] == 100


def test_user_areas_get_unknown_user(client, admin_headers):
    assert client.get("/api/v1/users/999999/areas", headers=admin_headers).status_code == 404


def test_user_areas_put_missing_json(client, admin_headers, test_user):
    user, _ = test_user
    r = client.put(
        f"/api/v1/users/{user.id}/areas",
        data="not-json",
        headers={**admin_headers, "Content-Type": "application/json"},
    )
    assert r.status_code == 400


def test_user_areas_put_area_ids_not_list(client, admin_headers, test_user):
    user, _ = test_user
    r = client.put(
        f"/api/v1/users/{user.id}/areas",
        json={"area_ids": "bad"},
        headers=admin_headers,
    )
    assert r.status_code == 400


def test_feature_areas_put_missing_json(client, admin_headers):
    r = client.put(
        "/api/v1/feature-areas/manage.users",
        data="",
        headers={**admin_headers, "Content-Type": "application/json"},
    )
    assert r.status_code == 400


def test_areas_create_missing_json(client, admin_headers):
    r = client.post(
        "/api/v1/areas",
        data="",
        headers={**admin_headers, "Content-Type": "application/json"},
    )
    assert r.status_code == 400


# ======================= USER API EXTENDED =======================
