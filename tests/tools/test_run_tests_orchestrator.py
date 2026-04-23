"""Contract tests for tests/run_tests.py suite wiring."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_runner_module():
    root = Path(__file__).resolve().parents[2]
    runner_path = root / "tests" / "run_tests.py"
    spec = importlib.util.spec_from_file_location("wos_run_tests", runner_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_all_suite_sequence_includes_root_groups() -> None:
    mod = _load_runner_module()
    sequence = list(mod.ALL_SUITE_SEQUENCE)
    for suite in (
        "root_core",
        "root_integration",
        "root_branching",
        "root_smoke",
        "root_tools",
        "root_requirements_hygiene",
        "root_e2e_python",
        "root_experience_scoring",
    ):
        assert suite in sequence


def test_get_suite_configs_all_keeps_external_lanes_opt_in() -> None:
    mod = _load_runner_module()
    suites = mod.get_suite_configs(["all"])
    assert "playwright_e2e" not in suites
    assert "compose_smoke" not in suites
    assert "backend" in suites
    assert "root_smoke" in suites


def test_get_suite_configs_can_add_external_lanes() -> None:
    mod = _load_runner_module()
    suites = mod.get_suite_configs(["all"], with_playwright=True, with_compose_smoke=True)
    assert "playwright_e2e" in suites
    assert "compose_smoke" in suites
    assert suites["playwright_e2e"].kind == "external"
    assert suites["compose_smoke"].kind == "external"

