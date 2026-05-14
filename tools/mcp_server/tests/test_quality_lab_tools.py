"""Tests for ``wos.quality_lab.*`` MCP handlers (ADR-0040 Phases 1-5).

Expected judge names, categories, aspect names, and trace names are
derived from canonical catalogs (`ai_stack.langfuse_evaluator_catalog`,
`ai_stack.quality_lab.trace_interpreter`, Quality Lab constants) per ADR-0039 — no hardcoded
literals in this file.
"""

from __future__ import annotations

from typing import Any

import pytest

from ai_stack.langfuse_evaluator_catalog import (
    BACKEND_TURN_ROOT_TRACE_NAME,
    WORLD_ENGINE_OPENING_TRACE_NAME,
    WORLD_ENGINE_TURN_TRACE_NAME,
)
from ai_stack.mcp_canonical_surface import (
    AUTH_QUALITY_LAB_ANALYSIS,
    CANONICAL_MCP_TOOL_DESCRIPTORS,
    McpSuite,
    McpToolClass,
    canonical_mcp_tool_descriptors_by_name,
)
from ai_stack.quality_lab.evaluator_catalog import (
    evaluator_view,
    evaluator_views_for_scope,
    list_evaluator_views,
)
from ai_stack.quality_lab.mcp_exchange_interpreter import (
    REQUIRED_REQUEST_CONTEXT_FIELDS,
)
from ai_stack.quality_lab.pattern_interpreter import (
    QUALITY_LAB_PATTERN_TOOL_NAMES,
)
from ai_stack.quality_lab.planning_interpreter import (
    QUALITY_LAB_PLANNING_TOOL_NAMES,
)
from ai_stack.quality_lab.trace_interpreter import (
    ASPECT_NAMES,
    EXPECTED_LIVE_METADATA_FIELDS,
)
from tools.mcp_server.tools_registry_handlers_quality_lab import (
    build_quality_lab_mcp_handlers,
)


# ---------------------------------------------------------------------------
# Canonical surface registration
# ---------------------------------------------------------------------------


def test_quality_lab_tool_registered_in_canonical_surface():
    by_name = canonical_mcp_tool_descriptors_by_name()
    desc = by_name.get("wos.quality_lab.review_judgments")
    assert desc is not None, "wos.quality_lab.review_judgments missing from canonical surface"
    assert desc.tool_class is McpToolClass.read_only
    assert desc.mcp_suite is McpSuite.wos_runtime_read
    assert desc.authority_source == AUTH_QUALITY_LAB_ANALYSIS


def test_quality_lab_canonical_surface_has_no_mutation_risk():
    desc = canonical_mcp_tool_descriptors_by_name()["wos.quality_lab.review_judgments"]
    # Read-only tools must not advertise direct mutation risk.
    assert "mutation" not in desc.narrative_mutation_risk.lower() or \
        desc.narrative_mutation_risk == "none_observation_only"


# ---------------------------------------------------------------------------
# Handler behavior
# ---------------------------------------------------------------------------


def _registry() -> dict:
    return build_quality_lab_mcp_handlers()


def _pick_judge_with_failure(scope: str) -> tuple[str, str]:
    for view in evaluator_views_for_scope(scope):
        members = sorted(view.severity_buckets.get("failure") or ())
        if members:
            return view.name, members[0]
    raise AssertionError(f"no failure-capable judge in scope {scope}")


def test_handler_rejects_non_dict_arguments():
    handler = _registry()["wos.quality_lab.review_judgments"]
    out = handler("not a dict")
    assert out["ok"] is False
    assert out["error"]["code"] == "invalid_input"


def test_handler_rejects_empty_scores():
    handler = _registry()["wos.quality_lab.review_judgments"]
    out = handler({})
    assert out["ok"] is False
    assert out["error"]["code"] == "no_scores_provided"


def test_handler_accepts_direct_scores_with_failure_category():
    handler = _registry()["wos.quality_lab.review_judgments"]
    judge, failure_cat = _pick_judge_with_failure("turn_generation")
    out = handler({
        "scores": {judge: {"category": failure_cat, "reasoning": "fixture"}},
        "is_opening": False,
    })
    assert out["ok"] is True
    [interp] = out["judge_interpretations"]
    assert interp["judge"] == judge
    assert interp["severity"] == "failure"
    assert out["qualitative_issue_clusters"]
    assert out["improvement_candidates"]
    assert out["deterministic_gates_remain_authoritative"] is True


def test_handler_accepts_fetch_langfuse_trace_scores_payload_shape():
    """The compose-and-extend contract: pass through a fetch_langfuse_trace_scores
    response and the handler extracts scores + is_opening_trace."""
    handler = _registry()["wos.quality_lab.review_judgments"]
    judge, failure_cat = _pick_judge_with_failure("opening_generation")
    payload = {
        "ok": True,
        "trace_id": "lf-test-1",
        "is_opening_trace": True,
        "judge_scores": {judge: {"category": failure_cat}},
        "deterministic_scores": {"live_opening_contract_pass": 1.0},
    }
    out = handler({"trace_scores_payload": payload})
    assert out["ok"] is True
    [interp] = out["judge_interpretations"]
    assert interp["severity"] == "failure"
    # Missing-judge detection should use the opening scope, not turn scope.
    missing = set(out["missing_judges"])
    opening_names = {v.name for v in evaluator_views_for_scope("opening_generation")}
    turn_only = {v.name for v in evaluator_views_for_scope("turn_generation")} - opening_names
    assert not (missing & turn_only)


def test_handler_surfaces_unknown_judges_without_failing():
    handler = _registry()["wos.quality_lab.review_judgments"]
    out = handler({"scores": {"not_a_real_judge": {"category": "x"}}})
    # Unknown-judge alone still leaves no real scores → coverage-gap path.
    assert out["ok"] is True
    assert out["unknown_judges"] == ["not_a_real_judge"]
    assert out["judge_interpretations"] == []


def test_handler_respects_explicit_expected_judge_names_override():
    handler = _registry()["wos.quality_lab.review_judgments"]
    view = next(iter(list_evaluator_views()))
    positive = sorted(view.severity_buckets.get("positive") or ())
    assert positive, "fixture: first judge has a positive category"
    out = handler({
        "scores": {view.name: {"category": positive[0]}},
        "expected_judge_names": [view.name],
    })
    assert out["ok"] is True
    assert out["missing_judges"] == []


# ===========================================================================
# Phase 2 — wos.quality_lab.review_trace
# ===========================================================================


def _live_metadata() -> dict[str, Any]:
    return {
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "session_id": "ses-1",
        "canonical_turn_id": "ses-1:turn:1",
        "environment": "live",
        "module_id": "god_of_carnage",
        "turn_number": 1,
        "turn_kind": "player",
        "runtime_mode": "live_runtime",
        "generation_mode": "openai_live",
    }


def _passing_aspects() -> dict[str, Any]:
    return {
        "input": {"applicable": True, "status": "passed", "actual": {"raw_player_input": "x"}},
        "action_resolution": {"applicable": True, "status": "passed", "actual": {}},
        "beat": {
            "applicable": True,
            "status": "passed",
            "selected": {"selected_beat_id": "beat-1"},
            "actual": {"realized": True},
        },
        "capability_selection": {
            "applicable": True,
            "status": "passed",
            "selected": {"selected_capabilities": ["player.speech.request"]},
            "actual": {
                "realized_capabilities": ["player.speech.request"],
                "missing_required_capabilities": [],
                "forbidden_capability_realized": False,
            },
        },
        "narrator_authority": {
            "applicable": False,
            "status": "not_applicable",
            "expected": {"required": False},
            "actual": {},
        },
        "npc_authority": {
            "applicable": True,
            "status": "passed",
            "expected": {"policy": "direct_response"},
            "actual": {"npc_takeover_detected": False},
        },
        "narrative_aspect": {"applicable": False, "status": "not_applicable"},
        "hierarchical_memory": {"applicable": False, "status": "not_applicable"},
        "validation": {"applicable": True, "status": "passed"},
        "commit": {"applicable": True, "status": "passed"},
        "visible_projection": {
            "applicable": True,
            "status": "passed",
            "actual": {"visible_block_origin_present": True},
        },
    }


def _raw_turn_trace(
    *,
    trace_id: str = "lf-turn-1",
    trace_name: str | None = None,
    metadata: dict[str, Any] | None = None,
    aspects: dict[str, Any] | None = None,
    observation_names: tuple[str, ...] = ("story.graph.path_summary", "story.model.generation"),
) -> dict[str, Any]:
    return {
        "id": trace_id,
        "name": trace_name or WORLD_ENGINE_TURN_TRACE_NAME,
        "environment": "live",
        "metadata": dict(metadata or _live_metadata()),
        "output": {
            "contract": "story_runtime_path_observability.v1",
            "turn_aspect_ledger": {
                "session_id": (metadata or _live_metadata()).get("session_id"),
                "canonical_turn_id": (metadata or _live_metadata()).get("canonical_turn_id"),
                "turn_number": (metadata or _live_metadata()).get("turn_number"),
                "turn_aspect_ledger": dict(aspects or _passing_aspects()),
            },
        },
        "observations": [{"name": name} for name in observation_names],
    }


def test_review_trace_registered_in_canonical_surface():
    by_name = canonical_mcp_tool_descriptors_by_name()
    desc = by_name.get("wos.quality_lab.review_trace")
    assert desc is not None, "wos.quality_lab.review_trace missing from canonical surface"
    assert desc.tool_class is McpToolClass.read_only
    assert desc.mcp_suite is McpSuite.wos_runtime_read
    assert desc.authority_source == AUTH_QUALITY_LAB_ANALYSIS


def test_review_trace_rejects_non_dict_arguments():
    handler = _registry()["wos.quality_lab.review_trace"]
    out = handler("not a dict")
    assert out["ok"] is False
    assert out["error"]["code"] == "invalid_input"


def test_review_trace_rejects_missing_trace():
    handler = _registry()["wos.quality_lab.review_trace"]
    out = handler({})
    assert out["ok"] is False
    assert out["error"]["code"] == "no_trace_provided"


def test_review_trace_accepts_raw_trace_directly():
    handler = _registry()["wos.quality_lab.review_trace"]
    raw = _raw_turn_trace()
    out = handler({"raw_trace": raw})
    assert out["ok"] is True
    assert out["trace_id"] == "lf-turn-1"
    assert out["trace_kind"] == "turn"
    assert out["live_evidence_qualified"] is True
    assert out["deterministic_gates_remain_authoritative"] is True
    # Aspect coverage spans the canonical aspect set.
    assert set(out["runtime_aspect_summary"]["aspect_states"].keys()) == set(ASPECT_NAMES)
    assert out["improvement_candidates"] == []
    assert out["next_user_decision"] is None


def test_review_trace_accepts_fetch_langfuse_trace_payload_shape():
    """Compose-and-extend: pass the full fetch_langfuse_trace output."""
    handler = _registry()["wos.quality_lab.review_trace"]
    raw = _raw_turn_trace(trace_id="lf-payload-1")
    payload = {
        "ok": True,
        "trace": {"trace_id": "lf-payload-1", "name": raw["name"]},
        "raw_trace": raw,
        "normalized_wos_evidence": {"session_id": "ses-1"},
        "evidence_sources": {"score_source": "trace.scores"},
    }
    out = handler({"trace_payload": payload})
    assert out["ok"] is True
    assert out["trace_id"] == "lf-payload-1"


def test_review_trace_surfaces_npc_takeover_as_urgent():
    handler = _registry()["wos.quality_lab.review_trace"]
    aspects = _passing_aspects()
    aspects["npc_authority"]["status"] = "failed"
    aspects["npc_authority"]["actual"]["npc_takeover_detected"] = True
    aspects["npc_authority"]["failure_reason"] = "npc_executed_player_action"
    out = handler({"raw_trace": _raw_turn_trace(aspects=aspects)})
    assert out["ok"] is True
    repairs = {c["repair_area"]: c["priority"] for c in out["improvement_candidates"]}
    assert repairs.get("repair_npc_authority_prevent_takeover") == "urgent"
    decision = out["next_user_decision"]
    assert decision is not None
    recommended = [o for o in decision["decision_options"] if o["recommended"]]
    assert len(recommended) == 1


def test_review_trace_detects_missing_generation_observation_when_live():
    handler = _registry()["wos.quality_lab.review_trace"]
    raw = _raw_turn_trace(observation_names=("story.graph.path_summary",))
    out = handler({"raw_trace": raw})
    assert out["ok"] is True
    kinds = {a["kind"] for a in out["span_anomalies"]}
    assert "missing_generation_observation" in kinds


def test_review_trace_classifies_opening_traces_by_canonical_name():
    handler = _registry()["wos.quality_lab.review_trace"]
    metadata = _live_metadata()
    metadata["turn_kind"] = "opening"
    metadata["turn_number"] = 0
    raw = _raw_turn_trace(
        trace_id="lf-opening-1",
        trace_name=WORLD_ENGINE_OPENING_TRACE_NAME,
        metadata=metadata,
        observation_names=("story.model.generation",),
    )
    out = handler({"raw_trace": raw})
    assert out["ok"] is True
    assert out["trace_kind"] == "opening"
    assert out["is_opening_trace"] is True
    # Opening traces don't require path_summary observation by Quality Lab rules.
    kinds = {a["kind"] for a in out["span_anomalies"]}
    assert "missing_expected_span" not in kinds


def test_review_trace_metadata_coverage_lists_canonical_fields():
    handler = _registry()["wos.quality_lab.review_trace"]
    raw = _raw_turn_trace()
    out = handler({"raw_trace": raw})
    present = set(out["metadata_coverage"]["present_fields"])
    # Every canonical field is accounted for (present or missing).
    assert present.union(out["metadata_coverage"]["missing_fields"]) >= set(
        EXPECTED_LIVE_METADATA_FIELDS
    )


# ===========================================================================
# Phase 3 — wos.quality_lab.review_mcp_exchange
# ===========================================================================


def _complete_exchange_request(tool: str = "wos.quality_lab.review_mcp_exchange") -> dict[str, Any]:
    return {
        "tool": tool,
        "focus": ["mcp_quality"],
        "arguments": {
            "trace_id": "lf-exchange-1",
            "session_id": "ses-1",
            "turn_id": "turn-1",
            "actor": "annette",
            "context": {"source": "test"},
        },
    }


def _useful_exchange_response() -> dict[str, Any]:
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


def test_review_mcp_exchange_registered_in_canonical_surface():
    by_name = canonical_mcp_tool_descriptors_by_name()
    desc = by_name.get("wos.quality_lab.review_mcp_exchange")
    assert desc is not None, "wos.quality_lab.review_mcp_exchange missing from canonical surface"
    assert desc.tool_class is McpToolClass.read_only
    assert desc.mcp_suite is McpSuite.wos_runtime_read
    assert desc.authority_source == AUTH_QUALITY_LAB_ANALYSIS


def test_review_mcp_exchange_rejects_non_dict_arguments():
    handler = _registry()["wos.quality_lab.review_mcp_exchange"]
    out = handler("not a dict")
    assert out["ok"] is False
    assert out["error"]["code"] == "invalid_input"


def test_review_mcp_exchange_rejects_missing_exchange():
    handler = _registry()["wos.quality_lab.review_mcp_exchange"]
    out = handler({})
    assert out["ok"] is False
    assert out["error"]["code"] == "no_exchange_provided"


def test_review_mcp_exchange_accepts_request_response_pair():
    handler = _registry()["wos.quality_lab.review_mcp_exchange"]
    out = handler({
        "request": _complete_exchange_request(),
        "response": _useful_exchange_response(),
    })
    assert out["ok"] is True
    assert out["mcp_request_quality"]["status"] == "actionable"
    assert out["mcp_response_quality"]["status"] == "useful"
    assert out["improvement_candidates"] == []
    assert out["deterministic_gates_remain_authoritative"] is True


def test_review_mcp_exchange_surfaces_missing_context_from_request():
    handler = _registry()["wos.quality_lab.review_mcp_exchange"]
    out = handler({
        "request": {"tool": "wos.quality_lab.review_trace", "focus": ["trace"], "arguments": {}},
        "response": {"ok": True},
    })
    assert out["ok"] is True
    missing = {entry["field"] for entry in out["missing_context"]}
    assert missing == set(REQUIRED_REQUEST_CONTEXT_FIELDS)
    assert out["next_user_decision"] is not None


def test_review_mcp_exchange_detects_stale_backend_trace_rejection():
    handler = _registry()["wos.quality_lab.review_mcp_exchange"]
    request = _complete_exchange_request("wos.quality_lab.review_trace")
    request["focus"] = ["trace"]
    request["arguments"]["trace_name"] = BACKEND_TURN_ROOT_TRACE_NAME
    out = handler({
        "request": request,
        "response": {
            **_useful_exchange_response(),
            "analysis": (
                f"Reject {BACKEND_TURN_ROOT_TRACE_NAME}; only "
                f"{WORLD_ENGINE_TURN_TRACE_NAME} is canonical."
            ),
        },
    })
    assert out["ok"] is True
    kinds = {entry["kind"] for entry in out["wrong_assumptions"]}
    assert "stale_trace_name_assumption" in kinds


def test_review_mcp_exchange_detects_raw_score_dump_response():
    handler = _registry()["wos.quality_lab.review_mcp_exchange"]
    view = next(iter(list_evaluator_views()))
    out = handler({
        "request": _complete_exchange_request("fetch_langfuse_trace_scores"),
        "response": {"ok": True, "judge_scores": {view.name: {"category": view.categories[0]}}},
        "focus": ["judges"],
    })
    assert out["ok"] is True
    assert out["mcp_response_quality"]["raw_score_dump"] is True
    repairs = {c["repair_area"] for c in out["improvement_candidates"]}
    assert "repair_mcp_response_interpret_scores" in repairs


# ===========================================================================
# Phases 4 & 5 — clustering, investigation, repair, judge, content planning
# ===========================================================================


def test_phase4_phase5_tools_registered_in_canonical_surface():
    by_name = canonical_mcp_tool_descriptors_by_name()
    for tool_name in (*QUALITY_LAB_PATTERN_TOOL_NAMES, *QUALITY_LAB_PLANNING_TOOL_NAMES):
        desc = by_name.get(tool_name)
        assert desc is not None, f"{tool_name} missing from canonical surface"
        assert desc.tool_class is McpToolClass.read_only
        assert desc.mcp_suite is McpSuite.wos_runtime_read
        assert desc.authority_source == AUTH_QUALITY_LAB_ANALYSIS


def test_find_patterns_handler_groups_repeated_repair_area():
    handler = _registry()["wos.quality_lab.find_patterns"]
    out = handler({
        "trace_summaries": [
            {"trace_id": "lf-1", "improvement_candidates": [{"repair_area": "runtime_authority"}]},
            {"trace_id": "lf-2", "improvement_candidates": [{"repair_area": "runtime_authority"}]},
        ],
        "cluster_by": ["runtime_area"],
        "include_claude_context": True,
    })
    assert out["ok"] is True
    assert out["recurring_patterns"]
    assert out["claude_context_queries"]


def test_suggest_investigation_handler_requires_problem_cluster():
    handler = _registry()["wos.quality_lab.suggest_investigation"]
    out = handler({})
    assert out["ok"] is False
    assert out["error"]["code"] == "no_problem_cluster_provided"


def test_suggest_investigation_handler_builds_followups():
    handler = _registry()["wos.quality_lab.suggest_investigation"]
    out = handler({
        "problem_cluster": {
            "title": "Recurring runtime authority",
            "affected_areas": ["runtime_authority"],
            "affected_traces": ["lf-1"],
        },
        "include_claude_context": True,
    })
    assert out["ok"] is True
    assert out["hypotheses"]
    assert out["mcp_followup_tools"]
    assert out["user_decision"]["requires_user_decision"] is True


def test_plan_repair_wave_handler_outputs_read_only_plan():
    handler = _registry()["wos.quality_lab.plan_repair_wave"]
    out = handler({
        "improvement_candidates": [
            {"candidate_id": "c1", "repair_area": "runtime_authority", "priority": "high"}
        ],
        "constraints": {"no_runtime_gate_weakening": True},
    })
    assert out["ok"] is True
    assert out["repair_waves"]
    assert out["deterministic_gates_remain_authoritative"] is True


def test_refine_judge_set_handler_uses_catalog_judge():
    handler = _registry()["wos.quality_lab.refine_judge_set"]
    view = next(iter(list_evaluator_views()))
    out = handler({
        "judge_names": [view.name],
        "observed_failures": [{"judge": view.name, "affected_area": view.group}],
        "examples": [{"input": "fixture", "output": "fixture"}],
    })
    assert out["ok"] is True
    assert out["prompt_delta_proposals"]
    assert out["requires_user_review"] is True


def test_plan_content_revision_handler_builds_tasks():
    handler = _registry()["wos.quality_lab.plan_content_revision"]
    out = handler({
        "content_module": "god_of_carnage",
        "quality_findings": [
            {"source": "content", "affected_area": "relationship_pressure"}
        ],
        "include_claude_context": True,
    })
    assert out["ok"] is True
    assert out["content_gap_hypotheses"]
    assert out["content_revision_tasks"]
    assert out["claude_context_queries"]
