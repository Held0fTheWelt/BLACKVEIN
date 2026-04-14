"""Administration-tool tests for research domain strategic pages."""

from __future__ import annotations

import pytest

RESEARCH_PATHS = [
    "/manage/research/overview",
    "/manage/research/source-intake",
    "/manage/research/extraction-tuning",
    "/manage/research/findings",
    "/manage/research/canonical-truth",
    "/manage/research/mcp-workbench",
]


@pytest.mark.parametrize("path", RESEARCH_PATHS)
def test_research_pages_render_200(app, client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "research-governance-page" in html
    assert "data-research-governance-page" in html


def test_research_overview_has_layer_summary_host(app, client):
    resp = client.get("/manage/research/overview")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "research-layer-cards" in body
    assert "manage_research_governance.js" in body


def test_research_findings_declares_non_canonical(app, client):
    resp = client.get("/manage/research/findings")
    assert resp.status_code == 200
    assert "Not canonical" in resp.get_data(as_text=True)


def test_research_canonical_page_declares_canonical(app, client):
    resp = client.get("/manage/research/canonical-truth")
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "Canonical" in text
    assert "promoted" in text.lower()


def test_research_mcp_page_mentions_workbench(app, client):
    resp = client.get("/manage/research/mcp-workbench")
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "MCP" in text
    assert "workbench" in text.lower()
