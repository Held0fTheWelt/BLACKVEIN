"""Projection section builder for `tonal_consistency`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_TONAL_CONSISTENCY_SECTION_PARAMS = ('tonal_actual', 'tonal_expected', 'tonal_rec', 'tonal_selected')


def build_tonal_consistency_section(**values: Any) -> dict[str, Any]:
    """Return the tonal consistency diagnostic section from normalized ledger records."""
    tonal_actual = values['tonal_actual']
    tonal_expected = values['tonal_expected']
    tonal_rec = values['tonal_rec']
    tonal_selected = values['tonal_selected']
    return {
                    "schema_version": tonal_expected.get("schema_version")
                    or tonal_selected.get("schema_version")
                    or tonal_actual.get("schema_version"),
                    "policy_present": bool(tonal_expected.get("policy_present")),
                    "policy_enabled": bool(tonal_expected.get("policy_enabled")),
                    "live_loop_mode": tonal_expected.get("live_loop_mode"),
                    "classification_source": tonal_expected.get("classification_source")
                    or tonal_actual.get("classification_source"),
                    "profile_id": tonal_selected.get("profile_id")
                    or _record_nested_value(tonal_selected, "profile_id", "target"),
                    "target_dimension_ids": tonal_selected.get("target_dimension_ids")
                    or (
                        tonal_selected.get("target", {}).get("target_dimension_ids")
                        if isinstance(tonal_selected.get("target"), dict)
                        else []
                    )
                    or [],
                    "required_dimension_ids": tonal_selected.get("required_dimension_ids")
                    or (
                        tonal_selected.get("target", {}).get("required_dimension_ids")
                        if isinstance(tonal_selected.get("target"), dict)
                        else []
                    )
                    or [],
                    "realized_dimension_ids": tonal_actual.get("realized_dimension_ids") or [],
                    "missing_required_dimension_ids": tonal_actual.get("missing_required_dimension_ids")
                    or [],
                    "required_dimension_present_count": int(
                        tonal_actual.get("required_dimension_present_count") or 0
                    ),
                    "register_label": tonal_actual.get("register_label"),
                    "genre_label": tonal_actual.get("genre_label"),
                    "dimension_marker_classes": tonal_selected.get("dimension_marker_classes")
                    or [],
                    "forbidden_marker_classes": tonal_selected.get("forbidden_marker_classes")
                    or [],
                    "forbidden_marker_hits": tonal_actual.get("forbidden_marker_hits") or {},
                    "marker_hit_count": int(tonal_actual.get("marker_hit_count") or 0),
                    "structured_classification_present": bool(
                        tonal_actual.get("structured_classification_present")
                    ),
                    "independent_classifier": tonal_actual.get("independent_classifier"),
                    "contract_pass": tonal_actual.get("contract_pass"),
                    "failure_codes": tonal_actual.get("failure_codes")
                    or _record_reasons(tonal_rec),
                    "failure_reason": tonal_rec.get("failure_reason")
                    or (_record_reasons(tonal_rec)[0] if _record_reasons(tonal_rec) else None),
                    "status": tonal_rec.get("status"),
                }

