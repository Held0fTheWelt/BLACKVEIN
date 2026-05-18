"""Narrator-path realization for the God of Carnage canonical opening.

This module is intentionally a renderer, not a second content database. It
loads the numbered canonical path and referenced location/object authority, then
projects the first narrator-only handoff into visible blocks.
"""

from __future__ import annotations

from typing import Any

from ai_stack.goc_yaml_authority import (
    load_goc_canonical_path_yaml,
    load_goc_locations_yaml,
)

NARRATOR_PATH_CONTRACT = "goc_narrator_path.opening.v1"
NARRATOR_PATH_ADAPTER = "goc_narrator_path_direct"
NARRATOR_PATH_INVOCATION_MODE = "narrator_path_direct"


def _indexed_places() -> dict[str, dict[str, Any]]:
    data = load_goc_locations_yaml()
    rows = data.get("places") if isinstance(data, dict) else []
    return {
        str(row.get("id") or "").strip(): row
        for row in (rows if isinstance(rows, list) else [])
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }


def _opening_steps(limit: int = 5) -> list[dict[str, Any]]:
    data = load_goc_canonical_path_yaml()
    steps = data.get("steps") if isinstance(data, dict) else []
    selected: list[dict[str, Any]] = []
    for row in steps if isinstance(steps, list) else []:
        if not isinstance(row, dict):
            continue
        mode = str(row.get("mode") or "").strip()
        if not mode.startswith("narrator_"):
            continue
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def _source_ref_for_step(step: dict[str, Any]) -> str:
    sequence = int(step.get("sequence") or 0)
    step_id = str(step.get("id") or "").strip()
    if sequence > 0 and step_id:
        suffix = step_id.removeprefix(f"opening_{sequence:03d}_")
        return f"canonical_path/{sequence:03d}_{suffix}.yaml"
    return f"canonical_path#{step_id or 'unknown'}"


def _delivery() -> dict[str, Any]:
    return {
        "mode": "typewriter",
        "characters_per_second": 44,
        "pause_before_ms": 150,
        "pause_after_ms": 650,
        "skippable": True,
    }


def _content_refs(step: dict[str, Any]) -> list[str]:
    refs: list[str] = [_source_ref_for_step(step)]
    loc = step.get("location_ref") if isinstance(step.get("location_ref"), dict) else {}
    if loc.get("source"):
        refs.append(str(loc["source"]))
    for key in ("support_refs", "object_refs"):
        rows = step.get(key)
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and row.get("source"):
                    refs.append(str(row["source"]))
    obj = step.get("object_focus_ref") if isinstance(step.get("object_focus_ref"), dict) else {}
    if obj.get("source"):
        refs.append(str(obj["source"]))
    topo = step.get("topology_ref") if isinstance(step.get("topology_ref"), dict) else {}
    if topo.get("source"):
        refs.append(str(topo["source"]))
    seen: set[str] = set()
    return [ref for ref in refs if not (ref in seen or seen.add(ref))]


def _block(
    *,
    index: int,
    text: str,
    beat: str,
    step: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": f"opening-narrator-path-{index}",
        "block_type": "narrator",
        "speaker_label": "Narrator",
        "actor_id": None,
        "target_actor_id": None,
        "text": text.strip(),
        "delivery": _delivery(),
        "source": "narrator_path_canonical_content",
        "narration_beat": beat,
        "canonical_step_id": str(step.get("id") or "").strip(),
        "canonical_step_sequence": int(step.get("sequence") or index),
        "source_refs": _content_refs(step),
    }


def _render_de(steps: list[dict[str, Any]], places: dict[str, dict[str, Any]]) -> list[str]:
    park = places.get("park_edge", {})
    park_name = str(park.get("name") or "Parc Montsouris").replace(" edge", "")
    court_name = "Basketballplatz"
    hallway_name = "dunklen Hausflur"
    living_name = "Wohnzimmer"
    return [
        (
            f"Am Rand des {park_name}, nahe dem {court_name}, stehen etwa ein Dutzend "
            "Jungen unter grauem Himmel. Kahle Bäume, Wege, Verkehr am Boulevard "
            "Jourdan und normales Parkleben bleiben im Hintergrund sichtbar."
        ),
        (
            "Zwei Jungen spielen weiter, während die anderen am Rand aufgeregt "
            "reden. Aus der Bewegung wird Streit: Einer greift nach einem Stock, "
            "der andere ruft ihm etwas hinterher, und die Worte gehen im Lärm des "
            "Platzes unter."
        ),
        (
            "Der Junge mit dem Stock hält an, dreht sich um und schlägt zu. Der "
            "andere krümmt sich; die Umstehenden helfen ihm wieder hoch und rufen "
            "dem Angreifer nach, ohne dass aus der Entfernung ein verlässlicher "
            "Satz entsteht."
        ),
        (
            "Im Weggehen tritt der Junge noch ein Fahrrad um. Dann verschwindet er "
            "aus dem Bild, und der kleine Schaden neben dem Platz bleibt bei der "
            "Verletzung zurück."
        ),
        (
            f"Der nächste Druck liegt im {hallway_name}: andere Wohnungstüren, "
            "schwaches Handynetz, ein Fahrstuhl, der nicht kommt, und Alain, der auf "
            f"einen dringenden Anruf wartet. Von hier führt die Wohnungstür in das "
            f"{living_name}, wo die Höflichkeit den Vorfall aufnehmen soll."
        ),
    ][: max(1, min(len(steps), 5))]


def _render_en(steps: list[dict[str, Any]], places: dict[str, dict[str, Any]]) -> list[str]:
    park = places.get("park_edge", {})
    court = places.get("basketball_court", {})
    hallway = places.get("building_hallway", {})
    living = places.get("living_room", {})
    park_name = str(park.get("name") or "Parc Montsouris").replace(" edge", "")
    court_name = str(court.get("name") or "basketball court")
    hallway_name = str(hallway.get("name") or "dark hallway")
    living_name = str(living.get("name") or "living room")
    return [
        (
            f"At the edge of {park_name}, near the {court_name}, about a dozen boys "
            "stand under a grey sky. Bare trees, paths, traffic on Boulevard "
            "Jourdan, and ordinary park life remain visible in the background."
        ),
        (
            "Two boys keep playing while the others talk excitedly at the edge. The "
            "movement turns into an argument: one boy takes up a stick, the other "
            "calls after him, and the words are lost in the noise of the court."
        ),
        (
            "The boy with the stick stops, turns, and strikes. The other boy bends "
            "over; the boys around him help him back up and shout after the attacker "
            "without forming a reliable sentence from this distance."
        ),
        (
            "As he leaves, the boy kicks over a bicycle. Then he disappears from "
            "view, leaving the small public damage beside the injury."
        ),
        (
            f"The next pressure waits in the {hallway_name}: other apartment doors, "
            "weak phone reception, an elevator that does not arrive, and Alain "
            f"waiting for an urgent call. From here the apartment door leads into "
            f"the {living_name}, where politeness is expected to contain the incident."
        ),
    ][: max(1, min(len(steps), 5))]


def build_goc_narrator_path_opening(*, session_output_language: str = "de") -> dict[str, Any]:
    """Return a narrator-only visible opening grounded in canonical path refs."""
    steps = _opening_steps(limit=5)
    if not steps:
        raise RuntimeError("God of Carnage canonical narrator path has no opening steps.")
    places = _indexed_places()
    lang = str(session_output_language or "de").strip().lower()[:2] or "de"
    texts = _render_en(steps, places) if lang == "en" else _render_de(steps, places)
    beats = [
        "public_edge_establish",
        "argument_to_stick",
        "blow_and_immediate_consequence",
        "bicycle_disappearance",
        "threshold_to_living_room",
    ]
    blocks = [
        _block(index=i + 1, text=text, beat=beats[i], step=steps[i])
        for i, text in enumerate(texts)
    ]
    step_ids = [str(step.get("id") or "").strip() for step in steps if str(step.get("id") or "").strip()]
    source_refs: list[str] = []
    for block in blocks:
        source_refs.extend(str(ref) for ref in block.get("source_refs") or [])
    source_refs = list(dict.fromkeys(source_refs))
    return {
        "contract": NARRATOR_PATH_CONTRACT,
        "path_mode": "narrator_path",
        "adapter": NARRATOR_PATH_ADAPTER,
        "adapter_invocation_mode": NARRATOR_PATH_INVOCATION_MODE,
        "path_id": "goc_opening_canonical_path",
        "canonical_step_ids": step_ids,
        "source_refs": source_refs,
        "scene_blocks": blocks,
        "gm_narration": [str(block["text"]) for block in blocks],
        "director_plan": {
            "contract": "director_narrator_path_plan.v1",
            "path_mode": "narrator_path",
            "speech_allowed": False,
            "npc_agency_required": False,
            "player_action_resolution_required": False,
            "selected_capabilities": ["narrator.opening_event.realize"],
            "skipped_capability_groups": [
                "player_action_resolution",
                "affordance_evaluation",
                "npc_agency",
                "npc_authority",
                "voice_classification",
                "dramatic_irony",
                "branch_forecast",
            ],
            "canonical_step_ids": step_ids,
            "content_source_refs": source_refs,
        },
    }
