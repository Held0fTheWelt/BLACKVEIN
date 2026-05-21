"""Social pressure and environment-sensitive shell readout phrases."""

from __future__ import annotations

from .common import *
from .environment_readout import *

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
    actor = _responder_label(responder_actor)
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
    actor = _responder_label(responder_actor)
    if asym == "blame_on_host_spouse_axis":
        return f"The host side and spouse axis are carrying the weight; {actor} is taking the room's boundary reading."
    if asym == "blame_under_repair_tension":
        return "The spouse axis is still carrying embarrassment while the room pretends to repair itself."
    if asym == "alliance_reposition_active" or _contains_any(open_pressures, "alliance"):
        return "Cross-couple strain is carrying more of the pressure than ordinary blame."
    if _responder_social_side(responder_actor) == "guest side":
        return f"The guest side is carrying more of the visible reading through {actor}."
    if _responder_social_side(responder_actor) == "host side":
        return f"The host side is carrying more of the visible reading through {actor}."
    return "The room is sorting pressure through social sides rather than neutrally."


def _host_guest_pressure_now(*, open_pressures: list[str], social_state: dict[str, Any], responder_actor: str | None) -> str:
    asym = str(social_state.get("responder_asymmetry_code") or "")
    if asym == "blame_on_host_spouse_axis":
        return "Host-side pressure is carrying more of the room; the guests have more room to watch than absorb."
    if asym == "alliance_reposition_active" or _contains_any(open_pressures, "alliance"):
        return "Pressure is bouncing across host and guest lines rather than staying parked on one side."
    if _responder_social_side(responder_actor) == "guest side":
        return "Guest-side pressure is more visible than host-side calm right now."
    if _responder_social_side(responder_actor) == "host side":
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
    if _responder_social_side(responder_actor) == "guest side":
        return "The guest side is carrying more of the visible reading than the host side right now."
    if _responder_social_side(responder_actor) == "host side":
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

__all__ = (
    '_response_pressure_line_now',
    '_response_side_pair_frame_now',
    '_room_pressure_now',
    '_salient_object_now',
    '_zone_sensitivity_now',
    '_object_sensitivity_now',
    '_situational_affordance_now',
    '_continued_wound_now',
    '_role_pressure_now',
    '_dominant_social_reading_now',
    '_social_axis_now',
    '_host_guest_pressure_now',
    '_spouse_axis_now',
    '_cross_couple_now',
    '_pressure_redistribution_now',
    '_callback_role_frame_now',
    '_object_social_reading_now',
    '_callback_summary',
    '_active_pressure_summary',
    '_recent_act_social_meaning',
    '_reaction_delta_now',
    '_carryover_delta_now',
    '_pressure_shift_delta_now',
    '_hot_surface_delta_now',
    '_social_weather_now',
    '_live_surface_now',
    '_carryover_now',
    '_social_geometry_now',
    '_situational_freedom_now',
    '_address_pressure_now',
    '_social_moment_now',
)
