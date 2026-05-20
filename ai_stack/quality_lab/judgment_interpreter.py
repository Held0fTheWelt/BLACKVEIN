"""Quality Lab judgment interpreter (ADR-0040 Phase 1).

Takes judge scores (typically from ``fetch_langfuse_trace_scores`` output)
and produces semantic interpretation: severity buckets, repair-area
aggregation, qualitative issue clusters, missing-judge detection,
coverage gaps, and prioritized improvement candidates.

LLM judge results are qualitative findings only; they never override
deterministic runtime gates (ADR-0033).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from ai_stack.quality_lab.evaluator_catalog import (
    EvaluatorView,
    category_severity_bucket,
    evaluator_view,
    evaluator_views_for_scope,
    list_evaluator_views,
)
from ai_stack.quality_lab.schemas import user_decision_prompt


def _normalize_score_entry(raw: Any) -> dict[str, Any]:
    """Coerce a per-judge score entry into a stable shape.

    Accepted inputs:
      - {"category": "...", "reasoning"?: "...", "value"?: ...}
      - "category_string"  (bare category)
      - {"value": 1.0, ...} without category (numeric only — rare for judges)
    """
    if isinstance(raw, dict):
        category = raw.get("category")
        reasoning = raw.get("reasoning")
        value = raw.get("value")
        return {
            "category": str(category).strip() if category else None,
            "reasoning": str(reasoning) if reasoning else None,
            "value": value,
        }
    if isinstance(raw, str):
        return {"category": raw.strip() or None, "reasoning": None, "value": None}
    return {"category": None, "reasoning": None, "value": None}


def _expected_judges(is_opening: bool | None) -> tuple[EvaluatorView, ...]:
    """Return judges expected to score given the trace scope.

    ``is_opening=True``  → opening_generation judges
    ``is_opening=False`` → turn_generation judges
    ``is_opening=None``  → all judges (caller could not determine scope)
    """
    if is_opening is True:
        return evaluator_views_for_scope("opening_generation")
    if is_opening is False:
        return evaluator_views_for_scope("turn_generation")
    return list_evaluator_views()


def _interpret_one(view: EvaluatorView, score: dict[str, Any]) -> dict[str, Any]:
    category = score["category"]
    bucket = category_severity_bucket(view.name, category)
    return {
        "judge": view.name,
        "group": view.group,
        "category": category,
        "severity": bucket,
        "reasoning": score.get("reasoning"),
        "suggested_repair_areas": list(view.suggested_repair_areas)
        if bucket in {"failure", "weak"}
        else [],
        "qualitative_only": True,
        "runtime_gate": False,
    }


def _cluster_failures_by_group(
    interpretations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in interpretations:
        if entry["severity"] == "failure":
            by_group[entry["group"]].append(entry)
    clusters: list[dict[str, Any]] = []
    for group, entries in sorted(by_group.items()):
        repair_areas: list[str] = []
        seen: set[str] = set()
        for entry in entries:
            for area in entry["suggested_repair_areas"]:
                if area not in seen:
                    repair_areas.append(area)
                    seen.add(area)
        clusters.append({
            "cluster_id": f"failure_cluster_{group}",
            "evaluator_group": group,
            "affected_judges": [e["judge"] for e in entries],
            "repeated_categories": sorted({e["category"] for e in entries if e["category"]}),
            "frequency": len(entries),
            "severity": "high" if len(entries) >= 2 else "medium",
            "confidence": "high",
            "suggested_repair_areas": repair_areas,
            "qualitative_only": True,
        })
    return clusters


def _repair_area_summary(interpretations: list[dict[str, Any]]) -> dict[str, Any]:
    area_to_judges: dict[str, list[str]] = defaultdict(list)
    for entry in interpretations:
        if entry["severity"] not in {"failure", "weak"}:
            continue
        for area in entry["suggested_repair_areas"]:
            if entry["judge"] not in area_to_judges[area]:
                area_to_judges[area].append(entry["judge"])
    ranked = sorted(
        area_to_judges.items(),
        key=lambda kv: (-len(kv[1]), kv[0]),
    )
    return {
        "top_repair_areas": [
            {"repair_area": area, "judges": judges, "judge_count": len(judges)}
            for area, judges in ranked[:5]
        ],
        "all_repair_areas": dict(area_to_judges),
    }


def _improvement_candidates(
    clusters: list[dict[str, Any]],
    interpretations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for idx, cluster in enumerate(clusters):
        priority = "urgent" if cluster["frequency"] >= 2 else "high"
        candidates.append({
            "candidate_id": f"improvement_{idx + 1}",
            "title": f"Repair {cluster['evaluator_group']} failures",
            "priority": priority,
            "severity": cluster["severity"],
            "confidence": cluster["confidence"],
            "affected_judges": cluster["affected_judges"],
            "affected_runtime_areas": cluster["suggested_repair_areas"],
            "evidence": [
                f"{entry['judge']}={entry['category']}"
                for entry in interpretations
                if entry["judge"] in cluster["affected_judges"]
            ],
            "recommended_actions": [
                f"Investigate {area}" for area in cluster["suggested_repair_areas"]
            ] or ["Investigate the runtime path producing this group of failures"],
            "qualitative_only": True,
            "requires_user_decision": False,
        })
    return candidates


def _missing_and_coverage(
    expected: Iterable[EvaluatorView],
    interpretations: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    judged_names = {entry["judge"] for entry in interpretations}
    missing = sorted(view.name for view in expected if view.name not in judged_names)
    coverage_gaps = [
        {
            "judge": entry["judge"],
            "category": entry["category"],
            "reason": entry["severity"],
        }
        for entry in interpretations
        if entry["severity"] in {"neutral", "insufficient_evidence", "unknown"}
    ]
    return missing, coverage_gaps


def interpret_judgments(
    scores: dict[str, Any] | None,
    *,
    is_opening: bool | None = None,
    expected_judge_names: set[str] | None = None,
) -> dict[str, Any]:
    """Return semantic interpretation of judge scores per ADR-0040.

    Args:
      scores: ``{judge_name: {"category": str, "reasoning"?: str, ...}}``
        as produced by ``fetch_langfuse_trace_scores`` or built by hand.
      is_opening: When known, restricts the "expected judges" set used for
        missing-judge detection. ``True`` → opening evaluators; ``False``
        → turn evaluators; ``None`` → all judges considered expected.
      expected_judge_names: Optional explicit override of the expected set,
        useful when the caller has trace-specific filter context.
    """
    scores = scores or {}

    interpretations: list[dict[str, Any]] = []
    unknown_judges: list[str] = []
    for raw_name, raw_score in scores.items():
        name = str(raw_name)
        view = evaluator_view(name)
        if view is None:
            unknown_judges.append(name)
            continue
        interpretations.append(_interpret_one(view, _normalize_score_entry(raw_score)))

    if expected_judge_names is not None:
        expected_views = tuple(
            v for v in list_evaluator_views() if v.name in expected_judge_names
        )
    else:
        expected_views = _expected_judges(is_opening)
    missing, coverage_gaps = _missing_and_coverage(expected_views, interpretations)

    clusters = _cluster_failures_by_group(interpretations)
    repair_summary = _repair_area_summary(interpretations)
    candidates = _improvement_candidates(clusters, interpretations)

    decision: dict[str, Any] | None = None
    if missing and not interpretations:
        decision = user_decision_prompt(
            question=(
                "No judge scores were attached to this trace. Should the "
                "Quality Lab assume the evaluators are not configured, or "
                "that the trace predates evaluator attachment?"
            ),
            context_summary=(
                f"Expected {len(missing)} judges for this trace scope; "
                "none ran."
            ),
            options=[
                {
                    "id": "treat_as_coverage_gap",
                    "label": "Treat as coverage gap",
                    "description": (
                        "Mark all expected judges as missing and surface a "
                        "Langfuse evaluator-attachment task."
                    ),
                    "ai_action": (
                        "Open Langfuse and attach the expected categorical "
                        "evaluators using the filter bundle from "
                        "ai_stack/langfuse/langfuse_evaluator_catalog.py."
                    ),
                    "tradeoff": "Requires Langfuse access; not a runtime fix.",
                    "recommended": True,
                },
                {
                    "id": "treat_as_pre_evaluator_trace",
                    "label": "Trace predates evaluator attachment",
                    "description": (
                        "Skip this trace for qualitative analysis and look "
                        "at deterministic gates only."
                    ),
                    "ai_action": (
                        "Query for newer traces with attached evaluators "
                        "before drawing qualitative conclusions."
                    ),
                    "tradeoff": "No qualitative signal from this trace.",
                },
            ],
            evidence_refs=[
                {"type": "adr", "ref": "docs/ADR/adr-0040-quality-lab-mcp-runtime-diagnostics.md"},
                {"type": "file", "ref": "ai_stack/langfuse/langfuse_evaluator_catalog.py"},
            ],
        )

    return {
        "judge_interpretations": interpretations,
        "qualitative_issue_clusters": clusters,
        "repair_area_summary": repair_summary,
        "missing_judges": missing,
        "coverage_gaps": coverage_gaps,
        "improvement_candidates": candidates,
        "unknown_judges": unknown_judges,
        "next_user_decision": decision,
        "canonical_evaluator_definition_doc": "docs/llm-as-a-judge/",
        "deterministic_gates_remain_authoritative": True,
    }
