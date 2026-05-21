"""Public semantic scene-plan enrichment builder."""

from __future__ import annotations

from typing import Any

from .actor_directives import _actor_directives, _handover_policy
from .capability_plan import _director_capability_manager_plan
from .content_frame import _content_frame, _speech_profile_for_frame
from .continuity import (
    _continuity_for_plan,
    _continuity_obligation,
    _expected_transition_pattern,
    _list_continuity_classes,
    _pressure_axis,
    _pressure_target,
)
from .dialogue_plan import (
    _dialogue_plan,
    _handover_policy_for_speech,
    _merge_dialogue_into_beats,
    _quote_moment_policy,
)
from .dramatic_beats import _dramatic_beats
from .mappings import SEMANTIC_SCENE_PLANNER_VERSION, TRANSITION_PATTERNS
from .scene_target import (
    _narrative_scene_function,
    _pressure_function,
    _realization_mode,
    _scene_target,
    _target_obligations,
)
from .utils import _append_unique, _as_dict, _clean


def build_semantic_scene_plan_enrichment(
    *,
    selected_scene_function: str,
    selected_responder_set: list[dict[str, Any]] | None,
    pacing_mode: str,
    silence_brevity_decision: dict[str, Any] | None,
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
    character_mind_records: list[dict[str, Any]] | None,
    scene_assessment: dict[str, Any] | None = None,
    implied_continuity_by_function: dict[str, str] | None = None,
    prior_continuity_impacts: list[dict[str, Any]] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
    selection_source: str = "semantic_pipeline_v1",
    current_scene_id: str = "",
    turn_input_class: str = "",
    canonical_path: dict[str, Any] | None = None,
    scene_graph: dict[str, Any] | None = None,
    locations: dict[str, Any] | None = None,
    objects: dict[str, Any] | None = None,
    character_documents: dict[str, Any] | None = None,
    content_access_policy: dict[str, Any] | None = None,
    beat_library: dict[str, Any] | None = None,
    opening_quote_anchors: dict[str, Any] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    environment_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build bounded scene-plan fields from structured planner records."""

    prior_classes = _list_continuity_classes(prior_continuity_impacts)
    sem = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    social = social_state_record if isinstance(social_state_record, dict) else {}
    scene = scene_assessment if isinstance(scene_assessment, dict) else {}
    silence = silence_brevity_decision if isinstance(silence_brevity_decision, dict) else {}
    scene_fn = _clean(selected_scene_function) or "establish_pressure"
    pacing = _clean(pacing_mode) or "standard"

    continuity_class = _continuity_for_plan(
        selected_scene_function=scene_fn,
        implied_continuity_by_function=implied_continuity_by_function,
        semantic_move_record=sem,
        social_state_record=social,
    )
    pressure_axis = _pressure_axis(
        selected_scene_function=scene_fn,
        semantic_move_record=sem,
    )
    transition = _expected_transition_pattern(
        selected_scene_function=scene_fn,
        continuity_class=continuity_class,
        semantic_move_record=sem,
        social_state_record=social,
        pacing_mode=pacing,
        prior_classes=prior_classes,


    )
    if transition not in TRANSITION_PATTERNS:
        transition = "soft"
    target = _pressure_target(
        selected_scene_function=scene_fn,
        selected_responder_set=selected_responder_set,
        semantic_move_record=sem,
        social_state_record=social,
        character_mind_records=character_mind_records,
        pressure_axis=pressure_axis,
    )
    obligation = _continuity_obligation(
        continuity_class=continuity_class,
        expected_transition_pattern=transition,
        prior_classes=prior_classes,
        pressure_axis=pressure_axis,
        selected_scene_function=scene_fn,
        prior_planner_truth=prior_planner_truth,
    )
    narrative_scene_function = _narrative_scene_function(
        selected_scene_function=scene_fn,
        silence_brevity_decision=silence,
        semantic_move_record=sem,
        scene_assessment=scene,
        selection_source=selection_source,
    )
    pressure_function = _pressure_function(
        pressure_axis=pressure_axis,
        narrative_scene_function=narrative_scene_function,
    )
    realization_mode = _realization_mode(narrative_scene_function)
    scene_target = _scene_target(
        selected_scene_function=scene_fn,
        narrative_scene_function=narrative_scene_function,
        pressure_function=pressure_function,
        pressure_target=target,
        social_state_record=social,
        scene_assessment=scene,
    )
    target.setdefault("target_id", scene_target.get("target_id"))
    target.setdefault("target_function", scene_target.get("target_function"))
    target.setdefault("narrative_scene_function", narrative_scene_function)
    target.setdefault("pressure_function", pressure_function)
    content_frame = _content_frame(
        canonical_path=canonical_path,
        scene_graph=scene_graph,
        locations=locations,
        objects=objects,
        character_documents=character_documents,
        content_access_policy=content_access_policy,
        scene_assessment=scene,
        environment_state=environment_state,
        current_scene_id=current_scene_id or _clean(scene.get("current_scene_id") or scene.get("scene_id")),
        narrative_scene_function=narrative_scene_function,
        selection_source=selection_source,
    )
    if content_frame.get("canonical_path_step_id"):
        scene_target["canonical_path_step_id"] = content_frame.get("canonical_path_step_id")
        scene_target["canonical_path_mode"] = content_frame.get("canonical_path_mode")
        target["canonical_path_step_id"] = content_frame.get("canonical_path_step_id")
    if content_frame.get("location_id"):
        scene_target["location_id"] = content_frame.get("location_id")
    if content_frame.get("object_focus_ids"):
        scene_target["object_focus_ids"] = list(content_frame.get("object_focus_ids") or [])

    speech_policy = _speech_profile_for_frame(
        content_frame=content_frame,
        narrative_scene_function=narrative_scene_function,
        selected_responder_set=selected_responder_set,
        actor_lane_context=actor_lane_context,
        opening_quote_anchors=opening_quote_anchors,
    )


    dialogue_plan = _dialogue_plan(
        content_frame=content_frame,
        speech_policy=speech_policy,
        selected_responder_set=selected_responder_set,
        actor_lane_context=actor_lane_context,
        beat_library=beat_library,
        character_documents=character_documents,
    )
    quote_moment_policy = _quote_moment_policy(
        content_frame=content_frame,
        speech_policy=speech_policy,
        dialogue_plan=dialogue_plan,
        opening_quote_anchors=opening_quote_anchors,
    )
    if dialogue_plan and speech_policy.get("speech_required"):
        has_dialogue_chain = any(
            _as_dict(row.get("forces_response_chain")).get("target_actor_id")
            for row in dialogue_plan
            if isinstance(row, dict)
        )
        realization_mode = (
            "content_guided_dialogue_chain"
            if has_dialogue_chain
            else "content_guided_dialogue"
        )
    elif dialogue_plan and speech_policy.get("speech_recommended"):
        realization_mode = "content_guided_optional_dialogue"

    beats = _dramatic_beats(
        selected_scene_function=scene_fn,
        narrative_scene_function=narrative_scene_function,
        scene_target=scene_target,
        expected_transition_pattern=transition,
        pacing_mode=pacing,
    )
    target_obligations = _target_obligations(
        scene_target=scene_target,
        continuity_obligation=obligation,
        narrative_scene_function=narrative_scene_function,
    )
    if speech_policy.get("speech_recommended"):
        target_obligations.append(
            {
                "obligation_order": len(target_obligations) + 1,
                "obligation_kind": "realize_content_guided_speech"
                if speech_policy.get("speech_required")
                else "offer_content_guided_speech",
                "applies_to": content_frame.get("canonical_path_step_id"),
                "required": bool(speech_policy.get("speech_required")),
                "success_condition": "dialogue_plan_realized_or_safely_degraded",
                "constraints": [
                    "do_not_force_player_speech",
                    "respect_quote_moment_policy",
                    "do_not_use_dialogue_as_unbounded_exposition",
                ],
            }
        )
    actor_directives = _actor_directives(
        selected_responder_set=selected_responder_set,
        narrative_scene_function=narrative_scene_function,
        scene_target=scene_target,
        silence_brevity_decision=silence,
    )
    for row in dialogue_plan:
        if not isinstance(row, dict):
            continue
        actor_id = _clean(row.get("actor_id"))
        if not actor_id:
            continue
        duplicate = any(
            _clean(existing.get("actor_id")) == actor_id
            and _clean(existing.get("directive")) == "deliver_npc_speech_beat"


            for existing in actor_directives
            if isinstance(existing, dict)
        )
        if duplicate:
            continue
        actor_directives.append(
            {
                "directive_order": len(actor_directives) + 1,
                "actor_id": actor_id,
                "actor_role": "content_dialogue_speaker",
                "directive": "deliver_npc_speech_beat",
                "visibility": "spoken_line",
                "required": bool(row.get("required")),
                "target_function": scene_target.get("target_function"),
                "dialogue_order": row.get("dialogue_order"),
                "beat_pattern_ref": row.get("beat_pattern_ref"),
                "constraints": list(row.get("constraints") or []),
                "reason_codes": [
                    f"speech_function:{speech_policy.get('speech_function')}",
                    f"dialogue_intent:{row.get('intent')}",
                ],
            }
        )
    beats = _merge_dialogue_into_beats(
        dramatic_beats=beats,
        dialogue_plan=dialogue_plan,
        expected_transition_pattern=transition,
        pacing_mode=pacing,
    )
    handover_policy = _handover_policy(
        narrative_scene_function=narrative_scene_function,
        dramatic_beats=beats,
        expected_transition_pattern=transition,
    )
    handover_policy = _handover_policy_for_speech(
        base_policy=handover_policy,
        speech_policy=speech_policy,
        dialogue_plan=dialogue_plan,
        dramatic_beats=beats,
    )
    capability_manager_plan = _director_capability_manager_plan(
        narrative_scene_function=narrative_scene_function,
        realization_mode=realization_mode,
        content_frame=content_frame,
        speech_policy=speech_policy,
        dialogue_plan=dialogue_plan,
        dramatic_beats=beats,
        actor_directives=actor_directives,
        turn_input_class=turn_input_class,
    )
    rationale_codes: list[str] = [SEMANTIC_SCENE_PLANNER_VERSION]
    _append_unique(rationale_codes, f"selection_source:{selection_source}")
    _append_unique(rationale_codes, f"pressure_axis:{pressure_axis}")
    _append_unique(rationale_codes, f"pressure_function:{pressure_function}")
    _append_unique(rationale_codes, f"narrative_scene_function:{narrative_scene_function}")
    _append_unique(rationale_codes, f"scene_target:{scene_target.get('target_function')}")
    _append_unique(rationale_codes, f"continuity_class:{continuity_class}")
    _append_unique(rationale_codes, f"transition_pattern:{transition}")
    if _clean(scene.get("pressure_state")):
        _append_unique(rationale_codes, f"scene_pressure:{scene.get('pressure_state')}")
    if _clean(silence.get("mode")) and _clean(silence.get("mode")) != "normal":
        _append_unique(rationale_codes, f"silence_mode:{silence.get('mode')}")
    if _clean(content_frame.get("canonical_path_step_id")):
        _append_unique(rationale_codes, f"canonical_path_step:{content_frame.get('canonical_path_step_id')}")
    if speech_policy.get("speech_recommended"):
        _append_unique(rationale_codes, f"speech_function:{speech_policy.get('speech_function')}")
    if quote_moment_policy.get("exact_quote_allowed"):
        _append_unique(rationale_codes, "quote_moment:moment_locked_exact_anchor_allowed")
    if capability_manager_plan.get("selected_capabilities"):
        _append_unique(rationale_codes, "capability_manager:selective_capability_gate")

    return {


        "semantic_scene_planner_version": SEMANTIC_SCENE_PLANNER_VERSION,
        "narrative_scene_function": narrative_scene_function,
        "realization_mode": realization_mode,
        "pressure_function": pressure_function,
        "scene_target": scene_target,
        "pressure_target": target,
        "target_obligations": target_obligations,
        "actor_directives": actor_directives,
        "dramatic_beats": beats,
        "handover_policy": handover_policy,
        "content_frame": content_frame,
        "speech_policy": speech_policy,
        "quote_moment_policy": quote_moment_policy,
        "dialogue_plan": dialogue_plan,
        "capability_manager_plan": capability_manager_plan,
        "continuity_obligation": obligation,
        "expected_transition_pattern": transition,
        "planner_rationale_codes": rationale_codes,
    }
