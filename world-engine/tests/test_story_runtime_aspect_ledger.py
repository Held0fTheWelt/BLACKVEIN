from __future__ import annotations

from typing import Any

from ai_stack import RuntimeTurnGraphExecutor
from ai_stack.runtime_aspect_ledger import (
    ASPECT_BEAT,
    ASPECT_COMMIT,
    ASPECT_HIERARCHICAL_MEMORY,
    ASPECT_NARRATIVE_ASPECT,
    ASPECT_NARRATOR_AUTHORITY,
    ASPECT_VALIDATION,
    ASPECT_VISIBLE_PROJECTION,
    initialize_runtime_aspect_ledger,
    make_aspect_record,
    set_aspect_record,
)

from app.story_runtime import StoryRuntimeManager
from app.story_runtime.manager import (
    StorySession,
    _live_scene_blocks_from_visible_bundle,
    _record_hierarchical_memory_aspect,
    _record_visible_projection_aspect,
)


class _FakeGraphInvoker:
    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        return state


class _FakeTurnGraph:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return dict(self._payload)


class _FakeModulePolicy:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, Any]:
        return dict(self._payload)


def _envelope(
    *,
    interpreted_input: dict[str, Any],
    generation: dict[str, Any],
) -> dict[str, Any]:
    gen = dict(generation)
    if "content" not in gen and "model_raw_text" not in gen:
        gen["content"] = "x" * 120
    return {
        "interpreted_input": interpreted_input,
        "generation": gen,
        "graph_diagnostics": {"errors": []},
        "retrieval": {"domain": "runtime", "status": "ok"},
        "routing": {"selected_model": "mock"},
        "validation_outcome": {"status": "approved", "reason": "test_fixture"},
        "visible_output_bundle": {"gm_narration": ["Fixture narration."]},
        "committed_result": {"commit_applied": True, "committed_effects": []},
    }


def _opening_envelope(start_scene_id: str) -> dict[str, Any]:
    return _envelope(
        interpreted_input={"kind": "speech", "confidence": 0.9},
        generation={
            "success": True,
            "metadata": {
                "structured_output": {
                    "narrative_response": "Opening fixture.",
                    "proposed_scene_id": start_scene_id,
                    "intent_summary": "",
                }
            },
        },
    )


def test_turn_emits_runtime_aspect_ledger() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    executor._graph = _FakeGraphInvoker()  # type: ignore[attr-defined]

    state = executor.run(
        session_id="session-1",
        module_id="m",
        current_scene_id="scene-1",
        player_input="Ich nehme ein Bier aus dem Kuehlschrank",
        turn_number=1,
        turn_initiator_type="player",
        trace_id="trace-1",
    )

    ledger = state["turn_aspect_ledger"]
    assert ledger["session_id"] == "session-1"
    assert ledger["turn_number"] == 1
    assert state["module_runtime_policy"]["module_id"] == "m"
    assert ledger["turn_aspect_ledger"]["input"]["actual"]["raw_player_input"].startswith("Ich nehme")
    assert ledger["turn_aspect_ledger"]["action_resolution"]["applicable"] is True


def test_turn_executor_propagates_runtime_profile_from_host_template() -> None:
    executor = object.__new__(RuntimeTurnGraphExecutor)
    executor._graph = _FakeGraphInvoker()  # type: ignore[attr-defined]

    state = executor.run(
        session_id="session-profile",
        module_id="m",
        current_scene_id="scene-1",
        player_input="Look around.",
        turn_number=1,
        turn_initiator_type="player",
        trace_id="trace-profile",
        host_experience_template={"runtime_profile_id": "profile-runtime", "template_id": "template-id"},
    )

    assert state["turn_aspect_ledger"]["runtime_profile_id"] == "profile-runtime"
    assert state["module_runtime_policy"]["runtime_profile_id"] == "profile-runtime"


def test_recoverable_turn_emits_runtime_aspect_ledger() -> None:
    manager = StoryRuntimeManager()
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    payload = _envelope(
        interpreted_input={"kind": "action", "player_input_kind": "action", "confidence": 0.81},
        generation={"success": True, "metadata": {}},
    )
    payload["validation_outcome"] = {
        "status": "rejected",
        "reason": "dramatic_effect_reject_continuity_pressure",
    }
    manager.turn_graph = _FakeTurnGraph(payload)  # type: ignore[assignment]

    turn = manager.execute_turn(session_id=session.session_id, player_input="Gehe ins Bad")

    ledger = turn["turn_aspect_ledger"]
    assert ledger["turn_number"] == 1
    assert ledger["turn_kind"] == "player_rejected_recoverable"
    assert ledger["turn_aspect_ledger"][ASPECT_VALIDATION]["status"] == "failed"
    assert (
        ledger["turn_aspect_ledger"][ASPECT_VALIDATION]["failure_reason"]
        == "dramatic_effect_reject_continuity_pressure"
    )
    assert ledger["turn_aspect_ledger"][ASPECT_VISIBLE_PROJECTION]["status"] == "passed"
    assert turn["diagnostics"]["turn_aspect_ledger"] == ledger
    assert ledger["canonical_turn_id"] == turn["canonical_turn_id"]


def test_committed_turn_ledger_uses_canonical_turn_id() -> None:
    manager = StoryRuntimeManager()
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "runtime_profile_id": "example_profile",
            "scenes": [{"id": "scene_1"}],
        },
    )
    manager.turn_graph = _FakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "action", "player_input_kind": "action", "confidence": 0.81},
            generation={"success": True, "metadata": {}},
        )
    )  # type: ignore[assignment]

    turn = manager.execute_turn(session_id=session.session_id, player_input="Gehe ins Bad")

    ledger = turn["turn_aspect_ledger"]
    assert ledger["canonical_turn_id"] == turn["canonical_turn_id"]
    assert ledger["story_session_id"] == session.session_id
    assert ledger["runtime_profile_id"] == "example_profile"
    assert ledger["runtime_intelligence_projection"]["canonical_turn_id"] == turn["canonical_turn_id"]
    assert ledger["runtime_intelligence_projection"]["runtime_profile_id"] == "example_profile"
    assert session.history[-1]["turn_aspect_ledger"]["canonical_turn_id"] == turn["canonical_turn_id"]


def test_path_summary_propagates_environment_and_runtime_profile(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_ENVIRONMENT", "staging")
    manager = StoryRuntimeManager()
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "runtime_profile_id": "profile-for-summary",
            "scenes": [{"id": "scene_1"}],
        },
    )
    manager.turn_graph = _FakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "action", "player_input_kind": "action", "confidence": 0.81},
            generation={"success": True, "metadata": {}},
        )
    )  # type: ignore[assignment]

    turn = manager.execute_turn(session_id=session.session_id, player_input="Gehe ins Bad")

    summary = turn["observability_path_summary"]
    assert summary["runtime_profile_id"] == "profile-for-summary"
    assert summary["environment"] == "staging"
    assert summary["turn_aspect_ledger"]["runtime_profile_id"] == "profile-for-summary"


def test_committed_turn_emits_branching_forecast_projection() -> None:
    manager = StoryRuntimeManager()
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "runtime_profile_id": "profile-branching",
            "scenes": [{"id": "scene_1"}],
        },
    )
    manager.turn_graph = _FakeTurnGraph(
        _envelope(
            interpreted_input={
                "kind": "speech",
                "player_input_kind": "speech",
                "confidence": 0.81,
                "ambiguity": "who is being blamed",
            },
            generation={"success": True, "metadata": {}},
        )
    )  # type: ignore[assignment]

    turn = manager.execute_turn(session_id=session.session_id, player_input="Wer wird hier beschuldigt?")

    forecast = turn["branching_forecast"]
    assert forecast["schema_version"] == "branching_forecast.v1"
    assert forecast["status"] == "forecasted"
    assert forecast["forecast_only"] is True
    assert forecast["authoritative"] is False
    assert forecast["mutates_canonical_state"] is False
    assert forecast["option_count"] >= 2

    ledger = turn["turn_aspect_ledger"]
    assert ledger["branching_forecast"] == forecast
    projected = ledger["runtime_intelligence_projection"]["branching_forecast"]
    assert projected["option_count"] == forecast["option_count"]
    assert projected["forecast_only"] is True
    assert projected["mutates_canonical_state"] is False

    summary = turn["observability_path_summary"]
    assert summary["branching_forecast_present"] is True
    assert summary["branch_option_count"] == forecast["option_count"]
    assert summary["inactive_branches_non_authoritative"] is True
    assert session.history[-1]["branching_forecast"]["canonical_turn_id"] == turn["canonical_turn_id"]
    state = manager.get_state(session.session_id)
    assert state["committed_state"]["last_branching_forecast"]["canonical_turn_id"] == turn["canonical_turn_id"]


def test_visible_projection_records_policy_driven_narrative_aspect(monkeypatch) -> None:
    policy = {
        "module_id": "module_alpha",
        "runtime_profile_id": "profile_alpha",
        "narrative_aspect_policy": {
            "schema_version": "narrative_aspect_policy.v1",
            "aspects": [
                {
                    "id": "aspect_alpha",
                    "enabled": True,
                    "activation": {"always": True},
                    "commit_impact": "diagnostic",
                    "evidence": [
                        {
                            "id": "visible_alpha",
                            "kind": "visible_origin_present",
                            "origin_aspect": "narrative_aspect",
                            "required": True,
                        }
                    ],
                }
            ],
        },
    }
    monkeypatch.setattr(
        "app.story_runtime.manager.load_module_runtime_policy",
        lambda **_kwargs: _FakeModulePolicy(policy),
    )
    ledger = initialize_runtime_aspect_ledger(
        session_id="session-narrative-aspect",
        module_id="module_alpha",
        runtime_profile_id="profile_alpha",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Look carefully.",
    )

    out = _record_visible_projection_aspect(
        ledger=ledger,
        session_id="session-narrative-aspect",
        module_id="module_alpha",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Look carefully.",
        trace_id="trace-narrative-aspect",
        scene_blocks=[
            {
                "id": "block-alpha",
                "block_type": "narrator",
                "text": "The room gives the action a visible pressure point.",
                "origin_aspect": ASPECT_NARRATIVE_ASPECT,
                "origin_aspect_id": "aspect_alpha",
                "origin_beat_id": "",
                "origin_capability": "narrative.aspect.evidence",
                "authority_owner": "system",
            }
        ],
    )

    record = out["turn_aspect_ledger"][ASPECT_NARRATIVE_ASPECT]
    assert record["status"] == "passed"
    assert record["selected"]["selected_aspects"] == ["aspect_alpha"]
    assert record["actual"]["realized_aspects"] == ["aspect_alpha"]
    assert out["runtime_intelligence_projection"]["narrative_aspect"]["selected_aspects"] == ["aspect_alpha"]


def test_visible_projection_records_policy_driven_theme_semantics(monkeypatch) -> None:
    semantic_profile = {
        "material_anchor": "glass table pressure visible room",
        "social_mask": "polite civility courtesy mask",
    }
    policy = {
        "module_id": "module_alpha",
        "runtime_profile_id": "profile_alpha",
        "narrative_aspect_policy": {
            "schema_version": "narrative_aspect_policy.v1",
            "aspects": [
                {
                    "id": "aspect_theme",
                    "enabled": True,
                    "activation": {"always": True},
                    "commit_impact": "diagnostic",
                    "semantic_policy": {"enabled": True, "required": True},
                    "semantic_profile": semantic_profile,
                    "metadata": {"table_b_refs": ["pi_12"]},
                }
            ],
        },
    }
    monkeypatch.setattr(
        "app.story_runtime.manager.load_module_runtime_policy",
        lambda **_kwargs: _FakeModulePolicy(policy),
    )
    ledger = initialize_runtime_aspect_ledger(
        session_id="session-theme-aspect",
        module_id="module_alpha",
        runtime_profile_id="profile_alpha",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Look carefully.",
    )
    profile_text = " ".join(
        token
        for value in semantic_profile.values()
        for token in str(value).split()[:3]
    )

    out = _record_visible_projection_aspect(
        ledger=ledger,
        session_id="session-theme-aspect",
        module_id="module_alpha",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Look carefully.",
        trace_id="trace-theme-aspect",
        scene_blocks=[
            {
                "id": "block-theme",
                "block_type": "narrator",
                "text": profile_text,
                "origin_aspect": ASPECT_NARRATIVE_ASPECT,
                "origin_aspect_id": "aspect_theme",
                "origin_beat_id": "",
                "origin_capability": "narrative.aspect.evidence",
                "authority_owner": "system",
            }
        ],
    )

    record = out["turn_aspect_ledger"][ASPECT_NARRATIVE_ASPECT]
    assert record["status"] == "passed"
    assert record["expected"]["theme_tracking_policy_present"] is True
    assert record["selected"]["selected_theme_aspects"] == ["aspect_theme"]
    assert record["actual"]["realized_theme_aspects"] == ["aspect_theme"]
    assert record["actual"]["semantic_classification_count"] == 1
    projected = out["runtime_intelligence_projection"]["narrative_aspect"]
    assert projected["selected_theme_aspects"] == ["aspect_theme"]
    assert projected["semantic_classification_count"] == 1


def test_hierarchical_memory_records_policy_driven_committed_turn(monkeypatch) -> None:
    policy = {
        "module_id": "module_alpha",
        "runtime_profile_id": "profile_alpha",
        "content_sources": ["module", "memory_policy"],
        "memory_policy": {
            "schema_version": "hierarchical_memory_policy.v1",
            "enabled": True,
            "write_requires_committed_turn": True,
            "allow_uncommitted_writes": False,
            "tiers": [
                {"id": "turn", "enabled": True, "max_items": 4, "max_context_items": 2},
                {"id": "session", "enabled": True, "max_items": 4, "max_context_items": 2},
                {"id": "actor", "enabled": True, "max_items": 4, "max_context_items": 2},
                {"id": "module", "enabled": True, "max_items": 2, "max_context_items": 1},
            ],
        },
    }
    monkeypatch.setattr(
        "app.story_runtime.manager.load_module_runtime_policy",
        lambda **_kwargs: _FakeModulePolicy(policy),
    )
    session = StorySession(
        session_id="session-memory",
        module_id="module_alpha",
        runtime_projection={
            "start_scene_id": "scene_alpha",
            "runtime_profile_id": "profile_alpha",
            "scenes": [{"id": "scene_alpha"}],
        },
    )
    ledger = initialize_runtime_aspect_ledger(
        session_id=session.session_id,
        module_id="module_alpha",
        runtime_profile_id="profile_alpha",
        turn_number=1,
        turn_kind="player",
        raw_player_input="This raw input must not become memory text.",
        turn_id=f"{session.session_id}:turn:1",
    )
    event = {
        "canonical_turn_id": f"{session.session_id}:turn:1",
        "turn_number": 1,
        "turn_kind": "player",
        "trace_id": "trace-memory",
        "raw_input": "This raw input must not become memory text.",
        "turn_aspect_ledger": ledger,
    }
    graph_state: dict[str, Any] = {"turn_aspect_ledger": ledger}

    surface = _record_hierarchical_memory_aspect(
        session=session,
        graph_state=graph_state,
        event=event,
        committed_turn={
            "canonical_turn_id": event["canonical_turn_id"],
            "module_id": "module_alpha",
            "runtime_profile_id": "profile_alpha",
            "turn_number": 1,
            "turn_outcome": "ok",
            "narrative_commit": {
                "allowed": True,
                "situation_status": "continue",
                "committed_scene_id": "scene_alpha",
                "committed_consequences": ["bounded consequence"],
            },
            "actor_turn_summary": {
                "primary_responder_id": "actor_alpha",
                "spoken_line_count": 1,
                "action_line_count": 0,
            },
            "turn_aspect_ledger": ledger,
        },
        allow_write=True,
    )

    record = event["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_HIERARCHICAL_MEMORY]
    assert record["status"] == "passed"
    assert record["actual"]["write_allowed"] is True
    assert record["actual"]["written_item_count"] >= 3
    assert session.hierarchical_memory["item_count"] >= 3
    assert surface["context"]["bounded"] is True
    assert graph_state["hierarchical_memory_context"]["memory_present"] is True
    assert "raw input must not become" not in str(session.hierarchical_memory)


def test_hierarchical_memory_does_not_write_recoverable_turn(monkeypatch) -> None:
    policy = {
        "module_id": "module_alpha",
        "runtime_profile_id": "profile_alpha",
        "memory_policy": {
            "schema_version": "hierarchical_memory_policy.v1",
            "enabled": True,
            "write_requires_committed_turn": True,
            "allow_uncommitted_writes": False,
            "tiers": [{"id": "turn", "enabled": True, "max_items": 4, "max_context_items": 2}],
        },
    }
    monkeypatch.setattr(
        "app.story_runtime.manager.load_module_runtime_policy",
        lambda **_kwargs: _FakeModulePolicy(policy),
    )
    session = StorySession(
        session_id="session-memory-rejected",
        module_id="module_alpha",
        runtime_projection={"start_scene_id": "scene_alpha", "runtime_profile_id": "profile_alpha"},
    )
    ledger = initialize_runtime_aspect_ledger(
        session_id=session.session_id,
        module_id="module_alpha",
        runtime_profile_id="profile_alpha",
        turn_number=1,
        turn_kind="player_rejected_recoverable",
        raw_player_input="Rejected input.",
        turn_id=f"{session.session_id}:turn:1",
    )
    event = {
        "canonical_turn_id": f"{session.session_id}:turn:1",
        "turn_number": 1,
        "turn_kind": "player_rejected_recoverable",
        "trace_id": "trace-memory-rejected",
        "raw_input": "Rejected input.",
        "turn_aspect_ledger": ledger,
    }
    graph_state: dict[str, Any] = {"turn_aspect_ledger": ledger}

    _record_hierarchical_memory_aspect(
        session=session,
        graph_state=graph_state,
        event=event,
        committed_turn={
            "canonical_turn_id": event["canonical_turn_id"],
            "turn_number": 1,
            "turn_outcome": "recoverable_rejection",
            "recoverable_outcome": True,
            "narrative_commit": {"allowed": False},
            "turn_aspect_ledger": ledger,
        },
        allow_write=False,
    )

    record = event["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_HIERARCHICAL_MEMORY]
    assert record["status"] == "not_applicable"
    assert record["actual"]["write_allowed"] is False
    assert session.hierarchical_memory["item_count"] == 0


def _projection() -> dict[str, Any]:
    return {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette_reille",
        "npc_actor_ids": ["michel_longstreet"],
        "actor_lanes": {"annette_reille": "human", "michel_longstreet": "npc"},
    }


def _ledger_with_required_narrator() -> dict[str, Any]:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-visible-origin",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Gehe ins Bad",
    )
    return set_aspect_record(
        ledger,
        ASPECT_NARRATOR_AUTHORITY,
        make_aspect_record(
            applicable=True,
            status="passed",
            expected={"required": True},
            actual={"narrator_block_present": True},
            source="runtime",
            expected_owner="narrator",
            actual_owner="narrator",
        ),
    )


def _ledger_with_required_beat(*, contractually_required: bool = False) -> dict[str, Any]:
    ledger = _ledger_with_required_narrator()
    return set_aspect_record(
        ledger,
        ASPECT_BEAT,
        make_aspect_record(
            applicable=True,
            status="partial",
            expected={
                "prior_beat_id": "civilized_negotiation",
                "candidate_beats": ["courtesy_pressure", "domestic_disruption"],
                "expected_realization": ["narrator.action_consequence.describe"],
                "contractually_required": contractually_required,
            },
            selected={
                "selected_beat_id": "domestic_disruption",
                "selection_reason": "player disrupts polite social frame",
                "transition_allowed": True,
            },
            actual={"realized": None, "committed": True},
            reasons=["beat_selected_not_yet_realized"],
            source="runtime",
            selected_beat="domestic_disruption",
        ),
    )


def _generic_ledger_with_required_narrator() -> dict[str, Any]:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-generic-projection",
        module_id="example_module",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Go to the side room.",
    )
    return set_aspect_record(
        ledger,
        ASPECT_NARRATOR_AUTHORITY,
        make_aspect_record(
            applicable=True,
            status="passed",
            expected={"required": True},
            actual={"narrator_block_present": True},
            source="runtime",
            expected_owner="narrator",
            actual_owner="narrator",
        ),
    )


def _generic_projection_payload(
    *,
    ledger: dict[str, Any],
    scene_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    return _envelope(
        interpreted_input={
            "kind": "action",
            "player_input_kind": "action",
            "confidence": 0.91,
        },
        generation={
            "success": True,
            "metadata": {
                "structured_output": {
                    "proposed_scene_id": "scene_2",
                    "intent_summary": "The player moves.",
                }
            },
        },
    ) | {
        "turn_aspect_ledger": ledger,
        "visible_output_bundle": {
            "gm_narration": [],
            "scene_blocks": scene_blocks,
        },
    }


def test_visible_narrator_block_has_origin_aspect() -> None:
    graph_state = {
        "turn_aspect_ledger": _ledger_with_required_narrator(),
        "player_action_frame": {"player_input_kind": "action"},
    }

    blocks = _live_scene_blocks_from_visible_bundle(
        {"gm_narration": ["Annette reaches the bathroom door."]},
        turn_number=1,
        runtime_projection=_projection(),
        graph_state=graph_state,
    )

    narrator = next(block for block in blocks if block["block_type"] == "narrator")
    assert narrator["origin_aspect"] == "narrator_authority"
    assert narrator["origin_capability"] == "narrator.action_consequence.describe"
    assert narrator["authority_owner"] == "narrator"


def test_visible_npc_block_has_origin_capability() -> None:
    blocks = _live_scene_blocks_from_visible_bundle(
        {"spoken_lines": [{"speaker_id": "michel_longstreet", "text": "Annette, wait."}]},
        turn_number=1,
        runtime_projection=_projection(),
        graph_state={"turn_aspect_ledger": _ledger_with_required_narrator()},
    )

    actor = next(block for block in blocks if block["block_type"] == "actor_line")
    assert actor["origin_aspect"] == "npc_authority"
    assert actor["origin_capability"] == "npc.social_reaction.optional"
    assert actor["authority_owner"] == "npc"


def test_visible_projection_preserves_origin_metadata() -> None:
    graph_state = {
        "turn_aspect_ledger": _ledger_with_required_narrator(),
        "player_action_frame": {"player_input_kind": "action"},
    }
    blocks = _live_scene_blocks_from_visible_bundle(
        {
            "gm_narration": ["Annette reaches the bathroom door."],
            "spoken_lines": [{"speaker_id": "michel_longstreet", "text": "Annette, wait."}],
        },
        turn_number=1,
        runtime_projection=_projection(),
        graph_state=graph_state,
    )

    ledger = _record_visible_projection_aspect(
        ledger=graph_state["turn_aspect_ledger"],
        session_id="s-visible-origin",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Gehe ins Bad",
        trace_id="trace-visible-origin",
        scene_blocks=blocks,
    )

    visible = ledger["turn_aspect_ledger"][ASPECT_VISIBLE_PROJECTION]
    assert visible["status"] == "passed"
    assert visible["actual"]["visible_block_origin_present"] is True
    assert visible["actual"]["required_narrator_block_present"] is True


def test_beat_realized_when_visible_block_matches_expected_origin() -> None:
    blocks = [
        {
            "id": "b1",
            "block_type": "narrator",
            "text": "Annette's movement breaks the polite frame.",
            "origin_aspect": "narrator_authority",
            "origin_beat_id": "domestic_disruption",
            "origin_capability": "narrator.action_consequence.describe",
            "authority_owner": "narrator",
        }
    ]

    ledger = _record_visible_projection_aspect(
        ledger=_ledger_with_required_beat(),
        session_id="s-visible-origin",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Ich nehme ein Bier aus dem Kuehlschrank",
        trace_id="trace-visible-origin",
        scene_blocks=blocks,
    )

    beat = ledger["turn_aspect_ledger"][ASPECT_BEAT]
    assert beat["status"] == "passed"
    assert beat["actual"]["realized"] is True
    assert beat["actual"]["missing_expected_realization"] == []


def test_beat_not_realized_when_lost_in_visible_projection() -> None:
    blocks = [
        {
            "id": "b1",
            "block_type": "actor_line",
            "actor_id": "michel_longstreet",
            "text": "Annette, wait.",
            "origin_aspect": "npc_authority",
            "origin_beat_id": "domestic_disruption",
            "origin_capability": "npc.social_reaction.optional",
            "authority_owner": "npc",
        }
    ]

    ledger = _record_visible_projection_aspect(
        ledger=_ledger_with_required_beat(),
        session_id="s-visible-origin",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Ich nehme ein Bier aus dem Kuehlschrank",
        trace_id="trace-visible-origin",
        scene_blocks=blocks,
    )

    beat = ledger["turn_aspect_ledger"][ASPECT_BEAT]
    assert beat["status"] == "partial"
    assert beat["failure_reason"] == "beat_realization_not_visible"
    assert beat["failure_class"] == "degradation_only"
    assert beat["lost_at_stage"] == "visible_projection"
    assert beat["actual"]["realized"] is False


def test_required_beat_lost_is_classified_as_hard_contract_failure() -> None:
    ledger = _record_visible_projection_aspect(
        ledger=_ledger_with_required_beat(contractually_required=True),
        session_id="s-visible-origin",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Ich nehme ein Bier aus dem Kuehlschrank",
        trace_id="trace-visible-origin",
        scene_blocks=[],
    )

    beat = ledger["turn_aspect_ledger"][ASPECT_BEAT]
    assert beat["status"] == "failed"
    assert beat["failure_class"] == "hard_contract_failure"
    assert beat["failure_reason"] == "selected_required_beat_lost"
    validation = ledger["turn_aspect_ledger"][ASPECT_VALIDATION]
    commit = ledger["turn_aspect_ledger"][ASPECT_COMMIT]
    assert validation["status"] == "failed"
    assert validation["failure_reason"] == "selected_required_beat_lost"
    assert commit["status"] == "partial"
    assert commit["failure_reason"] == "selected_required_beat_lost"


def test_block_folding_preserves_required_origin_evidence_for_beat() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s-visible-origin",
        module_id="example_module",
        turn_number=1,
        turn_kind="player",
        raw_player_input="I wait.",
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_BEAT,
        make_aspect_record(
            applicable=True,
            status="partial",
            expected={
                "candidate_beats": ["beat-1"],
                "expected_realization": ["npc.action_gesture.optional"],
            },
            selected={"selected_beat_id": "beat-1", "selection_source": "module_policy"},
            actual={"realized": None},
            source="runtime",
            selected_beat="beat-1",
        ),
    )
    blocks = [
        {
            "id": "folded-survivor",
            "block_type": "actor_line",
            "actor_id": "actor_a",
            "text": "Actor A answers while nodding.",
            "origin_aspect": "npc_authority",
            "origin_beat_id": "beat-1",
            "origin_capability": "npc.social_reaction.optional",
            "authority_owner": "npc",
            "folded_origin_evidence": [
                {
                    "origin_aspect": "npc_authority",
                    "origin_beat_id": "beat-1",
                    "origin_capability": "npc.action_gesture.optional",
                    "authority_owner": "npc",
                    "evidence_role": "required",
                }
            ],
        }
    ]

    ledger = _record_visible_projection_aspect(
        ledger=ledger,
        session_id="s-visible-origin",
        module_id="example_module",
        turn_number=1,
        turn_kind="player",
        raw_player_input="I wait.",
        trace_id="trace-visible-origin",
        scene_blocks=blocks,
    )

    visible = ledger["turn_aspect_ledger"][ASPECT_VISIBLE_PROJECTION]
    beat = ledger["turn_aspect_ledger"][ASPECT_BEAT]
    assert visible["actual"]["required_visible_origin_preserved"] is True
    assert beat["actual"]["realized"] is True


def test_required_narrator_block_not_lost_in_projection_classifies_validation_and_commit() -> None:
    blocks = [
        {
            "id": "b1",
            "block_type": "actor_line",
            "actor_id": "michel_longstreet",
            "text": "Annette, wait.",
            "origin_aspect": "npc_authority",
            "origin_beat_id": "domestic_disruption",
            "origin_capability": "npc.social_reaction.optional",
            "authority_owner": "npc",
        }
    ]

    ledger = _record_visible_projection_aspect(
        ledger=_ledger_with_required_narrator(),
        session_id="s-visible-origin",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Gehe ins Bad",
        trace_id="trace-visible-origin",
        scene_blocks=blocks,
    )

    visible = ledger["turn_aspect_ledger"][ASPECT_VISIBLE_PROJECTION]
    validation = ledger["turn_aspect_ledger"][ASPECT_VALIDATION]
    commit = ledger["turn_aspect_ledger"][ASPECT_COMMIT]
    assert visible["status"] == "failed"
    assert visible["failure_reason"] == "required_narrator_block_lost_in_projection"
    assert validation["status"] == "failed"
    assert validation["failure_class"] == "projection_failure"
    assert validation["actual"]["projection_failure_detected"] is True
    assert commit["status"] == "partial"
    assert commit["actual"]["projection_failure_detected"] is True


def test_projection_required_narrator_failure_returns_recoverable_turn_before_persist() -> None:
    manager = StoryRuntimeManager()
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="example_module",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )
    manager.turn_graph = _FakeTurnGraph(
        _generic_projection_payload(
            ledger=_generic_ledger_with_required_narrator(),
            scene_blocks=[
                {
                    "id": "b1",
                    "block_type": "actor_line",
                    "actor_id": "actor_a",
                    "text": "Wait.",
                    "origin_aspect": "npc_authority",
                    "origin_beat_id": "beat_a",
                    "origin_capability": "npc.social_reaction.optional",
                    "authority_owner": "npc",
                }
            ],
        )
    )  # type: ignore[assignment]

    turn = manager.execute_turn(session_id=session.session_id, player_input="Go to the side room.")

    ledger = turn["turn_aspect_ledger"]
    visible = ledger["turn_aspect_ledger"][ASPECT_VISIBLE_PROJECTION]
    validation = ledger["turn_aspect_ledger"][ASPECT_VALIDATION]
    commit = ledger["turn_aspect_ledger"][ASPECT_COMMIT]
    assert turn["turn_status"] == "rejected_recoverable"
    assert turn["turn_kind"] == "player_projection_rejected_recoverable"
    assert turn["reason"] == "required_narrator_block_lost_in_projection"
    assert turn["committed_result"]["commit_applied"] is False
    assert turn["narrative_commit"]["committed_scene_id"] == "scene_1"
    assert session.current_scene_id == "scene_1"
    assert visible["status"] == "failed"
    assert visible["failure_reason"] == "required_narrator_block_lost_in_projection"
    assert validation["status"] == "failed"
    assert validation["failure_reason"] == "required_narrator_block_lost_in_projection"
    assert commit["actual"]["commit_applied"] is False
    assert session.history[-1]["turn_outcome"] == "recoverable_projection_failure"


def test_projection_required_beat_failure_returns_recoverable_turn_before_persist() -> None:
    manager = StoryRuntimeManager()
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="example_module",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )
    ledger = set_aspect_record(
        _generic_ledger_with_required_narrator(),
        ASPECT_BEAT,
        make_aspect_record(
            applicable=True,
            status="partial",
            expected={
                "candidate_beats": ["beat_a"],
                "expected_realization": ["narrator.location_transition.describe"],
                "contractually_required": True,
            },
            selected={"selected_beat_id": "beat_a", "selection_source": "module_policy"},
            actual={"realized": None},
            reasons=["beat_selected_not_yet_realized"],
            source="runtime",
            selected_beat="beat_a",
        ),
    )
    manager.turn_graph = _FakeTurnGraph(
        _generic_projection_payload(
            ledger=ledger,
            scene_blocks=[
                {
                    "id": "b1",
                    "block_type": "narrator",
                    "text": "The room remains unchanged.",
                    "origin_aspect": "narrator_authority",
                    "origin_beat_id": "beat_a",
                    "origin_capability": "narrator.object_state.describe",
                    "authority_owner": "narrator",
                }
            ],
        )
    )  # type: ignore[assignment]

    turn = manager.execute_turn(session_id=session.session_id, player_input="Go to the side room.")

    ledger = turn["turn_aspect_ledger"]
    beat = ledger["turn_aspect_ledger"][ASPECT_BEAT]
    assert turn["turn_status"] == "rejected_recoverable"
    assert turn["reason"] == "selected_required_beat_lost"
    assert turn["committed_result"]["commit_applied"] is False
    assert beat["status"] == "failed"
    assert beat["failure_reason"] == "selected_required_beat_lost"
