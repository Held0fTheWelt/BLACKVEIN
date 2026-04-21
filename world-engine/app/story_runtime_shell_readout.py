from __future__ import annotations

from typing import Any
import re


def _first_responder_actor(last_diagnostic: dict[str, Any] | None) -> str | None:
    if not isinstance(last_diagnostic, dict):
        return None
    responders = last_diagnostic.get("selected_responder_set")
    if isinstance(responders, list) and responders and isinstance(responders[0], dict):
        actor = responders[0].get("actor_id")
        if isinstance(actor, str) and actor.strip():
            return actor.strip()
    return None

def _selected_scene_function(last_diagnostic: dict[str, Any] | None) -> str:
    if isinstance(last_diagnostic, dict):
        value = last_diagnostic.get("selected_scene_function")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""



def _social_state_record(last_diagnostic: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(last_diagnostic, dict):
        rec = last_diagnostic.get("social_state_record")
        if isinstance(rec, dict):
            return rec
    return {}


def _responder_social_side(responder_actor: str | None) -> str:
    actor = (responder_actor or "").strip().lower()
    if actor in {"veronique", "michel"}:
        return "host side"
    if actor in {"annette", "alain"}:
        return "guest side"
    return "room side"


def _response_pressure_line_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any]) -> str:
    values = open_pressures + consequences
    asym = str(social_state.get("responder_asymmetry_code") or "")
    if asym == "blame_on_host_spouse_axis":
        return "spouse-axis embarrassment"
    if asym == "alliance_reposition_active":
        return "cross-couple strain"
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "failed-departure pressure"
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "exposure-and-recovery pressure"
    if _contains_any(values, "book", "art"):
        return "taste-and-status pressure"
    if _contains_any(values, "flower", "tulip"):
        return "brittle hospitality pressure"
    if _contains_any(values, "rum", "drink", "glass", "hosting", "table", "coffee table"):
        return "hospitality-and-hosting pressure"
    if _contains_any(values, "phone"):
        return "humiliation-and-priority pressure"
    return "live room pressure"


def _response_side_pair_frame_now(*, social_state: dict[str, Any], responder_actor: str | None, selected_scene_function: str) -> str:
    asym = str(social_state.get("responder_asymmetry_code") or "")
    side = _responder_social_side(responder_actor)
    if asym == "blame_on_host_spouse_axis":
        return f"for the {side}, with spouse-axis embarrassment carrying the reply"
    if asym == "alliance_reposition_active":
        return f"for the {side}, with cross-couple strain carrying the reply"
    if selected_scene_function == "repair_or_stabilize":
        return f"for the {side}, with brittle repair pressure carrying the reply"
    if selected_scene_function == "redirect_blame":
        return f"for the {side}, with blame transfer carrying the reply"
    if selected_scene_function == "withhold_or_evade":
        return f"for the {side}, with evasive pressure carrying the reply"
    return f"for the {side}"


def _open_pressures(committed_state: dict[str, Any]) -> list[str]:
    raw = committed_state.get("last_open_pressures")
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    return []


def _last_consequences(committed_state: dict[str, Any]) -> list[str]:
    raw = committed_state.get("last_committed_consequences")
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    return []


def _thread_continuity(committed_state: dict[str, Any]) -> dict[str, Any]:
    tc = committed_state.get("narrative_thread_continuity")
    return tc if isinstance(tc, dict) else {}


def _contains_any(values: list[str], *needles: str) -> bool:
    lowered = " | ".join(values).lower().replace("_", " ").replace("-", " ")
    for needle in needles:
        normalized = needle.lower().replace("_", " ").replace("-", " ").strip()
        if not normalized:
            continue
        if re.search(rf"\b{re.escape(normalized)}\b", lowered):
            return True
    return False


def _has_hosting_surface(values: list[str]) -> bool:
    return _contains_any(values, "rum", "drink", "glass", "hosting", "table", "coffee table", "coffee_table")

def _room_pressure_now(*, current_scene_id: str, open_pressures: list[str], social_state: dict[str, Any]) -> str:
    pressure_state = str(social_state.get("scene_pressure_state") or "")
    if current_scene_id == "hallway_threshold" or _contains_any(open_pressures, "exit", "departure"):
        return "The room feels exit-loaded; the doorway still reads as a social trap."
    if current_scene_id == "bathroom_recovery" or _contains_any(open_pressures, "cleanup", "contamination", "vomit", "bathroom"):
        return "The room feels contaminated and exposed; recovery has become part of the scene."
    if pressure_state == "high_blame" or _contains_any(open_pressures, "blame", "judgment"):
        return "The room feels judgment-heavy; blame is carrying more weight than repair."
    if pressure_state == "moderate_tension" or social_state.get("social_risk_band") == "high":
        return "The room feels tighter than it looks; small acts are reading socially."
    return "The room remains socially live even when no one names it outright."


def _salient_object_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str]) -> str:
    values = open_pressures + consequences
    if _contains_any(values, "phone"):
        return "The phone is still carrying humiliation and public-priority pressure."
    if _contains_any(values, "book", "art"):
        return "The books are carrying taste, status, and household judgment."
    if _contains_any(values, "flower", "tulip"):
        return "The flowers are reading as a hospitality surface with boundary pressure attached."
    if _has_hosting_surface(values):
        return "The hosting surface is carrying brittle hospitality, escalation, and domestic performance pressure."
    if _contains_any(values, "cleanup", "basin", "bathroom", "vomit") or current_scene_id == "bathroom_recovery":
        return "Cleanup objects still carry exposure, relief, and embarrassment."
    if _contains_any(values, "exit", "departure") or current_scene_id == "hallway_threshold":
        return "The threshold itself is acting like a pressure object."
    return "Visible household surfaces are still carrying social meaning."

def _zone_sensitivity_now(*, current_scene_id: str, open_pressures: list[str], social_state: dict[str, Any]) -> str:
    pressure_state = str(social_state.get("scene_pressure_state") or "")
    if current_scene_id == "hallway_threshold" or _contains_any(open_pressures, "exit", "departure"):
        return "The doorway zone is socially charged; hovering there will read as pressure, not neutral movement."
    if current_scene_id == "bathroom_recovery" or _contains_any(open_pressures, "cleanup", "contamination", "vomit", "bathroom"):
        return "The bathroom edge is socially charged; checking or crossing it will read as concern, exposure, or intrusion."
    if _contains_any(open_pressures, "book", "art", "flower", "tulip", "phone"):
        return "The object-rich center of the room is socially hot; touching things there will not read as incidental."
    if pressure_state in {"high_blame", "moderate_tension"} or str(social_state.get("social_risk_band") or "") == "high":
        return "Distance, threshold use, and small repositioning moves are socially live in the room right now."
    return "The room is not neutral; where you stand and what you go near will still read socially."


def _object_sensitivity_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str]) -> str:
    values = open_pressures + consequences
    if _contains_any(values, "phone"):
        return "The phone is a humiliation surface; handling it will read as priority, contempt, or exposure."
    if _contains_any(values, "book", "art"):
        return "The books are a taste-and-status surface; handling them will read as judgment, manners, or intrusion."
    if _contains_any(values, "flower", "tulip"):
        return "The flowers are a hospitality surface; touching them will read as care, overfamiliarity, or bad manners."
    if _has_hosting_surface(values):
        return "The hosting surface is a hospitality-and-escalation surface; handling drinks there will read as care, pressure, or overfamiliarity."
    if _contains_any(values, "cleanup", "basin", "bathroom", "vomit") or current_scene_id == "bathroom_recovery":
        return "Cleanup objects are exposure surfaces; helping there will read as care, pity, or embarrassment management."
    if _contains_any(values, "exit", "departure") or current_scene_id == "hallway_threshold":
        return "The threshold itself is carrying object-like pressure; hovering there will read as failed departure, not idle movement."
    return "Household surfaces are socially loaded enough that touching them will likely mean something."

def _situational_affordance_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any]) -> str:
    values = open_pressures + consequences
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "Threshold movement, staying back, or edging toward the door are all socially legible right now."
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "Checking in, helping, tidying, or hanging back all carry visible social meaning right now."
    if _contains_any(values, "book", "art", "flower", "tulip", "phone"):
        return "Approaching, handling, helping, or deliberately not touching the loaded household surfaces will all read socially."
    if _has_hosting_surface(values):
        return "Pouring, helping with, hovering near, or pointedly ignoring the hosting surface will all read socially."
    if str(social_state.get("social_risk_band") or "") == "high":
        return "Small domestic acts, distance shifts, and object handling are all liable to be socially read right now."
    return "The room is live enough that movement, distance, silence, and handling household things will not read as neutral."

def _continued_wound_now(*, open_pressures: list[str], social_state: dict[str, Any], thread_continuity: dict[str, Any]) -> str:
    prior = social_state.get("prior_continuity_classes")
    prior_classes = [str(x) for x in prior] if isinstance(prior, list) else []
    if "blame_pressure" in prior_classes and "repair_attempt" in prior_classes:
        return "An earlier slight is still live beneath a thin attempt to smooth it over."
    if _contains_any(open_pressures, "exit", "departure"):
        return "Departure shame is still active; the room has not released the wish to leave."
    if _contains_any(open_pressures, "ambiguity"):
        return "A disputed reading is still active; the room is carrying uncertainty as pressure."
    if _contains_any(prior_classes, "alliance_shift") or str(thread_continuity.get("thread_pressure_level") or "") == "high":
        return "An earlier social repositioning is still hanging in the room."
    return "An earlier wound is still socially active even if no one is naming it directly."


def _role_pressure_now(*, social_state: dict[str, Any], responder_actor: str | None) -> str:
    asym = str(social_state.get("responder_asymmetry_code") or "")
    actor = responder_actor.title() if responder_actor else "Someone"
    if asym == "blame_on_host_spouse_axis":
        return f"{actor} is carrying host-side pressure; the room is reading this as a boundary problem, not a neutral act."
    if asym == "blame_under_repair_tension":
        return f"{actor} is carrying pressure while the room keeps trying to smooth over something it has not forgiven."
    if asym == "alliance_reposition_active":
        return "The room is leaning toward a tactical alliance shift rather than stable couple lines."
    return f"{actor} is reading the act socially; the room is not treating it as merely practical." if responder_actor else "The room is reading the act socially rather than neutrally."


def _dominant_social_reading_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any]) -> str:
    values = open_pressures + consequences
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "It is landing as failed repair and renewed departure pressure rather than a clean practical move."
    if _contains_any(values, "book", "art"):
        return "It is landing as judgment around taste and household status rather than neutral handling."
    if _contains_any(values, "flower", "tulip"):
        return "It is landing as overfamiliarity or bad manners around hospitality rather than simple care."
    if _contains_any(values, "cleanup", "bathroom", "vomit"):
        return "It is landing as care mixed with exposure and pity rather than uncomplicated help."
    if _contains_any(values, "phone"):
        return "It is landing as humiliation and priority pressure rather than ordinary interruption."
    if str(social_state.get("scene_pressure_state") or "") == "high_blame":
        return "It is landing as judgment more than care."
    return "It is landing socially rather than neutrally."


def _social_axis_now(*, open_pressures: list[str], social_state: dict[str, Any], responder_actor: str | None) -> str:
    asym = str(social_state.get("responder_asymmetry_code") or "")
    actor = responder_actor.title() if responder_actor else "Someone"
    if asym == "blame_on_host_spouse_axis":
        return f"The host side and spouse axis are carrying the weight; {actor} is taking the room's boundary reading."
    if asym == "blame_under_repair_tension":
        return "The spouse axis is still carrying embarrassment while the room pretends to repair itself."
    if asym == "alliance_reposition_active" or _contains_any(open_pressures, "alliance"):
        return "Cross-couple strain is carrying more of the pressure than ordinary blame."
    if responder_actor and responder_actor.lower() in {"annette", "alain"}:
        return f"The guest side is carrying more of the visible reading through {actor}."
    if responder_actor and responder_actor.lower() in {"veronique", "michel"}:
        return f"The host side is carrying more of the visible reading through {actor}."
    return "The room is sorting pressure through social sides rather than neutrally."


def _host_guest_pressure_now(*, open_pressures: list[str], social_state: dict[str, Any], responder_actor: str | None) -> str:
    asym = str(social_state.get("responder_asymmetry_code") or "")
    if asym == "blame_on_host_spouse_axis":
        return "Host-side pressure is carrying more of the room; the guests have more room to watch than absorb."
    if asym == "alliance_reposition_active" or _contains_any(open_pressures, "alliance"):
        return "Pressure is bouncing across host and guest lines rather than staying parked on one side."
    if responder_actor and responder_actor.lower() in {"annette", "alain"}:
        return "Guest-side pressure is more visible than host-side calm right now."
    if responder_actor and responder_actor.lower() in {"veronique", "michel"}:
        return "Host-side pressure is more visible than guest-side ease right now."
    return "Pressure is moving across host and guest lines rather than staying evenly shared."


def _spouse_axis_now(*, current_scene_id: str, open_pressures: list[str], social_state: dict[str, Any]) -> str:
    asym = str(social_state.get("responder_asymmetry_code") or "")
    if asym in {"blame_on_host_spouse_axis", "blame_under_repair_tension"}:
        return "One partner is carrying social cost for the other's act; the spouse axis is not settled."
    if current_scene_id == "hallway_threshold" or _contains_any(open_pressures, "exit", "departure"):
        return "Departure pressure is living partly inside the couples, not only between them."
    if current_scene_id == "bathroom_recovery" or _contains_any(open_pressures, "cleanup", "bathroom", "vomit"):
        return "Exposure and cleanup pressure are making the spouse axis carry embarrassment."
    return "The spouse axis is quieter than the room, but it is still carrying some social cost."


def _cross_couple_now(*, open_pressures: list[str], social_state: dict[str, Any]) -> str:
    asym = str(social_state.get("responder_asymmetry_code") or "")
    if asym == "alliance_reposition_active" or _contains_any(open_pressures, "alliance"):
        return "Cross-couple strain is sharper than stable pair loyalty; the room is tilting into temporary coalitions."
    if _contains_any(open_pressures, "blame", "judgment"):
        return "Cross-couple strain is present, but it has not fully replaced the couple lines."
    return "Cross-couple strain is live, though it is not fully taking over the room."


def _pressure_redistribution_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str]) -> str:
    values = open_pressures + consequences
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "Pressure has shifted from practical movement into spouse embarrassment and departure shame."
    if _contains_any(values, "book", "art"):
        return "Pressure has shifted from object handling into taste judgment and household status strain."
    if _contains_any(values, "flower", "tulip"):
        return "Pressure has shifted from hospitality surface into manners and boundary strain."
    if _contains_any(values, "cleanup", "bathroom", "vomit"):
        return "Pressure has shifted from practical help into exposure, pity, and social management."
    if _contains_any(values, "phone"):
        return "Pressure has shifted from interruption into humiliation and public-priority strain."
    return "Pressure has moved socially rather than staying where the act first landed."


def _callback_role_frame_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], thread_continuity: dict[str, Any]) -> str:
    values = open_pressures + consequences
    prior = social_state.get("prior_continuity_classes")
    prior_classes = [str(x) for x in prior] if isinstance(prior, list) else []
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "The callback is reviving departure shame and failed repair rather than opening a new issue."
    if _contains_any(values, "book", "art"):
        return "The callback is reusing taste and status as judgment."
    if _contains_any(values, "flower", "tulip"):
        return "The callback is reusing hospitality strain as a manners complaint."
    if _contains_any(values, "cleanup", "bathroom", "vomit"):
        return "The callback is reusing exposure and pity rather than simple concern."
    if _contains_any(values, "phone"):
        return "The callback is reusing humiliation and public-priority pressure."
    if _has_hosting_surface(values):
        return "The callback is reusing the hosting surface as brittle hospitality and escalation pressure."
    if "blame_pressure" in prior_classes or str(thread_continuity.get("thread_pressure_level") or "") == "high":
        return "The callback is reusing an earlier slight as active pressure rather than letting it die out."
    return "An older pressure line is still framing the room's reaction."

def _object_social_reading_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str]) -> str:
    values = open_pressures + consequences
    if _contains_any(values, "phone"):
        return "Right now the phone reads as a humiliation surface more than a neutral prop."
    if _contains_any(values, "book", "art"):
        return "Right now the books read as a taste-and-status wound more than background decor."
    if _contains_any(values, "flower", "tulip"):
        return "Right now the flowers read as a hospitality surface where manners can curdle into judgment."
    if _has_hosting_surface(values):
        return "Right now the hosting surface reads as brittle hospitality and escalation pressure rather than ordinary hosting."
    if _contains_any(values, "cleanup", "basin", "bathroom", "vomit") or current_scene_id == "bathroom_recovery":
        return "Right now the cleanup surfaces read as exposure management rather than ordinary household help."
    if _contains_any(values, "exit", "departure") or current_scene_id == "hallway_threshold":
        return "Right now the threshold reads as a failed-departure surface more than a neutral edge."
    return "Right now the visible household surfaces read socially rather than neutrally."

def _callback_summary(*, open_pressures: list[str], social_state: dict[str, Any], thread_continuity: dict[str, Any]) -> str:
    prior = social_state.get("prior_continuity_classes")
    prior_classes = [str(x) for x in prior] if isinstance(prior, list) else []
    if _contains_any(prior_classes, "blame_pressure") or _contains_any(open_pressures, "departure", "ambiguity"):
        return "This is still behaving like a callback; the room is reusing an earlier wound rather than reacting from scratch."
    if str(thread_continuity.get("thread_count") or 0) and str(thread_continuity.get("thread_pressure_level") or "") in {"moderate", "high"}:
        return "An earlier pressure line is still active and being reused."
    return "A prior pressure line is still shaping the room."


def _active_pressure_summary(open_pressures: list[str]) -> str:
    if not open_pressures:
        return "No single pressure has cleared the room; the tension remains socially distributed."
    labels: list[str] = []
    for item in open_pressures:
        low = item.lower()
        if "departure" in low or "exit" in low:
            labels.append("departure pressure")
        elif "ambiguity" in low:
            labels.append("reading dispute")
        elif "blame" in low:
            labels.append("blame pressure")
        elif "repair" in low:
            labels.append("fragile repair")
        elif "alliance" in low:
            labels.append("alliance instability")
        else:
            labels.append(item.replace("_", " "))
    deduped: list[str] = []
    for label in labels:
        if label not in deduped:
            deduped.append(label)
    return "Still live: " + ", ".join(deduped[:3])


def _recent_act_social_meaning(*, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any]) -> str:
    values = open_pressures + consequences
    if _contains_any(values, "departure", "exit"):
        return "The last act tightened the social trap instead of creating a clean way out."
    if _contains_any(values, "book", "flower", "tulip", "phone"):
        return "The last act landed on a symbolic household surface rather than staying purely practical."
    if _has_hosting_surface(values):
        return "The last act landed on the hosting surface and turned domestic hospitality into social pressure."
    if _contains_any(values, "cleanup", "bathroom", "vomit"):
        return "The last act read as exposure and management at the same time."
    if str(social_state.get("social_risk_band") or "") == "high":
        return "The last act landed as a socially loaded move rather than a neutral one."
    return "The room is treating the last act as meaningful, not incidental."

def _reaction_delta_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any]) -> str:
    values = open_pressures + consequences
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "Your last move tightened departure pressure; the room turned practical movement into failed repair."
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "Your last move made exposure more public; help and recoil both started reading socially."
    if _contains_any(values, "book", "art"):
        return "Your last move turned object handling into taste and status judgment."
    if _contains_any(values, "flower", "tulip"):
        return "Your last move turned hospitality into manners and boundary pressure."
    if _contains_any(values, "phone"):
        return "Your last move sharpened humiliation and public-priority pressure."
    if _has_hosting_surface(values):
        return "Your last move turned the hosting surface into visible hospitality and escalation pressure."
    if str(social_state.get("social_risk_band") or "") == "high":
        return "Your last move changed the room's social reading rather than staying merely practical."
    return "The room treated your last move as a social change, not a neutral one."

def _carryover_delta_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], thread_continuity: dict[str, Any]) -> str:
    values = open_pressures + consequences
    prior = social_state.get("prior_continuity_classes")
    prior_classes = [str(x) for x in prior] if isinstance(prior, list) else []
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "The earlier failed-exit wound was pulled back onto the doorway; departure shame is active again."
    if _contains_any(values, "book", "art"):
        return "The earlier taste-and-status wound was pulled back onto the books and turned active again."
    if _contains_any(values, "flower", "tulip"):
        return "The earlier manners wound was pulled back onto the flowers instead of fading out."
    if _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "The earlier exposure line was pulled back to the bathroom edge as pity and management pressure."
    if _contains_any(values, "phone"):
        return "The earlier humiliation line was pulled back onto the phone instead of staying in the background."
    if _has_hosting_surface(values):
        return "The earlier hospitality-and-hosting line was pulled back over the hosting surface instead of settling into decorum."
    if _contains_any(prior_classes, "blame_pressure", "alliance_shift") or str(thread_continuity.get("thread_pressure_level") or "") in {"moderate", "high"}:
        return "An older wound is doing fresh work in the room now, not just hanging around."
    return ""

def _pressure_shift_delta_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any]) -> str:
    values = open_pressures + consequences
    asym = str(social_state.get("responder_asymmetry_code") or "")
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "Pressure shifted onto the spouse axis and host-side embarrassment rather than staying with movement itself."
    if asym == "alliance_reposition_active" or _contains_any(values, "alliance"):
        return "Pressure shifted into cross-couple strain; the room is temporarily reading across the pairs."
    if _contains_any(values, "book", "art"):
        return "Pressure shifted from object handling into household judgment and status strain."
    if _contains_any(values, "flower", "tulip"):
        return "Pressure shifted from hospitality surface into boundary and manners strain."
    if _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "Pressure shifted from practical help into exposure, pity, and spouse-facing discomfort."
    if _contains_any(values, "phone"):
        return "Pressure shifted from interruption into humiliation and public-priority strain."
    if _has_hosting_surface(values):
        return "Pressure shifted from domestic hosting into hospitality strain, overfamiliarity, and escalation risk."
    return "Pressure moved socially after the last act instead of staying where it first landed."

def _hot_surface_delta_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str]) -> str:
    values = open_pressures + consequences
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "The doorway became newly hot because the last move made departure pressure live again."
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "The bathroom edge is hot because the last move exposed cleanup, care, and recoil at once."
    if _contains_any(values, "book", "art"):
        return "The books are hot because the last move turned them into a fresh taste-and-status wound."
    if _contains_any(values, "flower", "tulip"):
        return "The flowers are hot because the last move made hospitality and manners socially active again."
    if _contains_any(values, "phone"):
        return "The phone is hot because the last move brought humiliation and priority back to the front."
    if _has_hosting_surface(values):
        return "The hosting surface is hot because the last move turned drinks and domestic hosting into active social pressure."
    return "The last move made one part of the room newly live rather than leaving everything evenly charged."

def _social_weather_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any]) -> str:
    values = open_pressures + consequences
    pressure_state = str(social_state.get("scene_pressure_state") or "")
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "Exit pressure is dominating the room; even practical movement is reading as failed repair."
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "The room is carrying exposed cleanup pressure; help and recoil both read publicly."
    if _contains_any(values, "book", "art"):
        return "Judgment is dominating the room; taste and household status are doing more work than repair."
    if _contains_any(values, "flower", "tulip"):
        return "Hospitality pressure is dominating the room; manners and boundary strain are doing the reading."
    if _contains_any(values, "phone"):
        return "Humiliation pressure is dominating the room; priority and exposure are doing the reading."
    if _has_hosting_surface(values):
        return "Hospitality pressure is dominating the room; drinks and hosting surfaces are doing the reading."
    if pressure_state == "high_blame":
        return "Judgment is dominating the room more than care."
    return "The room is socially live enough that small acts are not staying neutral."

def _live_surface_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str]) -> str:
    values = open_pressures + consequences
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "The doorway is the hot surface right now; hovering there reads as departure pressure, not neutral movement."
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "The bathroom edge is the hot surface right now; help there reads as care, exposure, or pity management."
    if _contains_any(values, "book", "art"):
        return "The books are the hot surface right now; touching them reads as taste and status judgment."
    if _contains_any(values, "flower", "tulip"):
        return "The flowers are the hot surface right now; touching them reads as hospitality pressure or overfamiliarity."
    if _contains_any(values, "phone"):
        return "The phone is the hot surface right now; handling it reads as humiliation and priority pressure."
    if _has_hosting_surface(values):
        return "The hosting surface is the hot surface right now; touching drinks there reads as brittle hospitality, overfamiliarity, or escalation."
    return "Visible household surfaces remain socially charged enough to matter if you move on them."

def _carryover_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], thread_continuity: dict[str, Any]) -> str:
    values = open_pressures + consequences
    prior = social_state.get("prior_continuity_classes")
    prior_classes = [str(x) for x in prior] if isinstance(prior, list) else []
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "The earlier failed-exit wound is still sitting at the doorway; the room has not spent that departure shame."
    if _contains_any(values, "book", "art"):
        return "The earlier taste-and-status wound is still sitting on the books, ready to be reused as judgment."
    if _contains_any(values, "flower", "tulip"):
        return "The earlier manners wound is still sitting on the flowers; hospitality has not gone neutral again."
    if _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "The earlier exposure line is still sitting at the bathroom edge; help and pity have not been socially absorbed yet."
    if _contains_any(values, "phone"):
        return "The earlier humiliation line is still sitting on the phone; the interruption is not socially finished."
    if _has_hosting_surface(values):
        return "The earlier hospitality line is still sitting over the hosting surface; drinks have not gone socially neutral again."
    if _contains_any(prior_classes, "alliance_shift") or str(thread_continuity.get("thread_pressure_level") or "") in {"moderate", "high"}:
        return "An earlier social wound is still sitting in the room instead of fading out."
    return "A prior pressure line is still active enough to shape what the room does next."

def _social_geometry_now(*, open_pressures: list[str], social_state: dict[str, Any], responder_actor: str | None, current_scene_id: str) -> str:
    asym = str(social_state.get("responder_asymmetry_code") or "")
    if asym == "alliance_reposition_active" or _contains_any(open_pressures, "alliance"):
        return "The room is tilting across the couples; temporary coalitions matter more than stable pair lines right now."
    if asym == "blame_on_host_spouse_axis":
        return "Pressure is sitting with the host side and spouse axis rather than the guests."
    if asym == "blame_under_repair_tension":
        return "The spouse axis is carrying more embarrassment than the room is willing to admit outright."
    if current_scene_id == "hallway_threshold" or _contains_any(open_pressures, "exit", "departure"):
        return "Departure pressure is running through the couples as much as between them."
    if responder_actor and responder_actor.lower() in {"annette", "alain"}:
        return "The guest side is carrying more of the visible reading than the host side right now."
    if responder_actor and responder_actor.lower() in {"veronique", "michel"}:
        return "The host side is carrying more of the visible reading than the guest side right now."
    return "Pressure is moving across the room's sides rather than staying evenly shared."


def _situational_freedom_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any]) -> str:
    values = open_pressures + consequences
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "Distance shifts, hovering, and trying not to leave cleanly will all be socially legible here."
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "Checking in, helping, tidying, or hanging back will all be read in the exposed space around the bathroom edge."
    if _contains_any(values, "book", "art", "flower", "tulip", "phone"):
        return "Touching, not touching, helping around, or standing off from the loaded household surface will all mean something here."
    if str(social_state.get("social_risk_band") or "") == "high":
        return "Small domestic acts, silence, and where you place yourself are all socially live right now."
    return "The room is live enough that practical acts and small shifts in distance will not stay neutral."


def _address_pressure_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], responder_actor: str | None) -> str:
    values = open_pressures + consequences
    actor = responder_actor.title() if responder_actor else "Someone"
    asym = str(social_state.get("responder_asymmetry_code") or "")
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return f"{actor} is effectively pressing you through failed departure pressure; the doorway is acting like an accusation, not a neutral exit."
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return f"{actor} is effectively pressing you through exposure and recovery pressure; concern cannot stay neutral here."
    if _contains_any(values, "book", "art"):
        return f"{actor} is effectively pressing you through taste and household judgment, not just object attention."
    if _contains_any(values, "flower", "tulip"):
        return f"{actor} is effectively pressing you through brittle hospitality and manners pressure."
    if _contains_any(values, "phone"):
        return f"{actor} is effectively pressing you through humiliation and public-priority pressure."
    if _has_hosting_surface(values):
        return f"{actor} is effectively pressing you through brittle hospitality and hosting-surface pressure."
    if asym == "alliance_reposition_active":
        return "Pressure is reaching you through a shifting coalition rather than one settled side."
    return f"{actor} is effectively pressing you through the room's social reading of the act."

def _social_moment_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any]) -> str:
    values = open_pressures + consequences
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "This is a failed-exit moment under brittle civility."
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "This is an exposure-and-containment moment rather than ordinary hospitality."
    if _contains_any(values, "book", "art"):
        return "This is a judgment-and-status moment rather than neutral room talk."
    if _contains_any(values, "flower", "tulip"):
        return "This is a brittle-hospitality moment where manners are carrying accusation."
    if _contains_any(values, "phone"):
        return "This is a humiliation-and-priority moment more than a simple interruption."
    if _contains_any(values, "rum", "drink", "glass", "hosting", "table", "coffee table"):
        return "This is a brittle-hospitality moment where the hosting surface is doing the social work."
    if str(social_state.get("scene_pressure_state") or "") == "high_blame":
        return "This is an accusation-and-repair moment, not a neutral exchange."
    return "This is a socially charged moment where the room is expecting an answer of some kind."




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
    actor = (responder_actor or "").strip().lower()
    values = open_pressures + consequences
    if actor == "veronique":
        if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
            return "a principle-first rebuke that uses civility as correction"
        if _contains_any(values, "book", "art"):
            return "a civility-laden indictment that turns taste into judgment"
        if selected_scene_function == "repair_or_stabilize":
            return "a strained appeal to principle that keeps the room answerable"
        return "a wounded moral indictment that refuses to let the hurt sound private"
    if actor == "michel":
        if selected_scene_function == "withhold_or_evade":
            return "a practical retreat that tries to slide pressure sideways"
        if _contains_any(values, "flower", "tulip"):
            return "a smoothing deflection that offers manners instead of alignment"
        if _contains_any(values, "rum", "drink", "glass", "hosting", "table", "coffee table"):
            return "a smoothing deflection that offers hospitality instead of alignment"
        if selected_scene_function == "repair_or_stabilize":
            return "a smoothing deflection that buys calm by giving ground"
        return "a pragmatic sidestep that keeps loyalty blurred"
    if actor == "annette":
        if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
            return "a contemptuous dismantling that makes concern sound naive"
        if selected_scene_function == "repair_or_stabilize":
            return "a sharpened challenge that turns repair into fresh contradiction"
        if _contains_any(values, "book", "art"):
            return "a cutting contradiction that treats principle as performance"
        return "a contemptuous dismantling that strips courtesy down to appetite"
    if actor == "alain":
        if selected_scene_function == "withhold_or_evade" or _contains_any(values, "phone"):
            return "a tired evasive hedge dressed up as mediation"
        if selected_scene_function == "repair_or_stabilize":
            return "a thinning conciliatory appeal that cannot keep control"
        return "a weary mediation attempt that already sounds half-withdrawn"
    return "a socially loaded answer"


def _response_mask_slip_now(*, responder_actor: str | None, selected_scene_function: str, current_scene_id: str, open_pressures: list[str], consequences: list[str]) -> str:
    actor = (responder_actor or "").strip().lower()
    values = open_pressures + consequences
    if actor == "veronique":
        if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
            return "civility hardening into correction"
        if _contains_any(values, "book", "art"):
            return "principle hardening into judgment"
        return "principle covering visible hurt"
    if actor == "michel":
        if _contains_any(values, "flower", "tulip", "rum", "drink", "glass", "hosting", "table", "coffee table") or selected_scene_function == "repair_or_stabilize":
            return "smoothing starting to read as capitulation"
        if selected_scene_function == "withhold_or_evade":
            return "practical calm slipping into retreat"
        return "conciliation keeping loyalty blurred"
    if actor == "annette":
        if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
            return "intellectual distance hardening into contempt"
        if _contains_any(values, "book", "art"):
            return "wit exposing morality as pose"
        return "provocation stripping courtesy bare"
    if actor == "alain":
        if selected_scene_function == "withhold_or_evade" or _contains_any(values, "phone"):
            return "mediation thinning into evasion"
        if selected_scene_function == "repair_or_stabilize":
            return "conciliation giving way to fatigue"
        return "moderation already sounding half-withdrawn"
    return "social pressure breaking through the surface"


def _response_recentering_pull_now(*, responder_actor: str | None, selected_scene_function: str, current_scene_id: str, open_pressures: list[str], consequences: list[str]) -> str:
    actor = (responder_actor or "").strip().lower()
    values = open_pressures + consequences
    if actor == "veronique":
        if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
            return "pull the moment back under principle instead of letting the exit close it"
        return "pull the room back toward answerability instead of comfort"
    if actor == "michel":
        if _contains_any(values, "flower", "tulip", "rum", "drink", "glass", "hosting", "table", "coffee table"):
            return "pull the room back toward manners instead of open alignment"
        return "pull the room toward accommodation instead of a clean side"
    if actor == "annette":
        if _contains_any(values, "book", "art"):
            return "pull the room back to exposed contradiction instead of letting manners cover it"
        return "pull the room toward exposure instead of polite cover"
    if actor == "alain":
        if selected_scene_function == "withhold_or_evade" or _contains_any(values, "phone"):
            return "pull the room toward manageability without ever resolving it"
        return "pull the room toward temporary calm without mastering it"
    return "pull the room into a live answer rather than neutrality"


def _with_indefinite_article(phrase: str) -> str:
    stripped = (phrase or "").strip()
    if not stripped:
        return stripped
    return ("an " + stripped) if stripped[0].lower() in "aeiou" else ("a " + stripped)



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


def _previous_reply_continuity_context(*, state: dict[str, Any], committed_state: dict[str, Any]) -> dict[str, Any]:
    direct = committed_state.get("previous_reply_continuity_context")
    if isinstance(direct, dict):
        return direct
    last_turn = state.get("last_committed_turn")
    if isinstance(last_turn, dict):
        after = last_turn.get("committed_state_after")
        if isinstance(after, dict):
            prior = after.get("previous_reply_continuity_context")
            if isinstance(prior, dict):
                return prior
    return {}


def _earlier_reply_continuity_context(*, state: dict[str, Any], committed_state: dict[str, Any]) -> dict[str, Any]:
    direct = committed_state.get("earlier_reply_continuity_context")
    if isinstance(direct, dict):
        return direct
    last_turn = state.get("last_committed_turn")
    if isinstance(last_turn, dict):
        after = last_turn.get("committed_state_after")
        if isinstance(after, dict):
            prior = after.get("earlier_reply_continuity_context")
            if isinstance(prior, dict):
                return prior
    return {}


def _response_countermove_link_now(*, previous_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str) -> str:
    if not isinstance(previous_reply_context, dict) or not previous_reply_context:
        return ""
    previous_exchange = str(previous_reply_context.get("exchange_label") or "").strip()
    previous_surface = str(previous_reply_context.get("surface_token") or "").strip()
    if not previous_exchange:
        return ""
    current_exchange = _response_exchange_label_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    current_surface = _response_surface_token_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    same_surface = previous_surface and current_surface != "room" and previous_surface == current_surface
    if same_surface:
        if previous_exchange in {"failed repair", "brittle repair", "containment"} and current_exchange in {"accusation", "exposure", "status judgment"}:
            return f"turning the last {previous_exchange} back through the same {current_surface}"
        if previous_exchange in {"accusation", "status judgment", "exposure"} and current_exchange in {"failed repair", "brittle repair", "containment", "evasive pressure"}:
            return f"answering the last {previous_exchange} on the same {current_surface}"
        if previous_exchange == "evasive pressure":
            return f"after the last evasive turn left the same {current_surface} live"
        if previous_exchange == current_exchange:
            return f"carrying the last {current_exchange} forward on the same {current_surface}"
        return f"turning the last {previous_exchange} into {current_exchange} on the same {current_surface}"
    if previous_exchange in {"failed repair", "brittle repair", "containment"} and current_exchange in {"accusation", "exposure", "status judgment"}:
        return f"after the last {previous_exchange} only reopened the room"
    if previous_exchange in {"accusation", "status judgment", "exposure"} and current_exchange in {"failed repair", "brittle repair", "containment", "evasive pressure"}:
        return f"because the last {previous_exchange} forced a defensive return"
    if previous_exchange == "evasive pressure" and current_exchange in {"failed repair", "brittle repair", "accusation", "exposure", "status judgment"}:
        return "because the last evasive turn left the pressure live"
    if previous_exchange in {"failed repair", "brittle repair", "containment"} and current_exchange in {"failed repair", "brittle repair", "containment"}:
        return "because the room could not get out of the last repair loop"
    return "because the last visible answer left the pressure live"


def _response_delayed_countermove_link_now(*, earlier_reply_context: dict[str, Any], previous_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str) -> str:
    if not isinstance(earlier_reply_context, dict) or not earlier_reply_context:
        return ""
    earlier_exchange = str(earlier_reply_context.get("exchange_label") or "").strip()
    earlier_surface = str(earlier_reply_context.get("surface_token") or "").strip()
    previous_surface = str(previous_reply_context.get("surface_token") or "").strip() if isinstance(previous_reply_context, dict) else ""
    if not earlier_exchange:
        return ""
    current_exchange = _response_exchange_label_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    current_surface = _response_surface_token_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    if current_surface == "room" or not earlier_surface or earlier_surface != current_surface:
        return ""
    if previous_surface and previous_surface == current_surface:
        return ""
    if earlier_exchange in {"failed repair", "brittle repair", "containment"} and current_exchange in {"accusation", "exposure", "status judgment"}:
        return f"pulling the earlier {earlier_exchange} back onto the same {current_surface}"
    if earlier_exchange in {"accusation", "status judgment", "exposure"} and current_exchange in {"failed repair", "brittle repair", "containment", "evasive pressure"}:
        return f"answering the earlier {earlier_exchange} back on the same {current_surface}"
    if earlier_exchange == current_exchange:
        return f"bringing the earlier {current_exchange} back onto the same {current_surface}"
    return f"bringing the earlier {earlier_exchange} back as {current_exchange} on the same {current_surface}"


def _response_interruption_reentry_hook_now(*, previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str) -> str:
    current_exchange = _response_exchange_label_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    current_surface = _response_surface_token_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    previous_exchange = str(previous_reply_context.get("exchange_label") or "").strip() if isinstance(previous_reply_context, dict) else ""
    previous_surface = str(previous_reply_context.get("surface_token") or "").strip() if isinstance(previous_reply_context, dict) else ""
    earlier_exchange = str(earlier_reply_context.get("exchange_label") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    earlier_surface = str(earlier_reply_context.get("surface_token") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    same_surface = current_surface != "room" and previous_surface and previous_surface == current_surface

    if current_exchange == "evasive pressure":
        if same_surface and previous_exchange in {"accusation", "status judgment", "exposure"}:
            return f"trying to answer around the point on the same {current_surface}"
        if same_surface and previous_exchange in {"failed repair", "brittle repair", "containment"}:
            return f"trying to slide the same {current_surface} sideways without settling it"
        if previous_exchange in {"accusation", "status judgment", "exposure"}:
            return "trying to answer around the point without settling it"
        if previous_exchange in {"failed repair", "brittle repair", "containment"}:
            return "trying to shift the line sideways without settling it"

    if previous_exchange == "evasive pressure":
        if same_surface and current_exchange in {"accusation", "status judgment", "exposure", "failed repair", "brittle repair", "containment"}:
            return f"not letting the last dodge stand on the same {current_surface}"
        if current_exchange in {"accusation", "status judgment", "exposure", "failed repair", "brittle repair", "containment"}:
            return "not letting the last dodge settle into a subject shift"

    if earlier_exchange == "evasive pressure" and current_surface != "room" and earlier_surface == current_surface and previous_surface != current_surface and current_exchange != "evasive pressure":
        return f"dragging the earlier dodge back onto the same {current_surface}"

    return ""



def _response_rhythm_pressure_hook_now(*, previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str, responder_actor: str | None) -> str:
    current_exchange = _response_exchange_label_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    current_surface = _response_surface_token_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    actor = (responder_actor or "").strip().lower()
    previous_exchange = str(previous_reply_context.get("exchange_label") or "").strip() if isinstance(previous_reply_context, dict) else ""
    previous_surface = str(previous_reply_context.get("surface_token") or "").strip() if isinstance(previous_reply_context, dict) else ""
    earlier_exchange = str(earlier_reply_context.get("exchange_label") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    earlier_surface = str(earlier_reply_context.get("surface_token") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    same_surface = current_surface != "room" and previous_surface and previous_surface == current_surface
    earlier_same_surface = current_surface != "room" and earlier_surface and earlier_surface == current_surface and previous_surface != current_surface

    if current_exchange == "evasive pressure":
        if same_surface and previous_exchange in {"accusation", "status judgment", "exposure"}:
            if actor == "alain":
                return f"buying a beat on the same {current_surface} instead of answering it"
            if actor == "michel":
                return f"talking across the same {current_surface} instead of settling it"
            return f"letting a beat hang on the same {current_surface} instead of answering it"
        if same_surface and previous_exchange in {"failed repair", "brittle repair", "containment"}:
            return f"letting the same {current_surface} hang for a beat instead of settling it"

    if previous_exchange == "evasive pressure" and current_exchange in {"accusation", "status judgment", "exposure", "failed repair", "brittle repair", "containment"} and same_surface:
        if actor in {"annette", "veronique"}:
            return f"cutting back in before the dodge on the same {current_surface} can go quiet"
        return f"cutting back across the dodge on the same {current_surface} before it can settle"

    if earlier_same_surface and earlier_exchange == "evasive pressure" and current_exchange != "evasive pressure":
        return f"breaking the earlier pause back over the same {current_surface}"

    return ""



def _response_pressure_relay_hook_now(*, previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str, responder_actor: str | None) -> str:
    current_exchange = _response_exchange_label_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    current_surface = _response_surface_token_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    current_actor = (responder_actor or "").strip().lower()
    previous_exchange = str(previous_reply_context.get("exchange_label") or "").strip() if isinstance(previous_reply_context, dict) else ""
    previous_surface = str(previous_reply_context.get("surface_token") or "").strip() if isinstance(previous_reply_context, dict) else ""
    previous_actor = str(previous_reply_context.get("responder_actor") or "").strip().lower() if isinstance(previous_reply_context, dict) else ""
    earlier_exchange = str(earlier_reply_context.get("exchange_label") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    earlier_surface = str(earlier_reply_context.get("surface_token") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    earlier_actor = str(earlier_reply_context.get("responder_actor") or "").strip().lower() if isinstance(earlier_reply_context, dict) else ""

    if current_surface == "room" or not current_actor or not previous_actor or previous_actor == current_actor:
        return ""
    if previous_surface != current_surface:
        return ""

    assertive_exchanges = {"accusation", "status judgment", "exposure"}
    repair_exchanges = {"failed repair", "brittle repair", "containment"}
    across_room = " across the room" if _responder_social_side(previous_actor) != _responder_social_side(current_actor) else ""
    earlier_same_surface = earlier_surface == current_surface and bool(earlier_exchange)

    if previous_exchange == "evasive pressure" and current_exchange in assertive_exchanges | repair_exchanges:
        if earlier_same_surface and earlier_actor and earlier_actor not in {current_actor, previous_actor}:
            return f"letting the same {current_surface} pressure jump speakers{across_room} before the dodge can settle"
        return ""

    if previous_exchange in assertive_exchanges and current_exchange in assertive_exchanges:
        if earlier_same_surface and earlier_actor and earlier_actor not in {current_actor, previous_actor}:
            return f"letting the same {current_surface} pressure jump speakers{across_room} before it can cool"
        return f"picking up the same {current_surface}{across_room} before it can cool"

    if previous_exchange in assertive_exchanges and current_exchange in repair_exchanges:
        return f"taking up the same {current_surface}{across_room} without letting it drop"

    return ""


def _response_micro_weave_hook_now(*, previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str) -> str:
    current_exchange = _response_exchange_label_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    current_surface = _response_surface_token_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    previous_exchange = str(previous_reply_context.get("exchange_label") or "").strip() if isinstance(previous_reply_context, dict) else ""
    previous_surface = str(previous_reply_context.get("surface_token") or "").strip() if isinstance(previous_reply_context, dict) else ""
    earlier_exchange = str(earlier_reply_context.get("exchange_label") or "").strip() if isinstance(earlier_reply_context, dict) else ""
    earlier_surface = str(earlier_reply_context.get("surface_token") or "").strip() if isinstance(earlier_reply_context, dict) else ""

    if current_surface == "room" or current_exchange == "evasive pressure":
        return ""
    if previous_exchange != "evasive pressure":
        return ""
    if not earlier_exchange or earlier_exchange == "evasive pressure":
        return ""
    if previous_surface != current_surface or earlier_surface != current_surface:
        return ""

    if current_exchange in {"accusation", "exposure", "status judgment"}:
        return f"reopening the same {current_surface} through the dodge before the point can die"
    if current_exchange in {"failed repair", "brittle repair", "containment"}:
        return f"forcing the same {current_surface} back into answer before the dodge can stand"
    return f"bringing the same {current_surface} back through the dodge before it can die"



def _response_continuity_hook_now(*, previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str, responder_actor: str | None) -> str:
    relay = _response_pressure_relay_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
        responder_actor=responder_actor,
    )
    micro_weave = _response_micro_weave_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    rhythm = _response_rhythm_pressure_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
        responder_actor=responder_actor,
    )
    interruption = _response_interruption_reentry_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    immediate = _response_countermove_link_now(
        previous_reply_context=previous_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    delayed = _response_delayed_countermove_link_now(
        earlier_reply_context=earlier_reply_context,
        previous_reply_context=previous_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    generic_immediate = {
        "after the last evasive turn left the pressure live",
        "because the last evasive turn left the pressure live",
        "because the room could not get out of the last repair loop",
        "because the last visible answer left the pressure live",
    }
    generic_interruption = {
        "not letting the last dodge settle into a subject shift",
    }
    if relay:
        return relay
    if micro_weave:
        return micro_weave
    if rhythm:
        return rhythm
    if delayed and interruption in generic_interruption:
        return delayed
    if interruption:
        return interruption
    if delayed and (not immediate or immediate in generic_immediate or immediate.startswith("after the last ") or immediate.startswith("because the last ") or immediate.startswith("because the room could not")):
        return delayed
    return immediate


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


def _response_line_prefix_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], responder_actor: str | None, selected_scene_function: str, thread_continuity: dict[str, Any], previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any]) -> str:
    actor = responder_actor.title() if responder_actor else "Someone"
    exchange_type = _response_exchange_type_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    voice = _response_voice_phrase_now(social_state=social_state, responder_actor=responder_actor)
    heat = _response_surface_heat_phrase_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        responder_actor=responder_actor,
    )
    signature = _response_performance_signature_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    tail = _response_carryover_tail_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        thread_continuity=thread_continuity,
    )
    countermove = _response_continuity_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
        responder_actor=responder_actor,
    )
    base = f"{actor}, {voice}, answers in {exchange_type}"
    if heat:
        base = f"{base} with {heat}"
    if signature:
        base = f"{base}, in {signature}"
    if countermove:
        base = f"{base}, {countermove}"
    if tail:
        return f"{base}, {tail}"
    return base


def frame_story_runtime_visible_output_bundle(*, visible_output_bundle: dict[str, Any] | None, shell_readout_projection: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(visible_output_bundle, dict):
        return None
    if not isinstance(shell_readout_projection, dict):
        return dict(visible_output_bundle)
    prefix = shell_readout_projection.get("response_line_prefix_now")
    if not isinstance(prefix, str) or not prefix.strip():
        prefix = shell_readout_projection.get("response_address_source_now")
    if not isinstance(prefix, str) or not prefix.strip():
        return dict(visible_output_bundle)

    framed = dict(visible_output_bundle)
    for key in ("gm_narration", "spoken_lines"):
        lines = framed.get(key)
        if isinstance(lines, list) and lines:
            copied = [str(x) for x in lines]
            first = copied[0].strip()
            if first:
                copied[0] = f"{prefix.strip()} — {first}"
            framed[key] = copied
    return framed

def _response_pressure_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any]) -> str:
    values = open_pressures + consequences
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return "The room is pressing for repair, explanation, or restraint around departure and failed exit."
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return "The room is pressing around exposure, concern, recoil, and who must manage what has become public."
    if _contains_any(values, "book", "art"):
        return "The room is pressing for restraint or explanation around taste, manners, and status."
    if _contains_any(values, "flower", "tulip"):
        return "The room is pressing around manners, hospitality, and whether care has become overfamiliarity."
    if _contains_any(values, "phone"):
        return "The room is pressing for deference, apology, or exposure management around interruption and priority."
    if _has_hosting_surface(values):
        return "The room is pressing around brittle hospitality, overfamiliarity, and how one handles the hosting surface."
    if str(social_state.get("scene_pressure_state") or "") == "high_blame":
        return "The room is pressing for answerability rather than letting the act pass."
    return "The room is pressing for some form of social answer rather than letting the act remain neutral."

def _response_address_source_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], responder_actor: str | None, selected_scene_function: str = "") -> str:
    actor = responder_actor.title() if responder_actor else "Someone"
    voice = _response_voice_phrase_now(social_state=social_state, responder_actor=responder_actor)
    exchange_type = _response_exchange_type_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    heat = _response_surface_heat_phrase_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        responder_actor=responder_actor,
    )
    signature = _response_performance_signature_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    if heat:
        return f"{actor} answers {voice} in {exchange_type}, with {heat}, in {signature}."
    return f"{actor} answers {voice} in {exchange_type}, in {signature}."


def _response_exchange_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str, thread_continuity: dict[str, Any], previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], responder_actor: str | None = None) -> str:
    exchange_type = _response_exchange_type_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    cause = _response_cause_compressed_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
    )
    carry = _response_carryover_exchange_phrase_now(
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        thread_continuity=thread_continuity,
    )
    pull = _response_recentering_pull_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    countermove = _response_continuity_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
        responder_actor=responder_actor,
    )
    if carry and countermove:
        return f"Your act drew {_with_indefinite_article(exchange_type)} answer {cause}, {countermove}, {carry}, and let the reply {pull}."
    if carry:
        return f"Your act drew {_with_indefinite_article(exchange_type)} answer {cause}, {carry}, and let the reply {pull}."
    if countermove:
        return f"Your act drew {_with_indefinite_article(exchange_type)} answer {cause}, {countermove}, and let the reply {pull}."
    return f"Your act drew {_with_indefinite_article(exchange_type)} answer {cause}, and let the reply {pull}."


def _who_answers_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], responder_actor: str | None, selected_scene_function: str, social_state: dict[str, Any] | None = None) -> str:
    actor = responder_actor.title() if responder_actor else "Someone"
    side = _responder_social_side(responder_actor)
    line = _response_pressure_line_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state or {})
    mask = _response_mask_slip_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    if line == "spouse-axis embarrassment":
        return f"{actor} is the one answering now; the {side} is speaking through spouse embarrassment, with {mask}."
    if line == "cross-couple strain":
        return f"{actor} is the one answering now; the {side} is speaking through cross-couple strain, with {mask}."
    return f"{actor} is the one answering now; the {side} is speaking through {line}, with {mask}."



def _why_this_reply_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str, previous_reply_context: dict[str, Any], earlier_reply_context: dict[str, Any], responder_actor: str | None = None) -> str:
    values = open_pressures + consequences
    side = _responder_social_side(responder_actor)
    asym = str(social_state.get("responder_asymmetry_code") or "")
    pull = _response_recentering_pull_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    signature = _response_performance_signature_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    countermove = _response_continuity_hook_now(
        previous_reply_context=previous_reply_context,
        earlier_reply_context=earlier_reply_context,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
        social_state=social_state,
        selected_scene_function=selected_scene_function,
        responder_actor=responder_actor,
    )
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        if asym == "blame_on_host_spouse_axis":
            hook = f", {countermove}," if countermove else ""
            return f"The room read the act as failed repair, so the {side} answered through spouse embarrassment at the doorway{hook} and let the reply {pull}, in {signature}."
        hook = f", {countermove}," if countermove else ""
        return f"The room read the act as failed repair, so departure pressure pulled the {side} answer to the doorway{hook} and let the reply {pull}, in {signature}."
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        hook = f", {countermove}," if countermove else ""
        return f"The room read the act as exposure, so care, recoil, and witness pressure pulled the {side} answer to the bathroom edge{hook} and let the reply {pull}, in {signature}."
    if _contains_any(values, "book", "art"):
        if asym != "alliance_reposition_active":
            hook = f", {countermove}," if countermove else ""
            return f"The room read the act as taste and household judgment, so status strain pulled a {side} answer onto the books{hook} and let the reply {pull}, in {signature}."
        hook = f", {countermove}," if countermove else ""
        return f"The room read the act as taste and household judgment, so cross-couple strain answered through the books{hook} and let the reply {pull}, in {signature}."
    if _contains_any(values, "flower", "tulip"):
        hook = f", {countermove}," if countermove else ""
        return f"The room read the act through hospitality and manners, so boundary strain pulled a {side} answer onto the flowers{hook} and let the reply {pull}, in {signature}."
    if _contains_any(values, "phone"):
        hook = f", {countermove}," if countermove else ""
        return f"The room read the act through humiliation and public priority, so humiliation pressure pulled a {side} answer onto the phone{hook} and let the reply {pull}, in {signature}."
    if asym == "alliance_reposition_active":
        hook = f", {countermove}," if countermove else ""
        return f"The room is answering through a shifting coalition rather than a settled side{hook} and letting the reply {pull}, in {signature}."
    if selected_scene_function == "repair_or_stabilize":
        hook = f", {countermove}," if countermove else ""
        return f"The room is forcing the act into a repair-shaped exchange, making the {side} carry the answer{hook} and letting the reply {pull}, in {signature}."
    if selected_scene_function == "redirect_blame":
        hook = f", {countermove}," if countermove else ""
        return f"The room is reusing the act to move blame and social cost onto the {side} answer{hook} and letting the reply {pull}, in {signature}."
    if selected_scene_function == "withhold_or_evade":
        hook = f", {countermove}," if countermove else ""
        return f"The room is making the answer slippery; pressure is still there, it is arriving through the {side} obliquely{hook}, and the reply is trying to {pull}, in {signature}."
    hook = f", {countermove}," if countermove else ""
    return f"The room is treating the act as answerable, routing the reply through the {side}{hook}, and letting it {pull}, in {signature}."



def _observation_foothold_now(*, current_scene_id: str, open_pressures: list[str], consequences: list[str], social_state: dict[str, Any], selected_scene_function: str, responder_actor: str | None = None) -> str:
    values = open_pressures + consequences
    side = _responder_social_side(responder_actor)
    pull = _response_recentering_pull_now(
        responder_actor=responder_actor,
        selected_scene_function=selected_scene_function,
        current_scene_id=current_scene_id,
        open_pressures=open_pressures,
        consequences=consequences,
    )
    if current_scene_id == "hallway_threshold" or _contains_any(values, "exit", "departure"):
        return f"You are inside a failed-exit exchange now; the {side} is answering through departure pressure, and the reply is trying to {pull}."
    if current_scene_id == "bathroom_recovery" or _contains_any(values, "cleanup", "bathroom", "vomit", "contamination"):
        return f"You are inside an exposure exchange now; the {side} is answering through care, recoil, and witness pressure, trying to {pull}."
    if _contains_any(values, "book", "art"):
        return f"You are inside a judgment exchange now; the {side} is answering through taste, manners, and status, trying to {pull}."
    if _contains_any(values, "flower", "tulip"):
        return f"You are inside a brittle hospitality exchange now; the {side} is answering through manners and overfamiliarity pressure, trying to {pull}."
    if _contains_any(values, "phone"):
        return f"You are inside a humiliation exchange now; the {side} is answering through public priority and contempt risk, trying to {pull}."
    if selected_scene_function == "repair_or_stabilize":
        return f"You are inside a repair-shaped exchange now; the {side} is carrying the answer and trying to {pull}."
    if selected_scene_function == "redirect_blame":
        return f"You are inside a blame-moving exchange now; the {side} is carrying redistributed social cost and trying to {pull}."
    return f"You are inside a live exchange now; the {side} is answering what you did and trying to {pull}."

def build_story_runtime_shell_readout(*, state: dict[str, Any], last_diagnostic: dict[str, Any] | None) -> dict[str, Any]:
    committed_state = state.get("committed_state") if isinstance(state.get("committed_state"), dict) else {}
    current_scene_id = str(state.get("current_scene_id") or committed_state.get("current_scene_id") or "")
    open_pressures = _open_pressures(committed_state)
    consequences = _last_consequences(committed_state)
    thread_continuity = _thread_continuity(committed_state)
    previous_reply_context = _previous_reply_continuity_context(state=state, committed_state=committed_state)
    earlier_reply_context = _earlier_reply_continuity_context(state=state, committed_state=committed_state)
    social_state = _social_state_record(last_diagnostic)
    responder_actor = _first_responder_actor(last_diagnostic)
    selected_scene_function = _selected_scene_function(last_diagnostic)

    return {
        "social_weather_now": _social_weather_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "live_surface_now": _live_surface_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "carryover_now": _carryover_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, thread_continuity=thread_continuity),
        "social_geometry_now": _social_geometry_now(open_pressures=open_pressures, social_state=social_state, responder_actor=responder_actor, current_scene_id=current_scene_id),
        "situational_freedom_now": _situational_freedom_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "address_pressure_now": _address_pressure_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, responder_actor=responder_actor),
        "social_moment_now": _social_moment_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "response_pressure_now": _response_pressure_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "response_performance_signature_now": _response_performance_signature_now(responder_actor=responder_actor, selected_scene_function=selected_scene_function, current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "response_mask_slip_now": _response_mask_slip_now(responder_actor=responder_actor, selected_scene_function=selected_scene_function, current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "response_recentering_now": _response_recentering_pull_now(responder_actor=responder_actor, selected_scene_function=selected_scene_function, current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "response_address_source_now": _response_address_source_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, responder_actor=responder_actor, selected_scene_function=selected_scene_function),
        "response_exchange_now": _response_exchange_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, selected_scene_function=selected_scene_function, thread_continuity=thread_continuity, previous_reply_context=previous_reply_context, earlier_reply_context=earlier_reply_context, responder_actor=responder_actor),
        "response_exchange_label_now": _response_exchange_label_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, selected_scene_function=selected_scene_function),
        "response_carryover_now": _response_carryover_tail_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, thread_continuity=thread_continuity),
        "response_line_prefix_now": _response_line_prefix_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, responder_actor=responder_actor, selected_scene_function=selected_scene_function, thread_continuity=thread_continuity, previous_reply_context=previous_reply_context, earlier_reply_context=earlier_reply_context),
        "who_answers_now": _who_answers_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, responder_actor=responder_actor, selected_scene_function=selected_scene_function, social_state=social_state),
        "why_this_reply_now": _why_this_reply_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, selected_scene_function=selected_scene_function, previous_reply_context=previous_reply_context, earlier_reply_context=earlier_reply_context, responder_actor=responder_actor),
        "observation_foothold_now": _observation_foothold_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, selected_scene_function=selected_scene_function, responder_actor=responder_actor),
        "room_pressure_now": _room_pressure_now(current_scene_id=current_scene_id, open_pressures=open_pressures, social_state=social_state),
        "zone_sensitivity_now": _zone_sensitivity_now(current_scene_id=current_scene_id, open_pressures=open_pressures, social_state=social_state),
        "salient_object_now": _salient_object_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "object_sensitivity_now": _object_sensitivity_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "continued_wound_now": _continued_wound_now(open_pressures=open_pressures, social_state=social_state, thread_continuity=thread_continuity),
        "role_pressure_now": _role_pressure_now(social_state=social_state, responder_actor=responder_actor),
        "dominant_social_reading_now": _dominant_social_reading_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "social_axis_now": _social_axis_now(open_pressures=open_pressures, social_state=social_state, responder_actor=responder_actor),
        "host_guest_pressure_now": _host_guest_pressure_now(open_pressures=open_pressures, social_state=social_state, responder_actor=responder_actor),
        "spouse_axis_now": _spouse_axis_now(current_scene_id=current_scene_id, open_pressures=open_pressures, social_state=social_state),
        "cross_couple_now": _cross_couple_now(open_pressures=open_pressures, social_state=social_state),
        "pressure_redistribution_now": _pressure_redistribution_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "callback_pressure_now": _callback_summary(open_pressures=open_pressures, social_state=social_state, thread_continuity=thread_continuity),
        "callback_role_frame_now": _callback_role_frame_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, thread_continuity=thread_continuity),
        "active_pressure_now": _active_pressure_summary(open_pressures),
        "recent_act_social_meaning": _recent_act_social_meaning(open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "object_social_reading_now": _object_social_reading_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
        "situational_affordance_now": _situational_affordance_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "reaction_delta_now": _reaction_delta_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "carryover_delta_now": _carryover_delta_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state, thread_continuity=thread_continuity),
        "pressure_shift_delta_now": _pressure_shift_delta_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences, social_state=social_state),
        "hot_surface_delta_now": _hot_surface_delta_now(current_scene_id=current_scene_id, open_pressures=open_pressures, consequences=consequences),
    }
