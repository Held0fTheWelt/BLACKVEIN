"""Tests for ``ai_stack.quality_lab.mcp_exchange_interpreter`` (ADR-0040 Phase 3).

Per ADR-0039-style discipline, focus areas, required context fields, and
trace names are imported from canonical Quality Lab/runtime constants.
"""

from __future__ import annotations

from ai_stack.langfuse_evaluator_catalog import (
    BACKEND_TURN_ROOT_TRACE_NAME,
    WORLD_ENGINE_TURN_TRACE_NAME,
)
from ai_stack.quality_lab.evaluator_catalog import list_evaluator_views
from ai_stack.quality_lab.mcp_exchange_interpreter import (
    CANONICAL_TRACE_NAMES,
    MCP_EXCHANGE_FOCUS_AREAS,
    REQUIRED_REQUEST_CONTEXT_FIELDS,
    interpret_mcp_exchange,
)


def _complete_request(*, tool: str = "wos.quality_lab.review_mcp_exchange") -> dict:
    return {
        "tool": tool,
        "focus": ["mcp_quality"],
        "arguments": {
            "trace_id": "lf-1",
            "session_id": "ses-1",
            "turn_id": "turn-1",
            "actor": "annette",
            "context": {"source": "test"},
        },
    }


def _useful_response() -> dict:
    return {
        "ok": True,
        "mcp_request_quality": {"status": "actionable"},
        "mcp_response_quality": {"status": "useful"},
        "missing_context": [],
        "wrong_assumptions": [],
        "recommended_followup_queries": [],
        "improvement_candidates": [],
        "canonical_evaluator_definition_doc": "docs/llm-as-a-judge/",
        "deterministic_gates_remain_authoritative": True,
    }


def test_canonical_constants_are_exposed_for_tests_and_callers():
    assert "mcp_quality" in MCP_EXCHANGE_FOCUS_AREAS
    assert set(CANONICAL_TRACE_NAMES) >= {
        BACKEND_TURN_ROOT_TRACE_NAME,
        WORLD_ENGINE_TURN_TRACE_NAME,
    }
    assert REQUIRED_REQUEST_CONTEXT_FIELDS


def test_complete_exchange_is_actionable_and_needs_no_repair():
    result = interpret_mcp_exchange(_complete_request(), _useful_response())

    assert result["mcp_request_quality"]["status"] == "actionable"
    assert result["mcp_response_quality"]["status"] == "useful"
    assert result["missing_context"] == []
    assert result["wrong_assumptions"] == []
    assert result["improvement_candidates"] == []
    assert result["next_user_decision"] is None


def test_trace_focused_request_lists_missing_context_fields():
    result = interpret_mcp_exchange(
        {"tool": "wos.quality_lab.review_trace", "focus": ["trace"], "arguments": {}},
        {"ok": True},
    )

    missing = {entry["field"] for entry in result["missing_context"]}
    assert missing == set(REQUIRED_REQUEST_CONTEXT_FIELDS)
    assert result["mcp_request_quality"]["status"] == "insufficient_context"
    assert any(q["tool"] == "query_langfuse_traces" for q in result["recommended_followup_queries"])


def test_stale_backend_trace_rejection_is_flagged_as_wrong_assumption():
    request = _complete_request(tool="wos.quality_lab.review_trace")
    request["focus"] = ["trace"]
    request["arguments"]["trace_name"] = BACKEND_TURN_ROOT_TRACE_NAME
    response = {
        **_useful_response(),
        "analysis": (
            f"Reject {BACKEND_TURN_ROOT_TRACE_NAME}; only "
            f"{WORLD_ENGINE_TURN_TRACE_NAME} is canonical."
        ),
    }

    result = interpret_mcp_exchange(request, response)

    kinds = {entry["kind"] for entry in result["wrong_assumptions"]}
    assert "stale_trace_name_assumption" in kinds
    repairs = {c["repair_area"]: c["priority"] for c in result["improvement_candidates"]}
    assert repairs["repair_mcp_stale_assumptions"] == "high"


def test_judge_score_dump_without_interpretation_is_weak_response():
    view = next(iter(list_evaluator_views()))
    request = _complete_request(tool="fetch_langfuse_trace_scores")
    request["focus"] = ["judges"]
    response = {
        "ok": True,
        "judge_scores": {view.name: {"category": view.categories[0]}},
        "deterministic_scores": {"live_runtime_contract_pass": 1.0},
    }

    result = interpret_mcp_exchange(request, response)

    quality = result["mcp_response_quality"]
    assert quality["status"] == "weak"
    assert quality["raw_score_dump"] is True
    repairs = {c["repair_area"] for c in result["improvement_candidates"]}
    assert "repair_mcp_response_interpret_scores" in repairs
    assert any(q["tool"] == "wos.quality_lab.review_judgments" for q in result["recommended_followup_queries"])


def test_judge_gate_confusion_preserves_deterministic_authority():
    request = _complete_request()
    response = {
        **_useful_response(),
        "analysis": "The judge proves runtime gate pass and can replace deterministic checks.",
    }

    result = interpret_mcp_exchange(request, response)

    kinds = {entry["kind"] for entry in result["wrong_assumptions"]}
    assert "judge_gate_confusion" in kinds
    assert result["deterministic_gates_remain_authoritative"] is True


def test_wrong_quality_lab_tool_for_trace_focus_is_reported():
    request = _complete_request(tool="wos.quality_lab.review_judgments")
    request["focus"] = ["trace", "runtime", "metadata"]

    result = interpret_mcp_exchange(request, _useful_response())

    wrong = {entry["kind"]: entry for entry in result["wrong_assumptions"]}
    assert "wrong_tool_for_focus" in wrong
    assert "review_trace" in wrong["wrong_tool_for_focus"]["suggested_correction"]


def test_unsupported_runtime_claim_is_high_priority_response_issue():
    request = _complete_request()
    response = {
        "ok": True,
        "analysis": "Runtime is healthy; gate passed.",
        "improvement_candidates": [],
    }

    result = interpret_mcp_exchange(request, response)

    assert result["mcp_response_quality"]["status"] == "unsupported"
    repairs = {c["repair_area"]: c["priority"] for c in result["improvement_candidates"]}
    assert repairs["repair_mcp_response_evidence_support"] == "high"


def test_next_user_decision_has_single_recommended_option_when_action_needed():
    result = interpret_mcp_exchange(
        {"tool": "wos.quality_lab.review_trace", "focus": ["trace"], "arguments": {}},
        {"ok": True},
    )

    decision = result["next_user_decision"]
    assert decision is not None
    recommended = [o for o in decision["decision_options"] if o["recommended"]]
    assert len(recommended) == 1


def test_output_carries_authoritative_flags_and_canonical_trace_names():
    result = interpret_mcp_exchange(_complete_request(), _useful_response())

    assert result["canonical_evaluator_definition_doc"] == "docs/llm-as-a-judge/"
    assert result["deterministic_gates_remain_authoritative"] is True
    assert set(result["canonical_trace_names"]) == set(CANONICAL_TRACE_NAMES)
