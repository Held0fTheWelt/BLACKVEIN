"""Smoke checks for MVP generic baseline comparison script (no live API calls)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "mvp_generic_llm_baseline_chat.py"
DATA = REPO_ROOT / "scripts" / "data" / "mvp_goc_baseline_opening.json"


def _load_baseline_module():
    spec = importlib.util.spec_from_file_location("mvp_generic_llm_baseline_chat", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(not SCRIPT.is_file(), reason="baseline script missing")
def test_mvp_baseline_print_opening_exits_zero():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--print-opening"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    bundle = json.loads(proc.stdout)
    assert bundle.get("comparison_id")
    assert "arm_b_system_prompt" in bundle
    assert "opening_narration" in bundle


@pytest.mark.skipif(not SCRIPT.is_file(), reason="baseline script missing")
def test_mvp_baseline_data_file_matches_script_expectations():
    assert DATA.is_file()
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    mod = _load_baseline_module()
    b = mod.load_opening_bundle(DATA)
    assert b["comparison_id"] == raw["comparison_id"]
    msgs = mod.build_initial_messages(b)
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert raw["opening_narration"][:20] in msgs[1]["content"]
