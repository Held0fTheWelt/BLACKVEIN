"""Projection section builder for `social_pressure`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_SOCIAL_PRESSURE_SECTION_PARAMS = ('social_pressure_actual', 'social_pressure_expected', 'social_pressure_rec', 'social_pressure_selected')


def build_social_pressure_section(**values: Any) -> dict[str, Any]:
    social_pressure_actual = values['social_pressure_actual']
    social_pressure_expected = values['social_pressure_expected']
    social_pressure_rec = values['social_pressure_rec']
    social_pressure_selected = values['social_pressure_selected']
    return {
                    "schema_version": social_pressure_expected.get("schema_version")
                    or social_pressure_selected.get("schema_version")
                    or social_pressure_actual.get("schema_version"),
                    "policy_present": bool(social_pressure_expected.get("policy_present")),
                    "policy_enabled": bool(social_pressure_expected.get("policy_enabled")),
                    "target_score": float(
                        social_pressure_selected.get("target_score")
                        or (
                            social_pressure_selected.get("target", {}).get("target_score")
                            if isinstance(social_pressure_selected.get("target"), dict)
                            else 0.0
                        )
                        or 0.0
                    ),
                    "target_band": social_pressure_selected.get("target_band")
                    or (
                        social_pressure_selected.get("target", {}).get("target_band")
                        if isinstance(social_pressure_selected.get("target"), dict)
                        else None
                    ),
                    "trend": social_pressure_selected.get("trend")
                    or (
                        social_pressure_selected.get("target", {}).get("trend")
                        if isinstance(social_pressure_selected.get("target"), dict)
                        else None
                    )
                    or social_pressure_actual.get("trend"),
                    "current_score": float(social_pressure_actual.get("current_score") or 0.0),
                    "current_band": social_pressure_actual.get("current_band"),
                    "velocity": float(social_pressure_actual.get("velocity") or 0.0),
                    "requires_visible_pressure": bool(
                        social_pressure_selected.get("requires_visible_pressure")
                        or (
                            social_pressure_selected.get("target", {}).get("requires_visible_pressure")
                            if isinstance(social_pressure_selected.get("target"), dict)
                            else False
                        )
                    ),
                    "contract_pass": social_pressure_actual.get("contract_pass"),
                    "failure_codes": social_pressure_actual.get("failure_codes")
                    or _record_reasons(social_pressure_rec),
                    "failure_reason": social_pressure_rec.get("failure_reason")
                    or (
                        _record_reasons(social_pressure_rec)[0]
                        if _record_reasons(social_pressure_rec)
                        else None
                    ),
                    "status": social_pressure_rec.get("status"),
                }

