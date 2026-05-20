"""Context assembly before runtime aspect validation begins."""

from __future__ import annotations

from .contracts import RuntimeAspectValidationHooks, _RuntimeAspectBuild
from .dependencies import *

def _initial_context(
    *,
    state: Any,
    generation: dict[str, Any],
    proposed_state_effects: list[dict[str, Any]],
    outcome: dict[str, Any],
    hooks: RuntimeAspectValidationHooks,
) -> _RuntimeAspectBuild:
    next_outcome = dict(outcome or {})
    actor_lane = hooks.actor_lane_validation(state, generation)
    if actor_lane.get("status") == "rejected" and next_outcome.get("status") == "approved":
        next_outcome = {
            **next_outcome,
            "status": "rejected",
            "reason": actor_lane.get("reason") or "actor_lane_validation_rejected",
            "actor_lane_validation": actor_lane,
        }
    else:
        next_outcome = {**next_outcome, "actor_lane_validation": actor_lane}

    narrator, npc = hooks.build_authority_aspect_records(
        state=state,
        generation=generation,
        proposed_state_effects=proposed_state_effects,
    )
    ledger = state.get("turn_aspect_ledger") if isinstance(state.get("turn_aspect_ledger"), dict) else {}
    ledger = set_aspect_record(ledger, ASPECT_NARRATOR_AUTHORITY, narrator)
    ledger = set_aspect_record(ledger, ASPECT_NPC_AUTHORITY, npc)
    structured = hooks.structured_output_from_generation(generation)
    ctx = _RuntimeAspectBuild(
        state=state,
        generation=generation,
        proposed_state_effects=proposed_state_effects,
        hooks=hooks,
        outcome=next_outcome,
        dramatic_rejection_locked=bool(hooks.dramatic_quality_rejection_locked(next_outcome)),
        actor_lane_validation=actor_lane,
        ledger=ledger,
        structured_output=structured,
        narrator_authority=narrator,
        npc_authority=npc,
    )
    voice_validation = hooks.voice_consistency_validation(state=state, generation=generation)
    ctx.validations["voice_consistency"] = voice_validation
    ctx.ledger = set_aspect_record(
        ctx.ledger,
        ASPECT_VOICE_CONSISTENCY,
        hooks.voice_aspect_record(voice_validation),
    )
    return ctx
