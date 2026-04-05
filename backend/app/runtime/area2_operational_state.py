"""Area 2 — deterministic operational/bootstrap state and no-eligible discipline."""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

from app.runtime.model_routing_contracts import RouteReasonCode


class Area2OperationalState(str, Enum):
    """Process-level operational/bootstrap health for Area 2 (mutually exclusive)."""

    healthy = "healthy"
    intentionally_degraded = "intentionally_degraded"
    misconfigured = "misconfigured"
    test_isolated = "test_isolated"


class NoEligibleDiscipline(str, Enum):
    """Classification when routing hits ``no_eligible_adapter`` or adjacent skips (orthogonal to ops state)."""

    not_applicable = "not_applicable"
    missing_registration_or_specs = "missing_registration_or_specs"
    true_no_eligible_adapter = "true_no_eligible_adapter"
    intentional_degraded_route = "intentional_degraded_route"
    test_isolated_empty_registry = "test_isolated_empty_registry"
    bounded_executor_mismatch = "bounded_executor_mismatch"


def pytest_session_active() -> bool:
    """True when running under pytest (empty registry may be expected)."""
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def classify_no_eligible_discipline(
    *,
    route_reason_code: str | None,
    registry_spec_count: int,
    degradation_applied: bool,
    bounded_model_call: bool | None = None,
    skip_reason: str | None = None,
    selected_adapter_name: str | None = None,
) -> NoEligibleDiscipline:
    """Map a no-eligible (or related) outcome to a discipline label."""
    sr = (skip_reason or "").lower()
    sel = (selected_adapter_name or "").strip()
    if bounded_model_call is False and "missing_provider" in sr and sel:
        return NoEligibleDiscipline.bounded_executor_mismatch

    code = (route_reason_code or "").strip()
    if code != RouteReasonCode.no_eligible_adapter.value:
        return NoEligibleDiscipline.not_applicable

    if pytest_session_active() and registry_spec_count == 0:
        return NoEligibleDiscipline.test_isolated_empty_registry
    if registry_spec_count == 0:
        return NoEligibleDiscipline.missing_registration_or_specs
    if degradation_applied:
        return NoEligibleDiscipline.intentional_degraded_route
    return NoEligibleDiscipline.true_no_eligible_adapter


def classify_area2_operational_state(
    *,
    bootstrap_enabled: bool | None,
    registry_model_spec_count: int,
    canonical_surfaces_all_satisfied: bool | None,
) -> Area2OperationalState:
    """Derive a single Area2OperationalState from explicit facts (no telemetry).

    Note: Task 2E ``degradation_applied`` on a healthy route is normal (pool widen) and does
    not imply this enum's ``intentionally_degraded``; use ``NoEligibleDiscipline`` for
    routing-level degradation semantics.
    """

    if pytest_session_active() and bootstrap_enabled is False:
        return Area2OperationalState.test_isolated

    if bootstrap_enabled is True:
        if registry_model_spec_count == 0:
            return Area2OperationalState.misconfigured
        if canonical_surfaces_all_satisfied is False:
            return Area2OperationalState.misconfigured
        return Area2OperationalState.healthy

    if bootstrap_enabled is False:
        return Area2OperationalState.intentionally_degraded

    if registry_model_spec_count == 0:
        return Area2OperationalState.misconfigured
    if canonical_surfaces_all_satisfied is False:
        return Area2OperationalState.misconfigured
    return Area2OperationalState.healthy


def collect_degradation_applied_from_traces(traces: list[dict[str, Any]]) -> bool:
    """True if any stage trace decision sets degradation_applied."""
    for t in traces:
        if not isinstance(t, dict):
            continue
        dec = t.get("decision")
        if isinstance(dec, dict) and dec.get("degradation_applied") is True:
            return True
    return False


def collect_no_eligible_stages(traces: list[dict[str, Any]]) -> list[str]:
    """Stage keys where route_reason_code is no_eligible_adapter."""
    out: list[str] = []
    for t in traces:
        if not isinstance(t, dict):
            continue
        dec = t.get("decision")
        rev = t.get("routing_evidence")
        code = None
        if isinstance(dec, dict):
            code = dec.get("route_reason_code")
        if code is None and isinstance(rev, dict):
            code = rev.get("route_reason_code")
        if code == RouteReasonCode.no_eligible_adapter.value:
            sk = str(t.get("stage_id") or t.get("stage") or "")
            if sk:
                out.append(sk)
    return out


_NO_ELIGIBLE_SEVERITY_RANK: dict[NoEligibleDiscipline, int] = {
    NoEligibleDiscipline.not_applicable: 0,
    NoEligibleDiscipline.test_isolated_empty_registry: 1,
    NoEligibleDiscipline.intentional_degraded_route: 2,
    NoEligibleDiscipline.true_no_eligible_adapter: 3,
    NoEligibleDiscipline.bounded_executor_mismatch: 4,
    NoEligibleDiscipline.missing_registration_or_specs: 5,
}


def rollup_no_eligible_discipline_for_bounded_traces(
    traces: list[dict[str, Any]],
    *,
    registry_spec_count: int,
) -> dict[str, Any]:
    """Compact discipline view for preflight/synthesis-style traces."""
    worst = NoEligibleDiscipline.not_applicable

    per_stage: list[dict[str, Any]] = []
    for t in traces:
        if not isinstance(t, dict):
            continue
        dec = t.get("decision") if isinstance(t.get("decision"), dict) else {}
        code = dec.get("route_reason_code")
        deg = bool(dec.get("degradation_applied"))
        stage = str(t.get("stage_id") or t.get("stage") or "")
        sel = dec.get("selected_adapter_name")
        sel_str = str(sel) if sel is not None else ""
        disc = classify_no_eligible_discipline(
            route_reason_code=str(code) if code is not None else None,
            registry_spec_count=registry_spec_count,
            degradation_applied=deg,
            bounded_model_call=t.get("bounded_model_call") if "bounded_model_call" in t else None,
            skip_reason=str(t.get("skip_reason") or "") or None,
            selected_adapter_name=sel_str or None,
        )
        per_stage.append({"stage": stage, "discipline": disc.value})
        if _NO_ELIGIBLE_SEVERITY_RANK[disc] > _NO_ELIGIBLE_SEVERITY_RANK[worst]:
            worst = disc

    return {
        "rollup_worst_case": worst.value,
        "per_stage": per_stage,
    }
