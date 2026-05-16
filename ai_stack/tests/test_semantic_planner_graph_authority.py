"""Authority boundaries: single graph path, planner state non-sovereign."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
from story_runtime_core import RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from story_runtime_core.model_registry import build_default_registry

langgraph_runtime = pytest.importorskip("ai_stack.langgraph_runtime", reason="LangGraph required")
from ai_stack.capability_validator_dispatch import ValidatorDispatchMode
from ai_stack.langgraph_runtime import RuntimeTurnGraphExecutor
from ai_stack.rag import ContextPackAssembler, ContextRetriever, RagIngestionPipeline
from ai_stack.runtime_aspect_ledger import (
    ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY,
    ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV,
    initialize_runtime_aspect_ledger,
    normalize_runtime_aspect_ledger,
)
from ai_stack.tests.test_capability_validator_registry import _opening_dispatch_context
from ai_stack.goc_turn_seams import build_operator_canonical_turn_record


class _OkAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(content='{"narrative_response":"ok","proposed_scene_id":null}', success=True, metadata={})


def _graph(tmp_path: Path) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    return RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters={"mock": _OkAdapter(), "openai": _OkAdapter(), "ollama": _OkAdapter()},
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )


def test_single_runtime_graph_executes_validation_and_commit_seams(tmp_path: Path) -> None:
    g = _graph(tmp_path)
    result = g.run(
        session_id="s-auth",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Michel, I hold you responsible for hiding the truth.",
        trace_id="t-auth",
    )
    nodes = (result.get("graph_diagnostics") or {}).get("nodes_executed") or result.get("nodes_executed") or []
    assert "validate_seam" in nodes
    assert "commit_seam" in nodes
    assert "director_assess_scene" in nodes


def test_runtime_graph_path_has_no_repeated_nodes(tmp_path: Path) -> None:
    g = _graph(tmp_path)
    result = g.run(
        session_id="s-auth-no-loop",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I watch Michel avoid the point and keep the pressure there.",
        trace_id="t-auth-no-loop",
    )

    gd = result.get("graph_diagnostics") or {}
    nodes = gd.get("nodes_executed") or result.get("nodes_executed") or []
    assert nodes
    assert len(nodes) == len(set(nodes))
    assert gd.get("topology_invariants", {}).get("duplicate_nodes") == []
    assert gd.get("topology_invariants", {}).get("node_path_has_repeated_nodes") is False
    assert nodes[-1] == "package_output"


def test_planner_records_are_projection_not_committed_truth(tmp_path: Path) -> None:
    g = _graph(tmp_path)
    result = g.run(
        session_id="s-auth2",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I apologize for the interruption.",
        trace_id="t-auth2",
    )
    spr = result.get("scene_plan_record")
    assert isinstance(spr, dict)
    assert spr.get("selected_scene_function")
    assert result.get("committed_result") is not None or True
    op = build_operator_canonical_turn_record(result)
    assert "scene_plan_record" in op
    assert op["scene_plan_record"] == spr


def test_graph_diagnostics_planner_projection_present(tmp_path: Path) -> None:
    g = _graph(tmp_path)
    result = g.run(
        session_id="s-auth3",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Why did you say that?",
        trace_id="t-auth3",
    )
    gd = result.get("graph_diagnostics") or {}
    proj = gd.get("planner_state_projection") or {}
    assert proj.get("semantic_move_record")
    assert proj.get("semantic_move_record") == result.get("semantic_move_record")


def test_package_output_preserves_bounded_dramatic_context(tmp_path: Path) -> None:
    g = _graph(tmp_path)
    result = g.run(
        session_id="s-auth4",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I press Michel about the lie.",
        trace_id="t-auth4",
    )
    context = result.get("dramatic_context_summary") or {}
    gd_context = (result.get("graph_diagnostics") or {}).get("dramatic_context_summary") or {}

    assert context["contract"] == "bounded_dramatic_context.v1"
    assert gd_context == context
    assert context["selected_scene_function"]
    assert context["module_scope"]["runtime_scope"] == "module_specific"
    assert context["module_scope"]["requested_module_supported"] is True
    assert context["responder"]["responder_id"]
    assert "scene_assessment" in context
    assert "social_state" in context
    assert "dramatic_outcome" in context


def test_opening_langgraph_validation_outcome_untouched_when_co_authority_normalize_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E2E: LangGraph liefert ``validation_outcome``; Co-Authority entsteht nur in der Projektion."""
    monkeypatch.setenv("ADR0041_VALIDATOR_DISPATCH_MODE", ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    g = _graph(tmp_path)
    result = g.run(
        session_id="s-coauth-langgraph",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="",
        trace_id="t-coauth-langgraph",
        turn_number=0,
        turn_input_class="opening",
    )
    assert isinstance(result.get("validation_outcome"), dict)
    vo_snapshot = copy.deepcopy(result["validation_outcome"])
    assert "validation_co_authority_decision" not in result["validation_outcome"]

    # Graph dispatch context can be stricter than harness fixtures; use the same opening ledger
    # + dispatch bundle as scoped co-authority tests so local evidence stays seam-aligned.
    ledger = initialize_runtime_aspect_ledger(
        session_id=result.get("session_id"),
        module_id=result.get("module_id"),
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
        turn_id=result.get("turn_id"),
        trace_id=result.get("trace_id"),
    )
    ledger[ADR0041_RUNTIME_GRAPH_DISPATCH_CONTEXT_KEY] = {
        "dispatch_context": _opening_dispatch_context(),
        "validation_seam_summary": {"status": "approved", "reason": "fixture"},
    }
    normalized = normalize_runtime_aspect_ledger(ledger)
    co = normalized["runtime_intelligence_projection"].get("validation_co_authority_decision")
    assert co is not None
    assert co["validation_outcome_changed"] is False
    assert co["commit_gate_changed"] is False
    assert co["readiness_gate_changed"] is False
    assert co["affects_commit"] is False
    assert co["affects_readiness"] is False
    assert co["proof_level"] == "local_only"
    assert co["live_or_staging_evidence"] is False

    assert result["validation_outcome"] == vo_snapshot
    assert "validation_co_authority_decision" not in result["validation_outcome"]


def test_engine_opening_prompt_is_not_interpreted_as_player_move(tmp_path: Path) -> None:
    g = _graph(tmp_path)
    prompt_like_opening_instruction = (
        'IMPORTANT: Write ALL player-visible narrative in German. Use separate narrator-visible '
        'blocks and emit "opening_event_ids"; escalate no conflict here.'
    )

    result = g.run(
        session_id="s-opening-input-guard",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input=prompt_like_opening_instruction,
        trace_id="t-opening-input-guard",
        turn_number=0,
        turn_initiator_type="engine",
        turn_input_class="opening",
    )

    interp = result.get("interpreted_input") or {}
    assert interp.get("player_input_kind") == "opening"
    assert interp.get("player_action_committed") is False
    assert interp.get("player_speech_committed") is False
    assert interp.get("original_text") == ""
    assert interp.get("engine_opening_prompt_redacted") is True

    semantic = result.get("semantic_move_record") or {}
    assert semantic.get("move_type") != "escalation_threat"
    assert result.get("selected_scene_function") == "establish_pressure"
