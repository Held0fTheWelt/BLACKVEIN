"""Tests for Phase 2 AI Engineer Suite management pages."""

from __future__ import annotations

from conftest import captured_templates


def test_manage_runtime_dashboard_route_and_template(app, client):
    with captured_templates(app) as templates:
        response = client.get("/manage/runtime-dashboard")
    assert response.status_code == 200
    assert templates[-1][0] == "manage/runtime_dashboard.html"


def test_manage_rag_operations_route_and_template(app, client):
    with captured_templates(app) as templates:
        response = client.get("/manage/rag-operations")
    assert response.status_code == 200
    assert templates[-1][0] == "manage/rag_operations.html"


def test_manage_ai_orchestration_route_and_template(app, client):
    with captured_templates(app) as templates:
        response = client.get("/manage/ai-orchestration")
    assert response.status_code == 200
    assert templates[-1][0] == "manage/ai_orchestration.html"


def test_manage_runtime_settings_route_and_template(app, client):
    with captured_templates(app) as templates:
        response = client.get("/manage/runtime-settings")
    assert response.status_code == 200
    assert templates[-1][0] == "manage/runtime_settings.html"


def test_manage_base_includes_phase2_nav_entries(client):
    response = client.get("/manage")
    html = response.get_data(as_text=True)
    assert "manage-nav-runtime-dashboard" in html
    assert "manage-nav-runtime-settings" in html
    assert "manage-nav-rag-operations" in html
    assert "manage-nav-ai-orchestration" in html
    assert "/manage/runtime-dashboard" in html
    assert "/manage/runtime-settings" in html
    assert "/manage/rag-operations" in html
    assert "/manage/ai-orchestration" in html
    assert 'data-feature="manage.ai_runtime_governance"' in html


def test_manage_runtime_dashboard_mount_points(client):
    response = client.get("/manage/runtime-dashboard")
    html = response.get_data(as_text=True)
    assert "manage-rd-summary-lines" in html
    assert "manage-rd-blockers" in html
    assert "manage-rd-next-actions" in html
    assert "manage-rd-links" in html
    assert "manage_runtime_dashboard.js" in html


def test_manage_rag_operations_mount_points(client):
    response = client.get("/manage/rag-operations")
    html = response.get_data(as_text=True)
    assert "manage-rag-status-lines" in html
    assert "manage-rag-save-settings" in html
    assert "manage-rag-run-probe" in html
    assert "data-rag-action" in html
    assert "manage_rag_operations.js" in html


def test_manage_ai_orchestration_mount_points(client):
    response = client.get("/manage/ai-orchestration")
    html = response.get_data(as_text=True)
    assert "manage-orch-langgraph-lines" in html
    assert "manage-orch-langchain-lines" in html
    assert "manage-orch-save-settings" in html
    assert "manage_ai_orchestration.js" in html


def test_manage_runtime_settings_mount_points(client):
    response = client.get("/manage/runtime-settings")
    html = response.get_data(as_text=True)
    assert "manage-rs-presets" in html
    assert "manage-rs-save-settings" in html
    assert "manage-rs-effective-summary" in html
    assert "manage-rs-change-lines" in html
    assert "manage_runtime_settings.js" in html
