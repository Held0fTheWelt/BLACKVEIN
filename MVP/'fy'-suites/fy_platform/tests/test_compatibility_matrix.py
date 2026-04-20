from __future__ import annotations

import json
from pathlib import Path


def test_wave1_baseline_compatibility_matrix_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    matrix = root / "compatibility_matrix.wave1_baseline.json"
    assert matrix.is_file()
    data = json.loads(matrix.read_text(encoding="utf-8"))
    assert data["matrixVersion"] == "1"
    assert "docify" in data["suites"]
    assert "postmanify" in data["suites"]
    assert "operational_surfaces" in data
    assert "command_flag_surfaces" in data["operational_surfaces"]
    assert "default_filenames" in data["operational_surfaces"]
