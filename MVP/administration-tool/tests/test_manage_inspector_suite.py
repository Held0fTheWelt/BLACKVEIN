"""Tests for canonical /manage/inspector-workbench shell."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import captured_templates

CANONICAL_INSPECTOR_PATH = "/manage/inspector-workbench"


def test_manage_inspector_workbench_returns_200(client):
    response = client.get(CANONICAL_INSPECTOR_PATH)
    assert response.status_code == 200


def test_manage_inspector_workbench_renders_template(app, client):
    with captured_templates(app) as templates:
        response = client.get(CANONICAL_INSPECTOR_PATH)
    assert response.status_code == 200
    assert templates[-1][0] == "manage/inspector_workbench.html"


def test_manage_inspector_workbench_contains_turn_inspector_mountpoints(client):
    response = client.get(CANONICAL_INSPECTOR_PATH)
    html = response.get_data(as_text=True)
    assert "inspector-load-all" in html
    assert "inspector-panel-turn" in html
    assert "inspector-mermaid-host" in html
    assert "inspector-decision-summary" in html
    assert "inspector-authority-boundary" in html
    assert "inspector-fallback-status-grid" in html
    assert "inspector-provenance-canonical" in html
    assert "inspector-provenance-raw-json" in html
    assert "inspector-gate-posture-grid" in html
    assert "inspector-gate-legacy-block" in html
    assert "inspector-planner-structured" in html
    assert "inspector-mermaid-mode" in html
    assert "inspector-raw-json" in html
    assert "inspector-gate-outcome-grid" in html
    assert "inspector-validation-outcome-grid" in html


def test_manage_inspector_workbench_contains_all_material_sections(client):
    response = client.get(CANONICAL_INSPECTOR_PATH)
    html = response.get_data(as_text=True)
    assert "/api/v1/admin/ai-stack/inspector/turn/" in html
    assert "/api/v1/admin/ai-stack/inspector/timeline/" in html
    assert "inspector-panel-timeline" in html
    assert "inspector-panel-comparison" in html
    assert "inspector-panel-coverage" in html
    assert "inspector-panel-provenance-raw" in html
    assert "inspector-timeline-structured" in html
    assert "inspector-timeline-full-json" in html
    assert "inspector-comparison-structured" in html
    assert "inspector-comparison-full-json" in html
    assert "inspector-coverage-structured" in html
    assert "inspector-coverage-full-json" in html
    assert "inspector-provenance-full-json" in html
    assert "Canonical provenance entries" in html
    assert "Raw evidence bundle" in html


def test_manage_base_includes_single_canonical_inspector_nav(client):
    response = client.get("/manage")
    html = response.get_data(as_text=True)
    assert "manage-nav-inspector-workbench" in html
    assert CANONICAL_INSPECTOR_PATH in html
    assert "manage-nav-inspector-suite" not in html
    assert "manage-nav-ai-stack-governance" not in html


def test_comparison_renderer_includes_mandatory_structured_fields():
    script_path = Path(__file__).resolve().parents[1] / "static" / "manage_inspector_workbench.js"
    script = script_path.read_text(encoding="utf-8")
    assert "Mandatory dimension:" in script
    assert "from_trace_id" in script
    assert "to_trace_id" in script
    assert "continuity_support_posture_from" in script
    assert "continuity_support_posture_to" in script
    assert "renderComparisonRowBlocks" in script


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
        assert response.headers.get("Location") == CANONICAL_INSPECTOR_PATH


@pytest.mark.parametrize(
    "legacy_path",
    [
        "/manage/ai-stack/governance",
        "/manage/ai-stack-governance",
        "/manage/inspector-suite",
        "/manage/inspector-suite/turn",
    ],
)
def test_legacy_paths_follow_redirect_to_workbench(app, client, legacy_path):
    with captured_templates(app) as templates:
        response = client.get(legacy_path, follow_redirects=True)
    assert response.status_code == 200
    assert templates[-1][0] == "manage/inspector_workbench.html"
