"""Projection section builder for `visible_projection`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_VISIBLE_PROJECTION_SECTION_PARAMS = ('visible_actual',)


def build_visible_projection_section(**values: Any) -> dict[str, Any]:
    """Return the visible projection diagnostic section from normalized ledger records."""
    visible_actual = values['visible_actual']
    return {
                    "blocks_have_origin_aspect": bool(visible_actual.get("blocks_have_origin_aspect")),
                    "required_blocks_present": bool(visible_actual.get("required_blocks_present")),
                    "lost_required_narrator_block": bool(
                        visible_actual.get("lost_required_narrator_block")
                    ),
                    "visible_block_origins": visible_actual.get("visible_block_origins") or [],
                }

