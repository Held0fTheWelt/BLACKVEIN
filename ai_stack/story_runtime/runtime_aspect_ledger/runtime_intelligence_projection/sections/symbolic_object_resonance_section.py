"""Projection section builder for `symbolic_object_resonance`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_SYMBOLIC_OBJECT_RESONANCE_SECTION_PARAMS = ('symbolic_object_actual', 'symbolic_object_expected', 'symbolic_object_rec', 'symbolic_object_selected')


def build_symbolic_object_resonance_section(**values: Any) -> dict[str, Any]:
    """Return the symbolic object resonance diagnostic section from normalized ledger records."""
    symbolic_object_actual = values['symbolic_object_actual']
    symbolic_object_expected = values['symbolic_object_expected']
    symbolic_object_rec = values['symbolic_object_rec']
    symbolic_object_selected = values['symbolic_object_selected']
    return {
                    "schema_version": symbolic_object_expected.get("schema_version")
                    or symbolic_object_selected.get("schema_version")
                    or symbolic_object_actual.get("schema_version"),
                    "policy_present": bool(symbolic_object_expected.get("policy_present")),
                    "policy_enabled": bool(symbolic_object_expected.get("policy_enabled")),
                    "commit_impact": symbolic_object_expected.get("commit_impact"),
                    "require_structured_events": bool(
                        symbolic_object_expected.get("require_structured_events")
                    ),
                    "max_symbols_per_turn": int(
                        symbolic_object_expected.get("max_symbols_per_turn") or 0
                    ),
                    "allowed_resonance_roles": symbolic_object_expected.get(
                        "allowed_resonance_roles"
                    )
                    or [],
                    "selected_symbol_ids": symbolic_object_selected.get("selected_symbol_ids")
                    or (
                        symbolic_object_selected.get("target", {}).get("selected_symbol_ids")
                        if isinstance(symbolic_object_selected.get("target"), dict)
                        else []
                    )
                    or [],
                    "selected_object_ids": symbolic_object_selected.get("selected_object_ids")
                    or (
                        symbolic_object_selected.get("target", {}).get("selected_object_ids")
                        if isinstance(symbolic_object_selected.get("target"), dict)
                        else []
                    )
                    or [],
                    "selected_resonance_roles": symbolic_object_selected.get(
                        "selected_resonance_roles"
                    )
                    or (
                        symbolic_object_selected.get("target", {}).get(
                            "selected_resonance_roles"
                        )
                        if isinstance(symbolic_object_selected.get("target"), dict)
                        else []
                    )
                    or [],
                    "required_source_refs": symbolic_object_selected.get(
                        "required_source_refs"
                    )
                    or [],
                    "structured_events_present": bool(
                        symbolic_object_actual.get("structured_events_present")
                    ),
                    "event_count": int(symbolic_object_actual.get("event_count") or 0),
                    "realized_object_ids": symbolic_object_actual.get("realized_object_ids")
                    or [],
                    "realized_symbol_ids": symbolic_object_actual.get("realized_symbol_ids")
                    or [],
                    "realized_resonance_roles": symbolic_object_actual.get(
                        "realized_resonance_roles"
                    )
                    or [],
                    "contract_pass": symbolic_object_actual.get("contract_pass"),
                    "failure_codes": symbolic_object_actual.get("failure_codes")
                    or _record_reasons(symbolic_object_rec),
                    "failure_reason": symbolic_object_rec.get("failure_reason")
                    or (
                        _record_reasons(symbolic_object_rec)[0]
                        if _record_reasons(symbolic_object_rec)
                        else None
                    ),
                    "status": symbolic_object_rec.get("status"),
                }

