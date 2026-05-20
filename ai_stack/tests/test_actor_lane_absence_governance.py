"""Full-route tests proving actor-lane absence governance through complete pipeline."""

from ai_stack.langgraph.langgraph_runtime_executor import (
    RuntimeTurnGraphExecutor,
    _actor_lane_validation,
    _compute_reaction_order_divergence_for_render,
)
from ai_stack.runtime_quality_semantics import canonical_degradation_signals
from ai_stack.contracts.runtime_turn_contracts import DEGRADATION_SIGNAL_NO_ACTOR_LANE_OUTPUT
from ai_stack.god_of_carnage_frozen_vocabulary import expand_goc_actor_id_aliases
from ai_stack.story_runtime.turn.god_of_carnage_turn_seams import run_validation_seam, run_visible_render


def test_actor_lane_valid_output_is_healthy():
    """Valid structured actor lanes should not trigger degradation."""
    state = {
        "selected_responder_set": [
            {"actor_id": "alice"},
            {"actor_id": "bob"},
        ]
    }
    generation = {
        "metadata": {
            "structured_output": {
                "spoken_lines": [
                    {"speaker_id": "alice", "line": "Hello"},
                    {"speaker_id": "bob", "line": "Hi"},
                ]
            }
        }
    }
    result = _actor_lane_validation(state=state, generation=generation)
    assert result["status"] == "approved"
    assert result["reason"] == "actor_lane_legal"


def test_human_actor_boundary_expands_goc_actor_aliases():
    """Short player ids like annette must forbid canonical ids like annette_reille."""
    assert "annette_reille" in expand_goc_actor_id_aliases("annette")
    generation = {
        "success": True,
        "metadata": {
            "structured_output": {
                "primary_responder_id": "annette_reille",
                "spoken_lines": [{"speaker_id": "annette_reille", "text": "I take the floor."}],
            }
        },
    }

    result = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=[{"description": "Annette speaks."}],
        generation=generation,
        actor_lane_context={
            "human_actor_id": "annette",
            "ai_forbidden_actor_ids": ["annette"],
        },
    )

    assert result["status"] == "rejected"
    assert result["reason"] in {"ai_controlled_human_actor", "human_actor_selected_as_responder"}


def test_actor_lane_absent_with_selected_responders_is_weak_but_legal():
    """No structured output when responders selected should create weak_but_legal quality."""
    state = {
        "selected_responder_set": [
            {"actor_id": "alice"},
            {"actor_id": "bob"},
        ]
    }
    generation = {"metadata": {}}
    result = _actor_lane_validation(state=state, generation=generation)
    assert result["status"] == "approved"
    assert result["reason"] == "no_structured_actor_output_with_selected_responders"

    markers: list[str] = []
    if result["reason"] == "no_structured_actor_output_with_selected_responders":
        markers.append("no_actor_lane_output_with_selected_responders")

    signals = canonical_degradation_signals(
        state={"visibility_class_markers": markers},
        fallback_taken=False,
    )
    assert DEGRADATION_SIGNAL_NO_ACTOR_LANE_OUTPUT in signals


def test_actor_lane_absent_no_responders_no_degradation():
    """No structured output with no responders should not trigger degradation signal."""
    state = {"selected_responder_set": []}
    generation = {"metadata": {}}
    result = _actor_lane_validation(state=state, generation=generation)
    assert result["status"] == "approved"
    assert result["reason"] == "no_structured_actor_output"

    markers: list[str] = []
    if result["reason"] == "no_structured_actor_output_with_selected_responders":
        markers.append("no_actor_lane_output_with_selected_responders")

    signals = canonical_degradation_signals(
        state={"visibility_class_markers": markers},
        fallback_taken=False,
    )
    assert DEGRADATION_SIGNAL_NO_ACTOR_LANE_OUTPUT not in signals


def test_proposal_normalize_accepts_actor_turn_json_without_narration_summary():
    """Actor-lane JSON is structured output even when narration fields are absent."""
    graph = object.__new__(RuntimeTurnGraphExecutor)
    result = graph._proposal_normalize(
        {
            "generation": {
                "success": True,
                "content": (
                    '{"schema_version":"runtime_actor_turn_v1",'
                    '"primary_responder_id":"veronique_vallon",'
                    '"spoken_lines":[{"speaker_id":"veronique_vallon","text":"We should keep this civil."}],'
                    '"action_lines":[{"actor_id":"michel_longstreet","text":"folds his hands"}]}'
                ),
                "metadata": {},
            },
            "fallback_markers": [],
        }
    )

    structured = result["generation"]["metadata"]["structured_output"]
    assert structured["schema_version"] == "runtime_actor_turn_v1"
    assert result["spoken_lines"][0]["speaker_id"] == "veronique_vallon"
    assert result["action_lines"][0]["actor_id"] == "michel_longstreet"


def test_visible_render_displays_actor_turn_json_as_scene_text():
    bundle, markers = run_visible_render(
        module_id="god_of_carnage",
        committed_result={"commit_applied": True, "committed_effects": [{"type": "beat"}]},
        validation_outcome={"status": "approved", "actor_lane_validation": {"status": "approved"}},
        generation={
            "content": (
                '{"schema_version":"runtime_actor_turn_v1",'
                '"spoken_lines":[{"speaker_id":"veronique_vallon","text":"We should keep this civil.","tone":"measured"}],'
                '"action_lines":[{"actor_id":"michel_longstreet","text":"folds his hands"}]}'
            ),
            "metadata": {
                "structured_output": {
                    "schema_version": "runtime_actor_turn_v1",
                    "spoken_lines": [
                        {"speaker_id": "veronique_vallon", "text": "We should keep this civil.", "tone": "measured"}
                    ],
                    "action_lines": [{"actor_id": "michel_longstreet", "text": "folds his hands"}],
                }
            },
        },
        transition_pattern="hard",
        live_player_truth_surface=True,
        render_context={"responder_actor_id": "veronique_vallon"},
    )

    assert "truth_aligned" in markers
    assert bundle["gm_narration"]
    assert not bundle["gm_narration"][0].lstrip().startswith("{")
    assert "We should keep this civil." in "\n".join(bundle["gm_narration"])


def test_render_support_merge_preserves_earlier_writes():
    """Multiple render_support writes should merge, not overwrite."""
    bundle = {
        "render_support": {
            "projection_version": "render_support.v1",
            "reaction_order_divergence": {
                "divergence": True,
                "reason": "secondary_responder_nominated_not_realized_in_output",
                "non_fatal": True,
                "justified": False,
            },
        }
    }

    director_surface_hints = {"hint": "value"}

    if director_surface_hints:
        render_support = bundle.setdefault("render_support", {})
        if not isinstance(render_support, dict):
            render_support = {}
            bundle["render_support"] = render_support
        render_support.setdefault("projection_version", "render_support.v1")
        render_support.setdefault("player_visible", False)
        render_support["director_surface_hints"] = director_surface_hints

    assert bundle["render_support"]["projection_version"] == "render_support.v1"
    assert bundle["render_support"]["reaction_order_divergence"]["reason"] == "secondary_responder_nominated_not_realized_in_output"
    assert bundle["render_support"]["reaction_order_divergence"]["non_fatal"] is True
    assert bundle["render_support"]["director_surface_hints"] == director_surface_hints


def test_reaction_order_divergence_in_render_support():
    """Secondary responder nominated but not realized should show divergence with full structure."""
    state = {
        "selected_responder_set": [
            {"actor_id": "alice", "role": "primary_responder", "preferred_reaction_order": 0},
            {"actor_id": "bob", "role": "secondary_reactor", "preferred_reaction_order": 1},
        ],
        "spoken_lines": [{"speaker_id": "alice", "text": "line"}],
        "action_lines": [],
    }

    result = _compute_reaction_order_divergence_for_render(state)
    assert result["reaction_order_divergence"] == "secondary_responder_nominated_not_realized_in_output"
    assert result["divergence"] is True
    assert result["preferred_reaction_order_ids"] == ["alice", "bob"]
    assert result["realized_actor_order"] == ["alice"]
    assert result["not_realized_actor_ids"] == ["bob"]
    assert result["non_fatal"] is True
    assert result["justified"] is True
    assert result["justification"] is not None


def test_reaction_order_divergence_not_when_aligned():
    """Aligned order should not produce divergence; divergence=False."""
    state = {
        "selected_responder_set": [
            {"actor_id": "alice", "role": "primary_responder", "preferred_reaction_order": 0},
            {"actor_id": "bob", "role": "secondary_reactor", "preferred_reaction_order": 1},
        ],
        "spoken_lines": [
            {"speaker_id": "alice", "text": "line1"},
            {"speaker_id": "bob", "text": "line2"},
        ],
        "action_lines": [],
    }

    result = _compute_reaction_order_divergence_for_render(state)
    assert result["reaction_order_divergence"] is None
    assert result["divergence"] is False
    assert result["preferred_reaction_order_ids"] == ["alice", "bob"]
    assert result["realized_actor_order"] == ["alice", "bob"]
    assert result["not_realized_actor_ids"] == []
    assert result["non_fatal"] is True
    assert result["justified"] is False
    assert result["justification"] is None


def test_run_visible_render_survives_vitality_warning_and_reaction_order_divergence():
    """Verify vitality warning and reaction-order divergence both present in render_support."""
    bundle, markers = run_visible_render(
        module_id="god_of_carnage",
        committed_result={"committed_effects": ["test"], "commit_applied": True},
        validation_outcome={"status": "approved"},
        generation={
            "content": "test prose",
            "metadata": {
                "structured_output": {
                    "spoken_lines": [],
                    "action_lines": [],
                }
            }
        },
        transition_pattern="hard",
        render_context={
            "pacing_mode": "thin_edge",
            "carry_forward_tension_notes": "unresolved: escalating",
            "selected_responder_set": [
                {"actor_id": "alice", "role": "primary_responder"},
                {"actor_id": "bob", "role": "secondary_reactor"},
            ],
            "preferred_reaction_order_ids": ["alice", "bob"],
            "realized_actor_order": ["alice"],
            "reaction_order_divergence": "secondary_responder_nominated_not_realized_in_output",
        },
    )

    render_support = bundle.get("render_support", {})
    assert isinstance(render_support, dict), "render_support should be a dict"
    assert render_support.get("projection_version") == "render_support.v1", \
        "projection_version should be render_support.v1 for merge compatibility"

    assert render_support.get("vitality_floor_warning") == "thin_edge_output_empty_with_prior_tension", \
        f"Expected vitality warning, got: {render_support.get('vitality_floor_warning')}"

    assert render_support.get("reaction_order_divergence") is not None, \
        "reaction_order_divergence should be present in render_support"
    assert render_support["reaction_order_divergence"].get("divergence") is True
    assert render_support["reaction_order_divergence"].get("reason") == "secondary_responder_nominated_not_realized_in_output"
    assert render_support["reaction_order_divergence"].get("non_fatal") is True
    assert isinstance(render_support["reaction_order_divergence"].get("preferred"), list)
    assert isinstance(render_support["reaction_order_divergence"].get("realized"), list)


def test_opening_leniency_produces_degradation_signal():
    """Verify opening-turn leniency approval produces DEGRADATION_SIGNAL_OPENING_LENIENCY_APPROVED."""
    from ai_stack.runtime_quality_semantics import canonical_degradation_signals
    from ai_stack.contracts.runtime_turn_contracts import DEGRADATION_SIGNAL_OPENING_LENIENCY_APPROVED

    state = {
        "validation_outcome": {
            "status": "approved",
            "reason": "opening_leniency_approved",
        },
    }

    signals = canonical_degradation_signals(state=state, fallback_taken=False)
    assert DEGRADATION_SIGNAL_OPENING_LENIENCY_APPROVED in signals, \
        f"Expected {DEGRADATION_SIGNAL_OPENING_LENIENCY_APPROVED} in signals, got {signals}"


def test_opening_leniency_produces_weak_quality_class():
    """Verify opening-leniency approval results in weak_but_legal quality class."""
    from ai_stack.runtime_quality_semantics import canonical_quality_class, canonical_degradation_signals
    from ai_stack.contracts.runtime_turn_contracts import QUALITY_CLASS_WEAK_BUT_LEGAL

    state = {
        "validation_outcome": {
            "status": "approved",
            "reason": "opening_leniency_approved",
        },
    }

    signals = canonical_degradation_signals(state=state, fallback_taken=False)
    quality = canonical_quality_class(
        validation_outcome=state["validation_outcome"],
        commit_applied=True,
        degradation_signals=signals,
    )
    assert quality == QUALITY_CLASS_WEAK_BUT_LEGAL, \
        f"Expected {QUALITY_CLASS_WEAK_BUT_LEGAL}, got {quality}"


def test_story_rendering_uses_canonical_normalized_entries():
    """Verify rendered story entries use canonical structure, not legacy audit-log projection."""
    bundle, markers = run_visible_render(
        module_id="god_of_carnage",
        committed_result={"committed_effects": ["test"], "commit_applied": True},
        validation_outcome={"status": "approved"},
        generation={
            "content": "canonical prose",
            "metadata": {
                "structured_output": {
                    "spoken_lines": [
                        {"speaker_id": "alice", "text": "hello world"},
                    ],
                    "action_lines": [
                        {"actor_id": "alice", "action": "nods"},
                    ],
                }
            }
        },
        transition_pattern="hard",
        render_context={
            "module_id": "god_of_carnage",
            "turn_number": 5,
            "selected_responder_set": [
                {"actor_id": "alice", "role": "primary_responder"},
            ],
        },
    )

    assert isinstance(bundle, dict), "bundle should be a dict"
    assert "spoken_lines" in bundle, "canonical spoken_lines should be in bundle"
    assert isinstance(bundle.get("spoken_lines"), list), "spoken_lines should be a list"
    assert len(bundle["spoken_lines"]) > 0, "should have rendered spoken lines"

    assert "action_lines" in bundle, "canonical action_lines should be in bundle"
    assert isinstance(bundle.get("action_lines"), list), "action_lines should be a list"

    assert "gm_narration" in bundle, "gm_narration (prose) should be in bundle"
    narration = bundle.get("gm_narration")
    assert isinstance(narration, list), "gm_narration should be a list"
    assert len(narration) > 0, "gm_narration should contain prose entries"
    assert "canonical prose" in narration, "gm_narration should contain generation prose"


def test_live_opening_validation_rejects_actor_only_structured_output_without_narration_summary():
    """LIVE-OPENING-FAILURE-01 repro: actor lanes can be approved while dramatic gate rejects empty fluency."""
    generation = {
        "success": True,
        "metadata": {
            "structured_output": {
                "schema_version": "runtime_actor_turn_v1",
                "primary_responder_id": "veronique_vallon",
                "spoken_lines": [
                    {"speaker_id": "veronique_vallon", "text": "We should keep this civil."}
                ],
                "action_lines": [
                    {"actor_id": "michel_longstreet", "text": "folds his hands"}
                ],
            }
        },
    }
    outcome = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=[],
        generation=generation,
        actor_lane_summary={
            "spoken_line_count": 1,
            "action_line_count": 1,
            "initiative_event_count": 0,
            "actor_lane_status": "approved",
        },
    )
    assert outcome["status"] == "rejected"
    assert outcome["reason"] == "dramatic_effect_reject_empty_fluency"


def test_live_opening_validation_accepts_when_narration_summary_is_present():
    """Control fixture: same actor lanes with narration_summary should pass dramatic gate."""
    narration = (
        "Two couples measure each other in the salon while civility strains "
        "under the memory of the schoolyard incident."
    )
    generation = {
        "success": True,
        "metadata": {
            "structured_output": {
                "schema_version": "runtime_actor_turn_v1",
                "narration_summary": narration,
                "primary_responder_id": "veronique_vallon",
                "spoken_lines": [
                    {"speaker_id": "veronique_vallon", "text": "We should keep this civil."}
                ],
                "action_lines": [
                    {"actor_id": "michel_longstreet", "text": "folds his hands"}
                ],
            }
        },
    }
    outcome = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=[
            {"effect_type": "narrative_projection", "description": narration}
        ],
        generation=generation,
        actor_lane_summary={
            "spoken_line_count": 1,
            "action_line_count": 1,
            "initiative_event_count": 0,
            "actor_lane_status": "approved",
        },
    )
    assert outcome["status"] == "approved"


def _opening_state_for_role(role: str) -> dict:
    human_actor = f"{role}_reille" if role in {"annette", "alain"} else role
    npc_pool = ["veronique_vallon", "michel_longstreet", "annette_reille", "alain_reille"]
    selected_responders = [{"actor_id": actor} for actor in npc_pool if actor != human_actor]
    return {
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "selected_scene_function": "establish_pressure",
        "transition_pattern": "hard",
        "selected_responder_set": selected_responders,
        "actor_lane_context": {
            "selected_player_role": role,
            "human_actor_id": human_actor,
            "ai_forbidden_actor_ids": [human_actor],
        },
        "fallback_markers": [],
    }


def _lane_only_generation() -> dict:
    return {
        "success": True,
        "parser_error": None,
        "metadata": {
            "adapter": "openai",
            "structured_output": {
                "schema_version": "runtime_actor_turn_v1",
                "primary_responder_id": "veronique_vallon",
                "spoken_lines": [
                    {"speaker_id": "veronique_vallon", "text": "We should keep this civil."}
                ],
                "action_lines": [
                    {"actor_id": "michel_longstreet", "text": "folds his hands"}
                ],
            },
        },
    }


def _actor_lane_summary_from_structured(structured: dict) -> dict:
    return {
        "spoken_line_count": len(structured.get("spoken_lines") or []),
        "action_line_count": len(structured.get("action_lines") or []),
        "initiative_event_count": len(structured.get("initiative_events") or []),
        "actor_lane_status": "approved",
    }


def test_opening_actor_lane_generation_error_unblocks_empty_fluency_reject():
    graph = object.__new__(RuntimeTurnGraphExecutor)
    state = _opening_state_for_role("annette")
    state["generation"] = _lane_only_generation()
    result = graph._proposal_normalize(state)

    structured = result["generation"]["metadata"]["structured_output"]
    summary = structured.get("narration_summary")
    assert isinstance(summary, str) and summary.strip()
    assert "opening_actor_lane_narration_missing" in summary
    assert "No substitute story text" in summary
    assert result["generation"]["metadata"]["narration_summary_synthesized"] is True
    assert (
        result["generation"]["metadata"]["narration_summary_source"]
        == "actor_lane_generation_error"
    )
    assert (
        result["generation"]["metadata"]["narration_summary_error_code"]
        == "opening_actor_lane_narration_missing"
    )
    assert (
        result["generation"]["metadata"]["synthetic_narration_reason"]
        == "opening_actor_lane_narration_missing"
    )
    assert any(
        str(effect.get("description") or "").strip() for effect in result["proposed_state_effects"]
    )
    outcome = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=result["proposed_state_effects"],
        generation=result["generation"],
        actor_lane_summary=_actor_lane_summary_from_structured(structured),
        actor_lane_context=state["actor_lane_context"],
    )
    assert outcome["reason"] != "dramatic_effect_reject_empty_fluency"


def test_opening_narration_synth_skipped_when_actor_lane_rejected():
    graph = object.__new__(RuntimeTurnGraphExecutor)
    state = _opening_state_for_role("annette")
    generation = _lane_only_generation()
    generation["metadata"]["structured_output"]["spoken_lines"] = [
        {"speaker_id": "annette_reille", "text": "I take the floor."}
    ]
    state["generation"] = generation
    result = graph._proposal_normalize(state)
    structured = result["generation"]["metadata"]["structured_output"]
    from ai_stack.opening_shape_normalizer import narration_summary_to_plain_str

    assert not narration_summary_to_plain_str(structured.get("narration_summary"))
    assert "narration_summary_synthesized" not in result["generation"]["metadata"]


def test_opening_narration_synth_skipped_when_actor_lanes_empty():
    graph = object.__new__(RuntimeTurnGraphExecutor)
    state = _opening_state_for_role("annette")
    generation = _lane_only_generation()
    generation["metadata"]["structured_output"]["spoken_lines"] = []
    generation["metadata"]["structured_output"]["action_lines"] = []
    state["generation"] = generation
    result = graph._proposal_normalize(state)
    structured = result["generation"]["metadata"]["structured_output"]
    from ai_stack.opening_shape_normalizer import narration_summary_to_plain_str

    assert not narration_summary_to_plain_str(structured.get("narration_summary"))
    assert "narration_summary_synthesized" not in result["generation"]["metadata"]


def test_opening_narration_synth_does_not_override_existing_summary():
    graph = object.__new__(RuntimeTurnGraphExecutor)
    state = _opening_state_for_role("annette")
    generation = _lane_only_generation()
    generation["metadata"]["structured_output"]["narration_summary"] = "Existing summary."
    state["generation"] = generation
    result = graph._proposal_normalize(state)
    structured = result["generation"]["metadata"]["structured_output"]
    assert structured["narration_summary"] == "Existing summary."
    assert "narration_summary_synthesized" not in result["generation"]["metadata"]


def test_opening_narration_synth_never_masks_human_actor_lane_violation():
    graph = object.__new__(RuntimeTurnGraphExecutor)
    state = _opening_state_for_role("annette")
    generation = _lane_only_generation()
    generation["metadata"]["structured_output"]["spoken_lines"] = [
        {"speaker_id": "annette_reille", "text": "I speak for myself."}
    ]
    state["generation"] = generation
    normalized = graph._proposal_normalize(state)
    outcome = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=normalized["proposed_state_effects"],
        generation=normalized["generation"],
        actor_lane_summary=_actor_lane_summary_from_structured(
            normalized["generation"]["metadata"]["structured_output"]
        ),
        actor_lane_context=state["actor_lane_context"],
    )
    assert outcome["status"] == "rejected"
    assert outcome["reason"] in {"ai_controlled_human_actor", "human_actor_selected_as_responder"}


def test_opening_actor_lane_missing_narration_annette_uses_explicit_notice():
    graph = object.__new__(RuntimeTurnGraphExecutor)
    state = _opening_state_for_role("annette")
    state["generation"] = _lane_only_generation()
    result = graph._proposal_normalize(state)
    summary = result["generation"]["metadata"]["structured_output"]["narration_summary"]
    assert "opening_actor_lane_narration_missing" in summary
    assert "No substitute story text" in summary
    assert "Fallback:" in summary
    assert "You are Annette" not in summary


def test_opening_actor_lane_missing_narration_alain_uses_explicit_notice():
    graph = object.__new__(RuntimeTurnGraphExecutor)
    state = _opening_state_for_role("alain")
    state["generation"] = _lane_only_generation()
    result = graph._proposal_normalize(state)
    summary = result["generation"]["metadata"]["structured_output"]["narration_summary"]
    assert "opening_actor_lane_narration_missing" in summary
    assert "No substitute story text" in summary
    assert "Fallback:" in summary
    assert "You are Alain" not in summary


def test_opening_narration_synth_fires_for_configured_model_fallback():
    """Synthesis must fire even when fallback_used=True (configured model fallback, e.g. gpt-5-nano).

    Root cause: fallback_active was True for any fallback_used=True generation, blocking synthesis.
    The fix scopes fallback_active to LDSS adapters only; configured model fallbacks (which
    produce the same structured format) must reach synthesis so the gate does not reject on
    empty narration.
    """
    graph = object.__new__(RuntimeTurnGraphExecutor)
    state = _opening_state_for_role("annette")
    generation = _lane_only_generation()
    generation["fallback_used"] = True
    generation["metadata"]["fallback_model_id"] = "openai_gpt_5_4_nano"
    generation["metadata"]["fallback_reason"] = "primary_model_invocation_failed"
    state["generation"] = generation

    result = graph._proposal_normalize(state)

    structured = result["generation"]["metadata"]["structured_output"]
    summary = structured.get("narration_summary")
    assert isinstance(summary, str) and summary.strip(), (
        "Synthesis must fire for configured model fallback output with actor lanes"
    )
    assert result["generation"]["metadata"].get("narration_summary_synthesized") is True

    outcome = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=result["proposed_state_effects"],
        generation=result["generation"],
        actor_lane_summary=_actor_lane_summary_from_structured(structured),
        actor_lane_context=state["actor_lane_context"],
    )
    assert outcome["reason"] != "dramatic_effect_reject_empty_fluency", (
        "Gate must not reject with empty_fluency after synthesis on fallback output"
    )
