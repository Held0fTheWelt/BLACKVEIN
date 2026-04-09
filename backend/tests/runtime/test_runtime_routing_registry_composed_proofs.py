"""Registry and routing: composed proofs delegating to operational, startup, and cross-surface suites (G-T2-01 … G-T2-08).

Delegated tests are invoked via sibling **modules** (not ``from … import test_foo``) so pytest
does not collect them twice from this file.
"""

from __future__ import annotations

import pytest

from app.runtime.area2_routing_authority import (
    AUTHORITY_SOURCE_IMPROVEMENT,
    AUTHORITY_SOURCE_RUNTIME,
    AUTHORITY_SOURCE_WRITERS_ROOM,
    CanonicalSurface,
    authority_entries_for_surface,
)

from . import test_cross_surface_operator_audit_contract as _xs
from . import test_runtime_operational_bootstrap_and_routing_registry as _conv
from . import test_runtime_startup_profiles_operator_truth as _final
from .doc_test_paths import architecture_style_doc


def _assert_primary_authority_sources_per_surface() -> None:
    """G-T2-01: each canonical surface lists registry entries; spec sources are non-empty."""
    for surf in CanonicalSurface:
        assert authority_entries_for_surface(surf), f"no authority entries for {surf.value}"
    assert AUTHORITY_SOURCE_RUNTIME.strip()
    assert AUTHORITY_SOURCE_WRITERS_ROOM.strip()
    assert AUTHORITY_SOURCE_IMPROVEMENT == AUTHORITY_SOURCE_WRITERS_ROOM


def test_registry_routing_single_authority_across_surfaces() -> None:
    """G-T2-01: singular primary Task 2A policy; explicit non-competing layers in registry."""
    _conv.test_routing_registry_single_authority_policy()
    _final.test_operator_truth_practical_authority_registry()
    _assert_primary_authority_sources_per_surface()


def test_registry_routing_startup_and_state_classification() -> None:
    """G-T2-02: named profiles and operational/bootstrap classification are deterministic."""
    _final.test_startup_profile_bootstrap_facts_reproducible()
    _final.test_startup_profile_operational_state_expectations()
    _conv.test_classify_operational_state_matrix()


def test_registry_routing_no_eligible_discipline_distinct() -> None:
    """G-T2-04: degraded vs misconfigured vs test-isolated vs true no-eligible are distinct."""
    _conv.test_classify_no_eligible_discipline_matrix()
    _final.test_no_eligible_operator_meaning_not_normalized_away()


def test_registry_routing_operator_truth_on_bounded_http(client, auth_headers) -> None:
    """G-T2-05: compact operator truth on bounded HTTP plus legibility derivation."""
    _final.test_operator_truth_legibility_keys_present()
    _xs.test_writers_room_operator_audit_and_routing_evidence_contract(client, auth_headers)


def test_registry_routing_inventory_surfaces_covered() -> None:
    """G-T2-06: inventory surfaces satisfied by bootstrap specs and WR spec builder."""
    _conv.test_bounded_specs_cover_writers_room_and_improvement_surfaces()
    _conv.test_bootstrap_registry_populates_adapter_specs_for_staged_tuples()


def test_registry_routing_legacy_bootstrap_isolation() -> None:
    """G-T2-07: bootstrap-off test isolation and legacy expectations remain intact."""
    _conv.test_bootstrap_off_keeps_registry_empty_in_testing_config()
    _final.test_legacy_bootstrap_off_registry_isolation_preserved()


@pytest.mark.asyncio
async def test_registry_routing_healthy_staged_runtime_paths() -> None:
    """G-T2-03 (runtime): healthy specs and execute_turn do not routine-hit NEA."""
    _conv.test_bootstrap_registry_populates_adapter_specs_for_staged_tuples()
    await _conv.test_execute_turn_with_specs_avoids_routine_no_eligible_adapter()
    await _final.test_runtime_healthy_staged_paths_when_bootstrap_on()


def test_registry_routing_healthy_bounded_http_paths(
    client_bootstrap_on,
    auth_headers_bootstrap_on,
) -> None:
    """G-T2-03 (Writers-Room / Improvement): healthy bootstrap-on HTTP paths route."""
    _conv.test_bounded_specs_cover_writers_room_and_improvement_surfaces()
    _final.test_writers_room_healthy_routes_when_bootstrap_on(
        client_bootstrap_on, auth_headers_bootstrap_on
    )
    _final.test_improvement_healthy_routes_when_bootstrap_on(
        client_bootstrap_on, auth_headers_bootstrap_on
    )


def test_registry_routing_documentation_lists_task2_gate_ids() -> None:
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
        path = architecture_style_doc(name)
        assert path.is_file(), f"missing architecture doc {name}"
        text = path.read_text(encoding="utf-8")
        for n in range(1, 9):
            assert f"G-T2-{n:02d}" in text, f"{name} missing G-T2-{n:02d}"
        assert "area2_routing_authority" in text, f"{name} must reference area2_routing_authority"
