"""Projection section builder for `beat`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_BEAT_SECTION_PARAMS = ('beat_actual', 'beat_expected', 'beat_rec', 'beat_selected', 'selected_beat_id')


def build_beat_section(**values: Any) -> dict[str, Any]:
    """Return the beat diagnostic section from normalized ledger records."""
    beat_actual = values['beat_actual']
    beat_expected = values['beat_expected']
    beat_rec = values['beat_rec']
    beat_selected = values['beat_selected']
    selected_beat_id = values['selected_beat_id']
    return {
                    "beat_state_before": beat_expected.get("beat_state_before") or {},
                    "candidate_beats": beat_expected.get("candidate_beats") or [],
                    "selected_beat": {"id": selected_beat_id} if selected_beat_id else {},
                    "selection_source": beat_selected.get("selection_source")
                    or beat_rec.get("source")
                    or None,
                    "selection_reason": beat_selected.get("selection_reason"),
                    "expected_visible_functions": beat_expected.get("expected_realization")
                    or beat_expected.get("expected_visible_functions")
                    or [],
                    "realized": beat_actual.get("realized"),
                    "realization_evidence": beat_actual.get("realization_evidence") or [],
                    "failure_reason": beat_rec.get("failure_reason")
                    or (_record_reasons(beat_rec)[0] if _record_reasons(beat_rec) else None),
                    "beat_state_after": beat_actual.get("beat_state_after") or {},
                    "status": beat_rec.get("status"),
                }

