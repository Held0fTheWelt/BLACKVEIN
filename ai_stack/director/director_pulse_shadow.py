"""Director Pulse shadow path.

Evaluates one Director tick and returns a diagnostic bundle of four Pulse-MVP
events without touching the existing block-bundle path or session state.

Shadow mode (ADR-0058 §8):
* Runs in parallel to the existing visible_scene_output.blocks.v1 bundle path.
* Does not replace the bundle path — bundle path is still primary.
* Does not mutate caller state.
* Does not consume mandatory beats.
* Does not advance the canonical path.
* Always labeled ``shadow_only: True``.
* Silence is a first-class, recorded Director choice — not a fallback.

Governance:
* ADR-0058 — Director-Driven Pulse and Block-Stream-Bus
* ADR-0059 — Semantic NPC Motivation Score
* ADR-0060 — Souffleuse Inner Voice Composition
* ADR-0039 — No Pi/Π runtime keys; semantic names only
"""

from __future__ import annotations

import uuid
from typing import Any

from ai_stack.director.director_pulse_contracts import (
    ACTION_SILENCE,
    ACTION_SPEAK,
    CAPABILITY_NAME_ACTOR_PRESSURE_PROFILES,
    CAPABILITY_NAME_INTERACTION_PATTERNS,
    CAPABILITY_NAME_NARRATIVE_MOMENTUM,
    CAPABILITY_NAME_PACING_RHYTHM,
    CAPABILITY_NAME_RELATIONSHIP_DYNAMICS,
    CAPABILITY_NAME_SCENE_ENERGY,
    CAPABILITY_NAME_SOCIAL_PRESSURE,
    CUT_IN_CUT_EM_DASH,
    CUT_IN_CUT_SKIP_TO_END,
    CUT_IN_UNINTERRUPTED,
    LANE_PLAYER_HINT,
    LANE_VISIBLE_SCENE_OUTPUT,
    TRIGGER_MOTIVATION_THRESHOLD_CROSSED,
    TRIGGER_PLAYER_INPUT,
    BLOCK_TYPE_SOUFFLEUSE,
    build_block_stream_event,
    build_director_tick_decision,
    build_player_cut_in_event,
    resolve_cut_kind_for_block_type,
    CUT_KIND_EM_DASH,
)
from ai_stack.npc_agency.npc_motivation_score_engine import (
    compute_npc_motivation_scores,
    select_initiative_actor,
)


def _new_id() -> str:
    return str(uuid.uuid4())


def _std_composition_inputs() -> list[str]:
    return [
        CAPABILITY_NAME_SCENE_ENERGY,
        CAPABILITY_NAME_SOCIAL_PRESSURE,
        CAPABILITY_NAME_RELATIONSHIP_DYNAMICS,
        CAPABILITY_NAME_NARRATIVE_MOMENTUM,
        CAPABILITY_NAME_ACTOR_PRESSURE_PROFILES,
        CAPABILITY_NAME_INTERACTION_PATTERNS,
        CAPABILITY_NAME_PACING_RHYTHM,
    ]


def evaluate_director_tick(
    *,
    trigger_kind: str = TRIGGER_MOTIVATION_THRESHOLD_CROSSED,
    triggering_actor_id: str | None = None,
    npc_ids: list[str],
    scene_energy_output: dict[str, Any] | None = None,
    social_pressure_output: dict[str, Any] | None = None,
    relationship_state_output: dict[str, Any] | None = None,
    narrative_momentum_output: dict[str, Any] | None = None,
    actor_pressure_profiles: dict[str, Any] | None = None,
    npc_motivation_score_policy: dict[str, Any] | None = None,
    gathering_paused: bool = False,
    since_last_tick_ms: float | None = None,
    current_block_id: str | None = None,
    current_block_type: str | None = None,
    block_payload: dict[str, Any] | None = None,
    player_input_payload: dict[str, Any] | None = None,
    tick_id: str | None = None,
) -> dict[str, Any]:
    """Evaluate one Director tick. Returns the full Pulse diagnostic bundle.

    This is the shadow-path entry point. Caller may pass structured capability
    outputs extracted from the existing turn state; this function does not read
    turn state directly.

    Args:
        trigger_kind: What caused this tick evaluation (closed enum).
        triggering_actor_id: Actor that triggered (or None).
        npc_ids: NPC actor IDs present in the current scene.
        scene_energy_output: Structured output from scene_energy capability.
        social_pressure_output: Structured output from social_pressure capability.
        relationship_state_output: Structured output from relationship_dynamics.
        narrative_momentum_output: Structured output from narrative_momentum.
        actor_pressure_profiles: Loaded actor_pressure_profiles.yaml data.
        npc_motivation_score_policy: runtime_intelligence.npc_motivation_score from module.yaml.
        gathering_paused: Whether gathering_paused is active (ADR-0061).
            When True, shadow diagnostics still run; mandatory beats remain blocked.
        since_last_tick_ms: Elapsed ms since last tick (None on first tick).
        current_block_id: ID of the block currently being delivered (for cut-in).
        current_block_type: Type of block being delivered (determines cut-in kind).
        block_payload: The block being delivered this tick (if any).
        player_input_payload: Player's input, if player is cutting in.
        tick_id: Optional explicit tick ID (auto-generated when None).

    Returns:
        dict with keys:
            ``director_tick_decision`` — director_tick_decision.v1
            ``npc_motivation_scores`` — list of npc_motivation_score.v1
            ``block_stream_event`` — block_stream_event.v1 or None
            ``player_cut_in_event`` — player_cut_in_event.v1 or None
            ``gathering_paused`` — bool (passed through for diagnostic transparency)
            ``shadow_only`` — always True
    """
    resolved_tick_id = tick_id or _new_id()

    # 1. Per-NPC motivation scores
    #    Always computed — including when gathering_paused — for diagnostic record.
    motivation_scores = compute_npc_motivation_scores(
        npc_ids=npc_ids,
        tick_id=resolved_tick_id,
        scene_energy_output=scene_energy_output,
        social_pressure_output=social_pressure_output,
        relationship_state_output=relationship_state_output,
        narrative_momentum_output=narrative_momentum_output,
        actor_pressure_profiles=actor_pressure_profiles,
        npc_motivation_score_policy=npc_motivation_score_policy,
    )

    # 2. Initiative selection
    initiative_actor_id = select_initiative_actor(motivation_scores)

    # 3. Resolve trigger kind, action, and chosen actor
    if player_input_payload:
        resolved_trigger = TRIGGER_PLAYER_INPUT
        chosen_action = ACTION_SPEAK
        chosen_actor = triggering_actor_id or "player"
    elif initiative_actor_id:
        resolved_trigger = trigger_kind
        chosen_action = ACTION_SPEAK
        chosen_actor = initiative_actor_id
    else:
        # Silence is a first-class Director decision, not a fallback.
        resolved_trigger = trigger_kind
        chosen_action = ACTION_SILENCE
        chosen_actor = None

    # 4. director_tick_decision
    tick_decision = build_director_tick_decision(
        trigger_kind=resolved_trigger,
        triggering_actor_id=triggering_actor_id,
        chosen_action_kind=chosen_action,
        chosen_actor_id=chosen_actor,
        composition_inputs=_std_composition_inputs(),
        since_last_tick_ms=since_last_tick_ms,
        silence_reason="no_npc_above_motivation_threshold" if chosen_action == ACTION_SILENCE else None,
        tick_id=resolved_tick_id,
    )

    # 5. block_stream_event — emitted when a block is being delivered
    block_stream_ev: dict[str, Any] | None = None
    if block_payload and current_block_type:
        cut_in_state = CUT_IN_UNINTERRUPTED
        if player_input_payload and current_block_id:
            cut_kind = resolve_cut_kind_for_block_type(current_block_type)
            cut_in_state = CUT_IN_CUT_EM_DASH if cut_kind == CUT_KIND_EM_DASH else CUT_IN_CUT_SKIP_TO_END
        lane = LANE_PLAYER_HINT if current_block_type == BLOCK_TYPE_SOUFFLEUSE else LANE_VISIBLE_SCENE_OUTPUT
        block_stream_ev = build_block_stream_event(
            tick_id=resolved_tick_id,
            block_type=current_block_type,
            block_payload=block_payload,
            cut_in_state=cut_in_state,
            lane=lane,
            source=chosen_actor or "director",
        )

    # 6. player_cut_in_event — emitted when player interrupts
    cut_in_ev: dict[str, Any] | None = None
    if player_input_payload:
        cut_kind = resolve_cut_kind_for_block_type(current_block_type)
        cut_in_ev = build_player_cut_in_event(
            tick_id=resolved_tick_id,
            interrupted_block_id=current_block_id,
            interrupted_block_type=current_block_type,
            cut_kind=cut_kind,
            player_input_payload=player_input_payload,
        )

    return {
        "director_tick_decision": tick_decision,
        "npc_motivation_scores": motivation_scores,
        "block_stream_event": block_stream_ev,
        "player_cut_in_event": cut_in_ev,
        "gathering_paused": gathering_paused,
        "shadow_only": True,
    }


__all__ = [
    "evaluate_director_tick",
]
