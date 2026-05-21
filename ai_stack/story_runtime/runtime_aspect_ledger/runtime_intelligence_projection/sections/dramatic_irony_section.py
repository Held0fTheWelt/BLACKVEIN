"""Projection section builder for `dramatic_irony`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_DRAMATIC_IRONY_SECTION_PARAMS = ('dramatic_irony_actual', 'dramatic_irony_expected', 'dramatic_irony_rec', 'dramatic_irony_selected')


def build_dramatic_irony_section(**values: Any) -> dict[str, Any]:
    dramatic_irony_actual = values['dramatic_irony_actual']
    dramatic_irony_expected = values['dramatic_irony_expected']
    dramatic_irony_rec = values['dramatic_irony_rec']
    dramatic_irony_selected = values['dramatic_irony_selected']
    return {
                    "schema_version": dramatic_irony_expected.get("schema_version"),
                    "policy_present": bool(dramatic_irony_expected.get("policy_present")),
                    "policy_enabled": bool(dramatic_irony_expected.get("policy_enabled")),
                    "allowed_sources": dramatic_irony_expected.get("allowed_sources") or [],
                    "allowed_surface_modes": dramatic_irony_expected.get("allowed_surface_modes") or [],
                    "direct_reveal_allowed": bool(
                        dramatic_irony_expected.get("direct_reveal_allowed")
                    ),
                    "selected_opportunity_ids": dramatic_irony_selected.get("selected_opportunity_ids")
                    or [],
                    "selected_fact_ids": dramatic_irony_selected.get("selected_fact_ids") or [],
                    "fact_count": int(dramatic_irony_actual.get("fact_count") or 0),
                    "opportunity_count": int(dramatic_irony_actual.get("opportunity_count") or 0),
                    "selected_opportunity_count": int(
                        dramatic_irony_actual.get("selected_opportunity_count") or 0
                    ),
                    "realization_status": dramatic_irony_actual.get("realization_status"),
                    "realized_opportunity_ids": dramatic_irony_actual.get("realized_opportunity_ids")
                    or [],
                    "leak_blocked": bool(dramatic_irony_actual.get("leak_blocked")),
                    "violation_codes": dramatic_irony_actual.get("violation_codes") or [],
                    "contract_pass": dramatic_irony_actual.get("contract_pass"),
                    "failure_reason": dramatic_irony_rec.get("failure_reason")
                    or (
                        _record_reasons(dramatic_irony_rec)[0]
                        if _record_reasons(dramatic_irony_rec)
                        else None
                    ),
                    "status": dramatic_irony_rec.get("status"),
                }

