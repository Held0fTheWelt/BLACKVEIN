"""Task 1B: narrative commit record and in-process resolution semantics."""

from __future__ import annotations

import pytest

from app.content.module_models import (
    ContentModule,
    EndingCondition,
    ModuleMetadata,
    PhaseTransition,
    ScenePhase,
)
from app.runtime.runtime_models import (
    GuardOutcome,
    ProposalSource,
    ProposedStateDelta,
    SessionState,
    SessionStatus,
)
from app.runtime.scene_legality import SceneTransitionLegality
from app.runtime.turn_executor import (
    MockDecision,
    commit_turn_result,
    execute_turn,
)


@pytest.fixture
def conditional_module():
    """Module with conditional s2->s3 transition requiring unlock."""
    metadata = ModuleMetadata(
        module_id="conditional",
        title="Conditional",
        version="0.1.0",
        contract_version="1.0.0",
    )
    scenes = {
        "s1": ScenePhase(id="s1", name="S1", sequence=1, description=""),
        "s2": ScenePhase(id="s2", name="S2", sequence=2, description=""),
        "s3": ScenePhase(id="s3", name="S3", sequence=3, description=""),
    }
    transitions = {
        "t_conditional": PhaseTransition(
            id="t_conditional",
            from_phase="s2",
            to_phase="s3",
            trigger_conditions=["unlock"],
        ),
    }
    return ContentModule(
        metadata=metadata,
        scene_phases=scenes,
        phase_transitions=transitions,
        ending_conditions={},
        characters={},
        relationship_axes={},
        triggers={},
        assertions={},
    )


@pytest.fixture
def session_s2():
    return SessionState(
        session_id="test",
        module_id="conditional",
        module_version="0.1.0",
        current_scene_id="s2",
        status=SessionStatus.ACTIVE,
        canonical_state={},
    )


@pytest.mark.asyncio
async def test_successful_turn_has_narrative_commit(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    decision = MockDecision(
        proposed_deltas=[
            ProposedStateDelta(
                target="characters.veronique.emotional_state",
                next_value=60,
            )
        ],
        narrative_text="t",
        rationale="r",
    )
    result = await execute_turn(session, 1, decision, god_of_carnage_module)
    assert result.execution_status == "success"
    assert result.narrative_commit is not None
    nc = result.narrative_commit
    assert nc.committed_scene_id == session.current_scene_id or nc.situation_status in (
        "continue",
        "transitioned",
        "ending_reached",
    )
    assert nc.guard_outcome == GuardOutcome.ACCEPTED.value
    assert "characters.veronique.emotional_state" in nc.accepted_delta_targets


@pytest.mark.asyncio
async def test_continue_no_transition_in_consequences(conditional_module, session_s2):
    decision = MockDecision(
        proposed_deltas=[],
        proposed_scene_id=None,
        detected_triggers=[],
    )
    result = await execute_turn(session_s2, 1, decision, conditional_module)
    assert result.narrative_commit is not None
    nc = result.narrative_commit
    assert nc.situation_status == "continue"
    assert nc.committed_scene_id == "s2"
    assert any(c.startswith("scene_continue:s2") for c in nc.canonical_consequences)
    assert not any(c.startswith("scene_transition:") for c in nc.canonical_consequences)


@pytest.mark.asyncio
async def test_legal_proposed_scene_transition(conditional_module, session_s2):
    decision = MockDecision(
        proposed_scene_id="s3",
        proposed_deltas=[],
        detected_triggers=["unlock"],
    )
    result = await execute_turn(session_s2, 1, decision, conditional_module)
    nc = result.narrative_commit
    assert nc is not None
    assert nc.situation_status == "transitioned"
    assert nc.prior_scene_id == "s2"
    assert nc.committed_scene_id == "s3"
    assert any("scene_transition:s2->s3" in c for c in nc.canonical_consequences)


@pytest.mark.asyncio
async def test_blocked_proposed_scene_stays_continue(conditional_module, session_s2):
    decision = MockDecision(
        proposed_scene_id="s3",
        proposed_deltas=[],
        detected_triggers=[],
    )
    result = await execute_turn(session_s2, 1, decision, conditional_module)
    nc = result.narrative_commit
    assert nc.situation_status == "continue"
    assert nc.committed_scene_id == "s2"
    assert not any(c.startswith("scene_transition:") for c in nc.canonical_consequences)


@pytest.mark.asyncio
async def test_ending_terminal_and_commit_marks_session_ended(
    conditional_module,
    session_s2,
):
    ending_module = conditional_module
    ending_module.ending_conditions = {
        "end_default": EndingCondition(
            id="end_default",
            name="Default",
            description="Default ending",
            trigger_conditions=[],
            outcome={"type": "default"},
        )
    }
    decision = MockDecision(
        proposed_scene_id="s3",
        proposed_deltas=[],
        detected_triggers=["unlock"],
    )
    result = await execute_turn(session_s2, 1, decision, ending_module)
    nc = result.narrative_commit
    assert nc is not None
    assert nc.situation_status == "ending_reached"
    assert nc.committed_ending_id == "end_default"
    assert nc.is_terminal is True
    # Ending wins before explicit transition commit
    assert nc.committed_scene_id == "s2"

    updated = commit_turn_result(session_s2, result)
    assert updated.status == SessionStatus.ENDED


@pytest.mark.asyncio
async def test_legality_checks_see_post_delta_canonical_state(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
    monkeypatch,
):
    """Transition legality must receive a session whose canonical_state matches post-delta."""
    session = god_of_carnage_module_with_state
    seen_states: list[dict] = []

    orig = SceneTransitionLegality.check_transition_legal

    def wrapped(from_scene, to_scene, module, session=None, detected_triggers=None):
        if session is not None and isinstance(session.canonical_state, dict):
            seen_states.append(dict(session.canonical_state))
        return orig(
            from_scene,
            to_scene,
            module,
            session=session,
            detected_triggers=detected_triggers,
        )

    monkeypatch.setattr(SceneTransitionLegality, "check_transition_legal", wrapped)

    decision = MockDecision(
        proposed_scene_id="act_1_scene_2",
        proposed_deltas=[
            ProposedStateDelta(
                target="characters.veronique.emotional_state",
                next_value=77,
            )
        ],
        detected_triggers=["trigger_1"],
    )
    await execute_turn(session, 1, decision, god_of_carnage_module)
    assert seen_states, "expected transition legality to run with a session snapshot"
    assert any(
        s.get("characters", {}).get("veronique", {}).get("emotional_state") == 77
        for s in seen_states
    )


def test_commit_turn_result_appends_single_narrative_log_entry(
    god_of_carnage_module_with_state,
):
    from app.runtime.runtime_models import NarrativeCommitRecord

    session = god_of_carnage_module_with_state
    session.metadata.pop("narrative_commit_log", None)
    scene = session.current_scene_id
    nc = NarrativeCommitRecord(
        turn_number=1,
        prior_scene_id=scene,
        committed_scene_id=scene,
        situation_status="continue",
        guard_outcome=GuardOutcome.ACCEPTED.value,
        authoritative_reason="fixture",
        canonical_consequences=[f"scene_continue:{scene}"],
    )
    from app.runtime.turn_executor import TurnExecutionResult

    result = TurnExecutionResult(
        turn_number=1,
        session_id=session.session_id,
        execution_status="success",
        decision=MockDecision(proposed_deltas=[], narrative_text="", rationale=""),
        updated_canonical_state={"x": 1},
        narrative_commit=nc,
        started_at=session.updated_at,
        completed_at=session.updated_at,
        duration_ms=0.0,
        events=[],
    )
    updated = commit_turn_result(session, result)
    log = updated.metadata.get("narrative_commit_log") or []
    assert len(log) == 1
    assert log[0]["turn_number"] == 1


@pytest.mark.asyncio
async def test_gate_reject_path_has_narrative_commit_and_accumulates_context(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    prior = session.current_scene_id
    delta = ProposedStateDelta(
        target="characters.veronique.emotional_state",
        next_value=50,
        source="test",
    )
    decision = MockDecision(
        proposed_deltas=[delta],
        proposal_source=ProposalSource.MOCK,
    )
    result = await execute_turn(
        session,
        1,
        decision,
        god_of_carnage_module,
        enforce_responder_only=True,
    )
    assert result.execution_status == "success"
    assert result.guard_outcome == GuardOutcome.REJECTED
    nc = result.narrative_commit
    assert nc is not None
    assert nc.accepted_delta_targets == []
    assert nc.rejected_delta_targets == ["characters.veronique.emotional_state"]
    assert nc.committed_scene_id == prior
    assert nc.situation_status == "continue"
    assert nc.is_terminal is False
    assert "source_gate_rejected" in nc.canonical_consequences
    assert session.context_layers.session_history is not None
    assert session.context_layers.session_history.size >= 1
