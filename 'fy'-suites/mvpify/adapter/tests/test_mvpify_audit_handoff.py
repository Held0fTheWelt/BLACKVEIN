"""Audit-path handoff tests for MVPify."""
from __future__ import annotations

from pathlib import Path

from mvpify.adapter.service import MVPifyAdapter


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _mk_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    for name, text in {
        "README.md": "# Workspace\n",
        "pyproject.toml": '[project]\nname="workspace"\nversion="0.1.0"\n',
        "fy_governance_enforcement.yaml": "ok: true\n",
        "requirements.txt": "\n",
        "requirements-dev.txt": "\n",
        "requirements-test.txt": "\n",
    }.items():
        _write(ws / name, text)
    for suite in ["mvpify", "diagnosta", "contractify", "despaghettify", "testify"]:
        for rel in ["adapter", "tools", "reports", "state", "templates"]:
            (ws / suite / rel).mkdir(parents=True, exist_ok=True)
        _write(ws / suite / "README.md", f"# {suite}\n")
        _write(ws / suite / "adapter" / "service.py", "class Placeholder: pass\n")
        _write(ws / suite / "adapter" / "cli.py", "def main():\n    return 0\n")
    return ws


def test_mvpify_audit_emits_diagnosta_handoff(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    adapter = MVPifyAdapter(root=ws)

    payload = adapter.audit(str(ws))

    assert payload["ok"] is True
    assert payload["diagnosta_handoff"]["schema_version"] == "fy.mvpify-diagnosta-handoff.v1"
    assert (ws / "mvpify" / "reports" / "mvpify_diagnosta_handoff.json").is_file()
