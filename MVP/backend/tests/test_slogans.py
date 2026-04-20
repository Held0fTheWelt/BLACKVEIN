"""Tests for slogan CRUD API and site slogan resolution."""
from unittest.mock import patch

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


def test_slogans_list_plain_user_forbidden(client, auth_headers):
    """GET /api/v1/slogans as normal user returns 403."""
    r = client.get("/api/v1/slogans", headers=auth_headers)
    assert r.status_code == 403
    assert "Forbidden" in (r.get_json() or {}).get("error", "")


@patch("app.api.v1.slogan_routes.get_current_user", return_value=None)
def test_slogans_routes_user_not_found_returns_404(mock_gc, client, moderator_headers):
    """When get_current_user is None, slogan routes return 404."""
    r = client.get("/api/v1/slogans", headers=moderator_headers)
    assert r.status_code == 404


def test_slogans_create_missing_json_body(client, moderator_headers):
    """POST /api/v1/slogans without JSON returns 400."""
    r = client.post(
        "/api/v1/slogans",
        headers={**moderator_headers, "Content-Type": "application/json"},
        data="",
    )
    assert r.status_code == 400


def test_slogans_update_missing_json_body(client, moderator_headers):
    """PUT /api/v1/slogans/<id> without JSON returns 400."""
    r = client.post(
        "/api/v1/slogans",
        headers=moderator_headers,
        json={
            "text": "json body put test",
            "category": "landing_teaser",
            "placement_key": "landing.teaser.primary",
            "language_code": "de",
        },
    )
    assert r.status_code == 201
    sid = r.get_json()["id"]
    r2 = client.put(
        f"/api/v1/slogans/{sid}",
        headers={**moderator_headers, "Content-Type": "application/json"},
        data="",
    )
    assert r2.status_code == 400
    client.delete(f"/api/v1/slogans/{sid}", headers=moderator_headers)


def test_slogans_activate_not_found(client, moderator_headers):
    """POST activate on missing id returns 404."""
    r = client.post("/api/v1/slogans/999999/activate", headers=moderator_headers)
    assert r.status_code == 404


def test_slogans_deactivate_not_found(client, moderator_headers):
    """POST deactivate on missing id returns 404."""
    r = client.post("/api/v1/slogans/999999/deactivate", headers=moderator_headers)
    assert r.status_code == 404


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



"""Tests for TestSloganAPI."""

class TestSloganAPI:

    def test_slogan_resolve(self, app, client):
        resp = client.get("/api/v1/site/slogan?placement=hero")
        assert resp.status_code == 200

    def test_slogan_resolve_missing_placement(self, app, client):
        resp = client.get("/api/v1/site/slogan")
        assert resp.status_code == 400

    def test_slogans_list_public(self, app, client):
        resp = client.get("/api/v1/site/slogans?placement=hero")
        assert resp.status_code == 200

    def test_slogan_list_admin(self, app, client, admin_headers):
        resp = client.get("/api/v1/slogans", headers=admin_headers)
        assert resp.status_code == 200

    def _create_slogan(self, client, headers):
        return client.post(
            "/api/v1/slogans",
            json={
                "text": "Test Slogan",
                "category": "landing_hero",
                "placement_key": "landing.hero.primary",
                "language_code": "de",
            },
            headers=headers,
        )

    def test_slogan_create(self, app, client, moderator_headers):
        resp = self._create_slogan(client, moderator_headers)
        assert resp.status_code in (200, 201)

    def test_slogan_update(self, app, client, moderator_headers):
        resp = self._create_slogan(client, moderator_headers)
        if resp.status_code in (200, 201):
            slogan_id = resp.get_json().get("id")
            if slogan_id:
                resp = client.put(
                    f"/api/v1/slogans/{slogan_id}",
                    json={"text": "Updated Slogan"},
                    headers=moderator_headers,
                )
                assert resp.status_code == 200

    def test_slogan_delete(self, app, client, moderator_headers):
        resp = self._create_slogan(client, moderator_headers)
        if resp.status_code in (200, 201):
            slogan_id = resp.get_json().get("id")
            if slogan_id:
                resp = client.delete(f"/api/v1/slogans/{slogan_id}", headers=moderator_headers)
                assert resp.status_code == 200

    def test_slogan_activate_deactivate(self, app, client, moderator_headers):
        resp = self._create_slogan(client, moderator_headers)
        if resp.status_code in (200, 201):
            slogan_id = resp.get_json().get("id")
            if slogan_id:
                resp = client.post(f"/api/v1/slogans/{slogan_id}/activate", headers=moderator_headers)
                assert resp.status_code in (200, 204)
                resp = client.post(f"/api/v1/slogans/{slogan_id}/deactivate", headers=moderator_headers)
                assert resp.status_code in (200, 204)


# ======================= ROLE API TESTS =======================



"""Tests for TestSloganAPIExtended."""

class TestSloganAPIExtended:

    def test_slogan_get_by_id(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/slogans",
            json={
                "text": "Slogan Get",
                "category": "landing_hero",
                "placement_key": "landing.hero.primary",
                "language_code": "de",
            },
            headers=moderator_headers,
        )
        if resp.status_code in (200, 201):
            slogan_id = resp.get_json()["id"]
            resp = client.get(f"/api/v1/slogans/{slogan_id}", headers=moderator_headers)
            assert resp.status_code == 200

    def test_slogan_get_not_found(self, app, client, moderator_headers):
        resp = client.get("/api/v1/slogans/99999", headers=moderator_headers)
        assert resp.status_code == 404

    def test_slogan_update_not_found(self, app, client, moderator_headers):
        resp = client.put(
            "/api/v1/slogans/99999",
            json={"text": "X"},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_slogan_delete_not_found(self, app, client, moderator_headers):
        resp = client.delete("/api/v1/slogans/99999", headers=moderator_headers)
        assert resp.status_code == 404

    def test_slogan_list_with_filters(self, app, client, moderator_headers):
        resp = client.get(
            "/api/v1/slogans?category=landing_hero&placement_key=landing.hero.primary&active_only=true",
            headers=moderator_headers,
        )
        assert resp.status_code == 200

    def test_slogan_create_invalid_category(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/slogans",
            json={
                "text": "Bad Cat",
                "category": "invalid_cat",
                "placement_key": "landing.hero.primary",
                "language_code": "de",
            },
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_slogans_for_placement_list(self, app, client):
        resp = client.get("/api/v1/site/slogans?placement=landing.hero.primary&lang=de")
        assert resp.status_code == 200

    def test_slogan_resolve_with_lang(self, app, client):
        resp = client.get("/api/v1/site/slogan?placement=landing.hero.primary&lang=de")
        assert resp.status_code == 200


# ======================= ROLE API EXTENDED =======================
