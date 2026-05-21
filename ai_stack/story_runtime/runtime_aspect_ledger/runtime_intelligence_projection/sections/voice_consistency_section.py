"""Projection section builder for `voice_consistency`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_VOICE_CONSISTENCY_SECTION_PARAMS = ('voice_actual', 'voice_expected', 'voice_rec')


def build_voice_consistency_section(**values: Any) -> dict[str, Any]:
    """Return the voice consistency diagnostic section from normalized ledger records."""
    voice_actual = values['voice_actual']
    voice_expected = values['voice_expected']
    voice_rec = values['voice_rec']
    return {
                    "policy_present": bool(voice_expected.get("policy_present")),
                    "semantic_classification_enabled": bool(
                        voice_expected.get("semantic_classification_enabled")
                    ),
                    "profiles_checked": int(voice_actual.get("profiles_checked") or 0),
                    "spoken_line_count": int(voice_actual.get("spoken_line_count") or 0),
                    "finding_count": int(voice_actual.get("finding_count") or 0),
                    "blocking_finding_count": int(voice_actual.get("blocking_finding_count") or 0),
                    "semantic_classification_count": int(
                        voice_actual.get("semantic_classification_count") or 0
                    ),
                    "semantic_cross_actor_confusion_count": int(
                        voice_actual.get("semantic_cross_actor_confusion_count") or 0
                    ),
                    "semantic_mixed_signature_count": int(
                        voice_actual.get("semantic_mixed_signature_count") or 0
                    ),
                    "semantic_ambiguous_signature_count": int(
                        voice_actual.get("semantic_ambiguous_signature_count") or 0
                    ),
                    "semantic_weak_alignment_count": int(
                        voice_actual.get("semantic_weak_alignment_count") or 0
                    ),
                    "semantic_classifications": voice_actual.get("semantic_classifications")
                    or [],
                    "failure_reason": voice_rec.get("failure_reason")
                    or (_record_reasons(voice_rec)[0] if _record_reasons(voice_rec) else None),
                    "status": voice_rec.get("status"),
                }

