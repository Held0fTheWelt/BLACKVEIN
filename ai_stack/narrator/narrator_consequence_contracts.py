"""Stateless contracts for player local context transitions and narrator consequences.

Implements PLAYER-LOCAL-CONTEXT-AND-NARRATOR-CONSEQUENCE-01: given the resolved
player_action_frame + affordance_resolution + scene_affordance_model, computes:

  - LocalContextTransition  — what changed in the player's spatial context
  - NarratorConsequencePlan — what the narrator should report (sourced from
                               authored scene-affordance detail when available)
  - updated player_local_context — new area/perception state after the action
"""
from __future__ import annotations

from typing import Any


def normalize_scene_affordance_model_for_contracts(model: dict[str, Any] | None) -> dict[str, Any]:
    """Wrap flat resolver models so contracts see ``scene_affordances.{locations,objects}``."""
    sam = model if isinstance(model, dict) else {}
    inner = sam.get("scene_affordances")
    if isinstance(inner, dict) and inner:
        return sam
    locs = sam.get("locations")
    objs = sam.get("objects")
    if isinstance(locs, list) or isinstance(objs, list):
        inner_out: dict[str, Any] = {}
        if sam.get("current_area") is not None:
            inner_out["current_area"] = sam.get("current_area")
        if sam.get("inferred_area_policy") is not None:
            inner_out["inferred_area_policy"] = sam.get("inferred_area_policy")
        if isinstance(locs, list):
            inner_out["locations"] = locs
        if isinstance(objs, list):
            inner_out["objects"] = objs
        return {"scene_affordances": inner_out}
    return sam


def _find_location(
    scene_affordance_model: dict[str, Any],
    target_id: str,
    target_alias: str,
) -> dict[str, Any] | None:
    locations = (scene_affordance_model.get("scene_affordances") or {}).get("locations") or []
    t_id = target_id.lower()
    t_alias = target_alias.lower()
    for loc in locations:
        if not isinstance(loc, dict):
            continue
        if loc.get("id", "").lower() == t_id:
            return loc
        aliases_lower = [a.lower() for a in (loc.get("aliases") or loc.get("content_terms") or [])]
        if t_id in aliases_lower or t_alias in aliases_lower:
            return loc
    return None


def _find_object(
    scene_affordance_model: dict[str, Any],
    target_id: str,
    target_alias: str,
) -> dict[str, Any] | None:
    objects = (scene_affordance_model.get("scene_affordances") or {}).get("objects") or []
    t_id = target_id.lower()
    t_alias = target_alias.lower()
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        if obj.get("id", "").lower() == t_id:
            return obj
        aliases_lower = [a.lower() for a in (obj.get("aliases") or obj.get("content_terms") or [])]
        if t_id in aliases_lower or t_alias in aliases_lower:
            return obj
    return None


def build_local_context_transition(
    *,
    player_action_frame: dict[str, Any],
    affordance_resolution: dict[str, Any],
    scene_affordance_model: dict[str, Any],
    current_player_local_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute a LocalContextTransition from action frame + scene affordances."""
    verb = str(player_action_frame.get("verb") or "").strip().lower()
    action_kind = str(player_action_frame.get("action_kind") or "").strip().lower()
    affordance_status = str(affordance_resolution.get("affordance_status") or "").strip().lower()
    rt = player_action_frame.get("resolved_target") if isinstance(player_action_frame.get("resolved_target"), dict) else {}
    target_id = str(rt.get("target_id") or "").strip()
    target_alias = str(rt.get("matched_alias") or rt.get("canonical_name") or "").strip()
    target_resolution_source = str(player_action_frame.get("target_resolution_source") or "").strip()
    access_status = str(player_action_frame.get("access_status") or "").strip()
    semantic_inference = (
        player_action_frame.get("semantic_inference")
        if isinstance(player_action_frame.get("semantic_inference"), dict)
        else {}
    )
    plausible_inferred_target = (
        target_resolution_source == "ai_semantic_resolution.plausible_inference"
        or access_status == "inferred_plausible"
        or bool(semantic_inference)
    )

    scene_af = (scene_affordance_model.get("scene_affordances") or {}) if isinstance(scene_affordance_model, dict) else {}
    current_loc = str(
        (current_player_local_context or {}).get("current_location_id")
        or (current_player_local_context or {}).get("current_area")
        or scene_af.get("current_area")
        or ""
    ).strip()
    current_area = current_loc

    is_movement = action_kind == "movement"
    is_posture_change = action_kind == "posture_change"
    is_perception = action_kind == "perception"
    is_object_interaction = action_kind == "object_interaction"
    transition_allowed = affordance_status in {"allowed", "allowed_offscreen", "partial"}

    transition: dict[str, Any] = {
        "from_area": current_area or None,
        "to_area": None,
        "from_location_id": current_loc or None,
        "to_location_id": None,
        "transition_type": None,
        "transition_allowed": transition_allowed,
        "new_area_established": False,
        "location_found": False,
        "object_found": False,
        "object_inferred": False,
        "target_id": target_id or None,
        "target_alias": target_alias or None,
        "target_resolution_source": target_resolution_source or None,
        "semantic_inference": dict(semantic_inference) if semantic_inference else None,
    }

    if is_movement and transition_allowed:
        loc = _find_location(scene_affordance_model, target_id, target_alias)
        if loc:
            to_id = str(loc.get("id") or "").strip()
            transition["to_area"] = to_id
            transition["to_location_id"] = to_id or None
            transition["location_found"] = True
            transition["new_area_established"] = affordance_status in {"allowed", "allowed_offscreen"}
        transition["transition_type"] = (
            "move_offscreen" if affordance_status == "allowed_offscreen" else "movement"
        )
    elif is_posture_change:
        transition["transition_type"] = "posture_change"
        transition["new_area_established"] = False
    elif is_perception:
        obj = _find_object(scene_affordance_model, target_id, target_alias)
        if obj:
            transition["object_found"] = True
        elif plausible_inferred_target:
            transition["object_found"] = True
            transition["object_inferred"] = True
        transition["transition_type"] = "perception"
    elif is_object_interaction:
        obj = _find_object(scene_affordance_model, target_id, target_alias)
        if obj:
            transition["object_found"] = True
        elif plausible_inferred_target:
            transition["object_found"] = True
            transition["object_inferred"] = True
        transition["transition_type"] = "object_interaction"

    return transition


def build_narrator_consequence_plan(
    *,
    lang: str,
    player_action_frame: dict[str, Any],
    affordance_resolution: dict[str, Any],
    scene_affordance_model: dict[str, Any],
    local_context_transition: dict[str, Any],
) -> dict[str, Any]:
    """Build a NarratorConsequencePlan from scene affordance detail + transition."""
    rt = player_action_frame.get("resolved_target") if isinstance(player_action_frame.get("resolved_target"), dict) else {}
    target_id = str(rt.get("target_id") or "").strip()
    target_alias = str(rt.get("matched_alias") or rt.get("canonical_name") or "").strip()
    semantic_inference = (
        player_action_frame.get("semantic_inference")
        if isinstance(player_action_frame.get("semantic_inference"), dict)
        else {}
    )

    transition_type = str(local_context_transition.get("transition_type") or "").strip()
    lang_key = lang[:2].lower() if lang else "de"

    consequence_text: str | None = None
    consequence_type: str = "generic"
    source: str = "template_fallback"
    affordances_available: list[str] = []

    if transition_type in {"move_offscreen", "move_local", "movement"} and local_context_transition.get("location_found"):
        loc = _find_location(scene_affordance_model, target_id, target_alias)
        if loc:
            detail_map = loc.get("entry_sensory_detail") or {}
            detail = detail_map.get(lang_key) or detail_map.get("de") or detail_map.get("en")
            detail = detail or loc.get("description")
            if detail:
                consequence_text = str(detail)
                consequence_type = "area_transition"
                source = "scene_affordance_detail"
            affordances_available = list(loc.get("available_affordances") or [])
    elif transition_type == "perception" and local_context_transition.get("object_found"):
        if local_context_transition.get("object_inferred"):
            consequence_type = "plausible_perception_result"
            source = "ai_semantic_plausible_inference"
            affordances_available = []
        else:
            obj = _find_object(scene_affordance_model, target_id, target_alias)
            if obj:
                detail_map = obj.get("perception_detail") or {}
                detail = detail_map.get(lang_key) or detail_map.get("de") or detail_map.get("en")
                detail = detail or obj.get("description")
                if detail:
                    consequence_text = str(detail)
                    consequence_type = "perception_result"
                    source = "scene_affordance_detail"
    elif transition_type == "object_interaction" and local_context_transition.get("object_found"):
        if local_context_transition.get("object_inferred"):
            consequence_type = "plausible_object_interaction"
            source = "ai_semantic_plausible_inference"
        else:
            consequence_type = "object_state_change"

    return {
        "consequence_text": consequence_text,
        "consequence_type": consequence_type,
        "source": source,
        "requires_model_realization": source == "ai_semantic_plausible_inference" or consequence_text is None,
        "inferred_target": {
            "target_id": target_id or None,
            "target_alias": target_alias or None,
            "semantic_inference": dict(semantic_inference) if semantic_inference else None,
        }
        if source == "ai_semantic_plausible_inference"
        else None,
        "local_context_updated": local_context_transition.get("new_area_established", False),
        "affordances_available": affordances_available,
        "transition_type": transition_type,
    }


def build_updated_player_local_context(
    *,
    current_player_local_context: dict[str, Any] | None,
    local_context_transition: dict[str, Any],
    narrator_consequence_plan: dict[str, Any],
    scene_affordance_model: dict[str, Any],
) -> dict[str, Any]:
    """Return the updated player_local_context after a committed transition."""
    base = dict(current_player_local_context or {})

    if local_context_transition.get("new_area_established") and local_context_transition.get("to_area"):
        new_loc = str(local_context_transition["to_area"]).strip()
        prior_loc = str(
            (current_player_local_context or {}).get("current_location_id")
            or (current_player_local_context or {}).get("current_area")
            or ""
        ).strip()
        base["current_area"] = new_loc
        base["current_location_id"] = new_loc
        if prior_loc:
            base["previous_location_id"] = prior_loc
            base["previous_area"] = prior_loc
        base["available_affordances"] = narrator_consequence_plan.get("affordances_available") or []
        base["last_transition_type"] = local_context_transition.get("transition_type")
        base["last_perception_result"] = None
        base["last_perception_target"] = None
    elif local_context_transition.get("transition_type") == "perception":
        base["last_perception_result"] = narrator_consequence_plan.get("consequence_text")
        base["last_perception_target"] = local_context_transition.get("target_id")

    if not base.get("current_area"):
        scene_af = (scene_affordance_model.get("scene_affordances") or {}) if isinstance(scene_affordance_model, dict) else {}
        ca = scene_af.get("current_area") or "living_room"
        base.setdefault("current_area", ca)
        base.setdefault("current_location_id", ca)

    return base
