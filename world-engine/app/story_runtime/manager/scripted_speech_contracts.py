"""Scripted speech contracts.

Normalizes scripted speech lines and actor contracts before they enter visible projection or session history.
"""
from __future__ import annotations

from ._deps import *

def _scripted_npc_speech_text(
    *,
    actor_ref: str,
    intent: str,
    required_facts: Any,
    quote_excerpt: str,
    language: str,
) -> str:
    lang = str(language or "").strip().lower()[:2] or "en"
    facts = _required_fact_map(required_facts)
    intent_l = str(intent or "").strip().lower()
    quote = _speech_token(quote_excerpt, language=lang)
    if "single_word_question" in intent_l and quote:
        return f"{quote.rstrip('?')}?"
    if "accept_word" in intent_l:
        chosen = _speech_token(facts.get("chosen_word_token") or quote or "carrying", language=lang)
        return f"{chosen}, ja." if lang == "de" else f"{chosen}, yes."
    if "echo_the_chosen" in intent_l:
        phrase = _speech_token(facts.get("echoed_phrase_token") or quote or "was carrying a stick", language=lang)
        return f"{phrase}." if lang == "en" else f"{phrase}."
    if "typing" in intent_l or "read_back_the_corrected" in intent_l:
        word = _speech_token(facts.get("confirmed_word_token") or quote or "carrying", language=lang)
        return f"{word}."
    if "offer_alternatives" in intent_l or "offer_compromise" in intent_l:
        proposals = facts.get("propose_alternatives")
        if not isinstance(proposals, list):
            proposals = ["with it", "was carrying", "was carrying a stick"]
        rendered = [_speech_token(item, language=lang) for item in proposals[:3]]
        consult_token = str(facts.get("turn_to_michel_token") or "").strip()
        consult_label = consult_token.split(",", 1)[0].strip()
        if lang == "de":
            armed = _speech_token("armed", language=lang)
            consult = f" {consult_label}, was könnten wir sagen?" if consult_label else " was könnten wir sagen?"
            return f"{armed} ...{consult} {' Oder '.join(rendered)}?"
        consult = f" {consult_label}, what could we say?" if consult_label else " what could we say?"
        return f"Armed ...{consult} {' Or '.join(rendered)}?"
    if "read_aloud_first_half" in intent_l:
        date = _speech_token(facts.get("date_token") or "January 11, 2:30 p.m.", language=lang)
        location = _speech_token(facts.get("location_token") or "Parc Mont Sourire", language=lang)
        fallback_aggressor = "der Angreifer" if lang == "de" else "the aggressor"
        fallback_victim = "das andere Kind" if lang == "de" else "the other child"
        aggressor_source = facts.get("aggressor_id")
        victim_source = facts.get("victim_id")
        aggressor = _speech_token(aggressor_source or fallback_aggressor, language=lang)
        victim = _speech_token(victim_source or fallback_victim, language=lang)
        if aggressor_source:
            aggressor = aggressor.title()
        if victim_source:
            victim = victim.title()
        carried_word = _speech_token(facts.get("aggressor_carried_word") or "armed", language=lang)
        action = _speech_token(facts.get("struck_action") or "struck him in the face", language=lang)
        if lang == "de":
            action_de = "schlug ihm ins Gesicht" if action == "struck him in the face" else action
            return f"Am {date} war {aggressor} im {location} mit einem Stock {carried_word} und {action_de}: {victim}."
        return f"On {date}, in {location}, {aggressor} was {carried_word} with a stick and {action}: {victim}."
    if "read_aloud_second_half" in intent_l or "injury_clinical" in intent_l:
        injuries = [
            _speech_token(facts.get("injury_token_1") or "swelling_and_bruise_upper_lip", language=lang),
            _speech_token(facts.get("injury_token_2") or "two_broken_incisors", language=lang),
            _speech_token(facts.get("injury_token_3") or "nerve_injury_right_incisor", language=lang),
        ]
        if lang == "de":
            return f"{injuries[0]}, {injuries[1]} und {injuries[2]}."
        return f"{injuries[0]}, {injuries[1]}, and {injuries[2]}."
    if "name_the_format" in intent_l:
        if lang == "de":
            return "Ihre Erklärung wird getrennt sein; das hier ist unsere."
        return "Your statement will be separate; this is ours."
    if quote:
        return quote
    return str(intent or "").replace("_", " ").strip().capitalize() + "."

def _scripted_narration_frame(
    *,
    actor_ref: str,
    intent: str,
    perception: Any,
    language: str,
) -> str:
    rows = perception if isinstance(perception, list) else [perception]
    first_perception = next((str(row).strip() for row in rows if str(row or "").strip()), "")
    actor_name = _actor_first_name(actor_ref)
    lang = str(language or "").strip().lower()[:2]
    intent_l = str(intent or "").strip().lower()
    if lang == "de":
        if "read_aloud" in intent_l:
            return f"{actor_name} las mit fester Stimme vom Bildschirm:"
        if "single_word_question" in intent_l:
            return f"{actor_name} hob knapp den Blick:"
        if "offer" in intent_l:
            return f"{actor_name} hielt inne und suchte den Blickkontakt:"
        if "accept" in intent_l:
            return f"{actor_name} gab knapp zurück:"
        if "echo" in intent_l:
            return f"{actor_name} nickte freundlich:"
        if "typing" in intent_l or "read_back" in intent_l:
            return f"{actor_name} tippte die Korrektur ein und murmelte:"
        if "name_the_format" in intent_l:
            return f"{actor_name} wandte sich kurz zu den anderen:"
        return f"{actor_name} sagte:"
    if first_perception:
        return first_perception.rstrip(".") + ":"
    return f"{actor_name} said:"

def _embedded_speech_span(
    *,
    actor_ref: str,
    speech_text: str,
    intent: str,
    block: dict[str, Any],
) -> dict[str, Any]:
    actor_id = _resolve_goc_runtime_actor_id(actor_ref)
    return {
        "actor_id": actor_id,
        "speaker_label": _actor_first_name(actor_ref),
        "speech_text": speech_text,
        "speech_act": str(intent or "").strip(),
        "canonical_step_id": str(block.get("canonical_step_id") or "").strip(),
        "canonical_mandatory_beat_id": str(block.get("canonical_mandatory_beat_id") or "").strip(),
        "source": "npc_speak_directive",
    }

SUPPORTED_LIVE_STORY_MODULE_IDS = (GOD_OF_CARNAGE_MODULE_ID,)

class StorySessionContractError(ValueError):
    """Raised when a direct story-session create violates the governed runtime contract."""

NON_RECOVERABLE_TURN_EXCEPTION_TYPES = (
    LiveStoryGovernanceError,
    StorySessionContractError,
    TypeError,
    AttributeError,
    KeyError,
    ImportError,
    OSError,
)

def _is_recoverable_graph_execution_exception(exc: Exception) -> bool:
    return isinstance(exc, RuntimeError) and not isinstance(exc, NON_RECOVERABLE_TURN_EXCEPTION_TYPES)

def _require_non_empty_string(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise StorySessionContractError(f"{field_name} is required for governed live story sessions.")
    return text

def _resolve_goc_runtime_actor_id(actor_ref: str) -> str:
    ref = str(actor_ref or "").strip()
    if not ref:
        return ""
    identity = goc_actor_identity(ref)
    actor_id = str(identity.get("actor_id") or "").strip()
    if actor_id:
        return actor_id
    return str(canonicalize_goc_actor_id(ref) or ref).strip()

def _validate_runtime_projection_contract(module_id: str, runtime_projection: dict[str, Any]) -> None:
    if module_id != GOD_OF_CARNAGE_MODULE_ID:
        return

    if not isinstance(runtime_projection, dict):
        raise StorySessionContractError("runtime_projection must be a JSON object.")

    projection_module_id = str(runtime_projection.get("module_id") or "").strip()
    if projection_module_id and projection_module_id != module_id:
        raise StorySessionContractError(
            "runtime_projection.module_id must match the requested module_id for governed live sessions."
        )

    human_actor_id = _require_non_empty_string(runtime_projection.get("human_actor_id"), "human_actor_id")
    selected_player_role = _require_non_empty_string(
        runtime_projection.get("selected_player_role"),
        "selected_player_role",
    )
    resolved_selected_actor_id = _resolve_goc_runtime_actor_id(selected_player_role)
    resolved_human_actor_id = _resolve_goc_runtime_actor_id(human_actor_id)
    if resolved_selected_actor_id != resolved_human_actor_id:
        raise StorySessionContractError(
            "selected_player_role must resolve to human_actor_id for the canonical single-human live runtime path."
        )

    raw_npc_actor_ids = runtime_projection.get("npc_actor_ids")
    if not isinstance(raw_npc_actor_ids, list) or not raw_npc_actor_ids:
        raise StorySessionContractError("npc_actor_ids must contain the AI-controlled cast for governed live sessions.")
    npc_actor_ids = [str(item).strip() for item in raw_npc_actor_ids if str(item).strip()]
    if not npc_actor_ids:
        raise StorySessionContractError("npc_actor_ids must contain non-empty actor ids.")
    if resolved_human_actor_id in {_resolve_goc_runtime_actor_id(actor_id) for actor_id in npc_actor_ids}:
        raise StorySessionContractError("human_actor_id cannot also appear in npc_actor_ids.")

    actor_lanes = runtime_projection.get("actor_lanes")
    if not isinstance(actor_lanes, dict) or not actor_lanes:
        raise StorySessionContractError("actor_lanes is required for governed live sessions.")

    human_lane = str(actor_lanes.get(human_actor_id) or "").strip().lower()
    if human_lane != "human":
        raise StorySessionContractError("actor_lanes must mark human_actor_id with lane='human'.")

    missing_npcs = [actor_id for actor_id in npc_actor_ids if str(actor_lanes.get(actor_id) or "").strip().lower() != "npc"]
    if missing_npcs:
        raise StorySessionContractError(
            f"actor_lanes must mark every npc_actor_id with lane='npc' (missing: {', '.join(missing_npcs)})."
        )

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
