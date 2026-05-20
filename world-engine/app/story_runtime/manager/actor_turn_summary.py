from __future__ import annotations

from ._deps import *

def _build_actor_turn_summary(
    *,
    graph_state: dict[str, Any],
    visible_output_bundle: dict[str, Any] | None,
    dramatic_context_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    bundle = visible_output_bundle if isinstance(visible_output_bundle, dict) else {}
    context = dramatic_context_summary if isinstance(dramatic_context_summary, dict) else {}
    responder = context.get("responder") if isinstance(context.get("responder"), dict) else {}
    responder_scope = responder.get("responder_scope") if isinstance(responder.get("responder_scope"), list) else []
    primary_responder_id = (
        str(graph_state.get("responder_id") or "").strip()
        or str(responder.get("responder_id") or "").strip()
        or None
    )
    secondary_responder_ids = [
        str(x).strip()
        for x in responder_scope
        if str(x).strip() and str(x).strip() != (primary_responder_id or "")
    ]
    spoken_line_count = _actor_line_count(bundle.get("spoken_lines"))
    action_line_count = _actor_line_count(bundle.get("action_lines"))

    generation = graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {}
    metadata = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = metadata.get("structured_output") if isinstance(metadata.get("structured_output"), dict) else {}
    initiative_events = structured.get("initiative_events") if isinstance(structured.get("initiative_events"), list) else []
    initiative_types: list[str] = []
    initiative_actors: list[str] = []
    for event in initiative_events:
        if not isinstance(event, dict):
            continue
        raw_type = event.get("type")
        raw_actor = event.get("actor_id")
        event_type = str(raw_type).strip() if isinstance(raw_type, str) else ""
        actor_id = str(raw_actor).strip() if isinstance(raw_actor, str) else ""
        if event_type and event_type not in initiative_types:
            initiative_types.append(event_type)
        if actor_id and actor_id not in initiative_actors:
            initiative_actors.append(actor_id)
    initiative_summary = {
        "event_count": len([x for x in initiative_events if isinstance(x, dict)]),
        "event_types": initiative_types,
        "actors": initiative_actors,
    }

    validation = (
        graph_state.get("validation_outcome")
        if isinstance(graph_state.get("validation_outcome"), dict)
        else {}
    )
    actor_lane_validation = (
        validation.get("actor_lane_validation")
        if isinstance(validation.get("actor_lane_validation"), dict)
        else {}
    )
    social_outcome = str(graph_state.get("social_outcome") or "").strip()
    dramatic_direction = str(graph_state.get("dramatic_direction") or "").strip()
    summary_parts: list[str] = []
    if primary_responder_id:
        summary_parts.append(f"primary_responder={primary_responder_id}")
    summary_parts.append(f"spoken_lines={spoken_line_count}")
    summary_parts.append(f"action_lines={action_line_count}")
    if initiative_summary["event_count"]:
        summary_parts.append(f"initiative_events={initiative_summary['event_count']}")
    if social_outcome:
        summary_parts.append(f"social_outcome={social_outcome}")
    if dramatic_direction:
        summary_parts.append(f"dramatic_direction={dramatic_direction}")

    return {
        "contract": "actor_turn_summary.v1",
        "primary_responder_id": primary_responder_id,
        "secondary_responder_ids": secondary_responder_ids,
        "spoken_line_count": spoken_line_count,
        "action_line_count": action_line_count,
        "initiative_summary": initiative_summary,
        "actor_lane_validation_status": actor_lane_validation.get("status"),
        "last_actor_outcome_summary": ", ".join(summary_parts) if summary_parts else None,
    }

def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]

def _short_text(value: Any, *, limit: int = 500) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."

def _infer_execution_tier_for_pytest() -> str:
    current = str(os.environ.get("PYTEST_CURRENT_TEST") or "").lower()
    if not current:
        return "diagnostic"
    if "integration" in current:
        return "integration_test"
    if "contract" in current:
        return "contract_test"
    if "fixture" in current:
        return "fixture"
    return "contract_test"

def _goc_shell_actor_firstname(actor_id: str) -> str:
    aid = str(canonicalize_goc_actor_id(str(actor_id).strip()) or str(actor_id).strip()).strip()
    return goc_shell_actor_firstname(aid)

def _goc_npc_shell_legal_name(responder_id: str) -> str:
    rid = str(canonicalize_goc_actor_id(str(responder_id).strip()) or str(responder_id).strip()).strip()
    return goc_npc_shell_legal_name(rid)

def _goc_greeting_imperative_addressee_fragment(raw: str, *, lang: str) -> str | None:
    """If ``raw`` is a greet-X imperative (DE/EN), return the tail after the verb; else ``None``."""
    return greeting_imperative_addressee_fragment(
        raw,
        lang=lang,
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        content_modules_root=_goc_content_modules_root(),
    )

def _goc_addressee_shell_firstname(fragment: str) -> str:
    """Map a free-text addressee token to the same shell first-name spelling we use for NPC labels."""
    frag = str(fragment or "").strip()
    if not frag:
        return ""
    first = frag.split()[0] if frag.split() else frag
    first = first.strip(".,;:!?")
    canon = str(canonicalize_goc_actor_id(first) or first).strip()
    return _goc_shell_actor_firstname(canon)

def _goc_greeting_imperative_visible_pair(
    *,
    raw: str,
    player_shell_name: str,
    lang: str,
) -> tuple[str, str] | None:
    """Return (verbatim_player_typing, diegetic_attributed_line) for greet-X imperatives.

    Used when the player typed an imperative greeting to a named actor rather than
    direct in-scene speech. The story window emits two scene blocks.
    """
    tail = _goc_greeting_imperative_addressee_fragment(raw, lang=lang)
    if not tail:
        return None
    addressee = _goc_addressee_shell_firstname(tail)
    if not addressee:
        return None
    return greeting_imperative_visible_pair(
        raw,
        addressee=addressee,
        player_shell_name=player_shell_name,
        lang=lang,
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        content_modules_root=_goc_content_modules_root(),
    )

def _goc_player_attributed_visible_text(
    *,
    raw_input: str,
    human_actor_id: str,
    session_output_language: str,
    interpreted_input: dict[str, Any] | None,
) -> tuple[str, str]:
    """Return (speaker_label, full_visible_line) for a committed human player line."""
    raw = str(raw_input or "").strip()
    lang = str(session_output_language or DEFAULT_SESSION_LANGUAGE).strip().lower()[:2] or DEFAULT_SESSION_LANGUAGE
    name = _goc_shell_actor_firstname(human_actor_id)
    interp = interpreted_input if isinstance(interpreted_input, dict) else {}
    # Prefer fine-grained player_input_kind (set by classification rules) over coarse input_kind.
    pik_fine = str(interp.get("player_input_kind") or "").strip().lower()
    ik = pik_fine or str(interp.get("input_kind") or interp.get("kind") or "speech").strip().lower()
    pk = str(interp.get("projection_key") or "").strip() or None
    pc = interp.get("projection_captures") if isinstance(interp.get("projection_captures"), dict) else {}
    line = build_player_attributed_visible_line(
        name=name,
        raw=raw,
        input_kind=ik,
        lang=lang,
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        content_modules_root=_goc_content_modules_root(),
        projection_key=pk,
        projection_captures=pc,
    )
    return name, line

def _infer_generation_mode(path_summary_seed: dict[str, Any]) -> str:
    adapter = str(path_summary_seed.get("adapter") or "").strip().lower()
    final_adapter = str(path_summary_seed.get("final_adapter") or "").strip().lower()
    invocation_mode = str(path_summary_seed.get("adapter_invocation_mode") or "").strip().lower()
    fallback_mode = str(path_summary_seed.get("final_adapter_invocation_mode") or "").strip().lower()

    if adapter == "mock" or final_adapter == "mock":
        return "mock_only"
    if "ldss_fallback" in adapter or "ldss_fallback" in final_adapter:
        return "ldss_fallback"
    if "fixture" in invocation_mode or "fixture" in fallback_mode:
        return "deterministic_fixture"
    return "live_openai"

def _compose_resolved_target_status(
    player_action_frame: dict[str, Any],
    affordance_status: str | None,
) -> str | None:
    """Single operator-facing token for target + affordance (P0 evidence lane)."""
    rid = str(player_action_frame.get("resolved_target_id") or "").strip()
    aff = str(affordance_status or "").strip().lower()
    if rid:
        return f"{rid}:{aff}" if aff else rid
    if aff:
        return aff
    return "unresolved" if player_action_frame else None

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
