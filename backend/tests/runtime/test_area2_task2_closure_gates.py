"""Area 2 Task 2 — registry/routing convergence closure (G-T2-01 .. G-T2-08).

G-T2-01 .. G-T2-07 delegate to existing evolution/final/cross-surface proofs. Imported
test modules are referenced as **modules** (not ``from … import test_foo``) so pytest
does not collect delegated tests twice from this file.

G-T2-08 (documentation truth) is defined after Task 2 markdown exists (Phase 9).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.area2_routing_authority import (
    AUTHORITY_SOURCE_IMPROVEMENT,
    AUTHORITY_SOURCE_RUNTIME,
    AUTHORITY_SOURCE_WRITERS_ROOM,
    CanonicalSurface,
    authority_entries_for_surface,
)

from . import test_area2_convergence_gates as _conv
from . import test_area2_final_closure_gates as _final
from . import test_cross_surface_operator_audit_contract as _xs

REPO_ROOT = Path(__file__).resolve().parents[3]


def _assert_primary_authority_sources_per_surface() -> None:
    """G-T2-01: each canonical surface lists registry entries; spec sources are non-empty."""
    for surf in CanonicalSurface:
        assert authority_entries_for_surface(surf), f"no authority entries for {surf.value}"
    assert AUTHORITY_SOURCE_RUNTIME.strip()
    assert AUTHORITY_SOURCE_WRITERS_ROOM.strip()
    assert AUTHORITY_SOURCE_IMPROVEMENT == AUTHORITY_SOURCE_WRITERS_ROOM


def test_g_t2_01_authority_convergence_gate() -> None:
    """G-T2-01: singular primary Task 2A policy; explicit non-competing layers in registry."""
    _conv.test_g_conv_01_single_authority_gate()
    _final.test_g_final_03_practical_authority_convergence_gate()
    _assert_primary_authority_sources_per_surface()


def test_g_t2_02_startup_bootstrap_truth_gate() -> None:
    """G-T2-02: named profiles and operational/bootstrap classification are deterministic."""
    _final.test_g_final_01_reproducible_bootstrap_gate()
    _final.test_g_final_01_expected_operational_state_matrix()
    _conv.test_g_conv_03_state_classification_gate_matrix()


def test_g_t2_04_no_eligible_discipline_gate() -> None:
    """G-T2-04: degraded vs misconfigured vs test-isolated vs true no-eligible are distinct."""
    _conv.test_g_conv_04_no_eligible_discipline_gate()
    _final.test_g_final_04_no_eligible_non_normalization_gate()


def test_g_t2_05_operator_truth_gate(client, auth_headers) -> None:
    """G-T2-05: compact operator truth on bounded HTTP plus legibility derivation."""
    _final.test_g_final_05_operator_legibility_gate()
    _xs.test_writers_room_operator_audit_and_routing_evidence_contract(client, auth_headers)


def test_g_t2_06_inventory_coverage_truth_gate() -> None:
    """G-T2-06: inventory surfaces satisfied by bootstrap specs and WR spec builder."""
    _conv.test_bounded_specs_cover_writers_room_and_improvement_surfaces()
    _conv.test_g_conv_02_healthy_bootstrap_gate_runtime_specs()


def test_g_t2_07_legacy_compatibility_gate() -> None:
    """G-T2-07: bootstrap-off test isolation and legacy expectations remain intact."""
    _conv.test_g_conv_06_legacy_compatibility_gate()
    _final.test_g_final_07_legacy_compatibility_gate()


@pytest.mark.asyncio
async def test_g_t2_03_healthy_canonical_path_gate_runtime() -> None:
    """G-T2-03 (runtime): healthy specs and execute_turn do not routine-hit NEA."""
    _conv.test_g_conv_02_healthy_bootstrap_gate_runtime_specs()
    await _conv.test_g_conv_02_healthy_bootstrap_no_routine_no_eligible_on_execute_turn()
    await _final.test_g_final_02_healthy_canonical_paths_runtime_bootstrap_on()


def test_g_t2_03_healthy_canonical_path_gate_bounded_http(
    client_bootstrap_on,
    auth_headers_bootstrap_on,
) -> None:
    """G-T2-03 (Writers-Room / Improvement): healthy bootstrap-on HTTP paths route."""
    _conv.test_bounded_specs_cover_writers_room_and_improvement_surfaces()
    _final.test_g_final_02_healthy_canonical_paths_writers_room_bootstrap_on(
        client_bootstrap_on, auth_headers_bootstrap_on
    )
    _final.test_g_final_02_healthy_canonical_paths_improvement_bootstrap_on(
        client_bootstrap_on, auth_headers_bootstrap_on
    )


def test_g_t2_08_documentation_truth_gate() -> None:
    """G-T2-08: Task 2 docs and architecture cross-references list every G-T2 id."""
    task2_docs = (
        "area2_task2_closure_gates.md",
        "area2_registry_routing_convergence_closure_report.md",
    )
    crossref_docs = (
        "llm_slm_role_stratification.md",
        "ai_story_contract.md",
        "area2_convergence_gates.md",
        "area2_final_closure_gates.md",
    )
    for name in task2_docs + crossref_docs:
        path = REPO_ROOT / "docs" / "architecture" / name
        assert path.is_file(), f"missing architecture doc {name}"
        text = path.read_text(encoding="utf-8")
        for n in range(1, 9):
            assert f"G-T2-{n:02d}" in text, f"{name} missing G-T2-{n:02d}"
        assert "area2_routing_authority" in text, f"{name} must reference area2_routing_authority"
