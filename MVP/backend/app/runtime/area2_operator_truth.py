"""Area 2 — compact operator truth derived only from existing facts + explicit counts."""

from __future__ import annotations

from typing import Any

from app.runtime.area2_operational_state import (
    Area2OperationalState,
    classify_area2_operational_state,
    pytest_session_active,
    rollup_no_eligible_discipline_for_bounded_traces,
)
from app.runtime.area2_startup_profiles import resolve_startup_profile
from app.runtime.model_inventory_contract import InventorySurface
from app.runtime.model_inventory_report import validate_surface_coverage
from app.runtime.model_routing_contracts import RouteReasonCode
from app.runtime.operator_audit import (
    RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS,
    primary_concern_code,
)

# Stable cross-surface comparison grammar for operator-facing payloads (increment on breaking shape changes).
AREA2_OPERATOR_COMPARISON_GRAMMAR_VERSION = "area2_operator_comparison_v1"

# Mandatory keys on ``area2_operator_truth["compact_operator_comparison"]`` (all three surfaces).
COMPACT_OPERATOR_COMPARISON_KEYS: frozenset = frozenset(
    {
        "grammar_version",
        "surface",
        "authority_source",
        "startup_profile",
        "operational_state",
        "route_status",
        "primary_operational_concern",
        "no_eligible_operator_meaning",
        "policy_execution_comparison",
        "selected_vs_executed",
        "stage_outcome_briefs",
        "runtime_path_summary",
    }
)

NO_ELIGIBLE_OPERATOR_MEANING_KEYS: frozenset = frozenset(
    {
        "applicable",
        "operator_meaning_token",
        "discipline_worst_case",
        "stages_reporting_no_eligible_adapter",
    }
)

POLICY_EXECUTION_COMPARISON_KEYS: frozenset = frozenset({"posture", "per_stage"})

# Frozen summary aligned with AREA2_AUTHORITY_REGISTRY narrative (no runtime probe).
_CANONICAL_TASK2A_AUTHORITY_SUMMARY = (
    "Authoritative Task 2A policy: app.runtime.model_routing.route_model. "
    "Runtime uses adapter_registry model specs when specs=None; Writers-Room and Improvement "
    "use writers_room_model_routing (story_runtime_core.model_registry rows). "
    "ai_stack LangGraph RoutingPolicy is compatibility-only, not canonical for these HTTP paths."
)


def _derive_route_status(
    *,
    operational_state: Area2OperationalState,
    no_eligible_rollup: dict[str, Any],
    stages_with_no_eligible_adapter: list[str],
) -> str:
    """Single deterministic routing health label derived from classification + trace rollups."""

    worst = "not_applicable"
    if isinstance(no_eligible_rollup, dict):
        w = no_eligible_rollup.get("rollup_worst_case")
        if isinstance(w, str) and w:
            worst = w

    if operational_state is Area2OperationalState.test_isolated:
        return "test_isolated_expected_empty_registry"
    if operational_state is Area2OperationalState.misconfigured:
        return "misconfigured_registry_or_inventory"
    if operational_state is Area2OperationalState.intentionally_degraded:
        return "bootstrap_disabled_intentional_posture"

    if stages_with_no_eligible_adapter:
        if worst == "true_no_eligible_adapter":
            return "no_eligible_on_routed_stage_not_normalized_as_healthy"
        if worst == "intentional_degraded_route":
            return "no_eligible_with_task2e_degrade_on_stage"
        if worst == "bounded_executor_mismatch":
            return "selected_adapter_missing_from_bounded_executor"
        if worst == "test_isolated_empty_registry":
            return "no_eligible_discipline_test_isolated_on_route"
        if worst == "missing_registration_or_specs":
            return "no_eligible_discipline_missing_specs_on_route"
        return "no_eligible_on_routed_stage"

    if worst == "not_applicable":
        return "canonical_route_eligible"
    return f"healthy_process_routing_discipline_{worst}"


def _legibility_startup_profile(bootstrap_enabled: bool | None) -> str | None:
    if bootstrap_enabled is None:
        return None
    return resolve_startup_profile(
        routing_registry_bootstrap=bootstrap_enabled,
        under_pytest=pytest_session_active(),
    ).value


def _selected_executed_summary_runtime(
    traces: list[dict[str, Any]],
    model_routing_trace: dict[str, Any] | None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for t in traces:
        if not isinstance(t, dict):
            continue
        rev = t.get("routing_evidence")
        if not isinstance(rev, dict):
            continue
        sk = str(t.get("stage_id") or "")
        rows.append(
            {
                "stage_key": sk,
                "selected": rev.get("selected_adapter_name"),
                "executed": rev.get("executed_adapter_name"),
                "aligned": rev.get("policy_execution_aligned"),
                "route_reason_code": rev.get("route_reason_code"),
            }
        )
    rollup_code = None
    rollup_sel = None
    rollup_exec = None
    if model_routing_trace and isinstance(model_routing_trace, dict):
        rev2 = model_routing_trace.get("routing_evidence")
        if isinstance(rev2, dict):
            rollup_code = rev2.get("route_reason_code")
            rollup_sel = rev2.get("selected_adapter_name")
            rollup_exec = rev2.get("executed_adapter_name")
    return {
        "per_stage": rows,
        "legacy_roll_up": {
            "route_reason_code": rollup_code,
            "selected_adapter_name": rollup_sel,
            "executed_adapter_name": rollup_exec,
        },
    }


def _selected_executed_summary_bounded(traces: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for t in traces:
        if not isinstance(t, dict):
            continue
        rev = t.get("routing_evidence")
        dec = t.get("decision") if isinstance(t.get("decision"), dict) else {}
        sk = str(t.get("stage_id") or t.get("stage") or "")
        selected = dec.get("selected_adapter_name") if dec else None
        executed = t.get("executed_adapter_name")
        if executed is None and isinstance(rev, dict):
            executed = rev.get("executed_adapter_name")
        aligned = rev.get("policy_execution_aligned") if isinstance(rev, dict) else None
        code = dec.get("route_reason_code") if dec else None
        if code is None and isinstance(rev, dict):
            code = rev.get("route_reason_code")
        rows.append(
            {
                "stage_key": sk,
                "selected": selected,
                "executed": executed,
                "aligned": aligned,
                "route_reason_code": code,
            }
        )
    return {"per_stage": rows}


def _runtime_canonical_coverage(specs: list[Any]) -> tuple[dict[str, bool], bool]:
    r = validate_surface_coverage(specs, InventorySurface.runtime_staged)
    return {InventorySurface.runtime_staged.value: r.all_satisfied}, r.all_satisfied


def _runtime_ranking_summary_from_orchestration(
    summary: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Compact ranking legibility from staged ``runtime_orchestration_summary`` only (no invented values)."""
    if not summary or not isinstance(summary, dict):
        return None
    if not any(k in summary for k in RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS):
        return None
    return {k: summary.get(k) for k in RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS}


def _bounded_canonical_coverage(specs: list[Any]) -> tuple[dict[str, bool], bool]:
    wr = validate_surface_coverage(specs, InventorySurface.writers_room)
    imp = validate_surface_coverage(specs, InventorySurface.improvement_bounded)
    m = {
        InventorySurface.writers_room.value: wr.all_satisfied,
        InventorySurface.improvement_bounded.value: imp.all_satisfied,
    }
    return m, wr.all_satisfied and imp.all_satisfied


def _comparison_trace_rows(
    *,
    surface: str,
    traces_rt: list[dict[str, Any]],
    traces_bd: list[dict[str, Any]],
    model_routing_trace: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Traces used for compact comparison rows (includes legacy rollup-only runtime)."""
    if surface == "runtime":
        if traces_rt:
            return traces_rt
        if model_routing_trace and isinstance(model_routing_trace, dict):
            rev = model_routing_trace.get("routing_evidence")
            if isinstance(rev, dict) and rev:
                return [
                    {
                        "stage_id": "legacy_single_route",
                        "routing_evidence": rev,
                        "decision": model_routing_trace.get("decision"),
                    }
                ]
        return []
    return traces_bd


def _unified_selected_vs_executed_for_comparison(selected_executed: dict[str, Any]) -> dict[str, Any]:
    """Same ``per_stage`` + ``legacy_roll_up`` shape on every surface (bounded uses null rollup)."""
    per_stage = selected_executed.get("per_stage")
    if not isinstance(per_stage, list):
        per_stage = []
    roll = selected_executed.get("legacy_roll_up")
    if isinstance(roll, dict):
        rollup = {
            "route_reason_code": roll.get("route_reason_code"),
            "selected_adapter_name": roll.get("selected_adapter_name"),
            "executed_adapter_name": roll.get("executed_adapter_name"),
        }
    else:
        rollup = {"route_reason_code": None, "selected_adapter_name": None, "executed_adapter_name": None}
    return {"per_stage": per_stage, "legacy_roll_up": rollup}


def _routing_evidence_for_row(trace: dict[str, Any]) -> dict[str, Any]:
    rev = trace.get("routing_evidence")
    return rev if isinstance(rev, dict) else {}


def _policy_execution_rows(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for t in traces:
        if not isinstance(t, dict):
            continue
        sk = str(t.get("stage_id") or t.get("stage") or "")
        rev = _routing_evidence_for_row(t)
        dec = t.get("decision") if isinstance(t.get("decision"), dict) else {}
        if not rev and not dec:
            continue
        aligned = rev.get("policy_execution_aligned") if rev else None
        ed = rev.get("execution_deviation") if rev else None
        has_dev = isinstance(ed, dict) and bool(ed)
        rows.append(
            {
                "stage_key": sk,
                "policy_execution_aligned": aligned,
                "has_execution_deviation": has_dev,
            }
        )
    return rows


def _derive_policy_execution_posture(rows: list[dict[str, Any]]) -> str:
    """Deterministic posture from existing alignment and deviation flags only."""
    if not rows:
        return "not_applicable"
    any_true = False
    any_false = False
    any_dev = False
    any_known_align = False
    for r in rows:
        a = r.get("policy_execution_aligned")
        if a is True:
            any_true = True
            any_known_align = True
        elif a is False:
            any_false = True
            any_known_align = True
        if r.get("has_execution_deviation"):
            any_dev = True
    if not any_known_align and not any_dev:
        return "unknown"
    if any_dev or any_false:
        if any_true:
            return "mixed"
        return "misaligned"
    if any_true:
        return "aligned"
    return "unknown"


def _stage_outcome_briefs(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in traces:
        if not isinstance(t, dict):
            continue
        sk = str(t.get("stage_id") or t.get("stage") or "")
        rev = _routing_evidence_for_row(t)
        dov = rev.get("diagnostics_overview") if rev else None
        summary = None
        if isinstance(dov, dict):
            s = dov.get("summary")
            if isinstance(s, str) and s.strip():
                summary = s
        code = rev.get("route_reason_code") if rev else None
        if summary is None and code is not None:
            summary = str(code)
        if sk or summary is not None or code is not None:
            out.append(
                {
                    "stage_key": sk,
                    "outcome_summary": summary,
                    "route_reason_code": str(code) if code is not None else None,
                }
            )
    return out


def _explicit_runtime_path_summary(
    *,
    surface: str,
    runtime_orchestration_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """Ranking/Task-1 path fields: values on runtime when present, explicit nulls on bounded surfaces."""
    keys = RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS
    if surface != "runtime":
        return {k: None for k in keys}
    summary = runtime_orchestration_summary if isinstance(runtime_orchestration_summary, dict) else {}
    return {k: summary.get(k) for k in keys}


def _no_eligible_operator_meaning(
    *,
    operational_state: Area2OperationalState,
    discipline: dict[str, Any],
    stages_nea: list[str],
) -> dict[str, Any]:
    worst = "not_applicable"
    if isinstance(discipline, dict):
        w = discipline.get("rollup_worst_case")
        if isinstance(w, str) and w:
            worst = w

    token = "no_no_eligible_operator_concern_on_compact_view"
    if operational_state is Area2OperationalState.test_isolated:
        token = "operational_test_isolated_empty_registry_expected"
    elif operational_state is Area2OperationalState.misconfigured:
        token = "operational_misconfigured_registry_or_inventory"
    elif operational_state is Area2OperationalState.intentionally_degraded:
        token = "operational_bootstrap_disabled_intentional"
    elif stages_nea:
        if worst == "true_no_eligible_adapter":
            token = "routing_true_no_eligible_adapter_on_stage"
        elif worst == "intentional_degraded_route":
            token = "routing_no_eligible_with_task2e_degrade"
        elif worst == "bounded_executor_mismatch":
            token = "routing_bounded_executor_mismatch"
        elif worst == "test_isolated_empty_registry":
            token = "routing_no_eligible_test_isolated_discipline"
        elif worst == "missing_registration_or_specs":
            token = "routing_no_eligible_missing_specs"
        else:
            token = "routing_no_eligible_on_stage_other_discipline"
    elif worst != "not_applicable":
        token = "routing_discipline_signal_without_staged_no_eligible_list"

    applicable = (
        operational_state is not Area2OperationalState.healthy
        or bool(stages_nea)
        or (worst != "not_applicable")
    )

    return {
        "applicable": applicable,
        "operator_meaning_token": token,
        "discipline_worst_case": worst if worst != "not_applicable" else None,
        "stages_reporting_no_eligible_adapter": list(stages_nea),
    }


def _build_compact_operator_comparison(
    *,
    surface: str,
    authority_source: str,
    bootstrap_enabled: bool | None,
    operational_state: Area2OperationalState,
    route_status: str,
    primary_operational_concern: str | None,
    discipline: dict[str, Any],
    stages_nea: list[str],
    selected_executed: dict[str, Any],
    traces_rt: list[dict[str, Any]],
    traces_bd: list[dict[str, Any]],
    model_routing_trace: dict[str, Any] | None,
    runtime_orchestration_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """Single structured object for cross-surface operator comparison (derived-only)."""
    comp_tr = _comparison_trace_rows(
        surface=surface,
        traces_rt=traces_rt,
        traces_bd=traces_bd,
        model_routing_trace=model_routing_trace,
    )
    pe_rows = _policy_execution_rows(comp_tr)
    return {
        "grammar_version": AREA2_OPERATOR_COMPARISON_GRAMMAR_VERSION,
        "surface": surface,
        "authority_source": authority_source,
        "startup_profile": _legibility_startup_profile(bootstrap_enabled),
        "operational_state": operational_state.value,
        "route_status": route_status,
        "primary_operational_concern": primary_operational_concern,
        "no_eligible_operator_meaning": _no_eligible_operator_meaning(
            operational_state=operational_state,
            discipline=discipline,
            stages_nea=stages_nea,
        ),
        "policy_execution_comparison": {
            "posture": _derive_policy_execution_posture(pe_rows),
            "per_stage": pe_rows,
        },
        "selected_vs_executed": _unified_selected_vs_executed_for_comparison(selected_executed),
        "stage_outcome_briefs": _stage_outcome_briefs(comp_tr),
        "runtime_path_summary": _explicit_runtime_path_summary(
            surface=surface,
            runtime_orchestration_summary=runtime_orchestration_summary,
        ),
    }


def build_area2_operator_truth(
    *,
    surface: str,
    authority_source: str,
    bootstrap_enabled: bool | None,
    registry_model_spec_count: int,
    specs_for_coverage: list[Any] | None,
    runtime_stage_traces: list[dict[str, Any]] | None = None,
    model_routing_trace: dict[str, Any] | None = None,
    bounded_traces: list[dict[str, Any]] | None = None,
    runtime_orchestration_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble additive ``area2_operator_truth`` for operator_audit (English keys only)."""

    traces_rt = [t for t in (runtime_stage_traces or []) if isinstance(t, dict)]
    traces_bd = [t for t in (bounded_traces or []) if isinstance(t, dict)]
    active = traces_rt if traces_rt else traces_bd

    coverage_map: dict[str, bool] = {}
    all_sat: bool | None = None
    if specs_for_coverage is not None:
        if surface == "runtime":
            coverage_map, all_sat = _runtime_canonical_coverage(specs_for_coverage)
        elif surface in ("writers_room", "improvement"):
            coverage_map, all_sat = _bounded_canonical_coverage(specs_for_coverage)
        else:
            all_sat = None

    operational_state = classify_area2_operational_state(
        bootstrap_enabled=bootstrap_enabled,
        registry_model_spec_count=registry_model_spec_count,
        canonical_surfaces_all_satisfied=all_sat,
    )

    pcc = primary_concern_code(
        traces=active,
        model_routing_trace=model_routing_trace if surface == "runtime" else None,
    )

    no_eligible_stages = [
        str(t.get("stage_id") or t.get("stage") or "")
        for t in active
        if isinstance(t, dict)
        and (
            (isinstance(t.get("decision"), dict) and t["decision"].get("route_reason_code") == RouteReasonCode.no_eligible_adapter.value)
            or (
                isinstance(t.get("routing_evidence"), dict)
                and t["routing_evidence"].get("route_reason_code") == RouteReasonCode.no_eligible_adapter.value
            )
        )
    ]

    discipline = rollup_no_eligible_discipline_for_bounded_traces(
        active,
        registry_spec_count=registry_model_spec_count,
    )

    if surface == "runtime":
        selected_executed = _selected_executed_summary_runtime(traces_rt, model_routing_trace)
    else:
        selected_executed = _selected_executed_summary_bounded(traces_bd)

    stages_nea = [s for s in no_eligible_stages if s]
    route_status = _derive_route_status(
        operational_state=operational_state,
        no_eligible_rollup=discipline,
        stages_with_no_eligible_adapter=stages_nea,
    )
    legibility = {
        "authority_source": authority_source,
        "operational_state": operational_state.value,
        "route_status": route_status,
        "selected_vs_executed": selected_executed,
        "primary_operational_concern": pcc,
        "startup_profile": _legibility_startup_profile(bootstrap_enabled),
        "runtime_ranking_summary": (
            _runtime_ranking_summary_from_orchestration(runtime_orchestration_summary)
            if surface == "runtime"
            else None
        ),
    }

    compact_operator_comparison = _build_compact_operator_comparison(
        surface=surface,
        authority_source=authority_source,
        bootstrap_enabled=bootstrap_enabled,
        operational_state=operational_state,
        route_status=route_status,
        primary_operational_concern=pcc,
        discipline=discipline,
        stages_nea=stages_nea,
        selected_executed=selected_executed,
        traces_rt=traces_rt,
        traces_bd=traces_bd,
        model_routing_trace=model_routing_trace if surface == "runtime" else None,
        runtime_orchestration_summary=runtime_orchestration_summary if surface == "runtime" else None,
    )

    return {
        "surface": surface,
        "authority_source": authority_source,
        "bootstrap_enabled": bootstrap_enabled,
        "registry_model_spec_count": registry_model_spec_count,
        "route_coverage_state": coverage_map,
        "canonical_surfaces_all_satisfied": all_sat,
        "selected_vs_executed": selected_executed,
        "primary_operational_concern": pcc,
        "operational_state": operational_state.value,
        "no_eligible_discipline": discipline,
        "stages_with_no_eligible_adapter": stages_nea,
        "canonical_authority_summary": _CANONICAL_TASK2A_AUTHORITY_SUMMARY,
        "legibility": legibility,
        "compact_operator_comparison": compact_operator_comparison,
    }


def merge_area2_operator_truth(audit: dict[str, Any], truth: dict[str, Any]) -> None:
    """Attach truth to an existing operator_audit dict in place."""
    audit["area2_operator_truth"] = truth


def resolve_routing_bootstrap_enabled() -> bool | None:
    """Read ``ROUTING_REGISTRY_BOOTSTRAP`` when a Flask app context exists."""
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            return bool(current_app.config.get("ROUTING_REGISTRY_BOOTSTRAP", True))
    except Exception:
        return None
    return None


def enrich_operator_audit_with_area2_truth(
    audit: dict[str, Any],
    *,
    surface: str,
    authority_source: str,
    bootstrap_enabled: bool | None,
    registry_model_spec_count: int,
    specs_for_coverage: list[Any] | None,
    runtime_stage_traces: list[dict[str, Any]] | None = None,
    model_routing_trace: dict[str, Any] | None = None,
    bounded_traces: list[dict[str, Any]] | None = None,
    runtime_orchestration_summary: dict[str, Any] | None = None,
) -> None:
    """Populate ``area2_operator_truth`` on an existing operator_audit dict."""
    truth = build_area2_operator_truth(
        surface=surface,
        authority_source=authority_source,
        bootstrap_enabled=bootstrap_enabled,
        registry_model_spec_count=registry_model_spec_count,
        specs_for_coverage=specs_for_coverage,
        runtime_stage_traces=runtime_stage_traces,
        model_routing_trace=model_routing_trace,
        bounded_traces=bounded_traces,
        runtime_orchestration_summary=runtime_orchestration_summary,
    )
    merge_area2_operator_truth(audit, truth)


def bounded_traces_from_task_2a_routing(task_2a_routing: dict[str, Any]) -> list[dict[str, Any]]:
    """Ordered preflight/synthesis trace dicts from a ``task_2a_routing`` map."""
    out: list[dict[str, Any]] = []
    for key in ("preflight", "synthesis"):
        e = task_2a_routing.get(key)
        if isinstance(e, dict):
            out.append(e)
    return out
