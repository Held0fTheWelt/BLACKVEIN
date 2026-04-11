"""Deterministic registry inventory and surface coverage validation (Task 2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.runtime import adapter_registry
from app.runtime.model_inventory_contract import (
    InventorySurface,
    RequiredRoutingTuple,
    requirements_for_surface,
)
from app.runtime.model_routing import route_model
from app.runtime.model_routing_contracts import (
    AdapterModelSpec,
    RouteReasonCode,
    RoutingRequest,
)


class SetupClassification(str, Enum):
    """Coarse classification for operator/debug views; not telemetry."""

    intentional_degraded_route = "intentional_degraded_route"
    missing_registration_or_specs = "missing_registration_or_specs"
    true_no_eligible_adapter = "true_no_eligible_adapter"


@dataclass(slots=True)
class RegistryInventoryEntry:
    adapter_name: str
    has_legacy_instance: bool
    has_model_spec: bool
    stale_spec_risk: bool


@dataclass(slots=True)
class RegistryInventoryReport:
    entries: list[RegistryInventoryEntry]
    legacy_names_without_spec: list[str]


def report_registry_inventory() -> RegistryInventoryReport:
    """Snapshot legacy registrations and spec presence (deterministic name order)."""

    legacy_names, spec_names = adapter_registry.snapshot_registry_keys()
    all_names = sorted(set(legacy_names) | set(spec_names))
    entries: list[RegistryInventoryEntry] = []
    legacy_only: list[str] = []
    for name in all_names:
        has_legacy = name in legacy_names
        has_spec = name in spec_names
        stale_risk = has_legacy and not has_spec
        if has_legacy and not has_spec:
            legacy_only.append(name)
        entries.append(
            RegistryInventoryEntry(
                adapter_name=name,
                has_legacy_instance=has_legacy,
                has_model_spec=has_spec,
                stale_spec_risk=stale_risk,
            )
        )
    return RegistryInventoryReport(entries=entries, legacy_names_without_spec=legacy_only)


@dataclass(slots=True)
class TupleCoverageResult:
    required: RequiredRoutingTuple
    satisfied: bool
    selected_adapter_if_routed: str


@dataclass(slots=True)
class SurfaceCoverageReport:
    surface: InventorySurface
    tuple_results: list[TupleCoverageResult]
    all_satisfied: bool


def validate_surface_coverage(
    specs: list[AdapterModelSpec],
    surface: InventorySurface,
) -> SurfaceCoverageReport:
    """Check whether ``specs`` cover each required tuple for ``surface``."""

    results: list[TupleCoverageResult] = []
    for req in requirements_for_surface(surface):
        rr = RoutingRequest(
            workflow_phase=req.workflow_phase,
            task_kind=req.task_kind,
            requires_structured_output=req.requires_structured_output,
        )
        decision = route_model(rr, specs=specs)
        satisfied = decision.route_reason_code != RouteReasonCode.no_eligible_adapter
        results.append(
            TupleCoverageResult(
                required=req,
                satisfied=satisfied,
                selected_adapter_if_routed=decision.selected_adapter_name,
            )
        )
    return SurfaceCoverageReport(
        surface=surface,
        tuple_results=results,
        all_satisfied=all(r.satisfied for r in results),
    )


def classify_no_eligible_setup(
    *,
    registry_spec_count: int,
) -> SetupClassification:
    """Distinguish empty registry (setup gap) from honest policy exhaustion.

    Call only when ``route_reason_code == no_eligible_adapter``.
    """

    if registry_spec_count == 0:
        return SetupClassification.missing_registration_or_specs
    return SetupClassification.true_no_eligible_adapter


def classify_policy_degradation(*, degradation_applied: bool) -> SetupClassification | None:
    """Return intentional degraded path when policy flagged degradation; else None."""

    if degradation_applied:
        return SetupClassification.intentional_degraded_route
    return None


def inventory_summary_dict() -> dict[str, Any]:
    """Compact JSON-friendly summary for tests or debug payloads."""

    inv = report_registry_inventory()
    return {
        "adapter_names": [e.adapter_name for e in inv.entries],
        "legacy_without_spec": list(inv.legacy_names_without_spec),
        "model_spec_count": len(adapter_registry.iter_model_specs()),
    }
