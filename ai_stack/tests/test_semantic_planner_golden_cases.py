"""Golden regression: representative GoC dramatic patterns and planner-state shape."""

from __future__ import annotations

from pathlib import Path

import pytest
from story_runtime_core import RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from story_runtime_core.model_registry import build_default_registry

langgraph_runtime = pytest.importorskip("ai_stack.langgraph_runtime", reason="LangGraph required")
from ai_stack.langgraph_runtime import RuntimeTurnGraphExecutor
from ai_stack.rag import ContextPackAssembler, ContextRetriever, RagIngestionPipeline
from ai_stack.semantic_move_contract import SEMANTIC_MOVE_TYPES
from ai_stack.silence_negative_space_contract import SILENCE_NEGATIVE_SPACE_CONTRACT_VERSION


class _NarrAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(
            content='{"narrative_response":"Director beat.","proposed_scene_id":null}',
            success=True,
            metadata={},
        )


def _graph(tmp_path: Path) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage golden.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    return RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters={"mock": _NarrAdapter(), "openai": _NarrAdapter(), "ollama": _NarrAdapter()},
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )


def _assert_planner_state(result: dict) -> None:
    assert result.get("semantic_move_record", {}).get("move_type")
    assert result.get("social_state_record")
    assert isinstance(result.get("character_mind_records"), list)
    sp = result.get("scene_plan_record", {})
    assert sp.get("selected_scene_function")
    assert sp.get("narrative_scene_function")
    assert isinstance(sp.get("scene_target"), dict)
    assert isinstance(sp.get("pressure_target"), dict)
    assert isinstance(sp.get("target_obligations"), list)
    assert isinstance(sp.get("actor_directives"), list)
    assert isinstance(sp.get("dramatic_beats"), list)
    assert isinstance(sp.get("handover_policy"), dict)
    assert isinstance(sp.get("content_frame"), dict)
    assert isinstance(sp.get("speech_policy"), dict)
    assert isinstance(sp.get("quote_moment_policy"), dict)
    assert isinstance(sp.get("dialogue_plan"), list)
    assert isinstance(sp.get("capability_manager_plan"), dict)
    assert isinstance(sp.get("continuity_obligation"), dict)
    assert sp.get("expected_transition_pattern") in {"hard", "soft", "carry_forward", "diagnostics_only"}
    assert sp.get("semantic_scene_planner_version") == "goc_semantic_scene_planner_v1"


@pytest.mark.parametrize(
    ("player_input", "expected_move_type", "min_scene_fn"),
    [
        ("You are to blame for this.", "direct_accusation", "redirect_blame"),
        ("You provoke us deliberately with that performance.", "indirect_provocation", "escalate_conflict"),
        ("I am truly sorry.", "repair_attempt", "repair_or_stabilize"),
        ("I would rather change the subject than answer.", "evasive_deflection", "withhold_or_evade"),
        ("You humiliated my son in front of everyone.", "humiliating_exposure", "redirect_blame"),
        ("I stand with Michel against your wife.", "alliance_reposition", "scene_pivot"),
        ("I say nothing.", "silence_withdrawal", "withhold_or_evade"),
    ],
)
def test_golden_semantic_move_and_scene_plan(tmp_path: Path, player_input: str, expected_move_type: str, min_scene_fn: str) -> None:
    g = _graph(tmp_path)
    result = g.run(
        session_id="golden",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input=player_input,
        trace_id="tg",
    )
    sm = result.get("semantic_move_record") or {}
    assert sm.get("move_type") == expected_move_type
    sp = result.get("scene_plan_record") or {}
    assert sp.get("selected_scene_function") == min_scene_fn
    assert sp.get("selection_source") == "semantic_pipeline_v1"
    assert sp.get("scene_target", {}).get("target_function")
    assert sp.get("pressure_target", {}).get("pressure_axis")
    assert sp.get("dramatic_beats")
    assert sp.get("dramatic_beats", [{}])[0].get("beat_kind")
    _assert_planner_state(result)


def test_indirect_provocation_without_blame_keyword(tmp_path: Path) -> None:
    g = _graph(tmp_path)
    result = g.run(
        session_id="golden2",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Your civility is a mask and everyone here knows it.",
        trace_id="tg2",
    )
    sm = result.get("semantic_move_record") or {}
    assert sm.get("move_type") in ("indirect_provocation", "establish_situational_pressure", "direct_accusation")


def test_pi14_no_lexical_silence_reaches_director_pipeline(tmp_path: Path) -> None:
    """ADR-0039 coverage: legacy Pi label is historical; runtime fields are semantic."""
    g = _graph(tmp_path)
    result = g.run(
        session_id="silence-negative-space",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="...",
        trace_id="tg-silence-negative-space",
    )

    interpreted = result.get("interpreted_input") or {}
    assert interpreted.get("silence_negative_space_signal") is True
    assert interpreted.get("silence_negative_space_signal_source") == "non_lexical_input"

    sm = result.get("semantic_move_record") or {}
    assert sm.get("move_type") == "silence_withdrawal"
    assert sm.get("move_type") in SEMANTIC_MOVE_TYPES

    sp = result.get("scene_plan_record") or {}
    silence = sp.get("silence_brevity_decision") or {}
    assert sp.get("selected_scene_function") == "withhold_or_evade"
    assert silence.get("contract") == SILENCE_NEGATIVE_SPACE_CONTRACT_VERSION
    assert silence.get("mode") == "withheld"
    assert silence.get("blocks_forced_speech") is True
    assert silence.get("requires_visible_beat") is True
