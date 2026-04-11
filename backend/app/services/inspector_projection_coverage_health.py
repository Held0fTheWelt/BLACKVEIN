"""Coverage/health projection from diagnostics rows — DS-053."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ai_stack.semantic_planner_effect_surface import support_level_for_module

from app.contracts.inspector_turn_projection import (
    INSPECTOR_COVERAGE_HEALTH_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_SECTION_STATUS_SUPPORTED,
    make_supported_section,
    make_unavailable_section,
)
from app.services.ai_stack_evidence_service import build_session_evidence_bundle


def build_inspector_coverage_health_projection(*, session_id: str, trace_id: str) -> dict[str, Any]:
    """Return evidence-backed coverage/health aggregates."""
    from app.services.inspector_projection_service import _build_root, _diagnostics_rows

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
