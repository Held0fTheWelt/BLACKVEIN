"""Response surface, voice, and carryover shell readout phrases."""

from __future__ import annotations

from .common import *
from .environment_readout import *
from .social_pressure_readout import *

def _response_exchange_type_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str) -> str:
    values = open_pressures + consequences
    asym = str(social_state.get("responder_asymmetry_code") or "")
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "failed repair"
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "containment" if selected_scene_function == "repair_or_stabilize" else "exposure"
    if _contains_any(values, "book", "art"):
        return "accusation" if asym == "alliance_reposition_active" else "status judgment"
    if _contains_any(values, "flower", "tulip"):
        return "brittle repair" if selected_scene_function == "repair_or_stabilize" else "accusation"
    if _contains_any(values, "phone"):
        return "evasive pressure" if selected_scene_function == "withhold_or_evade" else "exposure"
    if _contains_any(values, "rum", "drink", "glass", "hosting", "table", "coffee table"):
        return "brittle repair" if selected_scene_function == "repair_or_stabilize" else ("evasive pressure" if selected_scene_function == "withhold_or_evade" else "containment")
    if selected_scene_function == "redirect_blame":
        return "blame transfer"
    if selected_scene_function == "repair_or_stabilize":
        return "brittle repair"
    if selected_scene_function == "withhold_or_evade":
        return "evasive pressure"
    if asym == "alliance_reposition_active":
        return "cross-couple accusation"
    return "direct answer"


def _response_surface_phrase_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str]) -> str:
    values = open_pressures + consequences
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "over the doorway"
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "around the bathroom edge"
    if _contains_any(values, "book", "art"):
        return "over the books"
    if _contains_any(values, "flower", "tulip"):
        return "over the flowers"
    if _contains_any(values, "phone"):
        return "around the phone on the hosting surface"
    if _contains_any(values, "rum", "drink", "glass", "hosting", "table", "coffee table"):
        return "over the hosting surface"
    return "in the room"


def _response_surface_heat_phrase_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], responder_actor: str | None) -> str:
    values = open_pressures + consequences
    asym = str(social_state.get("responder_asymmetry_code") or "")
    side = _responder_social_side(responder_actor)
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        if asym == "blame_on_host_spouse_axis":
            return "host-side spouse embarrassment at the doorway"
        if asym == "alliance_reposition_active":
            return "cross-couple departure strain at the doorway"
        if side == "guest side":
            return "guest-side departure strain at the doorway"
        if side == "host side":
            return "host-side departure strain at the doorway"
        return "departure strain at the doorway"
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        if asym in {"blame_on_host_spouse_axis", "blame_under_repair_tension"}:
            return "spouse-axis embarrassment at the bathroom edge"
        if asym == "alliance_reposition_active":
            return "cross-couple exposure at the bathroom edge"
        if side == "guest side":
            return "guest-side exposure at the bathroom edge"
        if side == "host side":
            return "host-side exposure at the bathroom edge"
        return "exposure at the bathroom edge"
    if _contains_any(values, "book", "art"):
        if asym == "alliance_reposition_active":
            return "cross-couple strain on the books"
        if side == "guest side":
            return "guest-side status judgment on the books"
        if side == "host side":
            return "host-side status judgment on the books"
        return "taste-and-status strain on the books"
    if _contains_any(values, "flower", "tulip"):
        if asym == "alliance_reposition_active":
            return "cross-couple manners strain on the flowers"
        if side == "guest side":
            return "guest-side hospitality strain on the flowers"
        if side == "host side":
            return "host-side manners strain on the flowers"
        return "hospitality strain on the flowers"
    if _contains_any(values, "phone"):
        if asym == "alliance_reposition_active":
            return "cross-couple humiliation on the phone"
        if side == "guest side":
            return "guest-side humiliation on the phone"
        if side == "host side":
            return "host-side humiliation on the phone"
        return "humiliation on the phone"
    if _contains_any(values, "rum", "drink", "glass", "hosting", "table", "coffee table"):
        if asym == "alliance_reposition_active":
            return "cross-couple hospitality strain over the hosting surface"
        if side == "guest side":
            return "guest-side overfamiliarity over the hosting surface"
        if side == "host side":
            return "host-side hospitality strain over the hosting surface"
        return "hospitality strain over the hosting surface"
    return ""


def _response_voice_phrase_now(*, social_state: dict[str, Any], responder_actor: str | None) -> str:
    side = _responder_social_side(responder_actor)
    asym = str(social_state.get("responder_asymmetry_code") or "")
    if asym == "blame_on_host_spouse_axis":
        return f"from the {side} through the spouse axis"
    if asym == "alliance_reposition_active":
        return f"from the {side} across the couples"
    return f"from the {side}"


def _response_performance_signature_now(*, responder_actor: str | None, selected_scene_function: str, current_scene_id: str, open_pressures: list[str], consequences: list[str]) -> str:
    values = open_pressures + consequences
    if _actor_has(responder_actor, "host") and _actor_has_any(responder_actor, "moral", "ideal"):
        if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
            return "a principle-first rebuke that uses civility as correction"
        if _contains_any(values, "book", "art"):
            return "a civility-laden indictment that turns taste into judgment"
        if selected_scene_function == "repair_or_stabilize":
            return "a strained appeal to principle that keeps the room answerable"
        return "a wounded moral indictment that refuses to let the hurt sound private"
    if _actor_has(responder_actor, "host") and _actor_has_any(responder_actor, "practical", "conflict", "spouse"):
        if selected_scene_function == "withhold_or_evade":
            return "a practical retreat that tries to slide pressure sideways"
        if _contains_any(values, "flower", "tulip"):
            return "a smoothing deflection that offers manners instead of alignment"
        if _contains_any(values, "rum", "drink", "glass", "hosting", "table", "coffee table"):
            return "a smoothing deflection that offers hospitality instead of alignment"
        if selected_scene_function == "repair_or_stabilize":
            return "a smoothing deflection that buys calm by giving ground"
        return "a pragmatic sidestep that keeps loyalty blurred"
    if _actor_has(responder_actor, "guest") and _actor_has_any(responder_actor, "injured", "mother", "pressure holder", "observer"):
        if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
            return "a contemptuous dismantling that makes concern sound naive"
        if selected_scene_function == "repair_or_stabilize":
            return "a sharpened challenge that turns repair into fresh contradiction"
        if _contains_any(values, "book", "art"):
            return "a cutting contradiction that treats principle as performance"
        return "a contemptuous dismantling that strips courtesy down to appetite"
    if _actor_has(responder_actor, "guest") and _actor_has_any(responder_actor, "lawyer", "pragmatist", "procedure"):
        if selected_scene_function == "withhold_or_evade" or _contains_any(values, "phone"):
            return "a tired evasive hedge dressed up as mediation"
        if selected_scene_function == "repair_or_stabilize":
            return "a thinning conciliatory appeal that cannot keep control"
        return "a weary mediation attempt that already sounds half-withdrawn"
    return "a socially loaded answer"


def _response_mask_slip_now(*, responder_actor: str | None, selected_scene_function: str, current_scene_id: str, open_pressures: list[str], consequences: list[str]) -> str:
    values = open_pressures + consequences
    if _actor_has(responder_actor, "host") and _actor_has_any(responder_actor, "moral", "ideal"):
        if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
            return "civility hardening into correction"
        if _contains_any(values, "book", "art"):
            return "principle hardening into judgment"
        return "principle covering visible hurt"
    if _actor_has(responder_actor, "host") and _actor_has_any(responder_actor, "practical", "conflict", "spouse"):
        if _contains_any(values, "flower", "tulip", "rum", "drink", "glass", "hosting", "table", "coffee table") or selected_scene_function == "repair_or_stabilize":
            return "smoothing starting to read as capitulation"
        if selected_scene_function == "withhold_or_evade":
            return "practical calm slipping into retreat"
        return "conciliation keeping loyalty blurred"
    if _actor_has(responder_actor, "guest") and _actor_has_any(responder_actor, "injured", "mother", "pressure holder", "observer"):
        if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
            return "intellectual distance hardening into contempt"
        if _contains_any(values, "book", "art"):
            return "wit exposing morality as pose"
        return "provocation stripping courtesy bare"
    if _actor_has(responder_actor, "guest") and _actor_has_any(responder_actor, "lawyer", "pragmatist", "procedure"):
        if selected_scene_function == "withhold_or_evade" or _contains_any(values, "phone"):
            return "mediation thinning into evasion"
        if selected_scene_function == "repair_or_stabilize":
            return "conciliation giving way to fatigue"
        return "moderation already sounding half-withdrawn"
    return "social pressure breaking through the surface"


def _response_recentering_pull_now(*, responder_actor: str | None, selected_scene_function: str, current_scene_id: str, open_pressures: list[str], consequences: list[str]) -> str:
    values = open_pressures + consequences
    if _actor_has(responder_actor, "host") and _actor_has_any(responder_actor, "moral", "ideal"):
        if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
            return "pull the moment back under principle instead of letting the exit close it"
        return "pull the room back toward answerability instead of comfort"
    if _actor_has(responder_actor, "host") and _actor_has_any(responder_actor, "practical", "conflict", "spouse"):
        if _contains_any(values, "flower", "tulip", "rum", "drink", "glass", "hosting", "table", "coffee table"):
            return "pull the room back toward manners instead of open alignment"
        return "pull the room toward accommodation instead of a clean side"
    if _actor_has(responder_actor, "guest") and _actor_has_any(responder_actor, "injured", "mother", "pressure holder", "observer"):
        if _contains_any(values, "book", "art"):
            return "pull the room back to exposed contradiction instead of letting manners cover it"
        return "pull the room toward exposure instead of polite cover"
    if _actor_has(responder_actor, "guest") and _actor_has_any(responder_actor, "lawyer", "pragmatist", "procedure"):
        if selected_scene_function == "withhold_or_evade" or _contains_any(values, "phone"):
            return "pull the room toward manageability without ever resolving it"
        return "pull the room toward temporary calm without mastering it"
    return "pull the room into a live answer rather than neutrality"


def _response_carryover_tail_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], thread_continuity: dict[str, Any]) -> str:
    values = open_pressures + consequences
    prior = social_state.get("prior_continuity_classes")
    prior_classes = [str(x) for x in prior] if isinstance(prior, list) else []
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "the earlier failed exit still sitting at the doorway"
    if _contains_any(values, "book", "art"):
        return "the earlier taste-and-status wound still sitting on the books"
    if _contains_any(values, "flower", "tulip"):
        return "the earlier hospitality-and-manners wound still sitting on the flowers"
    if _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "the earlier exposure line still sitting at the bathroom edge"
    if _contains_any(values, "phone"):
        return "the earlier humiliation line still sitting on the phone"
    if _contains_any(values, "rum", "drink", "glass", "hosting", "table", "coffee table"):
        return "the earlier hospitality-and-hosting line still sitting over the hosting surface"
    if _contains_any(prior_classes, "blame_pressure", "repair_attempt", "alliance_shift") or str(thread_continuity.get("thread_pressure_level") or "") in {"moderate", "high"}:
        return "an earlier social wound still sitting in the room"
    return ""


def _response_carryover_exchange_phrase_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], thread_continuity: dict[str, Any]) -> str:
    tail = _response_carryover_tail_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        thread_continuity=thread_continuity,
    )
    if not tail:
        return ""
    return f"with {tail}"


def _response_surface_token_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str]) -> str:
    values = open_pressures + consequences
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "doorway"
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "bathroom edge"
    if _contains_any(values, "book", "art"):
        return "books"
    if _contains_any(values, "flower", "tulip"):
        return "flowers"
    if _contains_any(values, "phone"):
        return "phone"
    if _contains_any(values, "rum", "drink", "glass", "hosting", "table", "coffee table"):
        return "hosting surface"
    return "room"



def _response_cause_compressed_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str) -> str:
    values = open_pressures + consequences
    asym = str(social_state.get("responder_asymmetry_code") or "")
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "because it put the doorway under pressure again"
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "because it put the bathroom edge under pressure again"
    if _contains_any(values, "book", "art"):
        return "because it put the books under pressure again"
    if _contains_any(values, "flower", "tulip"):
        return "because it put the flowers under pressure again"
    if _contains_any(values, "phone"):
        return "because it put the phone under pressure again"
    if _contains_any(values, "rum", "drink", "glass", "hosting", "table", "coffee table"):
        return "because it put the hosting surface under pressure again"
    if selected_scene_function == "redirect_blame":
        return "because the room is moving social cost instead of containing it"
    if selected_scene_function == "withhold_or_evade":
        return "because the room is keeping pressure active through evasion"
    if selected_scene_function == "repair_or_stabilize":
        return "because the room is forcing the act into brittle repair"
    if asym == "alliance_reposition_active":
        return "because the room is answering through a temporary coalition shift"
    return "because the act could not stay socially neutral"


def _response_exchange_label_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str) -> str:
    return _response_exchange_type_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
__all__ = (
    '_response_exchange_label_now',
    '_response_cause_compressed_now',
    '_response_exchange_type_now',
    '_response_surface_phrase_now',
    '_response_surface_heat_phrase_now',
    '_response_voice_phrase_now',
    '_response_performance_signature_now',
    '_response_mask_slip_now',
    '_response_recentering_pull_now',
    '_response_carryover_tail_now',
    '_response_carryover_exchange_phrase_now',
    '_response_surface_token_now',
)
