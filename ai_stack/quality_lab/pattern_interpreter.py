"""Pattern clustering and investigation planning (ADR-0040 Phase 4)."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from ai_stack.quality_lab.schemas import user_decision_prompt


PATTERN_CLUSTER_FIELDS: tuple[str, ...] = (
    "judge",
    "category",
    "runtime_area",
    "actor",
    "beat",
    "content_module",
    "trace_name",
)

QUALITY_LAB_PATTERN_TOOL_NAMES: tuple[str, ...] = (
    "wos.quality_lab.find_patterns",
    "wos.quality_lab.suggest_investigation",
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


def _first_present(item: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        val = item.get(key)
        if val not in (None, "", []):
            return val
    return None


def _severity_rank(value: Any) -> int:
    token = _coerce_str(value).lower()
    return {
        "critical": 0,
        "urgent": 0,
        "high": 1,
        "medium": 2,
        "warning": 2,
        "low": 3,
        "info": 4,
        "positive": 5,
    }.get(token, 3)


def _severity_token(items: Iterable[Mapping[str, Any]]) -> str:
    best = min(
        (_severity_rank(i.get("severity") or i.get("priority")) for i in items),
        default=4,
    )
    return {0: "critical", 1: "high", 2: "medium", 3: "low", 4: "info"}.get(best, "medium")


def _trace_ref(item: Mapping[str, Any]) -> str | None:
    return _coerce_str(
        _first_present(item, ("trace_id", "source_ref", "trace_name", "ref"))
    ) or None


def _field_values(item: Mapping[str, Any], field: str) -> list[str]:
    if field == "judge":
        raw = _first_present(item, ("judge", "evaluator", "evaluator_name"))
        vals = _as_list(raw) + _as_list(item.get("affected_judges"))
    elif field == "category":
        vals = _as_list(_first_present(item, ("category", "score_category"))) + _as_list(
            item.get("repeated_categories")
        )
    elif field == "runtime_area":
        vals = (
            _as_list(_first_present(item, ("runtime_area", "affected_area", "repair_area")))
            + _as_list(item.get("affected_runtime_areas"))
            + _as_list(item.get("suggested_repair_areas"))
        )
    elif field == "actor":
        vals = _as_list(_first_present(item, ("actor", "player_actor", "selected_actor", "player_role")))
    elif field == "beat":
        vals = _as_list(_first_present(item, ("beat", "selected_beat", "selected_beat_id", "beat_id")))
    elif field == "content_module":
        vals = _as_list(_first_present(item, ("content_module", "module_id", "module")))
    elif field == "trace_name":
        vals = _as_list(item.get("trace_name"))
    else:
        vals = []
    out: list[str] = []
    for val in vals:
        token = _coerce_str(val)
        if token and token not in out:
            out.append(token)
    return out


def _iter_items(
    trace_summaries: Iterable[Any],
    judge_results: Iterable[Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    nested_keys = (
        "improvement_candidates",
        "qualitative_issue_clusters",
        "judge_interpretations",
        "span_anomalies",
        "recurring_patterns",
    )
    for source_kind, payloads in (
        ("trace_summary", trace_summaries),
        ("judge_result", judge_results),
    ):
        for payload in payloads or []:
            if not isinstance(payload, Mapping):
                continue
            parent = dict(payload)
            parent.setdefault("source", source_kind)
            items.append(parent)
            inherited = {
                "trace_id": payload.get("trace_id"),
                "trace_name": payload.get("trace_name"),
                "module_id": payload.get("module_id"),
                "content_module": payload.get("content_module"),
                "actor": payload.get("actor"),
            }
            for key in nested_keys:
                for nested in _as_list(payload.get(key)):
                    if not isinstance(nested, Mapping):
                        continue
                    row = {k: v for k, v in inherited.items() if v not in (None, "", [])}
                    row.update(dict(nested))
                    row.setdefault("source", source_kind)
                    items.append(row)
    return items


def _cause_for_token(token: str) -> str:
    low = token.lower()
    if "authority" in low or "actor" in low:
        return "actor-lane or authority-boundary regression"
    if "metadata" in low or "origin" in low:
        return "missing runtime metadata or visible-origin propagation"
    if "beat" in low:
        return "beat selection not realized in the visible turn"
    if "capability" in low:
        return "capability selection and realization drift"
    if "rag" in low or "content" in low:
        return "content retrieval or module evidence gap"
    if "mcp" in low:
        return "MCP analysis quality or stale tooling assumption"
    if "generation" in low:
        return "generation observation or live-model emission gap"
    return "shared runtime or evaluator evidence gap"


def _pattern_from_group(
    *,
    idx: int,
    field: str,
    token: str,
    rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    traces = sorted({t for r in rows if (t := _trace_ref(r))})
    judges = sorted({v for r in rows for v in _field_values(r, "judge")})
    categories = sorted({v for r in rows for v in _field_values(r, "category")})
    areas = sorted({v for r in rows for v in _field_values(r, "runtime_area")})
    evidence = [
        _coerce_str(r.get("rationale") or r.get("interpretation") or r.get("category") or r.get("repair_area"))
        for r in rows[:5]
    ]
    evidence = [e for e in evidence if e]
    cause = _cause_for_token(token)
    return {
        "cluster_id": f"pattern_{idx}_{field}_{token.replace(' ', '_')}",
        "title": f"Recurring {field}: {token}",
        "cluster_by": field,
        "cluster_value": token,
        "affected_areas": areas,
        "affected_judges": judges,
        "affected_traces": traces,
        "repeated_categories": categories,
        "evidence": evidence,
        "likely_causes": [cause],
        "confidence": "high" if len(rows) >= 3 else "medium",
        "severity": _severity_token(rows),
        "frequency": len(rows),
        "next_best_investigation": f"Inspect evidence for {field}={token} and verify {cause}.",
    }


def _claude_queries(patterns: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    queries: list[dict[str, str]] = []
    for pattern in list(patterns)[:5]:
        value = _coerce_str(pattern.get("cluster_value") or pattern.get("title"))
        if not value:
            continue
        queries.append(
            {
                "query": f"Find runtime, evaluator, and MCP code paths related to {value}",
                "rationale": _coerce_str(pattern.get("next_best_investigation")),
            }
        )
    return queries


def find_patterns(
    *,
    trace_summaries: Iterable[Any] | None = None,
    judge_results: Iterable[Any] | None = None,
    cluster_by: Iterable[str] | None = None,
    include_claude_context: bool = False,
) -> dict[str, Any]:
    """Find recurring quality patterns across trace summaries and judge results."""
    fields = [
        f for f in (cluster_by or PATTERN_CLUSTER_FIELDS) if _coerce_str(f) in PATTERN_CLUSTER_FIELDS
    ]
    if not fields:
        fields = list(PATTERN_CLUSTER_FIELDS)
    items = _iter_items(trace_summaries or [], judge_results or [])

    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for item in items:
        for field in fields:
            for value in _field_values(item, field):
                grouped[(field, value)].append(item)

    patterns: list[dict[str, Any]] = []
    for idx, ((field, token), rows) in enumerate(
        sorted(
            ((key, val) for key, val in grouped.items() if len(val) >= 2),
            key=lambda kv: (-len(kv[1]), kv[0][0], kv[0][1]),
        ),
        start=1,
    ):
        patterns.append(_pattern_from_group(idx=idx, field=field, token=token, rows=list(rows)))

    target_counts: Counter[str] = Counter()
    for item in items:
        for area in _field_values(item, "runtime_area"):
            target_counts[area] += 1
    top_targets = [
        {
            "repair_area": area,
            "frequency": count,
            "priority": "high" if count >= 3 else "medium",
            "likely_cause": _cause_for_token(area),
        }
        for area, count in target_counts.most_common(5)
    ]
    root_causes = [
        {"cause": cause, "supporting_patterns": [p["cluster_id"] for p in patterns if cause in p["likely_causes"]]}
        for cause in sorted({c for p in patterns for c in p["likely_causes"]})
    ]
    repair_waves = [
        {
            "wave_id": f"wave_{idx}",
            "title": f"Repair recurring {target['repair_area']}",
            "priority": target["priority"],
            "target_repair_area": target["repair_area"],
            "evidence_frequency": target["frequency"],
        }
        for idx, target in enumerate(top_targets, start=1)
    ]

    return {
        "recurring_patterns": patterns,
        "top_improvement_targets": top_targets,
        "likely_root_causes": root_causes,
        "recommended_repair_waves": repair_waves,
        "claude_context_queries": _claude_queries(patterns) if include_claude_context else [],
        "deterministic_gates_remain_authoritative": True,
        "canonical_evaluator_definition_doc": "docs/llm-as-a-judge/",
    }


def suggest_investigation(
    *,
    problem_cluster: Mapping[str, Any] | None,
    available_context: Mapping[str, Any] | None = None,
    include_claude_context: bool = True,
) -> dict[str, Any]:
    """Convert one problem cluster into concrete investigation steps."""
    cluster = dict(problem_cluster or {})
    context = dict(available_context or {})
    title = _coerce_str(cluster.get("title") or cluster.get("cluster_id") or "quality cluster")
    affected_areas = [_coerce_str(v) for v in _as_list(cluster.get("affected_areas")) if _coerce_str(v)]
    affected_judges = [_coerce_str(v) for v in _as_list(cluster.get("affected_judges")) if _coerce_str(v)]
    affected_traces = [_coerce_str(v) for v in _as_list(cluster.get("affected_traces")) if _coerce_str(v)]
    causes = [_coerce_str(v) for v in _as_list(cluster.get("likely_causes")) if _coerce_str(v)]
    if not causes and affected_areas:
        causes = [_cause_for_token(affected_areas[0])]
    if not causes:
        causes = ["insufficient evidence to isolate root cause"]

    hypotheses = [
        {
            "hypothesis_id": f"hypothesis_{idx}",
            "title": cause,
            "confidence": cluster.get("confidence") or "medium",
            "evidence_refs": affected_traces[:3],
        }
        for idx, cause in enumerate(causes, start=1)
    ]
    investigation_steps = [
        {
            "step_id": "inspect_trace_evidence",
            "action": "Review affected trace summaries and span anomalies before changing code.",
            "evidence_needed": affected_traces or ["trace_id"],
        },
        {
            "step_id": "compare_runtime_and_judges",
            "action": "Compare deterministic runtime evidence with qualitative judge categories.",
            "evidence_needed": affected_judges or ["judge_interpretations"],
        },
        {
            "step_id": "map_repair_area",
            "action": "Map the top affected area to runtime, content, prompt, or MCP-analysis ownership.",
            "evidence_needed": affected_areas or ["affected_area"],
        },
    ]
    mcp_tools = ["wos.quality_lab.review_trace", "wos.quality_lab.review_judgments"]
    if context.get("mcp_exchange_available"):
        mcp_tools.append("wos.quality_lab.review_mcp_exchange")

    claude_queries = []
    if include_claude_context:
        for area in (affected_areas or causes)[:3]:
            claude_queries.append(
                {
                    "query": f"Find code, tests, and docs related to {area}",
                    "rationale": f"Support investigation for {title}.",
                }
            )

    evidence_needed = []
    if not affected_traces:
        evidence_needed.append("at least one trace_id or trace summary")
    if not affected_judges:
        evidence_needed.append("judge interpretations or explicit evaluator names")
    if not affected_areas:
        evidence_needed.append("affected runtime/content area")

    decision = user_decision_prompt(
        question=f"What should we investigate first for {title}?",
        context_summary=(
            f"Cluster severity={cluster.get('severity', 'unknown')}; "
            f"frequency={cluster.get('frequency', 'unknown')}; "
            f"likely causes={', '.join(causes)}."
        ),
        options=[
            {
                "id": "start_with_trace_evidence",
                "label": "Start with trace evidence",
                "description": "Inspect concrete runtime traces before proposing a repair.",
                "ai_action": "Run review_trace on affected traces and summarize aspect/span failures.",
                "tradeoff": "Most grounded, but needs trace payloads.",
                "recommended": True,
            },
            {
                "id": "start_with_judge_evidence",
                "label": "Start with judge evidence",
                "description": "Inspect evaluator categories and coverage gaps first.",
                "ai_action": "Run review_judgments on available judge score payloads and compare categories.",
                "tradeoff": "Useful for qualitative drift but cannot prove runtime contract status.",
            },
            {
                "id": "defer_until_more_examples",
                "label": "Wait for examples",
                "description": "Collect more traces before acting on this cluster.",
                "ai_action": "Query recent traces and rerun find_patterns once there are more examples.",
                "tradeoff": "Avoids overfitting but delays repair.",
            },
        ],
        evidence_refs=[{"type": "trace", "ref": ref} for ref in affected_traces[:3]],
    )

    return {
        "hypotheses": hypotheses,
        "investigation_steps": investigation_steps,
        "claude_context_queries": claude_queries,
        "mcp_followup_tools": mcp_tools,
        "evidence_needed": evidence_needed,
        "user_decision": decision,
        "deterministic_gates_remain_authoritative": True,
        "canonical_evaluator_definition_doc": "docs/llm-as-a-judge/",
    }
