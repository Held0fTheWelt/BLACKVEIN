"""Tests for canonical /manage/inspector-workbench shell."""

from __future__ import annotations

from conftest import captured_templates


def test_manage_inspector_workbench_returns_200(client):
    response = client.get("/manage/inspector-workbench")
    assert response.status_code == 200


def test_manage_inspector_workbench_renders_template(app, client):
    with captured_templates(app) as templates:
        response = client.get("/manage/inspector-workbench")
    assert response.status_code == 200
    assert templates[-1][0] == "manage/inspector_workbench.html"


def test_manage_inspector_workbench_contains_turn_inspector_mountpoints(client):
    response = client.get("/manage/inspector-workbench")
    html = response.get_data(as_text=True)
    assert "inspector-load-all" in html
    assert "inspector-panel-turn" in html
    assert "inspector-mermaid-host" in html
    assert "inspector-decision-summary" in html
    assert "inspector-authority-boundary" in html
    assert "inspector-fallback-status" in html
    assert "inspector-provenance" in html
    assert "inspector-rejection-analysis" in html
    assert "inspector-raw-json" in html


def test_manage_inspector_workbench_contains_all_material_sections(client):
    response = client.get("/manage/inspector-workbench")
    html = response.get_data(as_text=True)
    assert "inspector-panel-timeline" in html
    assert "inspector-panel-comparison" in html
    assert "inspector-panel-coverage" in html
    assert "inspector-panel-provenance-raw" in html
    assert "inspector-timeline-json" in html
    assert "inspector-comparison-json" in html
    assert "inspector-coverage-json" in html
    assert "inspector-provenance-json" in html


def test_manage_base_includes_single_canonical_inspector_nav(client):
    response = client.get("/manage")
    html = response.get_data(as_text=True)
    assert "manage-nav-inspector-workbench" in html
    assert "/manage/inspector-workbench" in html
    assert "manage-nav-inspector-suite" not in html
    assert "manage-nav-ai-stack-governance" not in html


def test_legacy_inspector_and_governance_paths_redirect_permanently(client):
    legacy_paths = [
        "/manage/ai-stack/governance",
        "/manage/ai-stack-governance",
        "/manage/inspector-suite",
        "/manage/inspector-suite/turn",
    ]
    for path in legacy_paths:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 308
        assert response.headers.get("Location", "").endswith("/manage/inspector-workbench")
