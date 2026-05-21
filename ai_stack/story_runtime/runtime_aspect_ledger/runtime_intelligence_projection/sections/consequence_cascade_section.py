"""Projection section builder for `consequence_cascade`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_CONSEQUENCE_CASCADE_SECTION_PARAMS = ('cascade_actual', 'cascade_expected', 'cascade_rec', 'cascade_selected')


def build_consequence_cascade_section(**values: Any) -> dict[str, Any]:
    """Return the consequence cascade diagnostic section from normalized ledger records."""
    cascade_actual = values['cascade_actual']
    cascade_expected = values['cascade_expected']
    cascade_rec = values['cascade_rec']
    cascade_selected = values['cascade_selected']
    return {
                    "policy_present": bool(cascade_expected.get("policy_present")),
                    "policy_enabled": bool(cascade_expected.get("policy_enabled")),
                    "cascade_id": cascade_actual.get("cascade_id"),
                    "selected_consequence_ids": cascade_selected.get("selected_consequence_ids")
                    or [],
                    "selected_edge_ids": cascade_selected.get("selected_edge_ids") or [],
                    "selected_continuity_classes": cascade_selected.get("selected_continuity_classes")
                    or [],
                    "selected_statuses": cascade_selected.get("selected_statuses") or [],
                    "atom_count": int(cascade_actual.get("atom_count") or 0),
                    "edge_count": int(cascade_actual.get("edge_count") or 0),
                    "active_atom_count": int(cascade_actual.get("active_atom_count") or 0),
                    "graph_item_count": int(cascade_actual.get("graph_item_count") or 0),
                    "status_counts": cascade_actual.get("status_counts") or {},
                    "edge_kind_counts": cascade_actual.get("edge_kind_counts") or {},
                    "continuity_classes": cascade_actual.get("continuity_classes") or [],
                    "contract_pass": cascade_actual.get("contract_pass"),
                    "failure_codes": cascade_actual.get("failure_codes")
                    or _record_reasons(cascade_rec),
                    "failure_reason": cascade_rec.get("failure_reason")
                    or (_record_reasons(cascade_rec)[0] if _record_reasons(cascade_rec) else None),
                    "status": cascade_rec.get("status"),
                }

