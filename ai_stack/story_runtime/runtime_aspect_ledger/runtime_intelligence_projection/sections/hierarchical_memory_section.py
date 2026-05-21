"""Projection section builder for `hierarchical_memory`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_HIERARCHICAL_MEMORY_SECTION_PARAMS = ('memory_actual', 'memory_expected', 'memory_rec', 'memory_selected')


def build_hierarchical_memory_section(**values: Any) -> dict[str, Any]:
    memory_actual = values['memory_actual']
    memory_expected = values['memory_expected']
    memory_rec = values['memory_rec']
    memory_selected = values['memory_selected']
    return {
                    "policy_present": bool(memory_expected.get("policy_present")),
                    "policy_enabled": bool(memory_expected.get("policy_enabled")),
                    "selected_tiers": memory_selected.get("selected_tiers") or [],
                    "source_canonical_turn_id": memory_selected.get("source_canonical_turn_id"),
                    "write_allowed": bool(memory_actual.get("write_allowed")),
                    "written_item_count": int(memory_actual.get("written_item_count") or 0),
                    "tiers_written": memory_actual.get("tiers_written") or [],
                    "memory_present": bool(memory_actual.get("memory_present")),
                    "context_item_count": int(memory_actual.get("context_item_count") or 0),
                    "context_bounded": bool(memory_actual.get("context_bounded")),
                    "uncommitted_write_detected": bool(memory_actual.get("uncommitted_write_detected")),
                    "failure_reason": memory_rec.get("failure_reason")
                    or (_record_reasons(memory_rec)[0] if _record_reasons(memory_rec) else None),
                    "status": memory_rec.get("status"),
                }

