"""Read-only projection services for Inspector timeline/comparison/coverage/provenance views."""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any

from ai_stack.semantic_planner_effect_surface import (
    resolve_dramatic_effect_evaluator,
    support_level_for_module,
)

from app.contracts.inspector_turn_projection import (
    INSPECTOR_COMPARISON_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_COVERAGE_HEALTH_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_PROVENANCE_RAW_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_SECTION_STATUS_SUPPORTED,
    INSPECTOR_TIMELINE_PROJECTION_SCHEMA_VERSION,
    build_inspector_view_projection_root,
    make_supported_section,
    make_unavailable_section,
)
from app.services.ai_stack_evidence_service import build_session_evidence_bundle


def _diagnostics_rows(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics = bundle.get("world_engine_diagnostics")
    if not isinstance(diagnostics, dict):
        return []
    rows = diagnostics.get("diagnostics")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _planner_slice(row: dict[str, Any]) -> dict[str, Any]:
    graph = row.get("graph")
    if isinstance(graph, dict):
        psp = graph.get("planner_state_projection")
        if isinstance(psp, dict):
            return psp
    return {}


def _semantic_move_record(row: dict[str, Any]) -> dict[str, Any] | None:
    sm = row.get("semantic_move_record")
    if isinstance(sm, dict):
        return sm
    ps = _planner_slice(row)
    inner = ps.get("semantic_move_record")
    return inner if isinstance(inner, dict) else None


def _dramatic_review(row: dict[str, Any]) -> dict[str, Any]:
    graph = row.get("graph")
    if not isinstance(graph, dict):
        return {}
    dr = graph.get("dramatic_review")
    return dr if isinstance(dr, dict) else {}


def _visible_narration_fingerprint(row: dict[str, Any]) -> str | None:
    vo = row.get("visible_output_bundle")
    if not isinstance(vo, dict):
        return None
    narr = vo.get("gm_narration")
    if not isinstance(narr, list):
        return None
    parts = [str(x) for x in narr if x is not None]
    if not parts:
        return None
    payload = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


def _build_root(
    *,
    bundle: dict[str, Any],
    session_id: str,
    schema_version: str,
    projection_status: str,
    section_key: str,
    section: dict[str, Any],
) -> dict[str, Any]:
    return build_inspector_view_projection_root(
        schema_version=schema_version,
        trace_id=bundle.get("trace_id"),
        backend_session_id=str(bundle.get("backend_session_id") or session_id),
        world_engine_story_session_id=bundle.get("world_engine_story_session_id"),
        projection_status=projection_status,
        section_key=section_key,
        section=section,
        warnings=list(bundle.get("degraded_path_signals") or []),
        raw_evidence_refs={
            "source": "world_engine_diagnostics_session_bridge",
        },
    )


def _extract_turn_view(row: dict[str, Any], idx: int, *, module_id: Any) -> dict[str, Any]:
    validation = row.get("validation_outcome")
    if not isinstance(validation, dict):
        validation = {}
    gate = validation.get("dramatic_effect_gate_outcome")
    if not isinstance(gate, dict):
        gate = {}
    model_route = row.get("model_route")
    if not isinstance(model_route, dict):
        model_route = {}
    graph = row.get("graph")
    if not isinstance(graph, dict):
        graph = {}

    sm = _semantic_move_record(row)
    move_type = sm.get("move_type") if isinstance(sm, dict) else None
    scene_risk_band = sm.get("scene_risk_band") if isinstance(sm, dict) else None

    trace = gate.get("diagnostic_trace")
    trace_codes: list[str] = []
    if isinstance(trace, list):
        for step in trace[:12]:
            if isinstance(step, dict) and step.get("code") is not None:
                trace_codes.append(str(step.get("code")))

    mid = module_id if isinstance(module_id, str) else ""
    support_level = support_level_for_module(mid).value

    return {
        "turn_index": idx + 1,
        "turn_number": row.get("turn_number") if isinstance(row.get("turn_number"), int) else idx + 1,
        "trace_id": row.get("trace_id"),
        "gate_result": gate.get("gate_result"),
        "validation_status": validation.get("status"),
        "validation_reason": validation.get("reason"),
        "dramatic_effect_weak_signal": validation.get("dramatic_effect_weak_signal"),
        "fallback_path_taken": bool(graph.get("fallback_path_taken") or model_route.get("fallback_stage_reached")),
        "execution_health": graph.get("execution_health"),
        "selected_scene_function": row.get("selected_scene_function"),
        "route_mode": model_route.get("route_mode"),
        "route_reason_code": model_route.get("route_reason_code") or model_route.get("route_reason"),
        "semantic_move_type": move_type,
        "scene_risk_band": scene_risk_band,
        "empty_fluency_risk": gate.get("empty_fluency_risk"),
        "character_plausibility_posture": gate.get("character_plausibility_posture"),
        "continuity_support_posture": gate.get("continuity_support_posture"),
        "continues_or_changes_pressure": gate.get("continues_or_changes_pressure"),
        "supports_scene_function": gate.get("supports_scene_function"),
        "legacy_fallback_used": gate.get("legacy_fallback_used"),
        "effect_rationale_codes": list(gate["effect_rationale_codes"])
        if isinstance(gate.get("effect_rationale_codes"), list)
        else None,
        "gate_diagnostic_trace_codes": trace_codes or None,
        "accepted_weak_signal": bool(gate.get("gate_result") == "accepted_with_weak_signal"),
        "semantic_planner_support_level": support_level,
    }


def build_inspector_timeline_projection(*, session_id: str, trace_id: str) -> dict[str, Any]:
    """Return per-turn timeline projection from existing diagnostics rows."""
    bundle = build_session_evidence_bundle(session_id=session_id, trace_id=trace_id)
    if bundle.get("error") == "backend_session_not_found":
        return bundle
    rows = _diagnostics_rows(bundle)
    if not rows:
        section = make_unavailable_section(reason="no_turn_diagnostics_for_session", data={"turns": []})
        return _build_root(
            bundle=bundle,
            session_id=session_id,
            schema_version=INSPECTOR_TIMELINE_PROJECTION_SCHEMA_VERSION,
            projection_status="partial",
            section_key="timeline_projection",
            section=section,
        )

    mid = bundle.get("module_id")
    turns = [_extract_turn_view(row, idx, module_id=mid) for idx, row in enumerate(rows)]
    section = make_supported_section(
        {
            "total_turns": len(turns),
            "turns": turns,
        }
    )
    return _build_root(
        bundle=bundle,
        session_id=session_id,
        schema_version=INSPECTOR_TIMELINE_PROJECTION_SCHEMA_VERSION,
        projection_status="ok",
        section_key="timeline_projection",
        section=section,
    )


def _session_has_candidate_matrix(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        dr = _dramatic_review(row)
        c = dr.get("multi_pressure_candidates")
        if isinstance(c, list) and len(c) > 0:
            return True
    return False


def build_inspector_comparison_projection(*, session_id: str, trace_id: str) -> dict[str, Any]:
    """Return bounded turn-to-turn comparison projection for one session."""
    bundle = build_session_evidence_bundle(session_id=session_id, trace_id=trace_id)
    if bundle.get("error") == "backend_session_not_found":
        return bundle
    rows = _diagnostics_rows(bundle)
    if len(rows) < 2:
        section = make_unavailable_section(
            reason="comparison_requires_at_least_two_turns",
            data={
                "mandatory_dimension": "turn_to_turn_within_session",
                "supported_dimensions": [],
                "unsupported_dimensions": [
                    "cross_session_comparison_no_shared_projection_source",
                    "cross_run_version_delta_not_emitted",
                ],
                "comparisons": [],
            },
        )
        return _build_root(
            bundle=bundle,
            session_id=session_id,
            schema_version=INSPECTOR_COMPARISON_PROJECTION_SCHEMA_VERSION,
            projection_status="partial",
            section_key="comparison_projection",
            section=section,
        )

    mid = bundle.get("module_id")
    turns = [_extract_turn_view(row, idx, module_id=mid) for idx, row in enumerate(rows)]
    has_candidates = _session_has_candidate_matrix(rows)
    unsupported_dimensions: list[str] = [
        "cross_session_comparison_no_shared_projection_source",
        "cross_run_version_delta_not_emitted",
    ]
    if not has_candidates:
        unsupported_dimensions.append("candidate_matrix_not_emitted_in_diagnostics")

    supported_dimensions = ["turn_to_turn_within_session", "planner_gate_posture_delta"]
    if has_candidates:
        supported_dimensions.append("candidate_matrix_when_present")

    comparisons: list[dict[str, Any]] = []
    for idx in range(1, len(rows)):
        prev_row, current_row = rows[idx - 1], rows[idx]
        prev, current = turns[idx - 1], turns[idx]
        dr_to = _dramatic_review(current_row)
        candidates_to = dr_to.get("multi_pressure_candidates") if has_candidates else None
        if has_candidates and not isinstance(candidates_to, list):
            candidates_to = None

        fp_prev = _visible_narration_fingerprint(prev_row)
        fp_curr = _visible_narration_fingerprint(current_row)
        surface_comparison: dict[str, Any] | str
        if fp_prev is None or fp_curr is None:
            surface_comparison = "unavailable_missing_visible_output_bundle"
        else:
            surface_comparison = {
                "visible_output_fingerprint_from": fp_prev,
                "visible_output_fingerprint_to": fp_curr,
                "phrasing_identical": fp_prev == fp_curr,
            }

        comparisons.append(
            {
                "from_turn_number": prev["turn_number"],
                "to_turn_number": current["turn_number"],
                "from_trace_id": prev["trace_id"],
                "to_trace_id": current["trace_id"],
                "gate_result_from": prev["gate_result"],
                "gate_result_to": current["gate_result"],
                "validation_status_from": prev["validation_status"],
                "validation_status_to": current["validation_status"],
                "fallback_path_taken_from": prev["fallback_path_taken"],
                "fallback_path_taken_to": current["fallback_path_taken"],
                "selected_scene_function_from": prev["selected_scene_function"],
                "selected_scene_function_to": current["selected_scene_function"],
                "empty_fluency_risk_from": prev["empty_fluency_risk"],
                "empty_fluency_risk_to": current["empty_fluency_risk"],
                "character_plausibility_posture_from": prev["character_plausibility_posture"],
                "character_plausibility_posture_to": current["character_plausibility_posture"],
                "continuity_support_posture_from": prev["continuity_support_posture"],
                "continuity_support_posture_to": current["continuity_support_posture"],
                "legacy_fallback_used_from": prev["legacy_fallback_used"],
                "legacy_fallback_used_to": current["legacy_fallback_used"],
                "semantic_move_type_from": prev["semantic_move_type"],
                "semantic_move_type_to": current["semantic_move_type"],
                "scene_risk_band_from": prev["scene_risk_band"],
                "scene_risk_band_to": current["scene_risk_band"],
                "multi_pressure_candidates_to": candidates_to,
                "visible_output_surface_comparison": surface_comparison,
            }
        )

    section = make_supported_section(
        {
            "mandatory_dimension": "turn_to_turn_within_session",
            "supported_dimensions": supported_dimensions,
            "unsupported_dimensions": unsupported_dimensions,
            "comparisons": comparisons,
            "semantic_planner_support_level": support_level_for_module(mid if isinstance(mid, str) else "").value,
            "dramatic_effect_evaluator_class": type(
                resolve_dramatic_effect_evaluator(mid if isinstance(mid, str) else "")
            ).__name__,
        }
    )
    return _build_root(
        bundle=bundle,
        session_id=session_id,
        schema_version=INSPECTOR_COMPARISON_PROJECTION_SCHEMA_VERSION,
        projection_status="ok",
        section_key="comparison_projection",
        section=section,
    )


def build_inspector_coverage_health_projection(*, session_id: str, trace_id: str) -> dict[str, Any]:
    """Return evidence-backed coverage/health aggregates."""
    bundle = build_session_evidence_bundle(session_id=session_id, trace_id=trace_id)
    if bundle.get("error") == "backend_session_not_found":
        return bundle
    rows = _diagnostics_rows(bundle)
    if not rows:
        section = make_unavailable_section(
            reason="no_turn_diagnostics_for_session",
            data={
                "metrics": {},
                "distribution": {},
            },
        )
        return _build_root(
            bundle=bundle,
            session_id=session_id,
            schema_version=INSPECTOR_COVERAGE_HEALTH_PROJECTION_SCHEMA_VERSION,
            projection_status="partial",
            section_key="coverage_health_projection",
            section=section,
        )

    gate_counter: Counter[str] = Counter()
    validation_counter: Counter[str] = Counter()
    rationale_counter: Counter[str] = Counter()
    fluency_counter: Counter[str] = Counter()
    plaus_counter: Counter[str] = Counter()
    continuity_counter: Counter[str] = Counter()
    weak_signal_counter: Counter[str] = Counter()
    legacy_fallback_counter: Counter[str] = Counter()
    support_counter: Counter[str] = Counter()
    legacy_dominant_counter: Counter[str] = Counter()
    fallback_turns = 0
    unsupported_unavailable_counter: Counter[str] = Counter()

    mid = bundle.get("module_id")
    session_support = support_level_for_module(mid if isinstance(mid, str) else "").value

    for idx, row in enumerate(rows):
        validation = row.get("validation_outcome")
        if not isinstance(validation, dict):
            validation = {}
            unsupported_unavailable_counter["validation_missing"] += 1
        gate = validation.get("dramatic_effect_gate_outcome")
        if not isinstance(gate, dict):
            gate = {}
            unsupported_unavailable_counter["gate_outcome_missing"] += 1

        gate_result = str(gate.get("gate_result") or "unavailable")
        validation_status = str(validation.get("status") or "unavailable")
        gate_counter[gate_result] += 1
        validation_counter[validation_status] += 1

        support_counter[session_support] += 1

        eff = gate.get("effect_rationale_codes")
        if isinstance(eff, list) and eff:
            for code in eff:
                rationale_counter[str(code)] += 1
        else:
            unsupported_unavailable_counter["effect_rationale_codes_missing"] += 1

        rej = gate.get("rejection_reasons")
        if isinstance(rej, list) and rej:
            for code in rej:
                rationale_counter[f"rejection_reason:{code}"] += 1

        dom = gate.get("dominant_rejection_category")
        if dom:
            legacy_dominant_counter[str(dom)] += 1

        efr = gate.get("empty_fluency_risk")
        fluency_counter[str(efr if efr is not None else "unavailable")] += 1

        cpp = gate.get("character_plausibility_posture")
        plaus_counter[str(cpp if cpp is not None else "unavailable")] += 1

        csp = gate.get("continuity_support_posture")
        continuity_counter[str(csp if csp is not None else "unavailable")] += 1

        lfu = gate.get("legacy_fallback_used")
        legacy_fallback_counter[str(lfu if lfu is not None else "unavailable")] += 1

        ws = validation.get("dramatic_effect_weak_signal")
        if ws is True:
            weak_signal_counter["true"] += 1
        elif ws is False:
            weak_signal_counter["false"] += 1
        else:
            weak_signal_counter["unavailable"] += 1

        graph = row.get("graph")
        model_route = row.get("model_route")
        graph = graph if isinstance(graph, dict) else {}
        model_route = model_route if isinstance(model_route, dict) else {}
        if graph.get("fallback_path_taken") or model_route.get("fallback_stage_reached"):
            fallback_turns += 1

        if row.get("selected_scene_function") in (None, ""):
            unsupported_unavailable_counter["selected_scene_function_missing"] += 1
        if row.get("trace_id") in (None, ""):
            unsupported_unavailable_counter["trace_id_missing"] += 1

        if idx == 0 and gate_result == "unavailable":
            unsupported_unavailable_counter["gate_distribution_partial"] += 0

    total_turns = len(rows)
    not_supported_rate = gate_counter.get("not_supported", 0) / total_turns if total_turns else 0.0
    section = make_supported_section(
        {
            "metrics": {
                "total_turns": total_turns,
                "fallback_frequency": {
                    "fallback_turns": fallback_turns,
                    "total_turns": total_turns,
                    "fallback_rate": fallback_turns / total_turns if total_turns else 0.0,
                },
                "not_supported_gate_rate": not_supported_rate,
            },
            "distribution": {
                "gate_outcome_distribution": dict(gate_counter),
                "validation_outcome_distribution": dict(validation_counter),
                "effect_and_rejection_rationale_distribution": dict(rationale_counter),
                "empty_fluency_risk_distribution": dict(fluency_counter),
                "character_plausibility_posture_distribution": dict(plaus_counter),
                "continuity_support_posture_distribution": dict(continuity_counter),
                "legacy_fallback_used_distribution": dict(legacy_fallback_counter),
                "dramatic_effect_weak_signal_distribution": dict(weak_signal_counter),
                "semantic_planner_support_level_distribution": dict(support_counter),
                "legacy_dominant_rejection_category_distribution": dict(legacy_dominant_counter),
                "unsupported_unavailable_frequency": dict(unsupported_unavailable_counter),
            },
            "required_minimum_metrics_status": {
                "gate_outcome_distribution": INSPECTOR_SECTION_STATUS_SUPPORTED,
                "validation_outcome_distribution": INSPECTOR_SECTION_STATUS_SUPPORTED,
                "fallback_frequency": INSPECTOR_SECTION_STATUS_SUPPORTED,
                "effect_and_rejection_rationale_distribution": INSPECTOR_SECTION_STATUS_SUPPORTED,
                "empty_fluency_risk_distribution": INSPECTOR_SECTION_STATUS_SUPPORTED,
                "unsupported_unavailable_frequency": INSPECTOR_SECTION_STATUS_SUPPORTED,
            },
        }
    )
    return _build_root(
        bundle=bundle,
        session_id=session_id,
        schema_version=INSPECTOR_COVERAGE_HEALTH_PROJECTION_SCHEMA_VERSION,
        projection_status="ok",
        section_key="coverage_health_projection",
        section=section,
    )


def build_inspector_provenance_raw_projection(
    *,
    session_id: str,
    trace_id: str,
    mode: str = "canonical",
) -> dict[str, Any]:
    """Return provenance entries and optional raw evidence bundle."""
    bundle = build_session_evidence_bundle(session_id=session_id, trace_id=trace_id)
    if bundle.get("error") == "backend_session_not_found":
        return bundle
    rows = _diagnostics_rows(bundle)
    if not rows:
        section = make_unavailable_section(reason="no_turn_diagnostics_for_session", data={"entries": []})
        payload = _build_root(
            bundle=bundle,
            session_id=session_id,
            schema_version=INSPECTOR_PROVENANCE_RAW_PROJECTION_SCHEMA_VERSION,
            projection_status="partial",
            section_key="provenance_raw_projection",
            section=section,
        )
        payload["raw_mode_loaded"] = False
        return payload

    last = rows[-1]
    validation = last.get("validation_outcome")
    if not isinstance(validation, dict):
        validation = {}
    gate = validation.get("dramatic_effect_gate_outcome")
    if not isinstance(gate, dict):
        gate = {}
    model_route = last.get("model_route")
    if not isinstance(model_route, dict):
        model_route = {}
    graph = last.get("graph")
    if not isinstance(graph, dict):
        graph = {}

    mid = bundle.get("module_id")
    mid_str = mid if isinstance(mid, str) else ""
    support_level = support_level_for_module(mid_str).value
    evaluator_class = type(resolve_dramatic_effect_evaluator(mid_str)).__name__

    trace_compact = None
    if isinstance(gate.get("diagnostic_trace"), list):
        trace_compact = [
            {"code": (s or {}).get("code"), "detail": str((s or {}).get("detail") or "")[:160]}
            for s in gate["diagnostic_trace"][:24]
            if isinstance(s, dict)
        ]

    entries = [
        {
            "field": "validation_status",
            "value": validation.get("status"),
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].validation_outcome.status",
        },
        {
            "field": "gate_result",
            "value": gate.get("gate_result"),
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].validation_outcome.dramatic_effect_gate_outcome.gate_result",
        },
        {
            "field": "effect_rationale_codes",
            "value": list(gate["effect_rationale_codes"])
            if isinstance(gate.get("effect_rationale_codes"), list)
            else None,
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].validation_outcome.dramatic_effect_gate_outcome.effect_rationale_codes",
        },
        {
            "field": "dramatic_effect_diagnostic_trace",
            "value": trace_compact,
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].validation_outcome.dramatic_effect_gate_outcome.diagnostic_trace",
        },
        {
            "field": "legacy_fallback_used",
            "value": gate.get("legacy_fallback_used"),
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].validation_outcome.dramatic_effect_gate_outcome.legacy_fallback_used",
        },
        {
            "field": "semantic_planner_support_level",
            "value": support_level,
            "source_kind": "capability_metadata",
            "source_ref": "ai_stack.semantic_planner_effect_surface.support_level_for_module",
        },
        {
            "field": "dramatic_effect_evaluator_class",
            "value": evaluator_class,
            "source_kind": "capability_metadata",
            "source_ref": "ai_stack.semantic_planner_effect_surface.resolve_dramatic_effect_evaluator",
        },
        {
            "field": "fallback_path_taken",
            "value": bool(graph.get("fallback_path_taken") or model_route.get("fallback_stage_reached")),
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].graph.fallback_path_taken|model_route.fallback_stage_reached",
        },
        {
            "field": "selected_scene_function",
            "value": last.get("selected_scene_function"),
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].selected_scene_function",
        },
    ]
    section = make_supported_section(
        {
            "entries": entries,
            "canonical_vs_raw_boundary": (
                "raw_evidence_is_operator_inspection_material_only_and_must_not_replace_canonical_projection_sections"
            ),
        }
    )
    payload = _build_root(
        bundle=bundle,
        session_id=session_id,
        schema_version=INSPECTOR_PROVENANCE_RAW_PROJECTION_SCHEMA_VERSION,
        projection_status="ok",
        section_key="provenance_raw_projection",
        section=section,
    )
    if mode == "raw":
        payload["raw_mode_loaded"] = True
        payload["raw_evidence"] = {
            "world_engine_state": bundle.get("world_engine_state"),
            "world_engine_diagnostics": bundle.get("world_engine_diagnostics"),
            "execution_truth": bundle.get("execution_truth"),
            "cross_layer_classifiers": bundle.get("cross_layer_classifiers"),
            "bridge_errors": bundle.get("bridge_errors"),
        }
    else:
        payload["raw_mode_loaded"] = False
    return payload
