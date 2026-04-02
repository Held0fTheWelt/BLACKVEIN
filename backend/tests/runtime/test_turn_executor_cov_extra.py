"""Extra branch coverage for app.runtime.turn_executor."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.runtime.turn_executor import (
    DeltaApplicationError,
    MockDecision,
    ProposedStateDelta,
    TurnExecutionResult,
    _compute_guard_outcome,
    _set_nested_value,
    apply_deltas,
    commit_turn_result,
    extract_entity_id,
    infer_delta_type,
)
from app.runtime.w2_models import (
    DeltaType,
    DeltaValidationStatus,
    GuardOutcome,
    StateDelta,
)


def test_set_nested_value_invalid_path():
    with pytest.raises(DeltaApplicationError):
        _set_nested_value({}, "", "x")
    with pytest.raises(DeltaApplicationError):
        _set_nested_value({}, None, "x")  # type: ignore[arg-type]


def test_set_nested_value_non_dict_traversal():
    state = {"a": "scalar"}
    with pytest.raises(DeltaApplicationError):
        _set_nested_value(state, "a.b", 1)


def test_infer_delta_type_and_extract_entity_id_edges():
    assert infer_delta_type("") == DeltaType.METADATA
    assert infer_delta_type(None) == DeltaType.METADATA  # type: ignore[arg-type]
    assert infer_delta_type("onlyone") == DeltaType.METADATA
    assert infer_delta_type("unknown.x.y") == DeltaType.METADATA
    assert infer_delta_type("relationships.axis.field") == DeltaType.RELATIONSHIP
    assert infer_delta_type("scene.main.props") == DeltaType.SCENE
    assert infer_delta_type("triggers.t1.state") == DeltaType.TRIGGER
    assert extract_entity_id("") is None
    assert extract_entity_id("single") is None
    assert extract_entity_id("characters.v.emotional") == "v"


class _SplitEmpty(str):
    """str subclass so split() can return [] (covers empty-parts branches)."""

    def split(self, sep=None, maxsplit=-1):  # noqa: ARG002
        return []


def test_set_nested_value_empty_parts_after_split():
    with pytest.raises(DeltaApplicationError, match="Empty path"):
        _set_nested_value({}, _SplitEmpty("ignored"), 1)


def test_infer_delta_type_empty_parts_after_split():
    assert infer_delta_type(_SplitEmpty("x")) == DeltaType.METADATA


def test_apply_deltas_skips_non_accepted():
    d_ok = StateDelta(
        delta_type=DeltaType.CHARACTER_STATE,
        target_path="c.x",
        target_entity="x",
        previous_value=None,
        next_value=1,
        source="t",
        turn_number=1,
        validation_status=DeltaValidationStatus.ACCEPTED,
    )
    d_bad = StateDelta(
        delta_type=DeltaType.CHARACTER_STATE,
        target_path="c.y",
        target_entity="y",
        previous_value=None,
        next_value=2,
        source="t",
        turn_number=1,
        validation_status=DeltaValidationStatus.REJECTED,
    )
    out = apply_deltas({}, [d_bad, d_ok])
    assert "c" in out and out["c"]["x"] == 1
    assert "y" not in out.get("c", {})


def test_apply_deltas_wraps_delta_application_error():
    d = StateDelta(
        delta_type=DeltaType.CHARACTER_STATE,
        target_path="c.nested",
        target_entity="c",
        previous_value=None,
        next_value=1,
        source="t",
        turn_number=1,
        validation_status=DeltaValidationStatus.ACCEPTED,
    )
    with pytest.raises(DeltaApplicationError):
        apply_deltas({"c": "not_dict"}, [d])


def test_compute_guard_outcome_non_success_status():
    assert (
        _compute_guard_outcome([], [], "system_error") == GuardOutcome.STRUCTURALLY_INVALID
    )


@pytest.mark.asyncio
async def test_execute_turn_system_error_path(god_of_carnage_module_with_state, god_of_carnage_module, monkeypatch):
    from app.runtime import turn_executor as te

    session = god_of_carnage_module_with_state
    decision = MockDecision(
        proposed_deltas=[
            ProposedStateDelta(target="characters.veronique.emotional_state", next_value=1)
        ],
        narrative_text="n",
        rationale="r",
    )

    def boom(*_a, **_kw):
        raise RuntimeError("forced")

    monkeypatch.setattr(te, "validate_decision", boom)
    result = await te.execute_turn(session, 1, decision, god_of_carnage_module)
    assert result.execution_status == "system_error"
    assert result.guard_outcome == GuardOutcome.STRUCTURALLY_INVALID


def test_commit_turn_result_rejects_non_success():
    from app.runtime.w2_models import SessionState

    session = SessionState(
        session_id="s",
        module_id="m",
        module_version="1",
        current_scene_id="sc",
        canonical_state={},
        turn_counter=0,
    )
    bad = TurnExecutionResult(
        turn_number=1,
        session_id="s",
        execution_status="system_error",
        decision=MockDecision(proposed_deltas=[], narrative_text="", rationale=""),
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_ms=1.0,
        events=[],
    )
    with pytest.raises(ValueError, match="non-successful"):
        commit_turn_result(session, bad)


def test_commit_turn_result_success_updates_session(god_of_carnage_module_with_state):
    from app.runtime.w2_models import SessionState

    session = god_of_carnage_module_with_state
    good = TurnExecutionResult(
        turn_number=1,
        session_id=session.session_id,
        execution_status="success",
        decision=MockDecision(proposed_deltas=[], narrative_text="", rationale=""),
        updated_canonical_state={"k": 1},
        updated_scene_id="new_scene",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_ms=1.0,
        events=[],
    )
    before = session.turn_counter
    updated = commit_turn_result(session, good)
    assert updated.canonical_state == {"k": 1}
    assert updated.current_scene_id == "new_scene"
    assert updated.turn_counter == before + 1


def test_commit_turn_result_success_without_scene_change(god_of_carnage_module_with_state):
    session = god_of_carnage_module_with_state
    scene_before = session.current_scene_id
    good = TurnExecutionResult(
        turn_number=1,
        session_id=session.session_id,
        execution_status="success",
        decision=MockDecision(proposed_deltas=[], narrative_text="", rationale=""),
        updated_canonical_state={"only": "state"},
        updated_scene_id=None,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_ms=1.0,
        events=[],
    )
    updated = commit_turn_result(session, good)
    assert updated.current_scene_id == scene_before
    assert updated.canonical_state == {"only": "state"}


def test_accumulate_turn_context_skips_add_when_history_not_session_history(
    god_of_carnage_module_with_state,
):
    from app.runtime.turn_executor import _accumulate_turn_context
    from app.runtime.w2_models import GuardOutcome

    session = god_of_carnage_module_with_state
    session.context_layers.session_history = []  # wrong type: not SessionHistory

    decision = MockDecision(proposed_deltas=[], narrative_text="", rationale="")
    result = TurnExecutionResult(
        turn_number=1,
        session_id=session.session_id,
        execution_status="success",
        decision=decision,
        accepted_deltas=[],
        rejected_deltas=[],
        updated_canonical_state=session.canonical_state,
        updated_scene_id=session.current_scene_id,
        guard_outcome=GuardOutcome.ACCEPTED,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_ms=1.0,
        events=[],
    )
    _accumulate_turn_context(session, result, prior_scene_id=session.current_scene_id)
    assert session.context_layers.short_term_context is not None
    assert session.context_layers.session_history == []


def test_derive_runtime_context_returns_when_history_empty(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    from app.runtime.session_history import SessionHistory
    from app.runtime.turn_executor import _derive_runtime_context

    session = god_of_carnage_module_with_state
    session.context_layers.session_history = SessionHistory(max_size=10)
    session.context_layers.progression_summary = None
    session.context_layers.relationship_axis_context = None
    session.context_layers.lore_direction_context = None
    _derive_runtime_context(session, god_of_carnage_module)
    assert session.context_layers.progression_summary is None
