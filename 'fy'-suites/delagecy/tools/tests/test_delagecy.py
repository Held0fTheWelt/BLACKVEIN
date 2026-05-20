from __future__ import annotations

import json
from pathlib import Path

from delagecy.tools.hub_cli import main
from delagecy.tools.scanner import scan


def test_scan_finds_ui_legacy_hit(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    target = root / "administration-tool" / "templates" / "manage"
    target.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (root / "'fy'-suites").mkdir()
    (target / "page.html").write_text("<div>Legacy compatibility</div>\n", encoding="utf-8")

    payload = scan(root)

    assert payload["hit_count"] == 1
    hit = payload["hits"][0]
    assert hit["kind"] == "ui"
    assert hit["path"].endswith("page.html")


def test_cli_register_approve_and_mark_removed(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    suite = root / "'fy'-suites" / "delagecy"
    src = root / "app.py"
    suite.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    src.write_text("# legacy path\n", encoding="utf-8")
    monkeypatch.chdir(root)

    scan_json = suite / "scan.json"
    assert main(["scan", "--out", str(scan_json)]) == 0
    payload = json.loads(scan_json.read_text(encoding="utf-8"))
    fp = payload["hits"][0]["fingerprint"]

    assert main(["register", "--scan-json", str(scan_json), "--fingerprint", fp, "--title", "legacy path"]) == 0
    assert main(["approve", "--id", "DLG-001", "--approved-by", "test", "--note", "approved"]) == 0
    assert main(["mark-removed", "--id", "DLG-001", "--verification", "verified"]) == 0

    out = capsys.readouterr().out
    assert "DLG-001" in out


def test_scanner_can_scan_delagecy_internal_selftest_area(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    internal = root / "'fy'-suites" / "delagecy" / "internal"
    internal.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (internal / "fixture.py").write_text("# legacy fixture\n", encoding="utf-8")

    payload = scan(root, include=["'fy'-suites/delagecy/internal"])

    assert payload["hit_count"] == 1
    assert payload["hits"][0]["path"].endswith("delagecy/internal/fixture.py")
