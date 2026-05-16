"""God of Carnage turn-0 opening dramaturgy handover (OPENING-DRAMATURGY-HANDOVER-01).

Canonical content: ``content/modules/god_of_carnage/direction/opening_sequence.yaml``.
Runtime enforces three narrator slots (premise → room/ritual → role anchor) plus
polite first-NPC surface; the model may style wording, but missing slots are filled
deterministically without weakening ``opening_shape_contract_pass``.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from ai_stack.goc_yaml_authority import load_goc_opening_sequence_yaml
from ai_stack.visible_narrative_contract import sanitize_gm_narration_beat_line


OPENING_HANDOVER_VERSION = "1.0.0"


@lru_cache(maxsize=1)
def _cached_opening_yaml() -> dict[str, Any]:
    return load_goc_opening_sequence_yaml()


def premise_fact_seeds_from_yaml() -> list[str]:
    data = _cached_opening_yaml()
    seeds = data.get("premise_fact_seeds")
    if not isinstance(seeds, list):
        return []
    return [str(s).strip() for s in seeds if str(s).strip()]


def _lang_norm(output_language: str | None) -> str:
    return (output_language or "de").strip().lower()[:2] or "de"


def _is_annette(*, human_actor_id: str | None, selected_player_role: str | None) -> bool:
    blob = f"{human_actor_id or ''} {selected_player_role or ''}".lower()
    return "annette" in blob


def _is_alain(*, human_actor_id: str | None, selected_player_role: str | None) -> bool:
    blob = f"{human_actor_id or ''} {selected_player_role or ''}".lower()
    return "alain" in blob


def role_display_name(*, human_actor_id: str | None, selected_player_role: str | None) -> str:
    raw = str(human_actor_id or selected_player_role or "").strip()
    if not raw:
        return "the player character"
    if "_" in raw:
        parts = [p for p in raw.split("_") if p]
        return " ".join(p[:1].upper() + p[1:] for p in parts if p)
    return raw[:1].upper() + raw[1:] if raw else "the player character"


def deterministic_part1_premise(*, output_language: str | None) -> str:
    """Background / shared premise: park court, two boys, stick, injury, civilised procedure."""
    lang = _lang_norm(output_language)
    if lang == "de":
        return sanitize_gm_narration_beat_line(
            "Am Rand eines Pariser Parks: grauer Herbsthimmel, kahle Bäume, ein Basketballplatz, Spielgerät und Fahrräder. "
            "Unter den Jungen kippt ein Streit; einer greift nach einem Stock, dreht sich um und schlägt zu, bevor er beim Weggehen noch ein Fahrrad umtritt. "
            "Die Eltern haben vereinbart, es »zivilisiert« zu klären — die Kluft zwischen kindlicher Gewalt und höflichem Verfahren ist schon spürbar."
        )
    return sanitize_gm_narration_beat_line(
        "At the edge of a Paris park: gray autumn sky, bare trees, a basketball court, playground equipment, and bicycles. "
        "A quarrel between boys turns; one grabs a stick, turns back, strikes, and kicks over a bicycle as he leaves. "
        "Their parents agreed to settle it the civilised way — the gap between child-world violence and polite procedure already hangs in the air."
    )


def deterministic_part2_room(*, output_language: str | None) -> str:
    """Paris salon / ritual civility: hosts, guests, coats, papers, art books, tulips, coffee, dessert."""
    lang = _lang_norm(output_language)
    if lang == "de":
        return sanitize_gm_narration_beat_line(
            "In der Pariser Wohnung der Vallons: Mäntel ordentlich gelegt, Papiere mit sauberen Kanten, "
            "Kunstbücher und Tulpen, die Kultur vorspiegeln. Espresso und ein Dessert stehen noch höflich bereit — "
            "Gastgeber und Gäste, gefangen in einem Ritual der Manieren, bevor aus Höflichkeit Anklage werden kann."
        )
    return sanitize_gm_narration_beat_line(
        "In the Vallons' Paris apartment: coats folded with care, papers with neat edges, art books and tulips "
        "advertising culture. Espresso and a dessert still wait politely — hosts and guests caught in a ritual of "
        "manners before courtesy can curdle into accusation."
    )


def deterministic_role_anchor_beat(
    *,
    output_language: str | None,
    human_actor_id: str | None,
    selected_player_role: str | None,
) -> str:
    """Narrator-only identity anchor: guest + spouse + not spectator; never prescribes speech or action."""
    lang = _lang_norm(output_language)
    display = role_display_name(human_actor_id=human_actor_id, selected_player_role=selected_player_role)
    if lang == "de":
        if _is_annette(human_actor_id=human_actor_id, selected_player_role=selected_player_role):
            return sanitize_gm_narration_beat_line(
                f"Du bist {display}, als Gast neben Alain gekommen — Ehefrau in dieser höflichen Phase, "
                "nicht Zuschauerin; was du sagst oder tust, entscheidest du selbst, nicht der Raum für dich."
            )
        if _is_alain(human_actor_id=human_actor_id, selected_player_role=selected_player_role):
            return sanitize_gm_narration_beat_line(
                f"Du bist {display}, als Gast neben Annette gekommen — Ehemann in dieser höflichen Phase, "
                "nicht Zuschauer; beruflicher Druck zieht am Rand deiner Aufmerksamkeit, ohne dir eine Zeile vorzuschreiben."
            )
        return sanitize_gm_narration_beat_line(
            f"Du bist {display}, als Gast in dieser Elternrunde — nicht außerhalb dessen, was zwischen den Paaren steht; "
            "deine nächste Geste bleibt dir überlassen."
        )
    if _is_annette(human_actor_id=human_actor_id, selected_player_role=selected_player_role):
        return sanitize_gm_narration_beat_line(
            f"You are {display}, arriving as a guest beside Alain — spouse in this courteous phase, not a spectator; "
            "what you say or do next is yours to choose, not scripted by the room."
        )
    if _is_alain(human_actor_id=human_actor_id, selected_player_role=selected_player_role):
        return sanitize_gm_narration_beat_line(
            f"You are {display}, arriving as a guest beside Annette — spouse in this courteous phase, not a spectator; "
            "professional pressure tugs at the edge of your attention without putting words in your mouth."
        )
    return sanitize_gm_narration_beat_line(
        f"You are {display}, present as a guest in this parents' meeting — not outside what is at stake between the couples; "
        "your next move remains yours to choose."
    )


def polite_ritual_first_actor_line(*, output_language: str | None, actor_id: str | None) -> str:
    lang = _lang_norm(output_language)
    aid = str(actor_id or "veronique_vallon").strip().lower()
    host_veronique = "veronique" in aid or aid.endswith("vallon") or aid == ""
    if lang == "de":
        if host_veronique:
            return "Bitte, setzen Sie sich; ich bringe noch einen Kaffee."
        return "Michel nickt höflich und rückt die Tassen zurecht, ohne das Thema zu benennen."
    if host_veronique:
        return "Please — sit; I'll bring more coffee."
    return "Michel gives a small polite nod and straightens the cups without naming the subject."


_RE_GENERIC_CONFLICT = re.compile(
    r"(conflict\s+resolution|mediation\s+session|konflikt(lösung|gespräch)?|"
    r"mediation|sitzung\s+zur\s+klärung|beilegung(s)?(gespräch|termin)?|"
    r"schlichtungs(stelle|gespräch)|family\s+mediation)",
    re.IGNORECASE,
)

_RE_PROSECUTORIAL = re.compile(
    r"(^|\b)(you\s+did|it'?s\s+your\s+fault|how\s+dare|"
    r"sie\s+haben|ihre\s+schuld|warum\s+haben\s+sie|dafür\s+sind\s+sie|"
    r"das\s+ist\s+ihre\s+schuld|you\s+started|you\s+caused)\b",
    re.IGNORECASE,
)


def generic_conflict_resolution_detected(text: str) -> bool:
    return bool(_RE_GENERIC_CONFLICT.search(text or ""))


def prosecutorial_opening_detected(text: str) -> bool:
    return bool(_RE_PROSECUTORIAL.search(text or ""))


def _lower_blob(parts: list[str]) -> str:
    return "\n\n".join(str(p or "").strip() for p in parts if str(p or "").strip()).lower()


def schoolyard_incident_present(text: str) -> bool:
    low = (text or "").lower()
    yard = any(
        k in low
        for k in (
            "schoolyard",
            "playground",
            "park",
            "basketball",
            "court",
            "schulhof",
            "spielplatz",
            "park",
            "basketball",
            "hof",
            "yard",
            "cour",
        )
    )
    boys = any(
        k in low
        for k in ("two boys", "zwei jungen", "jungen", "their children", "kinder", "sohn", "boys")
    )
    stick = any(k in low for k in ("stick", "stock", "branch", "ast", "schläger"))
    inj = any(k in low for k in ("injur", "verletz", "blut", "blood", "wunde", "hurt", "biss"))
    return yard and (boys or stick or inj)


def civilized_procedure_present(text: str) -> bool:
    low = (text or "").lower()
    civ = any(
        k in low
        for k in (
            "civil",
            "zivil",
            " höflich",
            "höflich",
            "procedure",
            "verfahren",
            "appointment",
            "termin",
            "eltern",
            "parents",
            "agreed",
            "vereinbart",
        )
    )
    return civ


def ritual_civility_objects_present(text: str) -> bool:
    low = (text or "").lower()
    paris_room = any(k in low for k in ("paris", "salon", "apartment", "wohnung", "wohnzimmer", "living room", "vallon"))
    objects = sum(
        1
        for k in (
            "tulip",
            "tulpen",
            "espresso",
            "coffee",
            "kaffee",
            "dessert",
            "coat",
            "mantel",
            "paper",
            "papiere",
            "book",
            "buch",
            "culture",
            "kultur",
        )
        if k in low
    )
    return paris_room and objects >= 2


def selected_role_anchor_present(
    anchor_beat: str,
    *,
    human_actor_id: str | None,
    selected_player_role: str | None,
) -> bool:
    low = (anchor_beat or "").lower()
    anchor_phrase = ("du bist" in low) or ("you are" in low)
    if _is_annette(human_actor_id=human_actor_id, selected_player_role=selected_player_role):
        return anchor_phrase and ("annette" in low) and ("gast" in low or "guest" in low)
    if _is_alain(human_actor_id=human_actor_id, selected_player_role=selected_player_role):
        return anchor_phrase and ("alain" in low) and ("gast" in low or "guest" in low)
    return anchor_phrase


def opening_part_1_premise_present(b1: str) -> bool:
    return schoolyard_incident_present(b1) and civilized_procedure_present(b1)


def opening_part_2_room_present(b2: str) -> bool:
    return ritual_civility_objects_present(b2)


def ritual_civility_present(*, room_beat: str, first_actor: str | None) -> bool:
    low_actor = (first_actor or "").lower()
    polite = any(
        k in low_actor
        for k in (
            "please",
            "bitte",
            "sit",
            "setzen",
            "coffee",
            "kaffee",
            "welcome",
            "willkommen",
            "thank",
            "danke",
            "cup",
            "tasse",
            "offer",
            "pour",
            "nick",  # höfliches Nicken / nod
            "nod",
            "civil",  # "keep this civil" / höfliche Formel
            "höflich",
            "entschuldig",  # apology formula
            "sorry",
        )
    )
    return (
        opening_part_2_room_present(room_beat)
        and polite
        and not prosecutorial_opening_detected(first_actor or "")
    )


def swap_beats_toward_canonical_order(beats: list[str]) -> list[str]:
    """Light reorder so premise/room/anchor land in 0/1/2 when the model permuted beats."""
    if len(beats) < 3:
        return beats
    b = [beats[0], beats[1], beats[2]]

    def _anchor_score(t: str) -> int:
        low = t.lower()
        s = 0
        if "du bist" in low or "you are" in low:
            s += 5
        if "guest" in low or "gast" in low:
            s += 2
        if "spectator" in low or "zuschau" in low:
            s += 1
        return s

    def _premise_score(t: str) -> int:
        low = t.lower()
        s = 0
        for k in ("school", "yard", "playground", "schulhof", "spielplatz", "stick", "stock", "injur", "verletz", "boys", "jungen"):
            if k in low:
                s += 1
        return s

    def _room_score(t: str) -> int:
        low = t.lower()
        s = 0
        for k in ("paris", "salon", "apartment", "tulip", "espresso", "coffee", "dessert", "mantel", "coat", "buch", "book"):
            if k in low:
                s += 1
        return s

    scores = [(i, _premise_score(b[i]), _room_score(b[i]), _anchor_score(b[i])) for i in range(3)]
    anchor_i = max(scores, key=lambda x: x[3])[0]
    premise_i = max(scores, key=lambda x: x[1])[0]
    room_i = max(scores, key=lambda x: x[2])[0]
    if len({anchor_i, premise_i, room_i}) == 3:
        return [b[premise_i], b[room_i], b[anchor_i]]
    return b


def enforce_opening_handover_on_beats(
    beats: list[str],
    *,
    output_language: str | None,
    human_actor_id: str | None,
    selected_player_role: str | None,
) -> tuple[list[str], dict[str, Any]]:
    """Ensure three narrator beats satisfy dramaturgy slots; replace weak beats with YAML-backed templates."""
    if len(beats) < 3:
        return beats, {"opening_handover_applied": False}
    out = swap_beats_toward_canonical_order([sanitize_gm_narration_beat_line(x) for x in beats[:3]])
    filled: list[str] = []
    reasons: list[str] = []
    p1 = out[0]
    if not opening_part_1_premise_present(p1):
        p1 = deterministic_part1_premise(output_language=output_language)
        filled.append("part_1_template")
        reasons.append("part_1_premise_weak")
    p2 = out[1]
    if not opening_part_2_room_present(p2):
        p2 = deterministic_part2_room(output_language=output_language)
        filled.append("part_2_template")
        reasons.append("part_2_room_weak")
    p3 = out[2]
    if not selected_role_anchor_present(
        p3, human_actor_id=human_actor_id, selected_player_role=selected_player_role
    ):
        p3 = deterministic_role_anchor_beat(
            output_language=output_language,
            human_actor_id=human_actor_id,
            selected_player_role=selected_player_role,
        )
        filled.append("role_anchor_template")
        reasons.append("role_anchor_weak")
    final = [
        sanitize_gm_narration_beat_line(p1),
        sanitize_gm_narration_beat_line(p2),
        sanitize_gm_narration_beat_line(p3),
    ]
    meta = {
        "opening_handover_applied": True,
        "opening_handover_version": OPENING_HANDOVER_VERSION,
        "opening_handover_slots_filled": filled,
        "opening_handover_swap_reasons": reasons,
    }
    return final, meta


def diagnose_opening_handover(
    narrator_beats: list[str],
    first_actor_text: str | None,
    *,
    human_actor_id: str | None,
    selected_player_role: str | None,
) -> dict[str, Any]:
    b = narrator_beats[:3] if narrator_beats else ["", "", ""]
    while len(b) < 3:
        b.append("")
    nb = _lower_blob(b)
    actor = first_actor_text or ""
    full = nb + "\n\n" + actor.lower()
    gen = generic_conflict_resolution_detected(full)
    proc = prosecutorial_opening_detected(actor)
    reacts = "reacts immediately" in full
    p1 = opening_part_1_premise_present(b[0])
    p2 = opening_part_2_room_present(b[1])
    sch = schoolyard_incident_present(b[0])
    civ = civilized_procedure_present(b[0])
    ritual = ritual_civility_present(room_beat=b[1], first_actor=actor)
    anchor = selected_role_anchor_present(
        b[2], human_actor_id=human_actor_id, selected_player_role=selected_player_role
    )
    failure_reasons: list[str] = []
    if not p1:
        failure_reasons.append("opening_part_1_premise_missing")
    if not p2:
        failure_reasons.append("opening_part_2_room_missing")
    if not anchor:
        failure_reasons.append("selected_role_anchor_missing")
    if not sch:
        failure_reasons.append("schoolyard_incident_missing")
    if not civ:
        failure_reasons.append("civilized_procedure_missing")
    if not ritual:
        failure_reasons.append("ritual_civility_missing")
    if gen:
        failure_reasons.append("generic_conflict_resolution_detected")
    if proc:
        failure_reasons.append("prosecutorial_first_actor")
    if reacts:
        failure_reasons.append("reacts_immediately_present")
    contract = (
        p1
        and p2
        and anchor
        and sch
        and civ
        and ritual
        and not gen
        and not proc
        and not reacts
    )
    return {
        "opening_part_1_premise_present": p1,
        "opening_part_2_room_present": p2,
        "schoolyard_incident_present": sch,
        "civilized_procedure_present": civ,
        "ritual_civility_present": ritual,
        "selected_role_anchor_present": anchor,
        "generic_conflict_resolution_detected": gen,
        "prosecutorial_first_actor": proc,
        "reacts_immediately_in_opening": reacts,
        "opening_handover_contract_pass": contract,
        "opening_handover_failure_reasons": failure_reasons,
    }


def polish_first_opening_actor_block(
    blocks: list[dict[str, Any]],
    *,
    output_language: str | None,
) -> tuple[list[dict[str, Any]], bool]:
    """Replace prosecutorial or generic-meeting first NPC line with polite ritual (turn 0)."""
    if len(blocks) < 4:
        return blocks, False

    def _bt(bb: dict[str, Any]) -> str:
        return str(bb.get("block_type") or bb.get("type") or "").strip().lower()

    idx = next((i for i, bb in enumerate(blocks) if _bt(bb) in {"actor_line", "actor_action"}), None)
    if idx is None or idx < 3:
        return blocks, False
    bb = blocks[idx]
    text = str(bb.get("text") or "").strip()
    aid = str(bb.get("actor_id") or "").strip() or None
    if not text:
        return blocks, False
    if (
        prosecutorial_opening_detected(text)
        or generic_conflict_resolution_detected(text)
        or "reacts immediately" in text.lower()
    ):
        out = list(blocks)
        nb = dict(bb)
        nb["text"] = polite_ritual_first_actor_line(output_language=output_language, actor_id=aid)
        _src = str(nb.get("source") or "live_runtime_graph").strip()
        nb["source"] = f"{_src}_opening_handover_polish"
        out[idx] = nb
        return out, True
    return blocks, False


def compute_opening_handover_from_scene_blocks(
    blocks: list[dict[str, Any]],
    *,
    human_actor_id: str | None,
    selected_player_role: str | None,
) -> dict[str, Any]:
    def _bt(bb: dict[str, Any]) -> str:
        return str(bb.get("block_type") or bb.get("type") or "").strip().lower()

    narr: list[str] = []
    first_actor: str | None = None
    for bb in blocks:
        if not isinstance(bb, dict):
            continue
        if _bt(bb) == "narrator" and len(narr) < 3:
            t = str(bb.get("text") or "").strip()
            if t:
                narr.append(t)
        elif _bt(bb) in {"actor_line", "actor_action"} and first_actor is None:
            first_actor = str(bb.get("text") or "").strip()
            break
    while len(narr) < 3:
        narr.append("")
    return diagnose_opening_handover(
        narr,
        first_actor,
        human_actor_id=human_actor_id,
        selected_player_role=selected_player_role,
    )
