"""Tests for operational governance manage page routing/rendering."""

from __future__ import annotations

from conftest import captured_templates


def test_manage_operational_governance_returns_200(client):
    response = client.get("/manage/operational-governance")
    assert response.status_code == 200


def test_manage_ai_runtime_governance_alias_returns_200(client):
    response = client.get("/manage/ai-runtime-governance")
    assert response.status_code == 200


def test_manage_operational_governance_template(app, client):
    with captured_templates(app) as templates:
        response = client.get("/manage/operational-governance")
    assert response.status_code == 200
    assert templates[-1][0] == "manage/operational_governance.html"


def test_manage_base_includes_operational_governance_nav(client):
    response = client.get("/manage")
    html = response.get_data(as_text=True)
    assert "manage-nav-operational-governance" in html
    assert "/manage/operational-governance" in html
    assert "manage-nav-ai-runtime-governance" in html
    assert "/manage/ai-runtime-governance" in html
    assert 'data-feature="manage.ai_runtime_governance"' in html


def test_manage_ai_runtime_governance_renders_readiness_overview(client):
    response = client.get("/manage/ai-runtime-governance")
    html = response.get_data(as_text=True)
    assert "manage-og-readiness-headline" in html
    assert "manage-og-readiness-blockers" in html
    assert "Runtime readiness overview" in html
