"""MCP Operations manage surface."""

from __future__ import annotations

from conftest import captured_templates


def test_manage_mcp_operations_returns_200(client):
    r = client.get("/manage/mcp-operations")
    assert r.status_code == 200


def test_manage_mcp_operations_renders_template(app, client):
    with captured_templates(app) as templates:
        r = client.get("/manage/mcp-operations")
    assert r.status_code == 200
    assert templates[-1][0] == "manage/mcp_operations.html"


def test_manage_mcp_operations_html_contains_shell(client):
    r = client.get("/manage/mcp-operations")
    html = r.get_data(as_text=True)
    assert "mcp-ops-tabs" in html
    assert "manage_mcp_operations.js" in html
    assert "mcp-tab-overview" in html


def test_manage_base_includes_mcp_operations_nav(client):
    r = client.get("/manage")
    html = r.get_data(as_text=True)
    assert "manage-nav-mcp-operations" in html
    assert "/manage/mcp-operations" in html
    assert 'data-feature="manage.mcp_operations"' in html
