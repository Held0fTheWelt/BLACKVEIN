"""Runtime validation orchestration: cross-surface contracts, bootstrap, drift checks, and doc alignment.

Gate identifiers **G-T4-01 … G-T4-08** remain documented traceability labels; this module is the executable
orchestrator referenced from ``area2_validation_commands``.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.runtime.area2_validation_commands import (
    AREA2_TASK4_FULL_CLOSURE_PYTEST_MODULES,
    AREA2_TASK4_GATE_MODULE,
    AREA2_TASK4_PROOF_PYTEST_MODULES,
    area2_task4_full_closure_pytest_invocation,
    area2_task4_proof_only_pytest_argv,
)

from .doc_test_paths import architecture_style_doc

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"

# Load sibling test modules under backend/tests/ without requiring a tests package __init__.
_TESTS_ROOT = Path(__file__).resolve().parents[1]


def _load_tests_py_module(relative_under_tests: str):
    path = _TESTS_ROOT / relative_under_tests
    name = path.stem
    spec = importlib.util.spec_from_file_location(f"_runtime_validation_{name}", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def minimal_module():
    from app.content.module_models import ContentModule, ModuleMetadata

    meta = ModuleMetadata(
        module_id="m1",
        title="T",
        version="1",
        contract_version="1.0.0",
    )
    return ContentModule(metadata=meta, scenes={}, characters={})


@pytest.mark.asyncio
async def test_full_validation_runtime_writers_room_improvement_operator_truth(
    client,
    auth_headers,
    minimal_module,
):
    """G-T4-01: Runtime, Writers-Room, and Improvement each have proven integration contract truth."""
    from . import test_cross_surface_operator_audit_contract as _xs

    await _xs.test_runtime_staged_operator_audit_matches_cross_surface_contract(minimal_module)
    _xs.test_writers_room_operator_audit_and_routing_evidence_contract(client, auth_headers)
    _xs.test_improvement_operator_audit_and_deterministic_base_separation(client, auth_headers)


@pytest.mark.asyncio
async def test_full_validation_bootstrap_profiles_and_staged_integration(minimal_module):
    """G-T4-02: named profiles, bootstrap on/off, and real create_app bootstrap-on staged path."""
    from . import test_runtime_operational_bootstrap_and_routing_registry as _conv
    from . import test_runtime_startup_profiles_operator_truth as _final

    _final.test_startup_profile_bootstrap_facts_reproducible()
    _final.test_startup_profile_operational_state_expectations()
    _conv.test_bootstrap_registry_populates_adapter_specs_for_staged_tuples()
    _conv.test_classify_operational_state_matrix()

    boot = _load_tests_py_module("test_bootstrap_staged_runtime_integration.py")
    await boot.test_create_app_with_bootstrap_registers_mock_and_staged_runtime_runs(minimal_module)


@pytest.mark.asyncio
async def test_full_validation_operator_comparison_and_cross_surface_contracts(
    app_bootstrap_on,
    client_bootstrap_on,
    auth_headers_bootstrap_on,
):
    """G-T4-03: compact_operator_comparison grammar and cross-surface contract regression layers."""
    from . import test_runtime_operator_comparison_cross_surface as _t3
    from . import test_cross_surface_operator_audit_contract as _xs

    await _t3.test_operator_comparison_compact_truth_payload_under_bootstrap(
        app_bootstrap_on,
        client_bootstrap_on,
        auth_headers_bootstrap_on,
    )
    _xs.test_operator_truth_coherent_across_bounded_http_surfaces(client_bootstrap_on, auth_headers_bootstrap_on)


@pytest.mark.asyncio
async def test_full_validation_degraded_runtime_and_improvement_honesty(minimal_module):
    """G-T4-04: degraded Runtime paths and Improvement missing-adapter honesty."""
    from . import test_runtime_ai_turn_degraded_paths_tool_loop as _hard

    await _hard.test_degraded_early_skip_then_synthesis_when_preflight_and_signal_unroutable(minimal_module)
    await _hard.test_empty_registry_staged_forces_synthesis_on_passed_adapter_with_degraded_path(minimal_module)

    imp_neg = _load_tests_py_module("improvement/test_improvement_model_routing_denied.py")
    imp_neg.test_run_routed_bounded_call_missing_provider_adapter_skips_with_skip_reason()


def test_full_validation_audit_schema_drift_resistance():
    """G-T4-05: audit schema and routing-evidence stable key expectations."""
    from . import test_runtime_drift_resistance as _drift

    _drift.test_audit_schema_version_is_stable_string()
    _drift.test_build_routing_evidence_emits_stable_key_superset_for_role_matrix_primary()
    _drift.test_runtime_operator_audit_empty_traces_still_emits_stable_top_level_keys()


def test_full_validation_documented_pytest_command_matches_code():
    """G-T4-06: testing-setup.md embeds the exact canonical Task 4 invocation from code."""
    inv = area2_task4_full_closure_pytest_invocation(no_cov=True)
    setup_doc = (REPO_ROOT / "docs" / "testing-setup.md").read_text(encoding="utf-8")
    assert inv in setup_doc, "docs/testing-setup.md must contain the exact area2_task4_full_closure_pytest_invocation() line"
    assert "cd backend" in setup_doc, "docs/testing-setup.md must document cwd=backend for Task 4 closure"
    closure_report = architecture_style_doc("area2_validation_hardening_closure_report.md").read_text(
        encoding="utf-8"
    )
    assert inv in closure_report, "closure report must embed the same canonical invocation line"
    for mod in AREA2_TASK4_FULL_CLOSURE_PYTEST_MODULES:
        assert mod in setup_doc, f"testing-setup.md Task 4 section must list module {mod}"


def test_full_validation_proof_modules_pass_without_gate_recursion():
    """G-T4-07: full proof module list passes (subprocess; excludes gate orchestrator to avoid recursion)."""
    env = os.environ.copy()
    for key in list(env.keys()):
        if any(
            p in key.upper()
            for p in (
                "OPENAI",
                "ANTHROPIC",
                "OLLAMA",
                "AZURE_OPENAI",
                "LANGCHAIN_API_KEY",
                "LANGFUSE",
            )
        ):
            env.pop(key, None)
    proc = subprocess.run(
        [sys.executable, *area2_task4_proof_only_pytest_argv(no_cov=True)],
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert proc.returncode == 0, (
        "Task 4 proof suite must pass from backend/ with --no-cov\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )


def test_full_validation_docs_reference_task4_gates_and_commands():
    """G-T4-08: required architecture docs reference every G-T4 gate and the command surface."""
    gate_doc = architecture_style_doc("area2_task4_closure_gates.md")
    assert gate_doc.is_file()
    gtext = gate_doc.read_text(encoding="utf-8")
    for n in range(1, 9):
        assert f"G-T4-{n:02d}" in gtext, f"area2_task4_closure_gates.md must mention G-T4-{n:02d}"

    doc_paths = (
        architecture_style_doc("llm_slm_role_stratification.md"),
        architecture_style_doc("ai_story_contract.md"),
        architecture_style_doc("area2_validation_hardening_closure_report.md"),
        REPO_ROOT / "docs" / "testing-setup.md",
    )
    for path in doc_paths:
        assert path.is_file(), f"missing doc {path}"
        text = path.read_text(encoding="utf-8")
        for n in range(1, 9):
            assert f"G-T4-{n:02d}" in text, f"{path.name} must reference G-T4-{n:02d}"
        assert "area2_task4_closure_gates.md" in text
        assert "area2_validation_hardening_closure_report.md" in text
        assert "area2_validation_commands" in text

    assert AREA2_TASK4_GATE_MODULE in AREA2_TASK4_FULL_CLOSURE_PYTEST_MODULES
