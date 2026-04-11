"""Parity checks between preview dry-run and canonical final guard path."""

from __future__ import annotations

import asyncio
from copy import deepcopy

from app.runtime.preview_delta import preview_delta_dry_run
from app.runtime.preview_models import PreviewDeltaRequest
from app.runtime.turn_executor import MockDecision, ProposedStateDelta, execute_turn


def _decision_from_preview_request(request: PreviewDeltaRequest) -> MockDecision:
    return MockDecision(
        detected_triggers=request.detected_triggers,
        proposed_scene_id=request.proposed_scene_id,
        narrative_text="[parity-test]",
        rationale=request.reasoning_summary or "",
        proposed_deltas=[
            ProposedStateDelta(
                target=delta.target_path,
                next_value=delta.next_value,
                source="preview_parity_test",
            )
            for delta in request.proposed_state_deltas
        ],
    )


def test_rejected_preview_delta_is_rejected_by_final_guard(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    request = PreviewDeltaRequest(
        proposed_state_deltas=[
            {
                "target_path": "characters.nonexistent.emotional_state",
                "next_value": 12,
                "delta_type": "state_update",
            }
        ]
    )
    preview = preview_delta_dry_run(
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        request=request,
    )
    assert preview.rejected_delta_count >= 1

    final_result = asyncio.run(
        execute_turn(
            deepcopy(session),
            current_turn=session.turn_counter + 1,
            mock_decision=_decision_from_preview_request(request),
            module=god_of_carnage_module,
            enforce_responder_only=False,
        )
    )
    assert len(final_result.rejected_deltas) >= 1


def test_preview_acceptance_is_coherent_with_final_guard(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    session.canonical_state.setdefault("characters", {}).setdefault(
        "veronique", {"emotional_state": 50}
    )
    request = PreviewDeltaRequest(
        proposed_state_deltas=[
            {
                "target_path": "characters.veronique.emotional_state",
                "next_value": 66,
                "delta_type": "state_update",
            }
        ]
    )
    preview = preview_delta_dry_run(
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        request=request,
    )
    assert preview.accepted_delta_count >= 1
    assert preview.preview_safe_no_write is True

    final_result = asyncio.run(
        execute_turn(
            deepcopy(session),
            current_turn=session.turn_counter + 1,
            mock_decision=_decision_from_preview_request(request),
            module=god_of_carnage_module,
            enforce_responder_only=False,
        )
    )
    assert len(final_result.accepted_deltas) >= 1
