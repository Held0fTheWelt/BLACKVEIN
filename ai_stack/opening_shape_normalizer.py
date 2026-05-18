"""Turn-0 opening narration: normalize model output into GM strings for projection.

Returns ``(beats, meta)`` where ``beats`` is ``None`` when this normalizer does not apply.
``None`` must not be interpreted as an empty narration list.

The normalizer may reorder and validate model-provided beats, but it must not
invent missing opening prose. If the model did not provide enough usable opening
material, callers should surface an explicit fallback instead.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ai_stack.goc_opening_transition import (
    enforce_opening_transition_on_beats,
)
from ai_stack.visible_narrative_contract import sanitize_gm_narration_beat_line

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

    if len(coerced) >= 3:
        beats = [sanitize_gm_narration_beat_line(b) for b in coerced]
        beats, transition_meta = enforce_opening_transition_on_beats(
            beats,
            output_language=output_language,
            human_actor_id=human_actor_id,
            selected_player_role=selected_player_role,
        )
        meta = {
            "opening_narration_normalized": True,
            "opening_narration_source": "model_list_three_plus",
            "opening_narration_beat_count": len(beats),
            "opening_narration_extra_beats_preserved": max(0, len(beats) - 3),
            "narration_summary_input_kind": "list" if input_was_list else "string",
            **transition_meta,
        }
        return beats, meta

    if len(coerced) == 1:
        first = coerced[0]
        if _is_diagnostic_narration(first):
            return None, None
        paras = _split_paragraphs(first)
        if len(paras) >= 3:
            beats = [sanitize_gm_narration_beat_line(b) for b in paras[:3]]
            beats, transition_meta = enforce_opening_transition_on_beats(
                beats,
                output_language=output_language,
                human_actor_id=human_actor_id,
                selected_player_role=selected_player_role,
            )
            meta = {
                "opening_narration_normalized": True,
                "opening_narration_source": "single_string_split_paragraphs",
                "opening_narration_beat_count": len(beats),
                "narration_summary_input_kind": "single_string",
                **transition_meta,
            }
            return beats, meta
        if not first.strip():
            return None, None
        return None, None

    if len(coerced) == 2:
        merged = "\n\n".join(c.strip() for c in coerced if c.strip())
        if _is_diagnostic_narration(merged):
            return None, None
        paras = _split_paragraphs(merged)
        if len(paras) >= 3:
            beats = [sanitize_gm_narration_beat_line(b) for b in paras[:3]]
            beats, transition_meta = enforce_opening_transition_on_beats(
                beats,
                output_language=output_language,
                human_actor_id=human_actor_id,
                selected_player_role=selected_player_role,
            )
            meta = {
                "opening_narration_normalized": True,
                "opening_narration_source": "two_entries_split_paragraphs",
                "opening_narration_beat_count": len(beats),
                "narration_summary_input_kind": "list",
                **transition_meta,
            }
            return beats, meta
        return None, None

    return None, None
