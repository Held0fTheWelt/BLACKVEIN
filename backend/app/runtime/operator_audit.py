"""Task 3: deterministic operator audit views derived from existing evidence only.

Adds ``audit_*`` structures alongside ``routing_evidence`` and Task 2F ``diagnostics_*``.
Does not change routing policy, adapter behavior, or guard semantics.
"""

from __future__ import annotations

from typing import Any

AUDIT_SCHEMA_VERSION = "1"

# Mirrored from ``runtime_orchestration_summary`` for compact operator_audit (canonical staged Runtime).
RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS: tuple[str, ...] = (
    "ranking_effect",
    "ranking_bounded_model_call",
    "ranking_suppressed_for_slm_only",
    "ranking_no_eligible_adapter",
)

_SEVERITY_RANK = {"normal": 0, "elevated": 1, "degraded": 2, "failed_selection": 3}

# First matching code wins when scanning merged diagnostics_causes from traces (deterministic).
_PRIMARY_CONCERN_PRIORITY: tuple[str, ...] = (
    "execution_deviation",
    "no_eligible_spec",
    "bounded_call_skipped",
    "structured_output_gap",
    "explicit_hint_present",
    "preferred_pool_empty",
    "preferred_pool_widened",
    "mandatory_llm_pool_applied",
    "counterfactual_latency_changed",
    "counterfactual_cost_changed",
    "escalation_trigger",
)

_PACKAGING_STAGE_IDS = frozenset({"packaging"})


def _severity_max(a: str | None, b: str | None) -> str:
    if not a:
        return b or "normal"
    if not b:
        return a
    ra = _SEVERITY_RANK.get(a, 0)
    rb = _SEVERITY_RANK.get(b, 0)
    return a if ra >= rb else b


def _routing_evidence_from_trace(trace: dict[str, Any]) -> dict[str, Any]:
    rev = trace.get("routing_evidence")
    return rev if isinstance(rev, dict) else {}


def runtime_additive_orchestration_fields(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Additive orchestration summary keys; legacy ``stages_skipped`` unchanged.

    Separates packaging (no model call by design) from routing skips (no eligible adapter).
    """
    packaging_ids: list[str] = []
    skipped_no_adapter: list[str] = []
    for t in traces:
        if not isinstance(t, dict):
            continue
        sid = str(t.get("stage_id") or "")
        sk = t.get("stage_kind")
        is_packaging = sid in _PACKAGING_STAGE_IDS or sk == "packaging"
        if is_packaging:
            if sid:
                packaging_ids.append(sid)
            else:
                packaging_ids.append("packaging")
            continue
        if t.get("bounded_model_call"):
            continue
        sr_raw = t.get("skip_reason")
        sr = str(sr_raw).lower() if sr_raw is not None else ""
        if "no_eligible" in sr:
            if sid:
                skipped_no_adapter.append(sid)
    return {
        "stages_without_bounded_model_call_by_design": packaging_ids,
        "stages_skipped_no_eligible_adapter": skipped_no_adapter,
    }


def build_audit_timeline_entry(ordinal: int, trace: dict[str, Any]) -> dict[str, Any]:
    sk = str(trace.get("stage_id") or trace.get("stage") or "")
    rev = _routing_evidence_from_trace(trace)
    dov_raw = rev.get("diagnostics_overview")
    dov = dov_raw if isinstance(dov_raw, dict) else {}
    err_list = trace.get("errors") if isinstance(trace.get("errors"), list) else []
    stage_kind = trace.get("stage_kind")
    if stage_kind is None and sk == "packaging":
        stage_kind = "packaging"
    if stage_kind is None and sk:
        stage_kind = "routed_model_stage"
    if stage_kind is None:
        stage_kind = "unknown"
    return {
        "ordinal": ordinal,
        "stage_key": sk,
        "stage_kind": stage_kind,
        "bounded_model_call": trace.get("bounded_model_call"),
        "skip_reason": trace.get("skip_reason"),
        "route_reason_code": rev.get("route_reason_code"),
        "diagnostics_route_class": dov.get("summary"),
        "diagnostics_severity": dov.get("severity"),
        "error_count": len(err_list),
    }


def collect_audit_deviations(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in traces:
        if not isinstance(t, dict):
            continue
        rev = _routing_evidence_from_trace(t)
        ed = rev.get("execution_deviation")
        if isinstance(ed, dict) and ed:
            sk = str(t.get("stage_id") or t.get("stage") or "")
            out.append({"stage_key": sk, "execution_deviation": dict(ed)})
    return out


def rollup_diagnostics_flags(traces: list[dict[str, Any]]) -> dict[str, Any]:
    acc: dict[str, Any] = {}
    for t in traces:
        if not isinstance(t, dict):
            continue
        rev = _routing_evidence_from_trace(t)
        df = rev.get("diagnostics_flags")
        if not isinstance(df, dict):
            continue
        for k, v in df.items():
            if isinstance(v, bool) and v:
                acc[k] = True
            elif k not in acc and v is not None and not isinstance(v, bool):
                acc[k] = v
    return acc


def _max_severity_from_evidence_dict(rev: dict[str, Any]) -> str | None:
    dov = rev.get("diagnostics_overview")
    if isinstance(dov, dict):
        sev = dov.get("severity")
        if isinstance(sev, str):
            return sev
    return None


def max_diagnostics_severity_across_traces(
    traces: list[dict[str, Any]],
    model_routing_trace: dict[str, Any] | None,
) -> str:
    best = "normal"
    for t in traces:
        if not isinstance(t, dict):
            continue
        rev = _routing_evidence_from_trace(t)
        s = _max_severity_from_evidence_dict(rev)
        if s:
            best = _severity_max(best, s)
    if model_routing_trace and isinstance(model_routing_trace, dict):
        rev2 = model_routing_trace.get("routing_evidence")
        if isinstance(rev2, dict):
            s2 = _max_severity_from_evidence_dict(rev2)
            if s2:
                best = _severity_max(best, s2)
    return best


def _collect_ordered_cause_codes(traces: list[dict[str, Any]], model_routing_trace: dict[str, Any] | None) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def consume_rev(rev: dict[str, Any]) -> None:
        causes = rev.get("diagnostics_causes")
        if not isinstance(causes, list):
            return
        for c in causes:
            if not isinstance(c, dict):
                continue
            code = c.get("code")
            if isinstance(code, str) and code not in seen:
                seen.add(code)
                ordered.append(code)

    for t in traces:
        if isinstance(t, dict):
            consume_rev(_routing_evidence_from_trace(t))
    if model_routing_trace and isinstance(model_routing_trace, dict):
        rev = model_routing_trace.get("routing_evidence")
        if isinstance(rev, dict):
            consume_rev(rev)
    return ordered


def primary_concern_code(
    *,
    traces: list[dict[str, Any]],
    model_routing_trace: dict[str, Any] | None,
) -> str | None:
    ordered = _collect_ordered_cause_codes(traces, model_routing_trace)
    ordered_set = set(ordered)
    for pref in _PRIMARY_CONCERN_PRIORITY:
        if pref in ordered_set:
            return pref
    return ordered[0] if ordered else None


def build_audit_review_fingerprint(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "stage_key": e.get("stage_key"),
            "route_reason_code": e.get("route_reason_code"),
            "diagnostics_route_class": e.get("diagnostics_route_class"),
        }
        for e in timeline
    ]
    return sorted(
        rows,
        key=lambda x: (str(x.get("stage_key") or ""), str(x.get("route_reason_code") or "")),
    )


def build_runtime_operator_audit_preempted(
    *,
    reason: str,
    summary_note: Any,
    model_routing_trace: dict[str, Any] | None,
) -> dict[str, Any]:
    traces: list[dict[str, Any]] = []
    if model_routing_trace and isinstance(model_routing_trace, dict):
        rev = model_routing_trace.get("routing_evidence")
        synthetic: dict[str, Any] = {
            "stage_id": "orchestration_preempted",
            "stage_kind": "orchestration_preempted",
            "bounded_model_call": None,
            "skip_reason": None,
            "routing_evidence": rev if isinstance(rev, dict) else {},
            "errors": [],
        }
        traces = [synthetic]
    timeline = [build_audit_timeline_entry(i, t) for i, t in enumerate(traces)]
    max_sev = max_diagnostics_severity_across_traces(traces, model_routing_trace)
    pcc = primary_concern_code(traces=traces, model_routing_trace=model_routing_trace)
    return {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "audit_summary": {
            "surface": "runtime",
            "staged_pipeline_preempted": reason,
            "preempt_reason_detail": summary_note,
            "max_diagnostics_severity": max_sev,
            "primary_concern_code": pcc,
            "note_deep_traces": (
                "Staged runtime pipeline not executed; see model_routing_trace for the single routing decision."
            ),
        },
        "audit_timeline": timeline,
        "audit_deviations": collect_audit_deviations(traces),
        "audit_flags": rollup_diagnostics_flags(traces),
        "audit_review_fingerprint": build_audit_review_fingerprint(timeline),
    }


def build_runtime_operator_audit(
    *,
    runtime_stage_traces: list[dict[str, Any]] | None,
    runtime_orchestration_summary: dict[str, Any] | None,
    model_routing_trace: dict[str, Any] | None,
) -> dict[str, Any]:
    traces = [t for t in (runtime_stage_traces or []) if isinstance(t, dict)]
    summary = runtime_orchestration_summary if isinstance(runtime_orchestration_summary, dict) else {}
    preempted = summary.get("staged_pipeline_preempted")

    if preempted:
        return build_runtime_operator_audit_preempted(
            reason=str(preempted),
            summary_note=summary.get("reason"),
            model_routing_trace=model_routing_trace,
        )

    timeline: list[dict[str, Any]] = []
    if traces:
        for i, t in enumerate(traces):
            timeline.append(build_audit_timeline_entry(i, t))
    elif model_routing_trace and isinstance(model_routing_trace, dict):
        rev = model_routing_trace.get("routing_evidence")
        synthetic = {
            "stage_id": "legacy_single_route",
            "stage_kind": "legacy_single_route",
            "bounded_model_call": None,
            "skip_reason": None,
            "routing_evidence": rev if isinstance(rev, dict) else {},
            "errors": [],
        }
        timeline.append(build_audit_timeline_entry(0, synthetic))

    deviations = collect_audit_deviations(traces) if traces else []
    if not deviations and model_routing_trace and isinstance(model_routing_trace, dict):
        rev = model_routing_trace.get("routing_evidence")
        if isinstance(rev, dict) and rev.get("execution_deviation"):
            deviations = [
                {
                    "stage_key": "legacy_single_route",
                    "execution_deviation": dict(rev["execution_deviation"]),
                }
            ]

    flags = rollup_diagnostics_flags(traces)
    if not traces and model_routing_trace and isinstance(model_routing_trace, dict):
        rev = model_routing_trace.get("routing_evidence")
        if isinstance(rev, dict):
            df = rev.get("diagnostics_flags")
            if isinstance(df, dict):
                flags = {k: v for k, v in df.items() if v}

    trace_input_for_primary = traces
    if not traces and model_routing_trace and isinstance(model_routing_trace, dict):
        rev = model_routing_trace.get("routing_evidence")
        if isinstance(rev, dict):
            trace_input_for_primary = [
                {
                    "stage_id": "legacy_single_route",
                    "routing_evidence": rev,
                    "errors": [],
                }
            ]

    max_sev = max_diagnostics_severity_across_traces(traces, model_routing_trace)
    pcc = primary_concern_code(traces=trace_input_for_primary, model_routing_trace=model_routing_trace)

    gate_reason = summary.get("synthesis_gate_reason") or summary.get("synthesis_skip_reason")

    audit_summary: dict[str, Any] = {
        "surface": "runtime",
        "final_path": summary.get("final_path"),
        "synthesis_skipped": summary.get("synthesis_skipped"),
        "synthesis_gate_reason": gate_reason,
        "max_diagnostics_severity": max_sev,
        "primary_concern_code": pcc,
        "stages_executed_count": len(traces),
        "note_deep_traces": (
            "Authoritative detail: runtime_stage_traces with per-stage routing_evidence; "
            "model_routing_trace is the legacy rollup."
        ),
    }
    for _rk in RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS:
        if _rk in summary:
            audit_summary[_rk] = summary[_rk]

    return {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "audit_summary": audit_summary,
        "audit_timeline": timeline,
        "audit_deviations": deviations,
        "audit_flags": flags,
        "audit_review_fingerprint": build_audit_review_fingerprint(timeline),
    }


def apply_stage_id_alias_to_bounded_traces(task_2a_routing: dict[str, Any]) -> None:
    """Additive ``stage_id`` for cross-surface comparison with Runtime (keeps ``stage``)."""
    for _k, entry in list(task_2a_routing.items()):
        if isinstance(entry, dict) and entry.get("stage") and not entry.get("stage_id"):
            entry["stage_id"] = entry["stage"]


def _bounded_traces_in_order(task_2a_routing: dict[str, Any]) -> list[dict[str, Any]]:
    order = ("preflight", "synthesis")
    out: list[dict[str, Any]] = []
    for key in order:
        e = task_2a_routing.get(key)
        if isinstance(e, dict):
            out.append(e)
    return out


def build_bounded_surface_operator_audit(
    *,
    surface: str,
    task_2a_routing: dict[str, Any],
    execution_hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    apply_stage_id_alias_to_bounded_traces(task_2a_routing)
    traces = [t for t in _bounded_traces_in_order(task_2a_routing) if isinstance(t, dict)]
    timeline = [build_audit_timeline_entry(i, t) for i, t in enumerate(traces)]
    deviations = collect_audit_deviations(traces)
    flags = rollup_diagnostics_flags(traces)
    max_sev = max_diagnostics_severity_across_traces(traces, None)
    pcc = primary_concern_code(traces=traces, model_routing_trace=None)

    interpretation_layer = "absent"
    if traces:
        any_call = any(t.get("bounded_model_call") is True for t in traces)
        any_skip = any(t.get("bounded_model_call") is False for t in traces)
        if any_call:
            interpretation_layer = "model_assisted_calls_present"
        elif any_skip:
            interpretation_layer = "bounded_calls_skipped"

    audit_summary: dict[str, Any] = {
        "surface": surface,
        "max_diagnostics_severity": max_sev,
        "primary_concern_code": pcc,
        "interpretation_layer": interpretation_layer,
        "note_deep_traces": "Per-stage routing_evidence and decision dicts remain authoritative.",
    }
    if execution_hints:
        audit_summary["execution_hints"] = execution_hints

    return {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "audit_summary": audit_summary,
        "audit_timeline": timeline,
        "audit_deviations": deviations,
        "audit_flags": flags,
        "audit_review_fingerprint": build_audit_review_fingerprint(timeline),
    }
