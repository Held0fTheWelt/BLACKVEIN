"""Tests for areas and user/feature area assignment API. Admin only; hierarchy and area checks."""
import pytest


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
