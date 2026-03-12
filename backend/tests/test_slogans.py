"""Tests for slogan CRUD API and site slogan resolution."""
import pytest


def test_site_slogan_public_no_auth(client):
    """GET /api/v1/site/slogan?placement=landing.teaser.primary is public (no 401)."""
    r = client.get("/api/v1/site/slogan?placement=landing.teaser.primary&lang=de")
    assert r.status_code == 200
    data = r.get_json()
    assert "text" in data
    assert data["placement_key"] == "landing.teaser.primary"
    assert data["language_code"] == "de"


def test_site_slogan_requires_placement(client):
    """GET /api/v1/site/slogan without placement returns 400."""
    r = client.get("/api/v1/site/slogan?lang=de")
    assert r.status_code == 400


def test_site_slogans_public_no_auth(client):
    """GET /api/v1/site/slogans is public (no 401)."""
    r = client.get("/api/v1/site/slogans?placement=landing.teaser.primary&lang=de")
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_site_slogans_requires_placement(client):
    """GET /api/v1/site/slogans without placement returns 400."""
    r = client.get("/api/v1/site/slogans?lang=de")
    assert r.status_code == 400


def test_site_slogans_returns_items_structure(client):
    """GET /api/v1/site/slogans returns items array; each item has text, placement_key, language_code."""
    r = client.get("/api/v1/site/slogans?placement=landing.teaser.primary&lang=de")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data["items"], list)
    for item in data["items"]:
        assert "text" in item
        assert "placement_key" in item
        assert "language_code" in item


def test_site_slogans_create_then_list(client, moderator_headers):
    """Create slogan then GET site/slogans returns it in items."""
    payload = {
        "text": "Slogan for list test",
        "category": "landing_teaser",
        "placement_key": "landing.teaser.primary",
        "language_code": "de",
        "is_active": True,
    }
    r = client.post("/api/v1/slogans", headers=moderator_headers, json=payload)
    assert r.status_code == 201
    slogan_id = r.get_json()["id"]

    r2 = client.get("/api/v1/site/slogans?placement=landing.teaser.primary&lang=de")
    assert r2.status_code == 200
    data2 = r2.get_json()
    assert any(it.get("text") == payload["text"] for it in data2["items"])

    client.delete("/api/v1/slogans/" + str(slogan_id), headers=moderator_headers)


def test_site_slogans_deactivate_then_list_excludes(client, moderator_headers):
    """After deactivating a slogan, site/slogans no longer includes it."""
    payload = {
        "text": "Only for deactivate list test",
        "category": "landing_teaser",
        "placement_key": "landing.ad.secondary",
        "language_code": "de",
        "is_active": True,
    }
    r = client.post("/api/v1/slogans", headers=moderator_headers, json=payload)
    assert r.status_code == 201
    sid = r.get_json()["id"]

    r2 = client.get("/api/v1/site/slogans?placement=landing.ad.secondary&lang=de")
    assert r2.status_code == 200
    assert any(it.get("text") == payload["text"] for it in r2.get_json()["items"])

    r3 = client.post("/api/v1/slogans/" + str(sid) + "/deactivate", headers=moderator_headers)
    assert r3.status_code == 200

    r4 = client.get("/api/v1/site/slogans?placement=landing.ad.secondary&lang=de")
    assert r4.status_code == 200
    assert not any(it.get("text") == payload["text"] for it in r4.get_json()["items"])

    client.delete("/api/v1/slogans/" + str(sid), headers=moderator_headers)


def test_site_slogans_multiple_returns_all(client, moderator_headers):
    """Create two slogans for same placement; site/slogans returns both."""
    payload1 = {
        "text": "First slogan",
        "category": "landing_teaser",
        "placement_key": "landing.teaser.primary",
        "language_code": "de",
        "is_active": True,
        "priority": 1,
    }
    payload2 = {
        "text": "Second slogan",
        "category": "landing_teaser",
        "placement_key": "landing.teaser.primary",
        "language_code": "de",
        "is_active": True,
        "priority": 0,
    }
    r1 = client.post("/api/v1/slogans", headers=moderator_headers, json=payload1)
    r2 = client.post("/api/v1/slogans", headers=moderator_headers, json=payload2)
    assert r1.status_code == 201 and r2.status_code == 201
    id1, id2 = r1.get_json()["id"], r2.get_json()["id"]

    r = client.get("/api/v1/site/slogans?placement=landing.teaser.primary&lang=de")
    assert r.status_code == 200
    items = r.get_json()["items"]
    texts = [it["text"] for it in items]
    assert "First slogan" in texts and "Second slogan" in texts

    client.delete("/api/v1/slogans/" + str(id1), headers=moderator_headers)
    client.delete("/api/v1/slogans/" + str(id2), headers=moderator_headers)


def test_site_settings_public_no_auth(client):
    """GET /api/v1/site/settings is public (no 401)."""
    r = client.get("/api/v1/site/settings")
    assert r.status_code == 200


def test_site_settings_returns_rotation_fields(client):
    """GET /api/v1/site/settings returns slogan_rotation_interval_seconds and slogan_rotation_enabled."""
    r = client.get("/api/v1/site/settings")
    assert r.status_code == 200
    data = r.get_json()
    assert "slogan_rotation_interval_seconds" in data
    assert "slogan_rotation_enabled" in data
    assert isinstance(data["slogan_rotation_interval_seconds"], int)
    assert data["slogan_rotation_interval_seconds"] >= 0
    assert isinstance(data["slogan_rotation_enabled"], bool)


def test_slogans_list_requires_auth(client):
    """GET /api/v1/slogans without token returns 401."""
    r = client.get("/api/v1/slogans")
    assert r.status_code == 401


def test_slogans_list_moderator_returns_200(client, moderator_headers):
    """GET /api/v1/slogans as moderator returns 200 and items array."""
    r = client.get("/api/v1/slogans", headers=moderator_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_slogans_create_and_resolve(client, moderator_headers):
    """Create a slogan via API then resolve it via site/slogan."""
    payload = {
        "text": "Test slogan for placement.",
        "category": "landing_teaser",
        "placement_key": "landing.teaser.primary",
        "language_code": "de",
        "is_active": True,
    }
    r = client.post("/api/v1/slogans", headers=moderator_headers, json=payload)
    assert r.status_code == 201
    data = r.get_json()
    assert data["text"] == payload["text"]
    assert data["placement_key"] == payload["placement_key"]
    slogan_id = data["id"]

    r2 = client.get("/api/v1/site/slogan?placement=landing.teaser.primary&lang=de")
    assert r2.status_code == 200
    data2 = r2.get_json()
    assert data2.get("text") == payload["text"]

    r3 = client.delete("/api/v1/slogans/" + str(slogan_id), headers=moderator_headers)
    assert r3.status_code == 200


def test_slogans_create_invalid_category_rejected(client, moderator_headers):
    """POST /api/v1/slogans with invalid category returns 400."""
    r = client.post(
        "/api/v1/slogans",
        headers=moderator_headers,
        json={
            "text": "x",
            "category": "invalid_category",
            "placement_key": "landing.teaser.primary",
            "language_code": "de",
        },
    )
    assert r.status_code == 400


def test_slogan_deactivate_then_resolve_returns_null(client, moderator_headers):
    """After deactivating a slogan, site/slogan returns text null or different."""
    payload = {
        "text": "Only active slogan here",
        "category": "landing_teaser",
        "placement_key": "landing.ad.primary",
        "language_code": "de",
        "is_active": True,
    }
    r = client.post("/api/v1/slogans", headers=moderator_headers, json=payload)
    assert r.status_code == 201
    sid = r.get_json()["id"]
    r2 = client.get("/api/v1/site/slogan?placement=landing.ad.primary&lang=de")
    assert r2.status_code == 200
    assert r2.get_json().get("text") == payload["text"]
    r3 = client.post("/api/v1/slogans/" + str(sid) + "/deactivate", headers=moderator_headers)
    assert r3.status_code == 200
    r4 = client.get("/api/v1/site/slogan?placement=landing.ad.primary&lang=de")
    assert r4.status_code == 200
    assert r4.get_json().get("text") is None
    client.delete("/api/v1/slogans/" + str(sid), headers=moderator_headers)
