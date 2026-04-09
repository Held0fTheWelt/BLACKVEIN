"""Read-only projection services for Inspector timeline/comparison/coverage/provenance views."""

from __future__ import annotations

from collections import Counter
from typing import Any

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


def _extract_turn_view(row: dict[str, Any], idx: int) -> dict[str, Any]:
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
    return {
        "turn_index": idx + 1,
        "turn_number": row.get("turn_number") if isinstance(row.get("turn_number"), int) else idx + 1,
        "trace_id": row.get("trace_id"),
        "gate_result": gate.get("gate_result"),
        "validation_status": validation.get("status"),
        "validation_reason": validation.get("reason"),
        "fallback_path_taken": bool(graph.get("fallback_path_taken") or model_route.get("fallback_stage_reached")),
        "execution_health": graph.get("execution_health"),
        "selected_scene_function": row.get("selected_scene_function"),
        "route_mode": model_route.get("route_mode"),
        "route_reason_code": model_route.get("route_reason_code") or model_route.get("route_reason"),
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

    turns = [_extract_turn_view(row, idx) for idx, row in enumerate(rows)]
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

    turns = [_extract_turn_view(row, idx) for idx, row in enumerate(rows)]
    comparisons: list[dict[str, Any]] = []
    for prev, current in zip(turns, turns[1:]):
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
            }
        )

    section = make_supported_section(
        {
            "mandatory_dimension": "turn_to_turn_within_session",
            "supported_dimensions": ["turn_to_turn_within_session"],
            "unsupported_dimensions": [
                "cross_session_comparison_no_shared_projection_source",
                "cross_run_version_delta_not_emitted",
                "candidate_matrix_not_emitted",
            ],
            "comparisons": comparisons,
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
    rejection_counter: Counter[str] = Counter()
    fallback_turns = 0
    unsupported_unavailable_counter: Counter[str] = Counter()

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

        rejection_codes = gate.get("rejection_reasons")
        if isinstance(rejection_codes, list):
            for code in rejection_codes:
                rejection_counter[str(code)] += 1
        else:
            unsupported_unavailable_counter["rejection_codes_missing"] += 1

        dominant = gate.get("dominant_rejection_category")
        if dominant:
            rejection_counter[f"dominant:{dominant}"] += 1
        else:
            unsupported_unavailable_counter["dominant_rejection_missing"] += 1

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
    section = make_supported_section(
        {
            "metrics": {
                "total_turns": total_turns,
                "fallback_frequency": {
                    "fallback_turns": fallback_turns,
                    "total_turns": total_turns,
                    "fallback_rate": fallback_turns / total_turns if total_turns else 0.0,
                },
            },
            "distribution": {
                "gate_outcome_distribution": dict(gate_counter),
                "validation_outcome_distribution": dict(validation_counter),
                "rejection_rationale_distribution": dict(rejection_counter),
                "unsupported_unavailable_frequency": dict(unsupported_unavailable_counter),
            },
            "required_minimum_metrics_status": {
                "gate_outcome_distribution": INSPECTOR_SECTION_STATUS_SUPPORTED,
                "validation_outcome_distribution": INSPECTOR_SECTION_STATUS_SUPPORTED,
                "fallback_frequency": INSPECTOR_SECTION_STATUS_SUPPORTED,
                "unsupported_unavailable_frequency": INSPECTOR_SECTION_STATUS_SUPPORTED,
                "rejection_rationale_distribution": INSPECTOR_SECTION_STATUS_SUPPORTED,
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
