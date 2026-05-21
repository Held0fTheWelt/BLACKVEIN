"""Projection section builder for `conversational_memory`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_CONVERSATIONAL_MEMORY_SECTION_PARAMS = ('conversational_memory_actual', 'conversational_memory_expected', 'conversational_memory_rec', 'conversational_memory_selected')


def build_conversational_memory_section(**values: Any) -> dict[str, Any]:
    """Return the conversational memory diagnostic section from normalized ledger records."""
    conversational_memory_actual = values['conversational_memory_actual']
    conversational_memory_expected = values['conversational_memory_expected']
    conversational_memory_rec = values['conversational_memory_rec']
    conversational_memory_selected = values['conversational_memory_selected']
    return {
                    "schema_version": conversational_memory_expected.get("schema_version"),
                    "selected_tiers": conversational_memory_selected.get("selected_tiers") or [],
                    "selected_memory_ref_ids": conversational_memory_selected.get(
                        "selected_memory_ref_ids"
                    )
                    or [],
                    "source_refs": conversational_memory_selected.get("source_refs") or [],
                    "memory_present": bool(conversational_memory_actual.get("memory_present")),
                    "bounded": bool(conversational_memory_actual.get("bounded")),
                    "context_line_count": int(
                        conversational_memory_actual.get("context_line_count") or 0
                    ),
                    "raw_player_input_included": bool(
                        conversational_memory_actual.get("raw_player_input_included")
                    ),
                    "raw_prompt_included": bool(
                        conversational_memory_actual.get("raw_prompt_included")
                    ),
                    "contract_pass": conversational_memory_actual.get("contract_pass"),
                    "failure_reason": conversational_memory_rec.get("failure_reason")
                    or (
                        _record_reasons(conversational_memory_rec)[0]
                        if _record_reasons(conversational_memory_rec)
                        else None
                    ),
                    "status": conversational_memory_rec.get("status"),
                }

