"""Projection section builder for `broad_nlu_listening`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_BROAD_NLU_LISTENING_SECTION_PARAMS = ('broad_nlu_actual', 'broad_nlu_expected', 'broad_nlu_rec', 'broad_nlu_selected')


def build_broad_nlu_listening_section(**values: Any) -> dict[str, Any]:
    """Return the broad nlu listening diagnostic section from normalized ledger records."""
    broad_nlu_actual = values['broad_nlu_actual']
    broad_nlu_expected = values['broad_nlu_expected']
    broad_nlu_rec = values['broad_nlu_rec']
    broad_nlu_selected = values['broad_nlu_selected']
    return {
                    "schema_version": broad_nlu_expected.get("schema_version"),
                    "primary_discourse_act": broad_nlu_selected.get("primary_discourse_act"),
                    "player_input_kind": broad_nlu_actual.get("player_input_kind"),
                    "confidence": broad_nlu_actual.get("confidence"),
                    "ambiguity_codes": broad_nlu_actual.get("ambiguity_codes") or [],
                    "repair_prompt_recommended": bool(
                        broad_nlu_actual.get("repair_prompt_recommended")
                    ),
                    "response_expectation": broad_nlu_actual.get("response_expectation"),
                    "target_actor_refs": broad_nlu_selected.get("target_actor_refs") or [],
                    "object_refs": broad_nlu_selected.get("object_refs") or [],
                    "source_refs": broad_nlu_selected.get("source_refs") or [],
                    "raw_player_input_included": bool(
                        broad_nlu_actual.get("raw_player_input_included")
                    ),
                    "contract_pass": broad_nlu_actual.get("contract_pass"),
                    "failure_reason": broad_nlu_rec.get("failure_reason")
                    or (
                        _record_reasons(broad_nlu_rec)[0]
                        if _record_reasons(broad_nlu_rec)
                        else None
                    ),
                    "status": broad_nlu_rec.get("status"),
                }

