"""Tests for /manage/world-engine-control-center page and nav wiring."""

from __future__ import annotations

from conftest import captured_templates


def test_manage_world_engine_control_center_returns_200(client):
    response = client.get("/manage/world-engine-control-center")
    assert response.status_code == 200


def test_manage_world_engine_control_center_renders_template(app, client):
    with captured_templates(app) as templates:
        response = client.get("/manage/world-engine-control-center")
    assert response.status_code == 200
    assert templates[-1][0] == "manage/world_engine_control_center.html"


def test_manage_world_engine_control_center_contains_mount_points(client):
    response = client.get("/manage/world-engine-control-center")
    html = response.get_data(as_text=True)
    assert "wecc-desired" in html
    assert "wecc-observed" in html
    assert "wecc-connectivity" in html
    assert "wecc-summary" in html
    assert "wecc-headline" in html
    assert "wecc-operator-controls" in html
    assert "manage_world_engine_control_center.js" in html


def test_manage_base_includes_world_engine_control_center_nav(client):
    response = client.get("/manage")
    html = response.get_data(as_text=True)
    assert "manage-nav-world-engine-control-center" in html
    assert "/manage/world-engine-control-center" in html
