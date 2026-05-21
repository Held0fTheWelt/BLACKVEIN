"""Director capability-manager plan construction."""

from __future__ import annotations

from typing import Any

from .mappings import (
    DIRECTOR_CAPABILITY_MANAGER_PLAN_SCHEMA_VERSION,
    NPC_ACTION_GESTURE_OPTIONAL,
    NPC_DIRECT_ANSWER_ALLOWED,
    NPC_SOCIAL_REACTION_OPTIONAL,
    NARRATOR_ACTION_CONSEQUENCE_DESCRIBE,
    NARRATOR_OBJECT_STATE_DESCRIBE,
    NARRATOR_OPENING_EVENT_REALIZE,
    NARRATOR_PERCEPTION_RESULT_DESCRIBE,
    NARRATOR_SCENE_CONTEXT_ESTABLISH,
    audit_director_capability_paths,
)
from .utils import _append_unique, _clean, _unique_clean


def _add_capability_step(
    steps: list[dict[str, Any]],
    *,
    capability: str,
    mode: str,
    reason: str,
    source: str,
    beat_orders: list[int] | None = None,
) -> None:
    if not capability:
        return
    for step in steps:
        if step.get("capability") == capability:
            existing_mode = _clean(step.get("mode"))
            if existing_mode != "required" and mode == "required":
                step["mode"] = "required"
            for order in beat_orders or []:
                if order not in step["activates_beat_orders"]:
                    step["activates_beat_orders"].append(order)
            _append_unique(step["reason_codes"], reason)
            return
    steps.append(
        {
            "capability": capability,
            "mode": mode,
            "reason_codes": [reason],
            "source": source,
            "activates_beat_orders": list(beat_orders or []),
        }
    )


def _director_capability_manager_plan(


    *,
    narrative_scene_function: str,
    realization_mode: str,
    content_frame: dict[str, Any],
    speech_policy: dict[str, Any],
    dialogue_plan: list[dict[str, Any]],
    dramatic_beats: list[dict[str, Any]],
    actor_directives: list[dict[str, Any]],
    turn_input_class: str,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    beat_orders_by_kind: dict[str, list[int]] = {}
    for beat in dramatic_beats:
        if not isinstance(beat, dict):
            continue
        kind = _clean(beat.get("beat_kind"))
        try:
            order = int(beat.get("beat_order") or 0)
        except (TypeError, ValueError):
            order = 0
        if kind and order:
            beat_orders_by_kind.setdefault(kind, []).append(order)

    required_narration = narrative_scene_function in {
        "arrange_scene",
        "contain_out_of_scope",
        "establish_scene_anchor",
        "establish_scene_pressure",
        "narrate_consequence",
        "narrate_sensory_focus",
        "surface_information",
    }
    if narrative_scene_function in {"arrange_scene", "establish_scene_anchor", "establish_scene_pressure"}:
        _add_capability_step(
            steps,
            capability=NARRATOR_SCENE_CONTEXT_ESTABLISH,
            mode="required",
            reason=f"narrative_scene_function:{narrative_scene_function}",
            source="scene_director",
            beat_orders=beat_orders_by_kind.get("setup_beat") or beat_orders_by_kind.get("environment_beat"),
        )
    if _clean(turn_input_class).lower() == "opening" or "opening" in _clean(content_frame.get("canonical_path_step_id")):
        _add_capability_step(
            steps,
            capability=NARRATOR_OPENING_EVENT_REALIZE,
            mode="required" if narrative_scene_function == "arrange_scene" else "optional",
            reason="canonical_opening_path_active",
            source="canonical_path",
            beat_orders=beat_orders_by_kind.get("setup_beat"),
        )
    if narrative_scene_function == "narrate_sensory_focus":
        _add_capability_step(
            steps,
            capability=NARRATOR_PERCEPTION_RESULT_DESCRIBE,
            mode="required",
            reason="narrative_scene_function:narrate_sensory_focus",
            source="scene_director",
            beat_orders=beat_orders_by_kind.get("environment_beat"),
        )
    elif content_frame.get("object_focus_ids") and narrative_scene_function in {
        "arrange_scene",
        "surface_information",
        "narrate_consequence",
    }:
        _add_capability_step(
            steps,
            capability=NARRATOR_OBJECT_STATE_DESCRIBE,
            mode="required" if narrative_scene_function == "surface_information" else "optional",
            reason="content_frame:object_focus",
            source="content_frame",
            beat_orders=beat_orders_by_kind.get("information_beat") or beat_orders_by_kind.get("setup_beat"),
        )


    elif required_narration:
        _add_capability_step(
            steps,
            capability=NARRATOR_ACTION_CONSEQUENCE_DESCRIBE,
            mode="required" if narrative_scene_function in {"contain_out_of_scope", "narrate_consequence"} else "optional",
            reason=f"narrative_scene_function:{narrative_scene_function}",
            source="scene_director",
            beat_orders=beat_orders_by_kind.get("narration_beat"),
        )

    if dialogue_plan:
        _add_capability_step(
            steps,
            capability=NPC_SOCIAL_REACTION_OPTIONAL,
            mode="required" if speech_policy.get("speech_required") else "optional",
            reason=f"speech_function:{speech_policy.get('speech_function')}",
            source="speech_policy",
            beat_orders=beat_orders_by_kind.get("npc_speak_beat")
            or beat_orders_by_kind.get("npc_dialogue_beat"),
        )
        if speech_policy.get("speech_function") in {"wording_dispute", "statement_procedure"}:
            _add_capability_step(
                steps,
                capability=NPC_DIRECT_ANSWER_ALLOWED,
                mode="optional",
                reason=f"speech_function:{speech_policy.get('speech_function')}",
                source="speech_policy",
                beat_orders=beat_orders_by_kind.get("npc_speak_beat"),
            )

    if any(
        _clean(row.get("directive")) in {
            "stage_npc_presence",
            "force_npc_reaction",
            "force_secondary_reaction",
            "force_npc_interruption",
            "hold_silence",
        }
        for row in actor_directives
        if isinstance(row, dict)
    ):
        _add_capability_step(
            steps,
            capability=NPC_ACTION_GESTURE_OPTIONAL,
            mode="optional",
            reason="actor_directives:visible_npc_action",
            source="actor_directives",
            beat_orders=beat_orders_by_kind.get("npc_action_beat") or beat_orders_by_kind.get("interruption_beat"),
        )

    required = [row["capability"] for row in steps if row.get("mode") == "required"]
    optional = [row["capability"] for row in steps if row.get("mode") != "required"]
    selected = _unique_clean([*required, *optional])
    suppressed: list[str] = []
    if not dialogue_plan and not speech_policy.get("speech_recommended"):
        suppressed.append(NPC_DIRECT_ANSWER_ALLOWED)
    if narrative_scene_function in {"contain_out_of_scope", "narrate_sensory_focus"} and not dialogue_plan:
        suppressed.append(NPC_SOCIAL_REACTION_OPTIONAL)
    dispatch_audit = audit_director_capability_paths(
        selected_capabilities=selected,
        capability_steps=steps,
        suppressed_capabilities=suppressed,
    )
    executable = list(dispatch_audit.get("executable_capabilities") or [])
    required = [cap for cap in required if cap in executable]
    optional = [cap for cap in optional if cap in executable]

    return {
        "schema_version": DIRECTOR_CAPABILITY_MANAGER_PLAN_SCHEMA_VERSION,
        "manager_contract": "dramatic_capability_manager",
        "selection_source": "semantic_scene_director",
        "execution_strategy": "selective_capability_gate",


        "run_only_selected_capabilities": True,
        "dispatch_status": dispatch_audit.get("status"),
        "decision_basis": {
            "narrative_scene_function": narrative_scene_function,
            "realization_mode": realization_mode,
            "canonical_path_step_id": content_frame.get("canonical_path_step_id"),
            "canonical_path_mode": content_frame.get("canonical_path_mode"),
            "location_id": content_frame.get("location_id"),
            "object_focus_ids": list(content_frame.get("object_focus_ids") or []),
            "speech_required": bool(speech_policy.get("speech_required")),
            "speech_recommended": bool(speech_policy.get("speech_recommended")),
            "speech_function": speech_policy.get("speech_function"),
            "dialogue_beat_count": len(dialogue_plan),
            "quote_anchor_refs": list(content_frame.get("quote_anchor_refs") or []),
        },
        "selected_capabilities": executable,
        "required_capabilities": required,
        "optional_capabilities": optional,
        "suppressed_capabilities": _unique_clean(suppressed),
        "capability_steps": steps,
        "capability_dispatch_paths": list(dispatch_audit.get("paths") or []),
        "capability_dispatch_audit": dispatch_audit,
        "dispatch_queue": list(dispatch_audit.get("dispatch_queue") or []),
        "requested_capabilities_before_audit": selected,
        "requested_visible_functions": executable,
        "realization_mode": realization_mode,
        "tree_pruning": {
            "skip_unselected_runtime_branches": True,
            "recursive_dispatch_allowed": False,
            "queue_expansion_allowed": False,
            "paths_checked_individually": True,
            "reason": "scene_director_selected_minimal_visible_capability_set",
        },
    }
