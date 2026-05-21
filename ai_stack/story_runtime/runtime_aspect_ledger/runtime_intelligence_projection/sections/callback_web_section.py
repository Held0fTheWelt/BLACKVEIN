"""Projection section builder for `callback_web`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_CALLBACK_WEB_SECTION_PARAMS = ('callback_actual', 'callback_expected', 'callback_rec', 'callback_selected')


def build_callback_web_section(**values: Any) -> dict[str, Any]:
    """Return the callback web diagnostic section from normalized ledger records."""
    callback_actual = values['callback_actual']
    callback_expected = values['callback_expected']
    callback_rec = values['callback_rec']
    callback_selected = values['callback_selected']
    return {
                    "policy_present": bool(callback_expected.get("policy_present")),
                    "policy_enabled": bool(callback_expected.get("policy_enabled")),
                    "callback_web_id": callback_actual.get("callback_web_id"),
                    "selected_callback_edge_id": callback_selected.get("selected_callback_edge_id"),
                    "selected_callback_kind": callback_selected.get("selected_callback_kind"),
                    "selected_continuity_classes": callback_selected.get("selected_continuity_classes")
                    or [],
                    "selected_thread_ids": callback_selected.get("selected_thread_ids") or [],
                    "edge_count": int(callback_actual.get("edge_count") or 0),
                    "observation_count": int(callback_actual.get("observation_count") or 0),
                    "graph_edge_count": int(callback_actual.get("graph_edge_count") or 0),
                    "callback_kind_counts": callback_actual.get("callback_kind_counts") or {},
                    "continuity_classes": callback_actual.get("continuity_classes") or [],
                    "thread_ids": callback_actual.get("thread_ids") or [],
                    "contract_pass": callback_actual.get("contract_pass"),
                    "failure_codes": callback_actual.get("failure_codes")
                    or _record_reasons(callback_rec),
                    "failure_reason": callback_rec.get("failure_reason")
                    or (_record_reasons(callback_rec)[0] if _record_reasons(callback_rec) else None),
                    "status": callback_rec.get("status"),
                }

