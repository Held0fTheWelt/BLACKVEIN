from __future__ import annotations

import json
from pathlib import Path

from fy_platform.tools.cli import main


def test_bootstrap_and_validate_with_explicit_project_root(tmp_path: Path, capsys) -> None:
    code = main(["bootstrap", "--project-root", str(tmp_path)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    manifest = tmp_path / "fy-manifest.yaml"
    assert manifest.is_file()

    code = main(["validate-manifest", "--project-root", str(tmp_path)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
