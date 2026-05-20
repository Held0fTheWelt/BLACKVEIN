"""Hydrate legacy narrative-only structured output into actor-turn lanes.

GoC tests and older adapters may return only ``narrative_response`` / ``narration_summary``.
Runtime validators for actor-response floors and npc initiative require ``spoken_lines`` /
``action_lines`` counts. This module bridges that gap deterministically from director state.
"""

from __future__ import annotations

import json
from typing import Any

from ai_stack.module_runtime_policy import minimum_actor_response_count_from_governance
from ai_stack.story_runtime.npc_agency.npc_agency_contracts import (
    coerce_dict_rows,
    dedupe_strings,
    is_forbidden_actor_id,
    planned_actor_ids_from_plan,
)
from ai_stack.opening_shape_normalizer import narration_summary_to_plain_str

GOC_MODULE_ID = "god_of_carnage"
RUNTIME_ACTOR_TURN_SCHEMA = "runtime_actor_turn_v1"


def _responder_actor_ids(selected_responder_set: list[Any] | None) -> list[str]:
    out: list[str] = []
    if not isinstance(selected_responder_set, list):
        return out
    for row in selected_responder_set:
        if not isinstance(row, dict):
            continue
        actor_id = str(row.get("actor_id") or "").strip()
        if actor_id and actor_id not in out:
            out.append(actor_id)
    return out


def _required_npc_actor_ids(
    npc_agency_plan: dict[str, Any] | None,
    *,
    actor_lane_context: dict[str, Any] | None,
) -> list[str]:
    if not isinstance(npc_agency_plan, dict):
        return []
    required = dedupe_strings(list(npc_agency_plan.get("required_actor_ids") or []))
    if required:
        return [
            actor_id
            for actor_id in required
            if not is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context)
        ]
    planned = planned_actor_ids_from_plan(npc_agency_plan)
    initiatives = coerce_dict_rows(npc_agency_plan.get("npc_initiatives"))
    required_from_rows = [
        str(row.get("actor_id") or "").strip()
        for row in initiatives
        if isinstance(row, dict) and row.get("required") and str(row.get("actor_id") or "").strip()
    ]
    merged = dedupe_strings(planned + required_from_rows)
    return [
        actor_id
        for actor_id in merged
        if not is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context)
    ]


def _spoken_line_text(*, narrative: str, actor_index: int) -> str:
    text = narrative.strip()
    if not text:
        return '"…"'
    if actor_index == 0:
        snippet = text[:120].strip()
        if len(text) > 120:
            snippet = snippet.rsplit(" ", 1)[0].strip() or snippet
        if not snippet.endswith((".", "!", "?", '"')):
            snippet = f"{snippet}."
        if not snippet.startswith('"'):
            snippet = f'"{snippet}"'
        return snippet
    return '"…"'


def _action_line_text(*, narrative: str, actor_id: str) -> str:
    snippet = narrative.strip()[:80] or "reacts in the room."
    return f"{actor_id.replace('_', ' ')} {snippet}"


def _actor_lane_substance_count(structured: dict[str, Any]) -> int:
    spoken = len([x for x in (structured.get("spoken_lines") or []) if isinstance(x, dict)])
    action = len([x for x in (structured.get("action_lines") or []) if isinstance(x, dict)])
    return spoken + action


def should_hydrate_legacy_actor_lanes(
    structured_output: dict[str, Any] | None,
    *,
    module_id: str,
    transition_pattern: str | None = None,
    parser_error: Any = None,
) -> bool:
    if module_id != GOC_MODULE_ID:
        return False
    if str(transition_pattern or "").strip().lower() == "diagnostics_only":
        return False
    if parser_error:
        return False
    if not isinstance(structured_output, dict):
        return False
    narrative = narration_summary_to_plain_str(structured_output.get("narration_summary"))
    if not narrative:
        narrative = str(structured_output.get("narrative_response") or "").strip()
    if not narrative:
        return False
    return _actor_lane_substance_count(structured_output) == 0


def hydrate_legacy_actor_lanes(
    structured_output: dict[str, Any],
    *,
    selected_responder_set: list[dict[str, Any]] | None = None,
    scene_energy_target: dict[str, Any] | None = None,
    pacing_mode: str | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
    selected_scene_function: str | None = None,
    npc_agency_plan: dict[str, Any] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    """Fill empty actor lanes from director state and narrative prose."""

    if not should_hydrate_legacy_actor_lanes(
        structured_output,
        module_id=GOC_MODULE_ID,
    ):
        return structured_output, False

    narrative = narration_summary_to_plain_str(structured_output.get("narration_summary"))
    if not narrative:
        narrative = str(structured_output.get("narrative_response") or "").strip()

    responder_ids = _responder_actor_ids(selected_responder_set)
    primary = str(structured_output.get("primary_responder_id") or "").strip()
    if not primary and responder_ids:
        primary = responder_ids[0]
    secondary = [
        str(x).strip()
        for x in (structured_output.get("secondary_responder_ids") or [])
        if str(x).strip()
    ]
    if not secondary and len(responder_ids) > 1:
        secondary = responder_ids[1:]

    min_actors = minimum_actor_response_count_from_governance(
        actor_response_floor_target=scene_energy_target,
        pacing_mode=pacing_mode,
        module_runtime_policy=module_runtime_policy,
        selected_scene_function=selected_scene_function,
    )
    required_npc = _required_npc_actor_ids(npc_agency_plan, actor_lane_context=actor_lane_context)
    low_density_pacing = str(pacing_mode or "").strip().lower() in {"thin_edge", "compressed"}

    target_actors: list[str] = []
    if low_density_pacing:
        for actor_id in dedupe_strings(
            ([primary] if primary else [])
            + required_npc
            + responder_ids
            + secondary
        ):
            if not actor_id or actor_id in target_actors:
                continue
            if is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context):
                continue
            target_actors.append(actor_id)
        while len(target_actors) < min_actors and secondary:
            for actor_id in secondary:
                if actor_id in target_actors:
                    continue
                if is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context):
                    continue
                target_actors.append(actor_id)
                if len(target_actors) >= min_actors:
                    break
    else:
        for actor_id in dedupe_strings(responder_ids + required_npc + ([primary] if primary else [])):
            if not actor_id:
                continue
            if is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context):
                continue
            if actor_id not in target_actors:
                target_actors.append(actor_id)

        while len(target_actors) < min_actors and secondary:
            for actor_id in secondary:
                if actor_id not in target_actors:
                    target_actors.append(actor_id)
                if len(target_actors) >= min_actors:
                    break

    if not target_actors and primary:
        target_actors = [primary]
    if not target_actors:
        return structured_output, False

    max_density = None
    if isinstance(scene_energy_target, dict):
        raw_max = scene_energy_target.get("maximum_visible_density_count")
        if isinstance(raw_max, int) and raw_max > 0:
            max_density = raw_max

    spoken_lines: list[dict[str, str]] = []
    action_lines: list[dict[str, str]] = []
    for idx, actor_id in enumerate(target_actors):
        if idx == 0:
            spoken_lines.append(
                {"speaker_id": actor_id, "text": _spoken_line_text(narrative=narrative, actor_index=idx)}
            )
        else:
            action_lines.append(
                {"actor_id": actor_id, "text": _action_line_text(narrative=narrative, actor_id=actor_id)}
            )

    initiative_events: list[dict[str, str]] = []
    skip_initiative = low_density_pacing
    if not skip_initiative:
        for actor_id in required_npc:
            if actor_id in target_actors:
                initiative_events.append(
                    {"actor_id": actor_id, "type": "seize", "reason": "legacy_actor_lane_hydration"}
                )

    if max_density is not None:
        narrative_blocks = 1 if narrative else 0
        lane_budget = max(0, max_density - narrative_blocks)
        while _actor_lane_substance_count(
            {"spoken_lines": spoken_lines, "action_lines": action_lines, "initiative_events": initiative_events}
        ) > lane_budget:
            if initiative_events:
                initiative_events.pop()
            elif action_lines:
                action_lines.pop()
            elif len(spoken_lines) > 1:
                spoken_lines.pop()
            else:
                break

    hydrated = dict(structured_output)
    hydrated["schema_version"] = RUNTIME_ACTOR_TURN_SCHEMA
    if primary:
        hydrated["primary_responder_id"] = primary
        hydrated["responder_id"] = primary
    if secondary:
        hydrated["secondary_responder_ids"] = secondary
    hydrated["spoken_lines"] = spoken_lines
    hydrated["action_lines"] = action_lines
    if initiative_events:
        existing = coerce_dict_rows(hydrated.get("initiative_events"))
        merged_events = existing + [
            row for row in initiative_events if row not in existing
        ]
        hydrated["initiative_events"] = merged_events
    # Keep one narrative prose field so pacing rhythm does not double-count blocks.
    if narrative:
        if str(hydrated.get("narrative_response") or "").strip():
            pass
        elif narration_summary_to_plain_str(hydrated.get("narration_summary")):
            pass
        else:
            hydrated["narrative_response"] = narrative
    return hydrated, True


def _hydrate_sensory_context_events(
    structured_output: dict[str, Any],
    *,
    sensory_context_target: dict[str, Any] | None,
) -> tuple[dict[str, Any], bool]:
    if not isinstance(sensory_context_target, dict) or not sensory_context_target:
        return structured_output, False
    if not bool(sensory_context_target.get("require_structured_events")):
        return structured_output, False
    existing = coerce_dict_rows(structured_output.get("sensory_context_events"))
    if existing:
        return structured_output, False
    layers = sensory_context_target.get("selected_layers")
    if not isinstance(layers, list) or not layers:
        return structured_output, False
    events: list[dict[str, str]] = []
    for row in layers:
        if not isinstance(row, dict):
            continue
        layer_id = str(row.get("layer_id") or "").strip()
        if not layer_id:
            continue
        events.append(
            {
                "layer_id": layer_id,
                "source_ref": str(row.get("source_ref") or "").strip(),
            }
        )
    if not events:
        return structured_output, False
    hydrated = dict(structured_output)
    hydrated["sensory_context_events"] = events
    return hydrated, True


def apply_legacy_structured_hydration(
    state: dict[str, Any],
    generation: dict[str, Any],
) -> dict[str, Any]:
    """Hydrate narrative-only generations before aspect validation or after rewrite."""

    if str(state.get("module_id") or "").strip() != GOC_MODULE_ID:
        return generation
    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output")
    if structured is None:
        raw = generation.get("content") if isinstance(generation.get("content"), str) else ""
        if raw.strip().startswith("{"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    meta = dict(meta)
                    meta["structured_output"] = parsed
                    structured = parsed
            except json.JSONDecodeError:
                return generation
        else:
            return generation
    if not isinstance(structured, dict):
        return generation

    parser_error = (
        generation.get("parser_error")
        or meta.get("langchain_parser_error")
        or meta.get("parser_error")
    )
    transition_pattern = str(state.get("transition_pattern") or "").strip().lower()
    hydrated_any = False
    cleaned = dict(structured)
    interp = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
    frame = state.get("player_action_frame") if isinstance(state.get("player_action_frame"), dict) else {}
    ncp = state.get("narrator_consequence_plan") if isinstance(state.get("narrator_consequence_plan"), dict) else {}
    narrator_only_local_consequence = (
        bool(ncp.get("requires_model_realization"))
        and not bool(interp.get("npc_response_expected"))
        and not bool(frame.get("npc_response_expected"))
    )

    if (
        not narrator_only_local_consequence
        and should_hydrate_legacy_actor_lanes(
            cleaned,
            module_id=GOC_MODULE_ID,
            transition_pattern=transition_pattern,
            parser_error=parser_error,
        )
    ):
        cleaned, actor_changed = hydrate_legacy_actor_lanes(
            cleaned,
            selected_responder_set=state.get("selected_responder_set")
            if isinstance(state.get("selected_responder_set"), list)
            else None,
            scene_energy_target=state.get("scene_energy_target")
            if isinstance(state.get("scene_energy_target"), dict)
            else None,
            pacing_mode=str(state.get("pacing_mode") or "") or None,
            module_runtime_policy=state.get("module_runtime_policy")
            if isinstance(state.get("module_runtime_policy"), dict)
            else None,
            selected_scene_function=str(state.get("selected_scene_function") or "") or None,
            npc_agency_plan=_npc_agency_plan_from_state(state),
            actor_lane_context=state.get("actor_lane_context")
            if isinstance(state.get("actor_lane_context"), dict)
            else None,
        )
        hydrated_any = hydrated_any or actor_changed

    cleaned, sensory_changed = _hydrate_sensory_context_events(
        cleaned,
        sensory_context_target=state.get("sensory_context_target")
        if isinstance(state.get("sensory_context_target"), dict)
        else None,
    )
    hydrated_any = hydrated_any or sensory_changed

    if not hydrated_any:
        return generation

    meta = dict(meta)
    meta["structured_output"] = cleaned
    meta["legacy_actor_lane_hydrated"] = True
    updated = dict(generation)
    updated["metadata"] = meta
    return updated


def _npc_agency_plan_from_state(state: dict[str, Any]) -> dict[str, Any] | None:
    packet = state.get("dramatic_generation_packet")
    if isinstance(packet, dict):
        plan = packet.get("npc_agency_plan")
        if isinstance(plan, dict):
            return plan
        simulation = packet.get("npc_agency_simulation")
        if isinstance(simulation, dict) and isinstance(simulation.get("npc_agency_plan"), dict):
            return simulation["npc_agency_plan"]
    direct = state.get("npc_agency_plan")
    return direct if isinstance(direct, dict) else None
