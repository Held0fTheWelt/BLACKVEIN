"""Projection section builder for `capability`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_CAPABILITY_SECTION_PARAMS = ('blocked_capabilities', 'cap_rec', 'realized_capabilities', 'required_capabilities', 'selected_capabilities', 'violated_capabilities')


def build_capability_section(**values: Any) -> dict[str, Any]:
    blocked_capabilities = values['blocked_capabilities']
    cap_rec = values['cap_rec']
    realized_capabilities = values['realized_capabilities']
    required_capabilities = values['required_capabilities']
    selected_capabilities = values['selected_capabilities']
    violated_capabilities = values['violated_capabilities']
    return {
                    "selected_capabilities": selected_capabilities
                    if isinstance(selected_capabilities, list)
                    else [],
                    "blocked_capabilities": blocked_capabilities
                    if isinstance(blocked_capabilities, list)
                    else [],
                    "required_capabilities": required_capabilities
                    if isinstance(required_capabilities, list)
                    else [],
                    "realized_capabilities": realized_capabilities
                    if isinstance(realized_capabilities, list)
                    else [],
                    "violated_capabilities": violated_capabilities
                    if isinstance(violated_capabilities, list)
                    else [],
                    "status": cap_rec.get("status"),
                }

