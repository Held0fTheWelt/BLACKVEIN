"""Execute the canonical validation seam and attach aspect validation output."""

from __future__ import annotations

from .contracts import RuntimeAspectValidationHooks
from .dependencies import *
from .builder import build_runtime_aspect_validation
from .retry_feedback import _dict_or_none, _list_or_empty

def run_runtime_validation_seam(
    *,
    state: Any,
    generation: dict[str, Any],
    proposed_state_effects: list[dict[str, Any]],
    silence_brevity_decision: dict[str, Any],
    actor_lane_validation: ValidationHook,
) -> dict[str, Any]:
    narr = extract_proposed_narrative_text(proposed_state_effects)
    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else {}
    lane_validation = actor_lane_validation(state, generation)
    actor_lane_summary = {
        "spoken_line_count": len(structured.get("spoken_lines") or []),
        "action_line_count": len(structured.get("action_lines") or []),
        "initiative_event_count": len(structured.get("initiative_events") or []),
        "actor_lane_status": str(lane_validation.get("status") or "not_evaluated").strip().lower(),
    }
    eval_ctx = build_evaluation_context_from_runtime_state(
        module_id=str(state.get("module_id") or ""),
        proposed_narrative=narr,
        selected_scene_function=str(state.get("selected_scene_function") or "establish_pressure"),
        pacing_mode=str(state.get("pacing_mode") or "standard"),
        silence_brevity_decision=dict(silence_brevity_decision),
        semantic_move_record=_dict_or_none(state.get("semantic_move_record")),
        social_state_record=_dict_or_none(state.get("social_state_record")),
        character_mind_records=_list_or_empty(state.get("character_mind_records")),
        scene_plan_record=_dict_or_none(state.get("scene_plan_record")),
        prior_continuity_impacts=_list_or_empty(state.get("prior_continuity_impacts")),
        selected_responder_set=_list_or_empty(state.get("selected_responder_set")),
        dramatic_irony_record=_dict_or_none(state.get("dramatic_irony_record")),
        actor_lane_summary=actor_lane_summary,
    )
    return run_validation_seam(
        module_id=state.get("module_id") or "",
        proposed_state_effects=proposed_state_effects,
        generation=generation if isinstance(generation, dict) else {},
        evaluation_context=eval_ctx,
        actor_lane_summary=actor_lane_summary,
        actor_lane_context=_dict_or_none(state.get("actor_lane_context")),
        story_runtime_experience=_dict_or_none(state.get("story_runtime_experience")),
        interpreted_input=_dict_or_none(state.get("interpreted_input")),
        raw_player_input=str(state.get("player_input") or "").strip() or None,
        player_action_frame=_dict_or_none(state.get("player_action_frame")),
        affordance_resolution=_dict_or_none(state.get("affordance_resolution")),
        opening_scene_sequence=_dict_or_none(state.get("opening_scene_sequence")),
        hard_forbidden_rules=_dict_or_none(state.get("hard_forbidden_rules")),
        turn_input_class=state.get("turn_input_class") if isinstance(state.get("turn_input_class"), str) else None,
        scene_plan_record=_dict_or_none(state.get("scene_plan_record")),
        current_scene_id=state.get("current_scene_id") if isinstance(state.get("current_scene_id"), str) else None,
        w5_latest_snapshot=state.get("w5_latest_snapshot"),
    )
