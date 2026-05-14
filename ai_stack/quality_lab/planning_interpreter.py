"""Repair, judge-set, and content planning (ADR-0040 Phase 5)."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from ai_stack.quality_lab.evaluator_catalog import evaluator_view, list_evaluator_views


DEFAULT_REPAIR_CONSTRAINTS: dict[str, bool] = {
    "no_runtime_gate_weakening": True,
    "no_hardcoded_content": True,
    "modular_only": True,
}

QUALITY_LAB_PLANNING_TOOL_NAMES: tuple[str, ...] = (
    "wos.quality_lab.plan_repair_wave",
    "wos.quality_lab.refine_judge_set",
    "wos.quality_lab.plan_content_revision",
)


def _coerce_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return sorted(value)
    return [value]


def _priority_rank(candidate: Mapping[str, Any]) -> int:
    token = _coerce_str(candidate.get("priority") or candidate.get("severity")).lower()
    return {"urgent": 0, "critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(token, 3)


def _candidate_area(candidate: Mapping[str, Any]) -> str:
    for key in ("repair_area", "affected_area", "title", "candidate_id"):
        val = _coerce_str(candidate.get(key))
        if val:
            return val
    areas = _as_list(candidate.get("affected_runtime_areas")) + _as_list(candidate.get("affected_content_areas"))
    return _coerce_str(areas[0]) if areas else "unspecified_quality_area"


def _candidate_id(candidate: Mapping[str, Any], idx: int) -> str:
    return _coerce_str(candidate.get("candidate_id") or candidate.get("repair_area")) or f"candidate_{idx}"


def _revision_relevance(candidate: Mapping[str, Any], token: str) -> bool:
    area = _candidate_area(candidate).lower()
    return token in area or _coerce_str(candidate.get(f"{token}_revision_relevance")).lower() in {
        "medium",
        "high",
    }


def _test_hint(area: str) -> str:
    low = area.lower()
    if "judge" in low:
        return "Add or update Quality Lab judgment/evaluator catalog tests."
    if "trace" in low or "metadata" in low or "span" in low:
        return "Add trace interpreter coverage for metadata/span evidence."
    if "mcp" in low:
        return "Add MCP handler/registry tests for the exchange."
    if "content" in low or "rag" in low or "beat" in low:
        return "Add content or runtime fixture coverage proving the repaired behavior."
    return "Add a focused regression test for the repaired quality area."


def plan_repair_wave(
    *,
    improvement_candidates: Iterable[Any] | None = None,
    constraints: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Turn improvement candidates into a safe, ordered repair plan."""
    active_constraints = dict(DEFAULT_REPAIR_CONSTRAINTS)
    active_constraints.update({k: bool(v) for k, v in dict(constraints or {}).items()})
    candidates = [dict(c) for c in improvement_candidates or [] if isinstance(c, Mapping)]
    candidates.sort(key=lambda c: (_priority_rank(c), _candidate_area(c)))

    buckets: dict[str, list[dict[str, Any]]] = {"wave_1": [], "wave_2": [], "wave_3": []}
    for candidate in candidates:
        rank = _priority_rank(candidate)
        area = _candidate_area(candidate).lower()
        if rank <= 1 or "authority" in area or "gate" in area:
            buckets["wave_1"].append(candidate)
        elif "content" in area or "judge" in area or "rag" in area:
            buckets["wave_2"].append(candidate)
        else:
            buckets["wave_3"].append(candidate)

    repair_waves: list[dict[str, Any]] = []
    wave_titles = {
        "wave_1": "Contract and runtime evidence repairs",
        "wave_2": "Evaluator, content, and retrieval repairs",
        "wave_3": "Follow-up hardening and cleanup",
    }
    for wave_id, rows in buckets.items():
        if not rows:
            continue
        repair_waves.append(
            {
                "wave_id": wave_id,
                "title": wave_titles[wave_id],
                "priority": rows[0].get("priority") or rows[0].get("severity") or "medium",
                "candidates": [_candidate_id(c, idx) for idx, c in enumerate(rows, start=1)],
                "target_repair_areas": [_candidate_area(c) for c in rows],
                "recommended_sequence": [
                    f"Repair {_candidate_area(c)} and verify with focused tests" for c in rows
                ],
            }
        )

    risks: list[dict[str, str]] = []
    if active_constraints.get("no_runtime_gate_weakening"):
        risks.append(
            {
                "risk": "runtime_gate_weakening",
                "mitigation": "Do not lower ADR-0033 deterministic gates; repair evidence or runtime behavior instead.",
            }
        )
    if active_constraints.get("no_hardcoded_content"):
        risks.append(
            {
                "risk": "hardcoded_content_patch",
                "mitigation": "Keep content fixes in module data or governed content revisions, not runtime shortcuts.",
            }
        )
    if active_constraints.get("modular_only"):
        risks.append(
            {
                "risk": "cross_module_regression",
                "mitigation": "Keep repairs scoped to the implicated runtime/content module boundary.",
            }
        )

    acceptance_criteria = [
        "Deterministic gates remain authoritative and unchanged unless a separate ADR changes them.",
        "Quality Lab outputs stay read-only and evidence-backed.",
    ]
    tests_to_add = sorted({_test_hint(_candidate_area(c)) for c in candidates})
    do_not_change = [
        "ADR-0033 deterministic runtime gate semantics",
        "Langfuse evaluator definitions without explicit judge-set review",
        "Runtime/content files outside the implicated repair area",
    ]

    return {
        "repair_waves": repair_waves,
        "risks": risks,
        "acceptance_criteria": acceptance_criteria,
        "tests_to_add": tests_to_add,
        "do_not_change": do_not_change,
        "constraints": active_constraints,
        "deterministic_gates_remain_authoritative": True,
        "canonical_evaluator_definition_doc": "docs/llm-as-a-judge/",
    }


def refine_judge_set(
    *,
    judge_names: Iterable[Any] | None = None,
    observed_failures: Iterable[Any] | None = None,
    examples: Iterable[Any] | None = None,
    mode: str = "analysis_only",
) -> dict[str, Any]:
    """Analyze judge-set maintenance needs without changing evaluator definitions."""
    known = {v.name for v in list_evaluator_views()}
    names = [_coerce_str(n) for n in judge_names or [] if _coerce_str(n)]
    failures = [dict(f) for f in observed_failures or [] if isinstance(f, Mapping)]
    example_rows = [dict(e) for e in examples or [] if isinstance(e, Mapping)]

    findings: list[dict[str, Any]] = []
    prompt_deltas: list[dict[str, Any]] = []
    category_deltas: list[dict[str, Any]] = []
    new_candidates: list[dict[str, Any]] = []
    merge_remove: list[dict[str, Any]] = []

    for name in names:
        view = evaluator_view(name)
        if view is None:
            findings.append(
                {
                    "judge": name,
                    "finding": "unknown_judge",
                    "severity": "medium",
                    "recommendation": "Check docs/llm-as-a-judge/ before adding or renaming this judge.",
                }
            )
            continue
        related_failures = [f for f in failures if _coerce_str(f.get("judge") or f.get("evaluator_name")) == name]
        if related_failures and not example_rows:
            findings.append(
                {
                    "judge": name,
                    "finding": "failures_need_examples",
                    "severity": "low",
                    "recommendation": "Collect representative input/output examples before prompt maintenance.",
                }
            )
        if related_failures:
            prompt_deltas.append(
                {
                    "judge": name,
                    "proposal": "Clarify prompt wording around recurring observed failures.",
                    "requires_user_review": True,
                    "evidence_count": len(related_failures),
                    "current_categories": list(view.categories),
                }
            )

    failure_areas: Counter[str] = Counter()
    for failure in failures:
        area = _coerce_str(
            failure.get("affected_area")
            or failure.get("repair_area")
            or failure.get("suggested_repair_area")
        )
        if area:
            failure_areas[area] += 1
        category = _coerce_str(failure.get("category"))
        judge = _coerce_str(failure.get("judge") or failure.get("evaluator_name"))
        if judge in known and category.lower() in {"unknown", "insufficient_evidence"}:
            category_deltas.append(
                {
                    "judge": judge,
                    "proposal": "Review whether the category definitions produce too many non-actionable labels.",
                    "category": category,
                    "requires_user_review": True,
                }
            )

    covered_groups = {
        evaluator_view(name).group for name in names if evaluator_view(name) is not None
    }
    for area, count in failure_areas.most_common(5):
        if count >= 2 and not any(area.lower() in group.lower() for group in covered_groups):
            new_candidates.append(
                {
                    "candidate": f"{area}_judge",
                    "rationale": f"{count} observed failures mention {area} without obvious judge coverage.",
                    "requires_user_review": True,
                }
            )

    if len(names) != len(set(names)):
        merge_remove.append(
            {
                "finding": "duplicate_judge_names_in_request",
                "recommendation": "Deduplicate requested judge names before maintenance review.",
                "requires_user_review": False,
            }
        )
    if mode != "analysis_only":
        findings.append(
            {
                "finding": "non_analysis_mode_requested",
                "severity": "high",
                "recommendation": "Quality Lab is read-only; emit proposals only.",
            }
        )

    return {
        "judge_maintenance_findings": findings,
        "prompt_delta_proposals": prompt_deltas,
        "category_delta_proposals": category_deltas,
        "new_judge_candidates": new_candidates,
        "merge_or_remove_candidates": merge_remove,
        "requires_user_review": True,
        "deterministic_gates_remain_authoritative": True,
        "canonical_evaluator_definition_doc": "docs/llm-as-a-judge/",
    }


def _content_related(finding: Mapping[str, Any]) -> bool:
    text = " ".join(
        _coerce_str(finding.get(k))
        for k in ("source", "affected_area", "repair_area", "suggested_repair_area", "category", "interpretation")
    ).lower()
    return any(token in text for token in ("content", "rag", "module", "beat", "tone", "relationship"))


def plan_content_revision(
    *,
    content_module: str | None = None,
    quality_findings: Iterable[Any] | None = None,
    scene_or_context: str | None = None,
    include_claude_context: bool = False,
) -> dict[str, Any]:
    """Connect quality findings to governed content-revision candidates."""
    module = _coerce_str(content_module) or "unspecified_content_module"
    findings = [dict(f) for f in quality_findings or [] if isinstance(f, Mapping)]
    content_findings = [f for f in findings if _content_related(f)]

    area_counts: dict[str, int] = defaultdict(int)
    for finding in content_findings:
        area = _coerce_str(
            finding.get("affected_area")
            or finding.get("repair_area")
            or finding.get("suggested_repair_area")
            or "content_quality"
        )
        area_counts[area] += 1

    hypotheses = [
        {
            "hypothesis_id": f"content_gap_{idx}",
            "content_module": module,
            "affected_area": area,
            "confidence": "high" if count >= 2 else "medium",
            "evidence_count": count,
            "hypothesis": f"{module} may lack enough authored support for {area}.",
        }
        for idx, (area, count) in enumerate(sorted(area_counts.items()), start=1)
    ]
    if not hypotheses and findings:
        hypotheses.append(
            {
                "hypothesis_id": "content_gap_1",
                "content_module": module,
                "affected_area": "uncertain",
                "confidence": "low",
                "evidence_count": len(findings),
                "hypothesis": "Findings do not clearly isolate a content gap; inspect runtime evidence first.",
            }
        )

    tasks = [
        {
            "task_id": f"content_revision_{idx}",
            "content_module": module,
            "title": f"Review authored support for {h['affected_area']}",
            "action": "Draft a governed content revision candidate; do not patch runtime output directly.",
            "acceptance_signal": "A replay or fixture shows the quality finding no longer appears.",
        }
        for idx, h in enumerate(hypotheses, start=1)
    ]
    questions = [
        {
            "question": f"Should {module} be revised for {h['affected_area']} or should runtime evidence be investigated first?",
            "rationale": h["hypothesis"],
        }
        for h in hypotheses
    ]
    queries = []
    if include_claude_context:
        for h in hypotheses[:5]:
            queries.append(
                {
                    "query": f"Find content module files and tests for {module} {h['affected_area']}",
                    "rationale": "Locate governed content surfaces before proposing revisions.",
                }
            )

    return {
        "content_gap_hypotheses": hypotheses,
        "content_revision_tasks": tasks,
        "content_questions_for_user": questions,
        "claude_context_queries": queries,
        "scene_or_context": _coerce_str(scene_or_context) or None,
        "deterministic_gates_remain_authoritative": True,
        "canonical_evaluator_definition_doc": "docs/llm-as-a-judge/",
    }
