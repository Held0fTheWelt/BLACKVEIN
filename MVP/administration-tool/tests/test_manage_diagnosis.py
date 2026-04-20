"""Tests for /manage/diagnosis page shell and navigation wiring."""

from __future__ import annotations

from conftest import captured_templates


def test_manage_diagnosis_returns_200(client):
    response = client.get("/manage/diagnosis")
    assert response.status_code == 200


def test_manage_diagnosis_renders_template(app, client):
    with captured_templates(app) as templates:
        response = client.get("/manage/diagnosis")
    assert response.status_code == 200
    assert templates[-1][0] == "manage/diagnosis.html"


def test_manage_diagnosis_html_contains_controls_and_mount_points(client):
    response = client.get("/manage/diagnosis")
    html = response.get_data(as_text=True)
    assert "manage-diagnosis-refresh" in html
    assert "manage-diagnosis-groups" in html
    assert "manage-diagnosis-meta" in html
    assert "manage-diagnosis-overall" in html


def test_manage_base_includes_diagnosis_nav(client):
    response = client.get("/manage")
    html = response.get_data(as_text=True)
    assert "manage-nav-diagnosis" in html
    assert "/manage/diagnosis" in html


def test_manage_dashboard_includes_diagnosis_card(client):
    response = client.get("/manage")
    html = response.get_data(as_text=True)
    assert "manage-dashboard-diagnosis" in html
    assert 'data-feature="manage.system_diagnosis"' in html
