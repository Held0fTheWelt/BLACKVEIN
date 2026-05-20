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


def _suite_targets(cfg) -> tuple[str, ...]:
    return (cfg.target, *cfg.extra_targets)


def test_engine_blocks_are_first_class_partial_suites() -> None:
    mod = _load_runner_module()
    for suite in mod.ENGINE_BLOCK_SUITES:
        cfg = mod.SUITE_CONFIGS[suite]
        assert cfg.kind == "pytest"
        assert cfg.cwd == mod.WORLD_ENGINE_DIR
        assert cfg.supports_coverage is False

    opening_targets = _suite_targets(mod.SUITE_CONFIGS["engine_opening_contracts"])
    assert "tests/test_mvp4_contract_opening_truthfulness.py" in opening_targets
    assert "tests/test_mvp2_runtime_state_actor_lanes.py" in opening_targets
    assert mod.SUITE_CONFIGS["engine_runtime"].target == "tests/runtime"
    assert set(mod.ENGINE_BLOCK_TARGETS).issubset(set(mod.SUITE_CONFIGS["engine_rest"].ignore_paths))
    assert mod.marker_filter_for_suite("engine_runtime", "contracts") == "contract"
    assert mod.marker_filter_for_suite("engine_runtime", "e2e") is None


def test_ai_stack_blocks_run_from_repo_root_and_have_rest_slice() -> None:
    mod = _load_runner_module()
    for suite in mod.AI_STACK_BLOCK_SUITES:
        cfg = mod.SUITE_CONFIGS[suite]
        assert cfg.kind == "pytest"
        assert cfg.cwd == mod.PROJECT_ROOT
        assert cfg.supports_coverage is False

    graph_targets = _suite_targets(mod.SUITE_CONFIGS["ai_stack_graph"])
    assert "ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py" in graph_targets
    assert "ai_stack/tests/test_langgraph_runtime.py" in graph_targets
    assert set(mod.AI_STACK_BLOCK_TARGETS).issubset(set(mod.SUITE_CONFIGS["ai_stack_rest"].ignore_paths))
    assert mod.marker_filter_for_suite("ai_stack_graph", "contracts") is None


def test_backend_play_block_is_subtracted_from_backend_rest() -> None:
    mod = _load_runner_module()
    cfg = mod.SUITE_CONFIGS["backend_play"]
    assert cfg.cwd == mod.BACKEND_DIR
    assert cfg.supports_scope is True
    assert cfg.supports_coverage is False
    assert "tests/test_world_engine_backend_api_contracts.py" in _suite_targets(cfg)
    assert set(mod.BACKEND_PLAY_TARGETS).issubset(set(mod.SUITE_CONFIGS["backend_rest"].ignore_paths))
