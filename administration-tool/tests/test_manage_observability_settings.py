"""Tests for /manage/observability-settings routing and UI mount points."""

from __future__ import annotations

from conftest import captured_templates


def test_manage_observability_settings_returns_200(client):
    response = client.get("/manage/observability-settings")
    assert response.status_code == 200


def test_manage_observability_settings_alt_route_returns_200(client):
    response = client.get("/manage/observability-settings/langfuse")
    assert response.status_code == 200


def test_manage_observability_settings_renders_template(app, client):
    with captured_templates(app) as templates:
        response = client.get("/manage/observability-settings")
    assert response.status_code == 200
    assert templates[-1][0] == "manage/observability_settings.html"


def test_manage_observability_settings_contains_expected_mount_points(client):
    response = client.get("/manage/observability-settings")
    html = response.get_data(as_text=True)
    assert "manage-obs-refresh" in html
    assert "manage-obs-save-config" in html
    assert "manage-obs-save-credential" in html
    assert "manage-obs-test-connection" in html
    assert "manage-obs-disable" in html
    assert "manage-obs-config-json" in html
    assert "Technical audit: full configuration JSON" in html
    assert "manage_observability_settings.js" in html
