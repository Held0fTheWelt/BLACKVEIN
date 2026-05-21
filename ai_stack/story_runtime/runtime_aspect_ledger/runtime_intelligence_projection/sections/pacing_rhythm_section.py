"""Projection section builder for `pacing_rhythm`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_PACING_RHYTHM_SECTION_PARAMS = ('pacing_rhythm_actual', 'pacing_rhythm_expected', 'pacing_rhythm_rec', 'pacing_rhythm_selected')


def build_pacing_rhythm_section(**values: Any) -> dict[str, Any]:
    pacing_rhythm_actual = values['pacing_rhythm_actual']
    pacing_rhythm_expected = values['pacing_rhythm_expected']
    pacing_rhythm_rec = values['pacing_rhythm_rec']
    pacing_rhythm_selected = values['pacing_rhythm_selected']
    return {
                    "schema_version": pacing_rhythm_expected.get("schema_version")
                    or pacing_rhythm_selected.get("schema_version")
                    or pacing_rhythm_actual.get("schema_version"),
                    "policy_present": bool(pacing_rhythm_expected.get("policy_present")),
                    "policy_enabled": bool(pacing_rhythm_expected.get("policy_enabled")),
                    "cadence": _record_nested_value(
                        pacing_rhythm_selected, "cadence", "target"
                    ),
                    "tempo_arc": _record_nested_value(
                        pacing_rhythm_selected, "tempo_arc", "target"
                    ),
                    "response_shape": _record_nested_value(
                        pacing_rhythm_selected, "response_shape", "target"
                    ),
                    "turn_change_policy": _record_nested_value(
                        pacing_rhythm_selected, "turn_change_policy", "target"
                    ),
                    "min_visible_blocks": int(
                        pacing_rhythm_selected.get("min_visible_blocks")
                        or (
                            pacing_rhythm_selected.get("target", {}).get("min_visible_blocks")
                            if isinstance(pacing_rhythm_selected.get("target"), dict)
                            else 0
                        )
                        or 0
                    ),
                    "max_visible_blocks": int(
                        pacing_rhythm_selected.get("max_visible_blocks")
                        or (
                            pacing_rhythm_selected.get("target", {}).get("max_visible_blocks")
                            if isinstance(pacing_rhythm_selected.get("target"), dict)
                            else 0
                        )
                        or 0
                    ),
                    "visible_block_count": int(
                        pacing_rhythm_actual.get("visible_block_count") or 0
                    ),
                    "actor_turn_count": int(pacing_rhythm_actual.get("actor_turn_count") or 0),
                    "requires_pause": bool(
                        pacing_rhythm_selected.get("requires_pause")
                        or (
                            pacing_rhythm_selected.get("target", {}).get("requires_pause")
                            if isinstance(pacing_rhythm_selected.get("target"), dict)
                            else False
                        )
                    ),
                    "blocks_forced_speech": bool(
                        pacing_rhythm_selected.get("blocks_forced_speech")
                        or (
                            pacing_rhythm_selected.get("target", {}).get("blocks_forced_speech")
                            if isinstance(pacing_rhythm_selected.get("target"), dict)
                            else False
                        )
                    ),
                    "contract_pass": pacing_rhythm_actual.get("contract_pass"),
                    "failure_codes": pacing_rhythm_actual.get("failure_codes")
                    or _record_reasons(pacing_rhythm_rec),
                    "failure_reason": pacing_rhythm_rec.get("failure_reason")
                    or (
                        _record_reasons(pacing_rhythm_rec)[0]
                        if _record_reasons(pacing_rhythm_rec)
                        else None
                    ),
                    "status": pacing_rhythm_rec.get("status"),
                }

