"""Canonical Area 2 validation command surfaces (Workstream B + Task 4 full closure).

- **G-B-06:** ``AREA2_DUAL_CLOSURE_PYTEST_MODULES`` / ``area2_dual_closure_pytest_invocation``.
- **G-T4-06 / G-T4-07:** ``AREA2_TASK4_FULL_CLOSURE_PYTEST_MODULES`` (and proof-only tuple for
  subprocess stability without recursive gate self-invocation).

Run from ``backend/`` so ``backend/pytest.ini`` applies (``pythonpath``, ``testpaths``).
Default ``addopts`` enable coverage; gate and closure runs MUST pass ``--no-cov`` to
match documented invocations.
"""

from __future__ import annotations

# Pytest targets: paths relative to backend/ (pytest.ini testpaths = tests).
AREA2_DUAL_CLOSURE_PYTEST_MODULES: tuple[str, ...] = (
    "tests/runtime/test_runtime_routing_registry_composed_proofs.py",
    "tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py",
    "tests/runtime/test_runtime_startup_profiles_operator_truth.py",
    "tests/runtime/test_cross_surface_operator_audit_contract.py",
    "tests/test_bootstrap_staged_runtime_integration.py",
    "tests/runtime/test_model_inventory_bootstrap.py",
)


def area2_dual_closure_pytest_invocation(*, no_cov: bool = True) -> str:
    """Single-line command string for documentation (shell; cwd = backend)."""
    parts = ["python", "-m", "pytest", *AREA2_DUAL_CLOSURE_PYTEST_MODULES, "-q", "--tb=short"]
    if no_cov:
        parts.append("--no-cov")
    return " ".join(parts)


def area2_dual_closure_pytest_argv(no_cov: bool = True) -> list[str]:
    """Argv for ``python -m pytest`` subprocess from backend cwd."""
    out = ["-m", "pytest", *AREA2_DUAL_CLOSURE_PYTEST_MODULES, "-q", "--tb=short"]
    if no_cov:
        out.append("--no-cov")
    return out


# --- Area 2 Task 4 full closure (G-T4): proof modules + gate orchestrator -----------------

AREA2_TASK4_GATE_MODULE: str = "tests/runtime/test_runtime_validation_commands_orchestration.py"

# Proof-only: used by G-T4-07 subprocess to avoid recursive self-invocation of the gate module.
AREA2_TASK4_PROOF_PYTEST_MODULES: tuple[str, ...] = (
    *AREA2_DUAL_CLOSURE_PYTEST_MODULES,
    "tests/runtime/test_runtime_operator_comparison_cross_surface.py",
    "tests/runtime/test_runtime_ai_turn_degraded_paths_tool_loop.py",
    "tests/runtime/test_runtime_drift_resistance.py",
    "tests/runtime/test_runtime_staged_orchestration.py",
    "tests/runtime/test_runtime_model_ranking_synthesis_contracts.py",
    "tests/improvement/test_improvement_model_routing_denied.py",
    "tests/runtime/test_ai_turn_executor.py::test_agent_orchestration_executes_real_separate_subagents_and_logs_trace",
)

# Single canonical ordered list: all proof modules, then Task 4 gate tests (documentation + G-T4-06).
AREA2_TASK4_FULL_CLOSURE_PYTEST_MODULES: tuple[str, ...] = (
    *AREA2_TASK4_PROOF_PYTEST_MODULES,
    AREA2_TASK4_GATE_MODULE,
)


def area2_task4_full_closure_pytest_invocation(*, no_cov: bool = True) -> str:
    """Single-line shell command; cwd must be ``backend/`` (pytest.ini testpaths)."""
    parts = ["python", "-m", "pytest", *AREA2_TASK4_FULL_CLOSURE_PYTEST_MODULES, "-q", "--tb=short"]
    if no_cov:
        parts.append("--no-cov")
    return " ".join(parts)


def area2_task4_full_closure_pytest_argv(*, no_cov: bool = True) -> list[str]:
    """Argv for ``python -m pytest`` from backend cwd (includes gate module)."""
    out = ["-m", "pytest", *AREA2_TASK4_FULL_CLOSURE_PYTEST_MODULES, "-q", "--tb=short"]
    if no_cov:
        out.append("--no-cov")
    return out


def area2_task4_proof_only_pytest_argv(*, no_cov: bool = True) -> list[str]:
    """Argv for G-T4-07: full proof suite without the Task 4 gate orchestrator module."""
    out = ["-m", "pytest", *AREA2_TASK4_PROOF_PYTEST_MODULES, "-q", "--tb=short"]
    if no_cov:
        out.append("--no-cov")
    return out
