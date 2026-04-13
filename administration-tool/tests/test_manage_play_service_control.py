"""Tests for /manage/play-service-control page and navigation wiring."""

from __future__ import annotations

from conftest import captured_templates


def test_manage_play_service_control_returns_200(client):
    response = client.get("/manage/play-service-control")
    assert response.status_code == 200


def test_manage_play_service_control_renders_template(app, client):
    with captured_templates(app) as templates:
        response = client.get("/manage/play-service-control")
    assert response.status_code == 200
    assert templates[-1][0] == "manage/play_service_control.html"


def test_manage_play_service_control_html_contains_controls(client):
    response = client.get("/manage/play-service-control")
    html = response.get_data(as_text=True)
    assert "manage-psc-form" in html
    assert "manage-psc-save" in html
    assert "manage-psc-test" in html
    assert "manage-psc-apply" in html
    assert "manage-psc-refresh" in html


def test_manage_base_includes_play_service_nav(client):
    response = client.get("/manage")
    html = response.get_data(as_text=True)
    assert "manage-nav-world-engine-console" in html
    assert "/manage/world-engine-console" in html
    assert "manage-nav-play-service-control" in html
    assert "/manage/play-service-control" in html


def test_manage_dashboard_includes_play_service_card(client):
    response = client.get("/manage")
    html = response.get_data(as_text=True)
    assert "manage-dashboard-world-engine-console" in html
    assert "data-feature-any=" in html
    assert "manage.world_engine_observe" in html
    assert "manage-dashboard-play-service-control" in html
    assert 'data-feature="manage.play_service_control"' in html
    assert "manage-dashboard-ai-runtime-governance" in html
    assert "manage-dashboard-world-engine-control-center" in html
    assert 'data-feature="manage.ai_runtime_governance"' in html


def test_manage_diagnosis_links_to_play_service_control(client):
    response = client.get("/manage/diagnosis")
    html = response.get_data(as_text=True)
    assert "/manage/world-engine-console" in html
    assert "/manage/play-service-control" in html


def test_manage_play_service_control_links_to_world_engine_console(client):
    response = client.get("/manage/play-service-control")
    html = response.get_data(as_text=True)
    assert "/manage/world-engine-console" in html
