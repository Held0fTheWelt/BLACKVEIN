"""Tests for ``ai_stack.quality_lab.trace_interpreter`` (ADR-0040 Phase 2).

Per ADR-0039: aspect names, expected metadata fields, and trace-name
constants are derived from canonical sources (the trace_interpreter
module's own catalog and ``ai_stack.langfuse_evaluator_catalog``) — never
from hardcoded literals in this file.
"""

from __future__ import annotations

from typing import Any

import pytest

from ai_stack.langfuse_evaluator_catalog import (
    BACKEND_TURN_ROOT_TRACE_NAME,
    WORLD_ENGINE_OPENING_TRACE_NAME,
    WORLD_ENGINE_TURN_TRACE_NAME,
)
from ai_stack.quality_lab.trace_interpreter import (
    ASPECT_NAMES,
    EXPECTED_LIVE_METADATA_FIELDS,
    classify_trace_kind,
    interpret_trace,
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _passing_aspects() -> dict[str, dict[str, Any]]:
    """Build a baseline ledger where every aspect passes (or N/A)."""
    return {
        "input": {
            "applicable": True,
            "status": "passed",
            "actual": {"raw_player_input": "x"},
        },
        "action_resolution": {
            "applicable": True,
            "status": "passed",
            "actual": {"action_commit_policy": "commit_action"},
        },
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


def _live_metadata() -> dict[str, Any]:
    return {
        field: value
        for field, value in {
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
        }.items()
    }


# ---------------------------------------------------------------------------
# classify_trace_kind
# ---------------------------------------------------------------------------


def test_classify_trace_kind_uses_canonical_constants():
    assert classify_trace_kind(WORLD_ENGINE_TURN_TRACE_NAME) == "turn"
    assert classify_trace_kind(BACKEND_TURN_ROOT_TRACE_NAME) == "turn"
    assert classify_trace_kind(WORLD_ENGINE_OPENING_TRACE_NAME) == "opening"
    assert classify_trace_kind(None) == "unknown"
    assert classify_trace_kind("some.other.span") == "unknown"


# ---------------------------------------------------------------------------
# interpret_trace — metadata coverage
# ---------------------------------------------------------------------------


def test_live_canonical_trace_qualifies_for_live_evidence():
    result = interpret_trace(
        trace_id="lf-1",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger=_passing_aspects(),
        observation_names=["story.graph.path_summary", "story.model.generation"],
    )
    assert result["live_evidence_qualified"] is True
    assert result["metadata_coverage"]["live_evidence_criteria"]["qualified"] is True
    # All required metadata fields present.
    assert set(result["metadata_coverage"]["present_fields"]) >= set(
        EXPECTED_LIVE_METADATA_FIELDS
    )
    assert result["metadata_coverage"]["missing_fields"] == []


def test_missing_canonical_player_flow_disqualifies_live_evidence():
    metadata = _live_metadata()
    metadata["canonical_player_flow"] = False
    result = interpret_trace(
        trace_id="lf-2",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=metadata,
        aspects_ledger=_passing_aspects(),
    )
    assert result["live_evidence_qualified"] is False
    assert result["metadata_coverage"]["live_evidence_criteria"]["qualified"] is False


def test_missing_metadata_fields_surfaced_as_improvement_candidate():
    metadata = _live_metadata()
    for field in ("session_id", "module_id", "canonical_turn_id"):
        metadata.pop(field, None)
    result = interpret_trace(
        trace_id="lf-3",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=metadata,
        aspects_ledger=_passing_aspects(),
        observation_names=["story.graph.path_summary", "story.model.generation"],
    )
    missing = set(result["metadata_coverage"]["missing_fields"])
    assert {"session_id", "module_id", "canonical_turn_id"} <= missing
    repair_areas = {c["repair_area"] for c in result["improvement_candidates"]}
    assert "repair_trace_metadata_coverage" in repair_areas


# ---------------------------------------------------------------------------
# runtime_aspect_summary
# ---------------------------------------------------------------------------


def test_runtime_aspect_summary_classifies_failed_partial_not_applicable():
    aspects = _passing_aspects()
    aspects["beat"]["status"] = "failed"
    aspects["beat"]["failure_reason"] = "beat_realization_not_visible"
    aspects["beat"]["actual"]["realized"] = False
    aspects["capability_selection"]["status"] = "partial"
    aspects["capability_selection"]["failure_reason"] = "missing_capability"
    result = interpret_trace(
        trace_id="lf-4",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger=aspects,
    )
    summary = result["runtime_aspect_summary"]
    assert "beat" in summary["failed_aspects"]
    assert "capability_selection" in summary["partial_aspects"]
    assert "narrator_authority" in summary["not_applicable_aspects"]
    # Every catalogued aspect appears in the state map.
    assert set(summary["aspect_states"].keys()) == set(ASPECT_NAMES)
    # primary_failure surfaces from the first failed aspect's failure_reason.
    assert summary["primary_failure"] == "beat_realization_not_visible"


def test_empty_ledger_marks_all_aspects_missing():
    result = interpret_trace(
        trace_id="lf-empty",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger={},
    )
    summary = result["runtime_aspect_summary"]
    assert set(summary["missing_aspects"]) == set(ASPECT_NAMES)
    assert summary["failed_aspects"] == []
    assert summary["primary_failure"] is None


# ---------------------------------------------------------------------------
# beat_capability_realization
# ---------------------------------------------------------------------------


def test_beat_not_realized_drives_high_priority_repair():
    aspects = _passing_aspects()
    aspects["beat"]["status"] = "partial"
    aspects["beat"]["failure_reason"] = "beat_realization_not_visible"
    aspects["beat"]["lost_at_stage"] = "visible_projection"
    aspects["beat"]["actual"]["realized"] = False
    result = interpret_trace(
        trace_id="lf-5",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger=aspects,
    )
    bc = result["beat_capability_realization"]
    assert bc["selected_beat"] == "beat-1"
    assert bc["beat_realized"] is False
    assert bc["beat_lost_at_stage"] == "visible_projection"
    priorities = {c["repair_area"]: c["priority"] for c in result["improvement_candidates"]}
    assert priorities.get("repair_beat_realization") == "high"


def test_forbidden_capability_realized_is_urgent_repair():
    aspects = _passing_aspects()
    aspects["capability_selection"]["actual"]["forbidden_capability_realized"] = True
    result = interpret_trace(
        trace_id="lf-6",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger=aspects,
    )
    repairs = {c["repair_area"]: c["priority"] for c in result["improvement_candidates"]}
    assert repairs.get("repair_capability_selection_block_forbidden_realization") == "urgent"


def test_missing_required_capabilities_listed_in_diagnosis():
    aspects = _passing_aspects()
    aspects["capability_selection"]["actual"]["missing_required_capabilities"] = [
        "narrator.action_consequence.describe"
    ]
    result = interpret_trace(
        trace_id="lf-7",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger=aspects,
    )
    bc = result["beat_capability_realization"]
    assert bc["missing_required_capabilities"] == ["narrator.action_consequence.describe"]
    repairs = [c["repair_area"] for c in result["improvement_candidates"]]
    assert "repair_capability_selection_realize_required" in repairs


# ---------------------------------------------------------------------------
# authority_clusters
# ---------------------------------------------------------------------------


def test_npc_takeover_is_urgent_repair():
    aspects = _passing_aspects()
    aspects["npc_authority"]["status"] = "failed"
    aspects["npc_authority"]["actual"]["npc_takeover_detected"] = True
    result = interpret_trace(
        trace_id="lf-8",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger=aspects,
    )
    npc = result["authority_clusters"]["npc"]
    assert npc["takeover_detected"] is True
    assert npc["policy_fulfilled"] is False
    repairs = {c["repair_area"]: c["priority"] for c in result["improvement_candidates"]}
    assert repairs.get("repair_npc_authority_prevent_takeover") == "urgent"


def test_narrator_required_but_absent_is_urgent_repair():
    aspects = _passing_aspects()
    aspects["narrator_authority"] = {
        "applicable": True,
        "status": "failed",
        "expected": {"required": True},
        "actual": {"narrator_block_present": False, "consequence_realized": False},
        "failure_reason": "narrator_required_missing",
    }
    result = interpret_trace(
        trace_id="lf-9",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger=aspects,
    )
    narrator = result["authority_clusters"]["narrator"]
    assert narrator["required"] is True
    assert narrator["present"] is False
    assert narrator["fulfilled"] is False
    repairs = {c["repair_area"]: c["priority"] for c in result["improvement_candidates"]}
    assert repairs.get("repair_narrator_authority_required_consequence") == "urgent"


# ---------------------------------------------------------------------------
# span_anomalies
# ---------------------------------------------------------------------------


def test_turn_trace_without_path_summary_observation_flagged():
    result = interpret_trace(
        trace_id="lf-10",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger=_passing_aspects(),
        observation_names=[],
    )
    kinds = {a["kind"] for a in result["span_anomalies"]}
    assert "missing_expected_span" in kinds


def test_live_generation_mode_without_generation_observation_flagged():
    metadata = _live_metadata()
    metadata["generation_mode"] = "openai_live"
    result = interpret_trace(
        trace_id="lf-11",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=metadata,
        aspects_ledger=_passing_aspects(),
        observation_names=["story.graph.path_summary"],
    )
    kinds = {a["kind"] for a in result["span_anomalies"]}
    assert "missing_generation_observation" in kinds


def test_mock_generation_mode_does_not_require_generation_observation():
    metadata = _live_metadata()
    metadata["generation_mode"] = "ldss_fallback"
    result = interpret_trace(
        trace_id="lf-12",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=metadata,
        aspects_ledger=_passing_aspects(),
        observation_names=["story.graph.path_summary"],
    )
    kinds = {a["kind"] for a in result["span_anomalies"]}
    assert "missing_generation_observation" not in kinds


def test_no_ledger_flags_missing_turn_aspect_ledger():
    result = interpret_trace(
        trace_id="lf-13",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger={},
    )
    kinds = {a["kind"] for a in result["span_anomalies"]}
    assert "missing_turn_aspect_ledger" in kinds


# ---------------------------------------------------------------------------
# next_user_decision
# ---------------------------------------------------------------------------


def test_healthy_trace_produces_no_decision_prompt():
    result = interpret_trace(
        trace_id="lf-14",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger=_passing_aspects(),
        observation_names=["story.graph.path_summary", "story.model.generation"],
    )
    assert result["improvement_candidates"] == []
    assert result["next_user_decision"] is None


def test_decision_prompt_recommends_top_repair_area_with_required_fields():
    aspects = _passing_aspects()
    aspects["npc_authority"]["actual"]["npc_takeover_detected"] = True
    aspects["npc_authority"]["status"] = "failed"
    result = interpret_trace(
        trace_id="lf-15",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger=aspects,
        observation_names=["story.graph.path_summary", "story.model.generation"],
    )
    decision = result["next_user_decision"]
    assert decision is not None
    assert decision["requires_user_decision"] is True
    recommended = [o for o in decision["decision_options"] if o["recommended"]]
    assert len(recommended) == 1
    for option in decision["decision_options"]:
        assert option["ai_action"], "ai_action must be specific"
    refs = decision["evidence_refs"]
    assert any(r["type"] == "langfuse_trace" and r["ref"] == "lf-15" for r in refs)


def test_no_ledger_decision_prompt_recommends_live_evidence_audit():
    result = interpret_trace(
        trace_id="lf-16",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger={},
    )
    decision = result["next_user_decision"]
    assert decision is not None
    recommended_ids = [o["id"] for o in decision["decision_options"] if o["recommended"]]
    assert recommended_ids == ["verify_live_evidence_criteria"]


# ---------------------------------------------------------------------------
# Authoritative flags
# ---------------------------------------------------------------------------


def test_output_carries_authoritative_flags():
    result = interpret_trace(
        trace_id="lf-17",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,
        trace_metadata=_live_metadata(),
        aspects_ledger=_passing_aspects(),
    )
    assert result["deterministic_gates_remain_authoritative"] is True
    assert result["canonical_evaluator_definition_doc"] == "docs/llm-as-a-judge/"


def test_is_opening_argument_overrides_trace_name_classification():
    result = interpret_trace(
        trace_id="lf-18",
        trace_name=WORLD_ENGINE_TURN_TRACE_NAME,  # would normally classify as "turn"
        trace_metadata=_live_metadata(),
        aspects_ledger=_passing_aspects(),
        is_opening=True,
    )
    assert result["trace_kind"] == "opening"
    assert result["is_opening_trace"] is True
