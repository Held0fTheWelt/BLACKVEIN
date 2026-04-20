from __future__ import annotations

import json
from pathlib import Path

from despaghettify.tools import hub_cli


def test_check_runs_with_manifest_driven_non_wos_root(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "portable-repo"
    src = repo / "src"
    src.mkdir(parents=True)
    (src / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (repo / "fy-manifest.yaml").write_text(
        "manifestVersion: 1\n"
        "suites:\n"
        "  despaghettify:\n"
        "    scan_roots:\n"
        "      - src\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DESPAG_REPO_ROOT", str(repo))
    out = repo / "despag-check.json"
    code = hub_cli.main(["check", "--out", str(out)])
    assert code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["kind"] == "despaghettify_check"
    assert payload["ds005"]["enabled"] is False
