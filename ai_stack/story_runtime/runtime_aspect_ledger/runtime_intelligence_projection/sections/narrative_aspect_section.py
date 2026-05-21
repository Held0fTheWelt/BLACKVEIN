"""Projection section builder for `narrative_aspect`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_NARRATIVE_ASPECT_SECTION_PARAMS = ('narrative_actual', 'narrative_expected', 'narrative_rec', 'narrative_selected')


def build_narrative_aspect_section(**values: Any) -> dict[str, Any]:
    narrative_actual = values['narrative_actual']
    narrative_expected = values['narrative_expected']
    narrative_rec = values['narrative_rec']
    narrative_selected = values['narrative_selected']
    return {
                    "policy_present": bool(narrative_expected.get("policy_present")),
                    "candidate_aspects": narrative_expected.get("candidate_aspects") or [],
                    "semantic_tracking_enabled": bool(narrative_expected.get("semantic_tracking_enabled")),
                    "semantic_profile_aspects": narrative_expected.get("semantic_profile_aspects") or [],
                    "selected_aspects": narrative_selected.get("selected_aspects") or [],
                    "selected_theme_aspects": narrative_selected.get("selected_theme_aspects") or narrative_actual.get("selected_theme_aspects") or [],
                    "selection_source": narrative_selected.get("selection_source"),
                    "realized_aspects": narrative_actual.get("realized_aspects") or [],
                    "realized_theme_aspects": narrative_actual.get("realized_theme_aspects") or [],
                    "missing_required_evidence": narrative_actual.get("missing_required_evidence") or [],
                    "evidence": narrative_actual.get("evidence") or [],
                    "visible_when_required": narrative_actual.get("visible_when_required"),
                    "semantic_classification_count": int(narrative_actual.get("semantic_classification_count") or 0),
                    "semantic_weak_alignment_count": int(narrative_actual.get("semantic_weak_alignment_count") or 0),
                    "semantic_required_weak_alignment_count": int(narrative_actual.get("semantic_required_weak_alignment_count") or 0),
                    "semantic_classifications": narrative_actual.get("semantic_classifications") or [],
                    "failure_reason": narrative_rec.get("failure_reason")
                    or (_record_reasons(narrative_rec)[0] if _record_reasons(narrative_rec) else None),
                    "status": narrative_rec.get("status"),
                }

