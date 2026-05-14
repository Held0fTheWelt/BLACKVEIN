"""MCP exchange diagnostic interpretation (ADR-0040 Phase 3).

Pure, read-only analysis of an MCP request/response pair. This module does
not call MCP tools, Langfuse, runtime code, or the filesystem. It only
classifies whether the supplied exchange has enough context, whether it uses
current ADR-0040 assumptions, and whether the response gives useful evidence
instead of raw output.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ai_stack.langfuse_evaluator_catalog import (
    BACKEND_TURN_ROOT_TRACE_NAME,
    WORLD_ENGINE_OPENING_TRACE_NAME,
    WORLD_ENGINE_TURN_TRACE_NAME,
)
from ai_stack.quality_lab.schemas import user_decision_prompt


MCP_EXCHANGE_FOCUS_AREAS: tuple[str, ...] = (
    "judges",
    "runtime",
    "trace",
    "metadata",
    "content",
    "rag",
    "prompt",
    "mcp_quality",
)

REQUIRED_REQUEST_CONTEXT_FIELDS: tuple[str, ...] = (
    "trace_id",
    "session_id",
    "turn_id",
    "actor",
    "context",
)

CANONICAL_TRACE_NAMES: tuple[str, ...] = (
    WORLD_ENGINE_OPENING_TRACE_NAME,
    BACKEND_TURN_ROOT_TRACE_NAME,
    WORLD_ENGINE_TURN_TRACE_NAME,
)

QUALITY_LAB_TOOL_FOCUS: dict[str, tuple[str, ...]] = {
    "wos.quality_lab.review_judgments": ("judges",),
    "wos.quality_lab.review_trace": ("trace", "runtime", "metadata"),
    "wos.quality_lab.review_mcp_exchange": ("mcp_quality",),
}


def _coerce_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _walk_values(value: Any) -> Iterable[Any]:
    stack = [value]
    seen = 0
    while stack and seen < 500:
        seen += 1
        current = stack.pop()
        yield current
        if isinstance(current, Mapping):
            stack.extend(current.values())
        elif isinstance(current, (list, tuple, set)):
            stack.extend(current)


def _walk_strings(value: Any) -> list[str]:
    return [_coerce_str(v) for v in _walk_values(value) if isinstance(v, str)]


def _has_key(value: Any, key_names: set[str]) -> bool:
    lowered = {k.lower() for k in key_names}
    for node in _walk_values(value):
        if isinstance(node, Mapping):
            if any(str(k).lower() in lowered for k in node.keys()):
                return True
    return False


def _first_value_for_keys(value: Any, key_names: set[str]) -> Any:
    lowered = {k.lower() for k in key_names}
    for node in _walk_values(value):
        if not isinstance(node, Mapping):
            continue
        for key, val in node.items():
            if str(key).lower() in lowered and val not in (None, "", []):
                return val
    return None


def _tool_name(request: Mapping[str, Any]) -> str | None:
    for key in ("tool", "tool_name", "name", "mcp_tool"):
        val = request.get(key)
        if val:
            return _coerce_str(val)
    params = request.get("params")
    if isinstance(params, Mapping):
        for key in ("tool", "tool_name", "name"):
            val = params.get(key)
            if val:
                return _coerce_str(val)
    return None


def _request_arguments(request: Mapping[str, Any]) -> Mapping[str, Any]:
    args = request.get("arguments")
    if isinstance(args, Mapping):
        return args
    params = request.get("params")
    if isinstance(params, Mapping):
        nested = params.get("arguments")
        if isinstance(nested, Mapping):
            return nested
    return {}


def _normalize_focus(
    request: Mapping[str, Any],
    explicit_focus: Iterable[str] | None,
) -> list[str]:
    raw_focus: list[Any] = []
    if explicit_focus is not None:
        raw_focus.extend(explicit_focus)
    req_focus = request.get("focus")
    if isinstance(req_focus, (list, tuple, set)):
        raw_focus.extend(req_focus)
    elif isinstance(req_focus, str):
        raw_focus.append(req_focus)

    args = _request_arguments(request)
    arg_focus = args.get("focus") if isinstance(args, Mapping) else None
    if isinstance(arg_focus, (list, tuple, set)):
        raw_focus.extend(arg_focus)
    elif isinstance(arg_focus, str):
        raw_focus.append(arg_focus)

    normalized: list[str] = []
    valid = set(MCP_EXCHANGE_FOCUS_AREAS)
    for item in raw_focus:
        token = _coerce_str(item).lower()
        if token in valid and token not in normalized:
            normalized.append(token)

    if normalized:
        return normalized

    tool = _tool_name(request)
    if tool in QUALITY_LAB_TOOL_FOCUS:
        return list(QUALITY_LAB_TOOL_FOCUS[tool])

    if _has_key(request, {"scores", "judge_scores", "trace_scores_payload"}):
        return ["judges"]
    if _has_key(request, {"raw_trace", "trace_payload", "trace_id"}):
        return ["trace", "runtime", "metadata"]
    return []


def _context_value(request: Mapping[str, Any], field: str) -> Any:
    aliases = {
        "trace_id": {"trace_id", "id"},
        "session_id": {"session_id"},
        "turn_id": {"turn_id", "canonical_turn_id"},
        "actor": {"actor", "player_actor", "selected_actor", "player_role"},
        "context": {"context", "metadata", "raw_trace", "trace_payload", "scores", "judge_scores"},
    }
    return _first_value_for_keys(request, aliases.get(field, {field}))


def _build_missing_context(
    request: Mapping[str, Any],
    focus: list[str],
) -> tuple[list[str], list[dict[str, str]]]:
    missing_fields: list[str] = []
    missing_context: list[dict[str, str]] = []
    trace_like_focus = bool({"trace", "runtime", "metadata"} & set(focus))
    for field in REQUIRED_REQUEST_CONTEXT_FIELDS:
        if _context_value(request, field) not in (None, "", []):
            continue
        missing_fields.append(field)
        severity = "high" if trace_like_focus and field in {"trace_id", "session_id"} else "medium"
        if field in {"actor", "context"} and not trace_like_focus:
            severity = "low"
        missing_context.append(
            {
                "field": field,
                "severity": severity,
                "detail": f"request did not provide {field} for the MCP analysis exchange",
            }
        )
    return missing_fields, missing_context


def _detect_wrong_assumptions(
    request: Mapping[str, Any],
    response: Mapping[str, Any],
) -> list[dict[str, str]]:
    wrong: list[dict[str, str]] = []
    combined_text = "\n".join(_walk_strings({"request": request, "response": response})).lower()

    backend = BACKEND_TURN_ROOT_TRACE_NAME.lower()
    if backend in combined_text and any(
        phrase in combined_text
        for phrase in (
            "reject backend.turn.execute",
            "backend.turn.execute is invalid",
            "backend.turn.execute is not canonical",
            "backend.turn.execute rejection",
            "only world-engine.turn.execute",
        )
    ):
        wrong.append(
            {
                "kind": "stale_trace_name_assumption",
                "detail": (
                    f"{BACKEND_TURN_ROOT_TRACE_NAME} and {WORLD_ENGINE_TURN_TRACE_NAME} "
                    "are paired turn observations, not alternatives."
                ),
                "evidence": BACKEND_TURN_ROOT_TRACE_NAME,
                "suggested_correction": (
                    "Treat missing backend/world-engine pair evidence as a degradation signal, "
                    "not as a trace-name rejection."
                ),
            }
        )

    trace_name = _coerce_str(_first_value_for_keys(request, {"trace_name", "name"}))
    if trace_name and trace_name.startswith("world-engine") and trace_name not in CANONICAL_TRACE_NAMES:
        wrong.append(
            {
                "kind": "unknown_trace_name",
                "detail": f"request used trace_name={trace_name!r}, which is not in the canonical set",
                "evidence": trace_name,
                "suggested_correction": "Verify the current trace-name constant before diagnosing runtime quality.",
            }
        )

    if "no_concern" in combined_text:
        wrong.append(
            {
                "kind": "stale_judge_category_label",
                "detail": "exchange references stale judge category label no_concern",
                "evidence": "no_concern",
                "suggested_correction": "Use the current canonical evaluator category from docs/llm-as-a-judge/.",
            }
        )

    if "judge" in combined_text and any(
        phrase in combined_text
        for phrase in (
            "override deterministic",
            "replace deterministic",
            "judge gate pass",
            "judge proves runtime",
        )
    ):
        wrong.append(
            {
                "kind": "judge_gate_confusion",
                "detail": "exchange appears to let qualitative judges override deterministic runtime gates",
                "evidence": "judge/deterministic gate wording",
                "suggested_correction": "Keep judge output qualitative; ADR-0033 deterministic gates remain authoritative.",
            }
        )

    return wrong


def _wrong_tool_for_focus(tool: str | None, focus: list[str]) -> dict[str, str] | None:
    if not tool or not tool.startswith("wos.quality_lab."):
        return None
    focus_set = set(focus)
    if tool == "wos.quality_lab.review_judgments" and focus_set & {"trace", "runtime", "metadata"}:
        return {
            "kind": "wrong_tool_for_focus",
            "detail": "trace/runtime focus was sent to review_judgments",
            "evidence": tool,
            "suggested_correction": "Use wos.quality_lab.review_trace for trace, runtime, and metadata analysis.",
        }
    if tool == "wos.quality_lab.review_trace" and focus_set == {"mcp_quality"}:
        return {
            "kind": "wrong_tool_for_focus",
            "detail": "MCP exchange quality focus was sent to review_trace",
            "evidence": tool,
            "suggested_correction": "Use wos.quality_lab.review_mcp_exchange for request/response analysis.",
        }
    return None


def _response_quality(response: Mapping[str, Any]) -> dict[str, Any]:
    has_scores = _has_key(response, {"scores", "judge_scores"})
    has_interpretation = _has_key(
        response,
        {
            "judge_interpretations",
            "qualitative_issue_clusters",
            "mcp_request_quality",
            "trace_quality",
            "runtime_aspect_summary",
        },
    )
    has_repair_direction = _has_key(
        response,
        {
            "improvement_candidates",
            "repair_area_summary",
            "recommended_actions",
            "recommended_followup_queries",
            "next_user_decision",
        },
    )
    distinguishes_gate_boundary = (
        response.get("deterministic_gates_remain_authoritative") is True
        or (
            _has_key(response, {"deterministic_runtime_status", "deterministic_scores"})
            and _has_key(response, {"qualitative_judge_status", "judge_interpretations"})
        )
    )
    uses_canonical_docs = (
        response.get("canonical_evaluator_definition_doc") == "docs/llm-as-a-judge/"
        or "docs/llm-as-a-judge" in "\n".join(_walk_strings(response))
    )
    has_uncertainty = _has_key(
        response,
        {
            "coverage_gaps",
            "missing_judges",
            "unknown_judges",
            "missing_context",
            "wrong_assumptions",
            "span_anomalies",
        },
    ) or any(
        token in "\n".join(_walk_strings(response)).lower()
        for token in ("insufficient evidence", "uncertain", "missing evidence")
    )
    has_followup = _has_key(response, {"next_user_decision", "recommended_followup_queries"})
    raw_score_dump = has_scores and not has_interpretation

    has_deterministic_evidence = _has_key(
        response,
        {
            "deterministic_scores",
            "deterministic_runtime_status",
            "live_runtime_contract_pass",
            "live_opening_contract_pass",
        },
    )
    response_text = "\n".join(_walk_strings(response)).lower()
    runtime_claim_without_evidence = (
        any(phrase in response_text for phrase in ("runtime is healthy", "runtime passed", "gate passed"))
        and not has_deterministic_evidence
    )

    weaknesses: list[str] = []
    if raw_score_dump:
        weaknesses.append("raw_score_dump_without_interpretation")
    if has_scores and not distinguishes_gate_boundary:
        weaknesses.append("missing_deterministic_vs_judge_boundary")
    if not has_repair_direction:
        weaknesses.append("missing_repair_direction")
    if not has_uncertainty:
        weaknesses.append("missing_uncertainty_labeling")
    if runtime_claim_without_evidence:
        weaknesses.append("unsupported_runtime_claim")

    status = "useful"
    if runtime_claim_without_evidence:
        status = "unsupported"
    elif raw_score_dump or len(weaknesses) >= 2:
        status = "weak"

    return {
        "status": status,
        "has_interpretation": has_interpretation,
        "has_repair_direction": has_repair_direction,
        "distinguishes_deterministic_vs_judges": distinguishes_gate_boundary,
        "uses_canonical_evaluator_docs": uses_canonical_docs,
        "has_uncertainty_labeling": has_uncertainty,
        "has_followup": has_followup,
        "raw_score_dump": raw_score_dump,
        "unsupported_runtime_claim": runtime_claim_without_evidence,
        "weaknesses": weaknesses,
    }


def _request_quality(
    *,
    request: Mapping[str, Any],
    focus: list[str],
    missing_fields: list[str],
    wrong_assumptions: list[dict[str, str]],
) -> dict[str, Any]:
    tool = _tool_name(request)
    provided = [
        field for field in REQUIRED_REQUEST_CONTEXT_FIELDS if field not in set(missing_fields)
    ]
    has_evidence_payload = _has_key(
        request,
        {"raw_trace", "trace_payload", "scores", "judge_scores", "trace_scores_payload", "response"},
    )
    if not focus:
        specificity = "vague"
    elif has_evidence_payload or _context_value(request, "trace_id"):
        specificity = "specific"
    else:
        specificity = "broad"

    status = "actionable"
    if not focus or len(missing_fields) >= 3:
        status = "insufficient_context"
    elif wrong_assumptions:
        status = "stale_assumptions"
    elif specificity != "specific":
        status = "weak"

    return {
        "status": status,
        "tool_name": tool,
        "focus": focus,
        "specificity": specificity,
        "provided_context_fields": provided,
        "missing_context_fields": missing_fields,
        "has_evidence_payload": has_evidence_payload,
    }


def _followups(
    *,
    focus: list[str],
    missing_fields: list[str],
    wrong_assumptions: list[dict[str, str]],
    response_quality: Mapping[str, Any],
) -> list[dict[str, Any]]:
    queries: list[dict[str, Any]] = []
    if "trace_id" in missing_fields:
        queries.append(
            {
                "tool": "query_langfuse_traces",
                "arguments_hint": {"trace_names": list(CANONICAL_TRACE_NAMES), "limit": 10},
                "rationale": "Find a concrete trace_id before diagnosing trace or judge quality.",
            }
        )
    if {"trace", "runtime", "metadata"} & set(focus):
        queries.append(
            {
                "tool": "wos.quality_lab.review_trace",
                "arguments_hint": {"trace_payload": "<fetch_langfuse_trace output>"},
                "rationale": "Use structural trace analysis for runtime, metadata, and span evidence.",
            }
        )
    if "judges" in focus or response_quality.get("raw_score_dump"):
        queries.append(
            {
                "tool": "wos.quality_lab.review_judgments",
                "arguments_hint": {"trace_scores_payload": "<fetch_langfuse_trace_scores output>"},
                "rationale": "Convert categorical judge scores into severity, coverage, and repair areas.",
            }
        )
    if wrong_assumptions:
        queries.append(
            {
                "tool": "wos.quality_lab.review_mcp_exchange",
                "arguments_hint": {"request": "<corrected request>", "response": "<new response>"},
                "rationale": "Re-check the corrected exchange after removing stale assumptions.",
            }
        )

    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for query in queries:
        key = (query["tool"], query["rationale"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(query)
    return unique


def _improvement_candidates(
    *,
    missing_context: list[dict[str, str]],
    wrong_assumptions: list[dict[str, str]],
    response_quality: Mapping[str, Any],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    def add(priority: str, repair_area: str, rationale: str, evidence_ref: str) -> None:
        candidates.append(
            {
                "priority": priority,
                "repair_area": repair_area,
                "rationale": rationale,
                "evidence_refs": [{"type": "mcp_exchange", "ref": evidence_ref}],
            }
        )

    high_missing = [m["field"] for m in missing_context if m.get("severity") == "high"]
    if high_missing:
        add(
            "high",
            "repair_mcp_request_context",
            "request is missing high-value context fields: " + ", ".join(high_missing),
            "request",
        )
    elif missing_context:
        add(
            "medium",
            "repair_mcp_request_context",
            "request is missing context fields: "
            + ", ".join(m["field"] for m in missing_context),
            "request",
        )

    if wrong_assumptions:
        add(
            "high",
            "repair_mcp_stale_assumptions",
            "exchange contains stale or incorrect assumptions: "
            + ", ".join(w["kind"] for w in wrong_assumptions),
            "request_response",
        )

    weaknesses = set(response_quality.get("weaknesses") or [])
    if "raw_score_dump_without_interpretation" in weaknesses:
        add(
            "medium",
            "repair_mcp_response_interpret_scores",
            "response dumps judge scores without category-aware interpretation",
            "response",
        )
    if "missing_deterministic_vs_judge_boundary" in weaknesses:
        add(
            "high",
            "repair_mcp_response_runtime_judge_boundary",
            "response does not keep deterministic gates separate from qualitative judge signals",
            "response",
        )
    if "missing_repair_direction" in weaknesses:
        add(
            "medium",
            "repair_mcp_response_followup_direction",
            "response does not provide repair direction or follow-up analysis",
            "response",
        )
    if "unsupported_runtime_claim" in weaknesses:
        add(
            "high",
            "repair_mcp_response_evidence_support",
            "response makes a runtime status claim without deterministic evidence",
            "response",
        )

    priority_rank = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    candidates.sort(key=lambda c: (priority_rank.get(c["priority"], 99), c["repair_area"]))
    return candidates


def _next_user_decision(
    improvement_candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not improvement_candidates:
        return None
    top = improvement_candidates[0]
    return user_decision_prompt(
        question=f"Top MCP exchange issue: {top['repair_area']}. What should happen next?",
        context_summary=top["rationale"],
        options=[
            {
                "id": "rerun_with_required_context",
                "label": "Re-run with required context",
                "description": "Supply the missing trace/session/turn evidence and repeat the analysis.",
                "ai_action": "Ask for or fetch the missing MCP evidence, then re-run the Quality Lab tool.",
                "tradeoff": "Best evidence quality, but requires another MCP call.",
                "recommended": True,
            },
            {
                "id": "accept_limited_analysis",
                "label": "Accept limited analysis",
                "description": "Keep the current response but label uncertainty and avoid runtime conclusions.",
                "ai_action": "Summarize only what is supported and mark all missing evidence explicitly.",
                "tradeoff": "Faster, but it may leave root cause unresolved.",
            },
            {
                "id": "switch_quality_lab_tool",
                "label": "Switch Quality Lab tool",
                "description": "Use review_trace or review_judgments if the exchange used the wrong surface.",
                "ai_action": "Select the Quality Lab tool that matches the focus and pass the current payload through it.",
                "tradeoff": "Improves routing but may still need missing trace evidence.",
            },
        ],
        evidence_refs=top.get("evidence_refs", []),
    )


def interpret_mcp_exchange(
    request: Mapping[str, Any] | None,
    response: Mapping[str, Any] | None,
    *,
    focus: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Analyze an MCP request/response pair per ADR-0040 Phase 3."""
    req: Mapping[str, Any] = request if _is_mapping(request) else {}
    resp: Mapping[str, Any] = response if _is_mapping(response) else {}

    normalized_focus = _normalize_focus(req, focus)
    missing_fields, missing_context = _build_missing_context(req, normalized_focus)
    wrong_assumptions = _detect_wrong_assumptions(req, resp)
    wrong_tool = _wrong_tool_for_focus(_tool_name(req), normalized_focus)
    if wrong_tool is not None:
        wrong_assumptions.append(wrong_tool)

    resp_quality = _response_quality(resp)
    req_quality = _request_quality(
        request=req,
        focus=normalized_focus,
        missing_fields=missing_fields,
        wrong_assumptions=wrong_assumptions,
    )
    followups = _followups(
        focus=normalized_focus,
        missing_fields=missing_fields,
        wrong_assumptions=wrong_assumptions,
        response_quality=resp_quality,
    )
    candidates = _improvement_candidates(
        missing_context=missing_context,
        wrong_assumptions=wrong_assumptions,
        response_quality=resp_quality,
    )

    return {
        "mcp_request_quality": req_quality,
        "mcp_response_quality": resp_quality,
        "missing_context": missing_context,
        "wrong_assumptions": wrong_assumptions,
        "recommended_followup_queries": followups,
        "improvement_candidates": candidates,
        "next_user_decision": _next_user_decision(candidates),
        "canonical_trace_names": list(CANONICAL_TRACE_NAMES),
        "deterministic_gates_remain_authoritative": True,
        "canonical_evaluator_definition_doc": "docs/llm-as-a-judge/",
    }
