"""Integration-style checks: operator defaults appear in manage HTML from Flask context only."""
from __future__ import annotations

import re

import pytest


def _wec_new_module_input_open_tag(html: str) -> str:
    m = re.search(r"<input\b[^>]*\bid=\"wec-new-module\"[^>]*>", html, re.IGNORECASE)
    return m.group(0) if m else ""


@pytest.mark.integration
def test_manage_world_engine_console_reflects_injected_content_module_id(app_factory):
    app = app_factory(
        test_config={
            "TESTING": True,
            "BACKEND_API_URL": "https://backend.example.test",
            "SECRET_KEY": "test-secret-key",
            "ADMIN_DEFAULT_CONTENT_MODULE_ID": "acme_content_module",
            "ADMIN_DEFAULT_EXPERIENCE_TEMPLATE_ID": "acme_runtime_template",
        }
    )
    client = app.test_client()
    r = client.get("/manage/world-engine-console")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'data-content-module-id="acme_content_module"' in html
    assert 'data-default-template-id="acme_runtime_template"' in html
    tag = _wec_new_module_input_open_tag(html)
    assert tag
    assert "acme_content_module" in tag
    assert "god_of_carnage" not in tag.lower()


@pytest.mark.integration
def test_manage_world_engine_console_no_hardcoded_module_when_injection_empty(app_factory):
    app = app_factory(
        test_config={
            "TESTING": True,
            "BACKEND_API_URL": "https://backend.example.test",
            "SECRET_KEY": "test-secret-key",
            "ADMIN_DEFAULT_CONTENT_MODULE_ID": "",
            "ADMIN_DEFAULT_EXPERIENCE_TEMPLATE_ID": "",
        }
    )
    client = app.test_client()
    r = client.get("/manage/world-engine-console")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'data-content-module-id=""' in html
    tag = _wec_new_module_input_open_tag(html)
    assert tag
    assert "god_of_carnage" not in tag.lower()
