from __future__ import annotations

from pathlib import Path

from conftest import captured_templates


def test_manage_governance_console_route_renders_template(app, client):
    with captured_templates(app) as templates:
        response = client.get("/manage/governance-console")
    assert response.status_code == 200
    assert templates[-1][0] == "manage/governance_console.html"


def test_manage_base_includes_governance_console_nav(client):
    response = client.get("/manage")
    html = response.get_data(as_text=True)
    assert "manage-nav-governance-console" in html
    assert "/manage/governance-console" in html
    assert 'data-feature="manage.ai_runtime_governance"' in html


def test_runtime_config_truth_js_uses_manage_auth_and_ok_data_envelope():
    js = Path(__file__).resolve().parents[1] / "static" / "manage_runtime_config_truth.js"
    text = js.read_text(encoding="utf-8")
    assert "ManageAuth.apiFetchWithAuth" in text
    assert 'Object.prototype.hasOwnProperty.call(res, "ok")' in text
    assert "resp.success" not in text


def test_governance_console_template_mounts_all_required_views(client):
    response = client.get("/manage/governance-console")
    html = response.get_data(as_text=True)
    required_mounts = {
        "gov-runtime-readiness": "Runtime Readiness",
        "gov-adr0041-authority": "Capability Authority",
        "gov-capability-matrix": "Capability Matrix",
        "gov-validator-registry": "Validator Registry",
        "gov-evidence": "Langfuse / MCP",
        "gov-ledger": "Runtime Aspect Ledger",
        "gov-narrative-systems": "Runtime Systems",
        "gov-feature-flags": "Feature Flag Ownership",
    }
    for element_id, label in required_mounts.items():
        assert f'id="{element_id}"' in html
        assert f'data-json-label="{label}"' in html
    assert "manage_governance_console.js" in html
    assert "gov-console-card-grid" in html
    assert 'class="manage-psc-json" data-json-viewer' in html


def test_governance_console_includes_adr0041_and_evidence_guidance(client):
    response = client.get("/manage/governance-console")
    html = response.get_data(as_text=True)
    assert "ADR-0041 critical flags" in html
    assert "cannot upgrade reject" in html
    assert "Credential readiness" in html
    assert "score proof" in html
    assert "admin_read_only" in html
    assert "env_only (ADR flags)" in html


def test_runtime_config_truth_template_includes_probe_warning(client):
    response = client.get("/manage/runtime/config-truth")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "`requires_http_probe` is not ready" in html
    assert "False-green prevention" in html
