"""Tests for /manage/world-engine-console page and wiring."""

from __future__ import annotations

from conftest import captured_templates


def test_manage_world_engine_console_returns_200(client):
    response = client.get("/manage/world-engine-console")
    assert response.status_code == 200


def test_manage_world_engine_console_renders_template(app, client):
    with captured_templates(app) as templates:
        response = client.get("/manage/world-engine-console")
    assert response.status_code == 200
    assert templates[-1][0] == "manage/world_engine_console.html"


def test_manage_world_engine_console_html_contains_mount_points(client):
    response = client.get("/manage/world-engine-console")
    html = response.get_data(as_text=True)
    assert "wec-ready" in html
    assert "wec-runs" in html
    assert "wec-sessions" in html
    assert "manage_world_engine_console.js" in html
