"""Tests for MVPify handoff into Diagnosta readiness analysis."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from mvpify.adapter.service import MVPifyAdapter


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _mk_workspace(tmp_path: Path) -> Path:
    for name, text in {
        "README.md": "# test\n",
        "pyproject.toml": '[project]\nname="x"\nversion="0"\n',
        "fy_governance_enforcement.yaml": "mode: test\n",
        "requirements.txt": "\n",
        "requirements-dev.txt": "\n",
        "requirements-test.txt": "\n",
    }.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    for suite in [
        "mvpify",
        "diagnosta",
        "contractify",
        "testify",
        "despaghettify",
    ]:
        for rel in ["adapter", "tools", "reports", "state", "templates"]:
            (tmp_path / suite / rel).mkdir(parents=True, exist_ok=True)
        (tmp_path / suite / "README.md").write_text(
            f"# {suite}\n", encoding="utf-8"
        )
        (tmp_path / suite / "adapter" / "service.py").write_text(
            "class Placeholder: pass\n", encoding="utf-8"
        )
        (tmp_path / suite / "adapter" / "cli.py").write_text(
            "def main():\n    return 0\n", encoding="utf-8"
        )
    _write_json(
        tmp_path / "contractify" / "reports" / "audit_latest.json",
        {"drift_findings": [], "conflicts": [], "manual_unresolved_areas": []},
    )
    _write_json(
        tmp_path / "testify" / "reports" / "testify_audit.json",
        {"summary": {"finding_count": 0, "warning_count": 0}, "warnings": [], "findings": []},
    )
    _write_json(
        tmp_path / "despaghettify" / "reports" / "latest_check_with_metrics.json",
        {"global_category": "low", "local_spike_count": 0, "file_spikes": [], "function_spikes": []},
    )
    return tmp_path


def _build_bundle(tmp_path: Path) -> Path:
    src = tmp_path / "bundle_src"
    (src / "bundle" / "docs").mkdir(parents=True)
    (src / "bundle" / "contractify" / "reports").mkdir(parents=True)
    (src / "bundle" / "README.md").write_text("# Imported MVP\n", encoding="utf-8")
    (src / "bundle" / "docs" / "MVP.md").write_text("# MVP\n", encoding="utf-8")
    (src / "bundle" / "contractify" / "reports" / "contract_audit.json").write_text(
        '{"ok": true}\n', encoding="utf-8"
    )
    z = tmp_path / "bundle.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for path in src.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(src))
    return z


def test_mvpify_import_bundle_emits_diagnosta_handoff(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    bundle = _build_bundle(tmp_path)
    adapter = MVPifyAdapter(root=ws)
    payload = adapter.import_bundle(str(bundle))
    assert payload["ok"] is True
    handoff = payload["diagnosta_handoff"]
    assert handoff["implementation_outcome"] in {
        "implementation_ready_with_residue",
        "not_ready",
        "not_ready_insufficient_evidence",
    }
    assert handoff["readiness_status"]
    assert (ws / "mvpify" / "reports" / "mvpify_diagnosta_handoff.json").is_file()
    assert handoff["diagnosta_paths"]["readiness_case"]
