"""Turn-0 opening narration: normalize model output into three GM strings for projection.

Returns ``(beats, meta)`` where ``beats`` is ``None`` when this normalizer does not apply.
``None`` must not be interpreted as an empty narration list.
"""

from __future__ import annotations

import json
import re
from typing import Any

GOD_OF_CARNAGE_MODULE_ID = "god_of_carnage"


def narration_summary_to_plain_str(value: Any) -> str:
    """Flatten ``narration_summary`` for legacy string-only consumers (effects, gates)."""
    if isinstance(value, list):
        return "\n\n".join(str(x).strip() for x in value if str(x).strip()).strip()
    return str(value or "").strip()

_DIAGNOSTIC_MARKERS = (
    "system_degraded",
    "diagnostics_only",
    "preview staging",
    "preview staging —",
    "[mock]",
)


def _is_diagnostic_narration(text: str) -> bool:
    low = text.lower().strip()
    if not low:
        return True
    return any(m in low for m in _DIAGNOSTIC_MARKERS)


def _actor_lane_substance(existing_actor_lines: list[Any] | None) -> bool:
    if not isinstance(existing_actor_lines, list):
        return False
    for row in existing_actor_lines:
        if isinstance(row, dict) and str(row.get("text") or row.get("line") or "").strip():
            return True
    return False


def _role_display_name(*, human_actor_id: str | None, selected_player_role: str | None) -> str:
    raw = str(human_actor_id or selected_player_role or "").strip()
    if not raw:
        return "the player character"
    if "_" in raw:
        parts = [p for p in raw.split("_") if p]
        return " ".join(p[:1].upper() + p[1:] for p in parts if p)
    return raw[:1].upper() + raw[1:] if raw else "the player character"


def _is_annette(*, human_actor_id: str | None, selected_player_role: str | None) -> bool:
    blob = f"{human_actor_id or ''} {selected_player_role or ''}".lower()
    return "annette" in blob


def _is_alain(*, human_actor_id: str | None, selected_player_role: str | None) -> bool:
    blob = f"{human_actor_id or ''} {selected_player_role or ''}".lower()
    return "alain" in blob


def _deterministic_role_anchor(
    *,
    role_display: str,
    output_language: str | None,
    human_actor_id: str | None,
    selected_player_role: str | None,
) -> str:
    lang = (output_language or "de").strip().lower()
    if lang == "de":
        if _is_annette(human_actor_id=human_actor_id, selected_player_role=selected_player_role):
            return (
                f"Du bist {role_display}, die mit Alain in einen Raum kommt, "
                "in dem sich Höflichkeit bereits zu Vorwürfen verhärtet."
            )
        if _is_alain(human_actor_id=human_actor_id, selected_player_role=selected_player_role):
            return (
                f"Du bist {role_display}, in der Vallon-Wohnung anwesend — nicht als Zuschauer, "
                "sondern als einer der Eltern, deren Fassung schon Teil der Szene ist."
            )
        return (
            f"Du bist {role_display}, in diesem Moment Teil der Elternrunde — "
            "nicht außerhalb dessen, was im Raum zwischen den Paaren steht."
        )
    if _is_annette(human_actor_id=human_actor_id, selected_player_role=selected_player_role):
        return (
            f"You are {role_display}, arriving with Alain into a room where courtesy "
            "is already beginning to harden into accusation."
        )
    if _is_alain(human_actor_id=human_actor_id, selected_player_role=selected_player_role):
        return (
            f"You are {role_display}, present in the Vallon apartment not as a spectator "
            "but as one of the parents whose composure is already part of the scene."
        )
    return (
        f"You are {role_display}, present in the room as one of the adults whose "
        "composure is already part of the scene — not detached from what is at stake."
    )


def _deterministic_scene_setup(*, output_language: str | None) -> str:
    lang = (output_language or "de").strip().lower()
    if lang == "de":
        return (
            "Der Pariser Salon: Stühle einander zugewandt, kalte Tassen, "
            "gesellschaftliche Spannung direkt unter der höflichen Oberfläche."
        )
    return (
        "The Paris salon: chairs facing each other, cooling cups, social pressure "
        "just under the polite surface."
    )


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n+", (text or "").strip())
    return [p.strip() for p in parts if p and str(p).strip()]


def _coerce_narration_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        if s.startswith("["):
            try:
                parsed = json.loads(s)
            except (json.JSONDecodeError, ValueError, TypeError):
                parsed = None
            if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                return [x.strip() for x in parsed if str(x).strip()]
        return [s]
    if isinstance(value, list):
        out: list[str] = []
        for x in value:
            if isinstance(x, str) and x.strip():
                out.append(x.strip())
        return out
    return None


def normalize_opening_narration_beats(
    narration_summary: Any,
    *,
    selected_player_role: str | None,
    human_actor_id: str | None,
    module_id: str,
    turn_number: int,
    output_language: str | None = None,
    existing_actor_lines: list[Any] | None = None,
) -> tuple[list[str] | None, dict[str, Any] | None]:
    """Return ``(beats, meta)`` or ``(None, None)`` when normalization does not apply."""
    if turn_number != 0 or str(module_id or "").strip() != GOD_OF_CARNAGE_MODULE_ID:
        return None, None

    coerced = _coerce_narration_list(narration_summary)
    if coerced is None:
        return None, None

    input_was_single_string = isinstance(narration_summary, str) and bool(
        str(narration_summary).strip()
    )
    input_was_list = isinstance(narration_summary, list)

    if not coerced:
        return None, None

    role_display = _role_display_name(
        human_actor_id=human_actor_id,
        selected_player_role=selected_player_role,
    )

    if len(coerced) >= 3:
        beats = coerced[:3]
        meta = {
            "opening_narration_normalized": True,
            "opening_narration_source": "model_list_three_plus",
            "opening_narration_beat_count": len(beats),
            "narration_summary_input_kind": "list" if input_was_list else "string",
        }
        return beats, meta

    if len(coerced) == 1:
        first = coerced[0]
        if _is_diagnostic_narration(first):
            return None, None
        paras = _split_paragraphs(first)
        if len(paras) >= 3:
            beats = paras[:3]
            meta = {
                "opening_narration_normalized": True,
                "opening_narration_source": "single_string_split_paragraphs",
                "opening_narration_beat_count": len(beats),
                "narration_summary_input_kind": "single_string",
            }
            return beats, meta
        if not first.strip():
            return None, None
        if not _actor_lane_substance(existing_actor_lines):
            return None, None
        beats = [
            first.strip(),
            _deterministic_role_anchor(
                role_display=role_display,
                output_language=output_language,
                human_actor_id=human_actor_id,
                selected_player_role=selected_player_role,
            ),
            _deterministic_scene_setup(output_language=output_language),
        ]
        meta = {
            "opening_narration_normalized": True,
            "opening_narration_source": "single_string_plus_deterministic_anchors",
            "opening_narration_beat_count": len(beats),
            "narration_summary_input_kind": "single_string",
        }
        return beats, meta

    if len(coerced) == 2:
        merged = "\n\n".join(c.strip() for c in coerced if c.strip())
        if _is_diagnostic_narration(merged):
            return None, None
        paras = _split_paragraphs(merged)
        if len(paras) >= 3:
            beats = paras[:3]
            meta = {
                "opening_narration_normalized": True,
                "opening_narration_source": "two_entries_split_paragraphs",
                "opening_narration_beat_count": len(beats),
                "narration_summary_input_kind": "list",
            }
            return beats, meta
        if not _actor_lane_substance(existing_actor_lines):
            return None, None
        a, b = coerced[0].strip(), coerced[1].strip()
        beats = [
            a,
            b,
            _deterministic_scene_setup(output_language=output_language),
        ]
        meta = {
            "opening_narration_normalized": True,
            "opening_narration_source": "two_strings_plus_scene_setup",
            "opening_narration_beat_count": 3,
            "narration_summary_input_kind": "list",
        }
        return beats, meta

    return None, None
