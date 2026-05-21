"""Projection section builder for `authority`."""

from __future__ import annotations

from typing import Any

from ...constants import *
from ...projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons

BUILD_AUTHORITY_SECTION_PARAMS = ('narr_actual', 'narr_expected', 'narr_rec', 'npc_actual', 'npc_expected', 'npc_rec')


def build_authority_section(**values: Any) -> dict[str, Any]:
    narr_actual = values['narr_actual']
    narr_expected = values['narr_expected']
    narr_rec = values['narr_rec']
    npc_actual = values['npc_actual']
    npc_expected = values['npc_expected']
    npc_rec = values['npc_rec']
    return {
                    "narrator": {
                        "required": bool(narr_expected.get("required")),
                        "expected_owner": narr_rec.get("expected_owner")
                        or narr_expected.get("expected_owner")
                        or "narrator",
                        "actual_owners": narr_actual.get("actual_owners") or [],
                        "fulfilled": narr_actual.get("fulfilled")
                        if "fulfilled" in narr_actual
                        else narr_actual.get("narrator_block_present")
                        or narr_actual.get("consequence_realized"),
                        "evidence_blocks": narr_actual.get("evidence_blocks") or [],
                        "failure_reason": narr_rec.get("failure_reason")
                        or (_record_reasons(narr_rec)[0] if _record_reasons(narr_rec) else None),
                    },
                    "npc": {
                        "policy": npc_expected.get("policy"),
                        "allowed_actors": npc_expected.get("allowed_actors") or [],
                        "actual_actors": npc_actual.get("actual_actors") or [],
                        "takeover_detected": bool(npc_actual.get("npc_takeover_detected")),
                        "offending_blocks": npc_actual.get("offending_blocks") or [],
                        "status": npc_rec.get("status"),
                    },
                    "player": {
                        "selected_human_actor_id": narr_expected.get("selected_human_actor_id")
                        or npc_expected.get("selected_human_actor_id"),
                        "forced_speech_detected": bool(npc_actual.get("forced_speech_detected")),
                        "forced_decision_detected": bool(npc_actual.get("forced_decision_detected")),
                        "agency_violation_detected": bool(npc_actual.get("agency_violation_detected")),
                    },
                }

