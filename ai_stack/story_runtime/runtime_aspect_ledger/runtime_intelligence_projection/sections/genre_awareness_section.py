"""Projection section builder for `genre_awareness`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_GENRE_AWARENESS_SECTION_PARAMS = ('genre_awareness_actual', 'genre_awareness_expected', 'genre_awareness_rec', 'genre_awareness_selected')


def build_genre_awareness_section(**values: Any) -> dict[str, Any]:
    genre_awareness_actual = values['genre_awareness_actual']
    genre_awareness_expected = values['genre_awareness_expected']
    genre_awareness_rec = values['genre_awareness_rec']
    genre_awareness_selected = values['genre_awareness_selected']
    return {
                    "schema_version": genre_awareness_expected.get("schema_version")
                    or genre_awareness_selected.get("schema_version")
                    or genre_awareness_actual.get("schema_version"),
                    "policy_present": bool(genre_awareness_expected.get("policy_present")),
                    "policy_enabled": bool(genre_awareness_expected.get("policy_enabled")),
                    "commit_impact": genre_awareness_expected.get("commit_impact"),
                    "require_structured_events": bool(
                        genre_awareness_expected.get("require_structured_events")
                    ),
                    "genre_profile_id": genre_awareness_selected.get("genre_profile_id")
                    or _record_nested_value(genre_awareness_selected, "genre_profile_id", "target"),
                    "selected_registers": genre_awareness_selected.get("selected_registers")
                    or (
                        genre_awareness_selected.get("target", {}).get("selected_registers")
                        if isinstance(genre_awareness_selected.get("target"), dict)
                        else []
                    )
                    or [],
                    "required_conventions": genre_awareness_selected.get("required_conventions")
                    or (
                        genre_awareness_selected.get("target", {}).get("required_conventions")
                        if isinstance(genre_awareness_selected.get("target"), dict)
                        else []
                    )
                    or [],
                    "forbidden_marker_ids": genre_awareness_selected.get("forbidden_marker_ids")
                    or (
                        genre_awareness_selected.get("target", {}).get("forbidden_marker_ids")
                        if isinstance(genre_awareness_selected.get("target"), dict)
                        else []
                    )
                    or [],
                    "max_genre_signals_per_turn": int(
                        genre_awareness_expected.get("max_genre_signals_per_turn")
                        or (
                            genre_awareness_selected.get("target", {}).get("max_genre_signals_per_turn")
                            if isinstance(genre_awareness_selected.get("target"), dict)
                            else 0
                        )
                        or 0
                    ),
                    "structured_events_present": bool(
                        genre_awareness_actual.get("structured_events_present")
                    ),
                    "event_count": int(genre_awareness_actual.get("event_count") or 0),
                    "realized_profile_ids": genre_awareness_actual.get("realized_profile_ids")
                    or [],
                    "realized_registers": genre_awareness_actual.get("realized_registers") or [],
                    "realized_conventions": genre_awareness_actual.get("realized_conventions")
                    or [],
                    "missing_required_conventions": genre_awareness_actual.get(
                        "missing_required_conventions"
                    )
                    or [],
                    "contract_pass": genre_awareness_actual.get("contract_pass"),
                    "failure_codes": genre_awareness_actual.get("failure_codes")
                    or _record_reasons(genre_awareness_rec),
                    "failure_reason": genre_awareness_rec.get("failure_reason")
                    or (
                        _record_reasons(genre_awareness_rec)[0]
                        if _record_reasons(genre_awareness_rec)
                        else None
                    ),
                    "status": genre_awareness_rec.get("status"),
                }

