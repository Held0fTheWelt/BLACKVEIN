"""Pure aggregation for coverage/health inspector projection (DS-007)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _CoverageAccum:
    gate_counter: Counter[str] = field(default_factory=Counter)
    validation_counter: Counter[str] = field(default_factory=Counter)
    rationale_counter: Counter[str] = field(default_factory=Counter)
    fluency_counter: Counter[str] = field(default_factory=Counter)
    plaus_counter: Counter[str] = field(default_factory=Counter)
    continuity_counter: Counter[str] = field(default_factory=Counter)
    weak_signal_counter: Counter[str] = field(default_factory=Counter)
    structural_fallback_counter: Counter[str] = field(default_factory=Counter)
    support_counter: Counter[str] = field(default_factory=Counter)
    dominant_rejection_counter: Counter[str] = field(default_factory=Counter)
    unsupported_unavailable_counter: Counter[str] = field(default_factory=Counter)
    fallback_turns: int = 0


def _accumulate_row(acc: _CoverageAccum, idx: int, row: dict[str, Any], session_support: str) -> None:
    validation = row.get("validation_outcome")
    if not isinstance(validation, dict):
        validation = {}
        acc.unsupported_unavailable_counter["validation_missing"] += 1
    gate = validation.get("dramatic_effect_gate_outcome")
    if not isinstance(gate, dict):
        gate = {}
        acc.unsupported_unavailable_counter["gate_outcome_missing"] += 1

    gate_result = str(gate.get("gate_result") or "unavailable")
    validation_status = str(validation.get("status") or "unavailable")
    acc.gate_counter[gate_result] += 1
    acc.validation_counter[validation_status] += 1
    acc.support_counter[session_support] += 1

    eff = gate.get("effect_rationale_codes")
    if isinstance(eff, list) and eff:
        for code in eff:
            acc.rationale_counter[str(code)] += 1
    else:
        acc.unsupported_unavailable_counter["effect_rationale_codes_missing"] += 1

    rej = gate.get("rejection_reasons")
    if isinstance(rej, list) and rej:
        for code in rej:
            acc.rationale_counter[f"rejection_reason:{code}"] += 1

    dom = gate.get("dominant_rejection_category")
    if dom:
        acc.dominant_rejection_counter[str(dom)] += 1

    efr = gate.get("empty_fluency_risk")
    acc.fluency_counter[str(efr if efr is not None else "unavailable")] += 1

    cpp = gate.get("character_plausibility_posture")
    acc.plaus_counter[str(cpp if cpp is not None else "unavailable")] += 1

    csp = gate.get("continuity_support_posture")
    acc.continuity_counter[str(csp if csp is not None else "unavailable")] += 1

    lfu = gate.get("structural_fallback_used")
    acc.structural_fallback_counter[str(lfu if lfu is not None else "unavailable")] += 1

    ws = validation.get("dramatic_effect_weak_signal")
    if ws is True:
        acc.weak_signal_counter["true"] += 1
    elif ws is False:
        acc.weak_signal_counter["false"] += 1
    else:
        acc.weak_signal_counter["unavailable"] += 1

    graph = row.get("graph")
    model_route = row.get("model_route")
    graph = graph if isinstance(graph, dict) else {}
    model_route = model_route if isinstance(model_route, dict) else {}
    if graph.get("fallback_path_taken") or model_route.get("fallback_stage_reached"):
        acc.fallback_turns += 1

    if row.get("selected_scene_function") in (None, ""):
        acc.unsupported_unavailable_counter["selected_scene_function_missing"] += 1
    if row.get("trace_id") in (None, ""):
        acc.unsupported_unavailable_counter["trace_id_missing"] += 1

    if idx == 0 and gate_result == "unavailable":
        acc.unsupported_unavailable_counter["gate_distribution_partial"] += 0


def accumulate_coverage_health(rows: list[dict[str, Any]], session_support: str) -> _CoverageAccum:
    acc = _CoverageAccum()
    for idx, row in enumerate(rows):
        _accumulate_row(acc, idx, row, session_support)
    return acc


def build_coverage_health_supported_inner(
    rows: list[dict[str, Any]],
    *,
    session_support: str,
    required_minimum_metrics_status: dict[str, str],
) -> dict[str, Any]:
    """Build the `data` payload passed to `make_supported_section` for the ok path."""
    acc = accumulate_coverage_health(rows, session_support)
    total_turns = len(rows)
    not_supported_rate = acc.gate_counter.get("not_supported", 0) / total_turns if total_turns else 0.0
    return {
        "metrics": {
            "total_turns": total_turns,
            "fallback_frequency": {
                "fallback_turns": acc.fallback_turns,
                "total_turns": total_turns,
                "fallback_rate": acc.fallback_turns / total_turns if total_turns else 0.0,
            },
            "not_supported_gate_rate": not_supported_rate,
        },
        "distribution": {
            "gate_outcome_distribution": dict(acc.gate_counter),
            "validation_outcome_distribution": dict(acc.validation_counter),
            "effect_and_rejection_rationale_distribution": dict(acc.rationale_counter),
            "empty_fluency_risk_distribution": dict(acc.fluency_counter),
            "character_plausibility_posture_distribution": dict(acc.plaus_counter),
            "continuity_support_posture_distribution": dict(acc.continuity_counter),
            "structural_fallback_used_distribution": dict(acc.structural_fallback_counter),
            "dramatic_effect_weak_signal_distribution": dict(acc.weak_signal_counter),
            "semantic_planner_support_level_distribution": dict(acc.support_counter),
            "dominant_rejection_category_distribution": dict(acc.dominant_rejection_counter),
            "unsupported_unavailable_frequency": dict(acc.unsupported_unavailable_counter),
        },
        "required_minimum_metrics_status": required_minimum_metrics_status,
    }
