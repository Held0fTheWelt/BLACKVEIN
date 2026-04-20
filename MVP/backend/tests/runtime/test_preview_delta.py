"""Tests for guarded preview-delta dry-run evaluation."""

from __future__ import annotations

import asyncio
from copy import deepcopy

from app.runtime.preview_delta import preview_delta_dry_run
from app.runtime.preview_models import PreviewDeltaRequest
from app.runtime.turn_executor import MockDecision, ProposedStateDelta, execute_turn
from app.runtime.runtime_models import DeltaType


def _legacy_preview_with_full_deepcopy(
    session,
    module,
    current_turn: int,
    request: PreviewDeltaRequest,
):
    clone = deepcopy(session)

    def _coerce(raw: str | None):
        if raw is None:
            return None
        try:
            return DeltaType(raw)
        except ValueError:
            return None

    decision = MockDecision(
        detected_triggers=request.detected_triggers,
        proposed_deltas=[
            ProposedStateDelta(
                target=delta.target_path,
                next_value=delta.next_value,
                delta_type=_coerce(delta.delta_type),
                source="preview_request",
            )
            for delta in request.proposed_state_deltas
        ],
        proposed_scene_id=request.proposed_scene_id,
        narrative_text="[preview dry-run]",
        rationale=request.reasoning_summary or "",
    )
    return asyncio.run(
        execute_turn(
            clone,
            current_turn=current_turn,
            mock_decision=decision,
            module=module,
            enforce_responder_only=False,
        )
    )


def test_preview_returns_structured_feedback_for_valid_delta(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    session = god_of_carnage_module_with_state
    session.canonical_state.setdefault("characters", {}).setdefault(
        "veronique", {"emotional_state": 50}
    )
    request = PreviewDeltaRequest(
        scene_id=session.current_scene_id,
        proposed_state_deltas=[
            {
                "target_path": "characters.veronique.emotional_state",
                "next_value": 65,
                "delta_type": "state_update",
            }
        ],
    )
    result = preview_delta_dry_run(
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        request=request,
    )

    assert result.guard_outcome in {"accepted", "partially_accepted", "rejected", "structurally_invalid"}
    assert result.input_delta_count == 1
    assert isinstance(result.summary, str) and result.summary
    assert result.preview_safe_no_write is True
    assert result.normalized_feedback["guard_outcome"] == result.guard_outcome


def test_preview_rejects_illegal_targets_with_reasons(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    session = god_of_carnage_module_with_state
    request = PreviewDeltaRequest(
        proposed_state_deltas=[
            {
                "target_path": "characters.nonexistent.emotional_state",
                "next_value": 99,
                "delta_type": "state_update",
            }
        ]
    )
    result = preview_delta_dry_run(
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        request=request,
    )

    assert result.rejected_delta_count >= 1
    assert len(result.rejection_reasons) >= 1
    assert result.preview_safe_no_write is True


def test_preview_partial_acceptance_is_reported(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    session = god_of_carnage_module_with_state
    session.canonical_state.setdefault("characters", {}).setdefault(
        "veronique", {"emotional_state": 50}
    )
    request = PreviewDeltaRequest(
        proposed_state_deltas=[
            {
                "target_path": "characters.veronique.emotional_state",
                "next_value": 70,
                "delta_type": "state_update",
            },
            {
                "target_path": "characters.nonexistent.emotional_state",
                "next_value": 80,
                "delta_type": "state_update",
            },
        ]
    )
    result = preview_delta_dry_run(
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        request=request,
    )
    assert result.partial_acceptance is True
    assert result.accepted_delta_count >= 1
    assert result.rejected_delta_count >= 1
    assert result.normalized_feedback["partial_acceptance"] is True


def test_preview_is_side_effect_free_on_canonical_state(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    session = god_of_carnage_module_with_state
    before_state = deepcopy(session.canonical_state)
    before_scene = session.current_scene_id
    before_turn = session.turn_counter

    request = PreviewDeltaRequest(
        proposed_state_deltas=[
            {
                "target_path": "characters.veronique.emotional_state",
                "next_value": 75,
                "delta_type": "state_update",
            }
        ]
    )
    _ = preview_delta_dry_run(
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        request=request,
    )
    _ = preview_delta_dry_run(
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        request=request,
    )

    assert session.canonical_state == before_state
    assert session.current_scene_id == before_scene
    assert session.turn_counter == before_turn


def test_preview_equivalence_with_legacy_full_deepcopy_path(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """New bounded clone path matches legacy full deepcopy guard verdict semantics."""
    session = god_of_carnage_module_with_state
    session.canonical_state.setdefault("characters", {}).setdefault(
        "veronique", {"emotional_state": 50}
    )
    request = PreviewDeltaRequest(
        scene_id=session.current_scene_id,
        proposed_state_deltas=[
            {
                "target_path": "characters.veronique.emotional_state",
                "next_value": 72,
                "delta_type": "state_update",
            },
            {
                "target_path": "characters.nonexistent.emotional_state",
                "next_value": 99,
                "delta_type": "state_update",
            },
        ],
    )

    result = preview_delta_dry_run(
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        request=request,
    )
    legacy = _legacy_preview_with_full_deepcopy(
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        request=request,
    )

    assert result.guard_outcome == legacy.guard_outcome.value
    assert result.accepted_delta_count == len(legacy.accepted_deltas)
    assert result.rejected_delta_count == len(legacy.rejected_deltas)
    assert sorted(result.accepted_deltas) == sorted([d.target_path for d in legacy.accepted_deltas])
    assert sorted(result.rejected_deltas) == sorted([d.target_path for d in legacy.rejected_deltas])


def test_preview_many_calls_remain_side_effect_free(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Repeated preview calls do not mutate canonical session state."""
    session = god_of_carnage_module_with_state
    before_state = deepcopy(session.canonical_state)
    before_scene = session.current_scene_id
    before_turn = session.turn_counter

    request = PreviewDeltaRequest(
        proposed_state_deltas=[
            {
                "target_path": "characters.nonexistent.emotional_state",
                "next_value": 11,
                "delta_type": "state_update",
            }
        ]
    )
    for _ in range(30):
        _ = preview_delta_dry_run(
            session=session,
            module=god_of_carnage_module,
            current_turn=session.turn_counter + 1,
            request=request,
        )

    assert session.canonical_state == before_state
    assert session.current_scene_id == before_scene
    assert session.turn_counter == before_turn
