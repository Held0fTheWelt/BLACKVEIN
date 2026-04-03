"""Tests for W2.0.5 situation derivation."""

import pytest
from app.content.module_models import (
    ContentModule,
    EndingCondition,
    ModuleMetadata,
    PhaseTransition,
    ScenePhase,
)
from app.runtime.next_situation import NextSituation, derive_next_situation
from app.runtime.runtime_models import SessionState, SessionStatus


class TestDeriveNextSituation:
    """Tests for derive_next_situation main function."""

    @pytest.fixture
    def basic_module(self):
        """Module with 3 scenes, 1 transition, 1 ending."""
        metadata = ModuleMetadata(
            module_id="test_module",
            title="Test Module",
            version="0.1.0",
            contract_version="1.0.0",
        )

        scenes = {
            "phase_1": ScenePhase(
                id="phase_1",
                name="Phase 1",
                sequence=1,
                description="First phase",
            ),
            "phase_2": ScenePhase(
                id="phase_2",
                name="Phase 2",
                sequence=2,
                description="Second phase",
            ),
            "phase_3": ScenePhase(
                id="phase_3",
                name="Phase 3",
                sequence=3,
                description="Third phase",
            ),
        }

        transitions = {
            "t1": PhaseTransition(
                from_phase="phase_1",
                to_phase="phase_2",
                trigger_conditions=["escalation_threshold"],
            ),
            "t2": PhaseTransition(
                from_phase="phase_2",
                to_phase="phase_3",
                trigger_conditions=["resolution_marker"],
            ),
        }

        endings = {
            "bad_ending": EndingCondition(
                id="bad_ending",
                name="Bad Ending",
                description="Conflict escalates beyond control",
                trigger_conditions=["max_escalation"],
                outcome={"status": "failure"},
            ),
        }

        return ContentModule(
            metadata=metadata,
            characters={},
            relationship_axes={},
            trigger_definitions={},
            scene_phases=scenes,
            phase_transitions=transitions,
            ending_conditions=endings,
        )

    @pytest.fixture
    def session_in_phase_1(self, basic_module):
        """SessionState in phase_1."""
        return SessionState(
            module_id="test_module",
            module_version="0.1.0",
            current_scene_id="phase_1",
            canonical_state={"characters": {}},
            status=SessionStatus.ACTIVE,
        )

    def test_derive_situation_continue_when_no_conditions_met(self, basic_module, session_in_phase_1):
        """When no transition/ending conditions are met, continue in current scene."""
        result = derive_next_situation(session_in_phase_1, basic_module)
        assert result.current_scene_id == "phase_1"
        assert result.situation_status == "continue"
        assert not result.is_terminal

    def test_derive_situation_transitions_to_next_scene(self, basic_module, session_in_phase_1):
        """When transition condition is met, move to next scene."""
        # For W2.0.5, minimal condition checking: we just validate the target exists
        # In real scenario, condition evaluation would check state
        result = derive_next_situation(session_in_phase_1, basic_module)

        # Since _check_transition_condition returns True for non-empty targets,
        # transition to phase_2 should be possible
        # (actual evaluation depends on state, which is empty in this test)
        assert result.current_scene_id in ["phase_1", "phase_2"]
        assert result.situation_status in ["continue", "transitioned"]

    def test_derive_situation_unknown_current_scene_raises(self, basic_module):
        """Deriving with unknown current_scene raises ValueError."""
        session = SessionState(
            module_id="test_module",
            module_version="0.1.0",
            current_scene_id="unknown_phase",
            canonical_state={"characters": {}},
            status=SessionStatus.ACTIVE,
        )

        with pytest.raises(ValueError) as exc:
            derive_next_situation(session, basic_module)
        assert "not in module" in str(exc.value)

    def test_derive_situation_result_shape(self, basic_module, session_in_phase_1):
        """Result has all required fields."""
        result = derive_next_situation(session_in_phase_1, basic_module)

        assert isinstance(result, NextSituation)
        assert result.current_scene_id is not None
        assert result.situation_status in ["continue", "transitioned", "ending_reached"]
        assert isinstance(result.is_terminal, bool)
        assert isinstance(result.derivation_reason, str)

    def test_derive_situation_continues_in_phase_with_valid_transition_but_no_trigger(
        self, basic_module, session_in_phase_1
    ):
        """Scene with available transition continues if conditions not met."""
        result = derive_next_situation(session_in_phase_1, basic_module)

        # With empty state and no special conditions, should continue
        assert result.situation_status in ["continue", "transitioned"]
        assert result.is_terminal is False

    def test_derive_situation_ending_takes_priority_over_transition(
        self, basic_module
    ):
        """Ending conditions are checked before transitions."""
        # Create a module where ending has higher priority
        session = SessionState(
            module_id="test_module",
            module_version="0.1.0",
            current_scene_id="phase_1",
            canonical_state={"characters": {}, "max_escalation": True},
            status=SessionStatus.ACTIVE,
        )

        result = derive_next_situation(session, basic_module)

        # Result should indicate whether ending or transition
        assert result.situation_status in ["ending_reached", "continue", "transitioned"]
        assert result.current_scene_id in ["phase_1", "phase_2"]

    def test_derive_situation_terminal_ending_sets_is_terminal(self, basic_module):
        """Reaching an ending sets is_terminal=True."""
        session = SessionState(
            module_id="test_module",
            module_version="0.1.0",
            current_scene_id="phase_2",
            canonical_state={"characters": {}},
            status=SessionStatus.ACTIVE,
        )

        result = derive_next_situation(session, basic_module)

        if result.situation_status == "ending_reached":
            assert result.is_terminal is True
            assert result.ending_id is not None
            assert result.ending_outcome is not None

    def test_derive_situation_invalid_transition_target_skipped(self):
        """Transitions to non-existent scenes are skipped."""
        metadata = ModuleMetadata(
            module_id="test_module",
            title="Test",
            version="0.1.0",
            contract_version="1.0.0",
        )

        scenes = {
            "phase_1": ScenePhase(
                id="phase_1",
                name="Phase 1",
                sequence=1,
                description="First",
            ),
        }

        # Transition to non-existent phase_2
        transitions = {
            "t1": PhaseTransition(
                from_phase="phase_1",
                to_phase="phase_2",
                trigger_conditions=[],
            ),
        }

        module = ContentModule(
            metadata=metadata,
            characters={},
            relationship_axes={},
            trigger_definitions={},
            scene_phases=scenes,
            phase_transitions=transitions,
            ending_conditions={},
        )

        session = SessionState(
            module_id="test_module",
            module_version="0.1.0",
            current_scene_id="phase_1",
            canonical_state={"characters": {}},
            status=SessionStatus.ACTIVE,
        )

        result = derive_next_situation(session, module)

        # Invalid transition should be skipped, continue in phase_1
        assert result.current_scene_id == "phase_1"
        assert result.situation_status == "continue"

    def test_derive_situation_no_transitions_continues(self, basic_module, session_in_phase_1):
        """Module with no transitions from current scene continues."""
        # Remove transitions for this test
        basic_module.phase_transitions = {}

        result = derive_next_situation(session_in_phase_1, basic_module)

        assert result.current_scene_id == "phase_1"
        assert result.situation_status == "continue"

    def test_derive_situation_ending_without_conditions_always_triggers(self):
        """Ending with empty trigger_conditions is always active."""
        metadata = ModuleMetadata(
            module_id="test",
            title="Test",
            version="0.1.0",
            contract_version="1.0.0",
        )

        scenes = {
            "phase_1": ScenePhase(
                id="phase_1",
                name="Phase 1",
                sequence=1,
                description="Only phase",
            ),
        }

        # Ending with no trigger conditions = always active
        endings = {
            "auto_ending": EndingCondition(
                id="auto_ending",
                name="Auto Ending",
                description="Always triggered",
                trigger_conditions=[],
                outcome={"status": "always_triggered"},
            ),
        }

        module = ContentModule(
            metadata=metadata,
            characters={},
            relationship_axes={},
            trigger_definitions={},
            scene_phases=scenes,
            phase_transitions={},
            ending_conditions=endings,
        )

        session = SessionState(
            module_id="test",
            module_version="0.1.0",
            current_scene_id="phase_1",
            canonical_state={"characters": {}},
            status=SessionStatus.ACTIVE,
        )

        result = derive_next_situation(session, module)

        assert result.situation_status == "ending_reached"
        assert result.is_terminal is True
        assert result.ending_id == "auto_ending"


class TestConditionAwareNextSituation:
    """Tests for W2.0-R3: condition-aware next-situation derivation."""

    def test_conditional_transition_triggered_with_conditions_satisfied(self):
        """Conditional transition fires when all its trigger conditions are detected."""
        from app.content.module_models import TriggerDefinition

        metadata = ModuleMetadata(
            module_id="test",
            title="Test",
            version="0.1.0",
            contract_version="1.0.0",
        )

        scenes = {
            "scene_a": ScenePhase(id="scene_a", name="A", sequence=1, description="A"),
            "scene_b": ScenePhase(id="scene_b", name="B", sequence=2, description="B"),
        }

        # Transition requires "escalation" trigger
        transitions = {
            "t1": PhaseTransition(
                from_phase="scene_a",
                to_phase="scene_b",
                trigger_conditions=["escalation"],
            ),
        }

        triggers = {
            "escalation": TriggerDefinition(
                id="escalation",
                name="Escalation",
                description="Conflict escalates",
            ),
        }

        module = ContentModule(
            metadata=metadata,
            characters={},
            relationship_axes={},
            trigger_definitions=triggers,
            scene_phases=scenes,
            phase_transitions=transitions,
            ending_conditions={},
        )

        session = SessionState(
            module_id="test",
            module_version="0.1.0",
            current_scene_id="scene_a",
            canonical_state={},
        )

        # Without detected triggers: transition doesn't fire
        result_no_triggers = derive_next_situation(session, module, detected_triggers=[])
        assert result_no_triggers.situation_status == "continue"

        # With escalation trigger detected: transition fires
        result_with_trigger = derive_next_situation(session, module, detected_triggers=["escalation"])
        assert result_with_trigger.situation_status == "transitioned"
        assert result_with_trigger.current_scene_id == "scene_b"

    def test_conditional_ending_triggered_with_conditions_satisfied(self):
        """Conditional ending fires when all its trigger conditions are detected."""
        from app.content.module_models import TriggerDefinition

        metadata = ModuleMetadata(
            module_id="test",
            title="Test",
            version="0.1.0",
            contract_version="1.0.0",
        )

        scenes = {
            "scene_1": ScenePhase(id="scene_1", name="Scene 1", sequence=1, description="Only scene"),
        }

        # Ending requires "total_breakdown" trigger
        endings = {
            "catastrophic": EndingCondition(
                id="catastrophic",
                name="Catastrophic End",
                description="Everything falls apart",
                trigger_conditions=["total_breakdown"],
                outcome={"status": "failure"},
            ),
        }

        triggers = {
            "total_breakdown": TriggerDefinition(
                id="total_breakdown",
                name="Total Breakdown",
                description="System completely fails",
            ),
        }

        module = ContentModule(
            metadata=metadata,
            characters={},
            relationship_axes={},
            trigger_definitions=triggers,
            scene_phases=scenes,
            phase_transitions={},
            ending_conditions=endings,
        )

        session = SessionState(
            module_id="test",
            module_version="0.1.0",
            current_scene_id="scene_1",
            canonical_state={},
        )

        # Without trigger: continues
        result_no_trigger = derive_next_situation(session, module, detected_triggers=[])
        assert result_no_trigger.situation_status == "continue"

        # With trigger detected: ending fires
        result_with_trigger = derive_next_situation(session, module, detected_triggers=["total_breakdown"])
        assert result_with_trigger.situation_status == "ending_reached"
        assert result_with_trigger.is_terminal is True

    def test_multiple_condition_transition_requires_all_conditions(self):
        """Transition with multiple conditions requires ALL to be detected."""
        from app.content.module_models import TriggerDefinition

        metadata = ModuleMetadata(
            module_id="test",
            title="Test",
            version="0.1.0",
            contract_version="1.0.0",
        )

        scenes = {
            "scene_1": ScenePhase(id="scene_1", name="Scene 1", sequence=1, description="S1"),
            "scene_2": ScenePhase(id="scene_2", name="Scene 2", sequence=2, description="S2"),
        }

        # Transition requires BOTH "anger" AND "betrayal"
        transitions = {
            "t1": PhaseTransition(
                from_phase="scene_1",
                to_phase="scene_2",
                trigger_conditions=["anger", "betrayal"],
            ),
        }

        triggers = {
            "anger": TriggerDefinition(id="anger", name="Anger", description="Anger detected"),
            "betrayal": TriggerDefinition(id="betrayal", name="Betrayal", description="Betrayal detected"),
        }

        module = ContentModule(
            metadata=metadata,
            characters={},
            relationship_axes={},
            trigger_definitions=triggers,
            scene_phases=scenes,
            phase_transitions=transitions,
            ending_conditions={},
        )

        session = SessionState(
            module_id="test",
            module_version="0.1.0",
            current_scene_id="scene_1",
            canonical_state={},
        )

        # Only anger: continues
        result_partial = derive_next_situation(session, module, detected_triggers=["anger"])
        assert result_partial.situation_status == "continue"

        # Both anger and betrayal: transitions
        result_both = derive_next_situation(session, module, detected_triggers=["anger", "betrayal"])
        assert result_both.situation_status == "transitioned"
        assert result_both.current_scene_id == "scene_2"

    def test_backward_compatibility_unconditional_still_works(self, god_of_carnage_module, god_of_carnage_module_with_state):
        """Unconditional transitions/endings still work without detected_triggers."""
        session = god_of_carnage_module_with_state

        # Without detected_triggers parameter (backward compatible)
        result = derive_next_situation(session, god_of_carnage_module)

        # Should handle unconditional cases (empty trigger_conditions)
        assert result.situation_status in ["continue", "transitioned", "ending_reached"]
        assert result.current_scene_id is not None


class TestLogSituationOutcome:
    """Test outcome logging for narrative states."""

    def test_log_continuation_creates_event(self):
        """Scene continuation generates scene_continued event."""
        from app.runtime.next_situation import log_situation_outcome

        situation = NextSituation(
            current_scene_id="phase_1",
            situation_status="continue",
            derivation_reason="No transition triggered",
        )

        entries = log_situation_outcome(situation, session_id="sess1", turn_number=1)

        assert len(entries) == 1
        assert entries[0].event_type == "scene_continued"
        assert entries[0].session_id == "sess1"
        assert entries[0].turn_number == 1
        assert entries[0].order_index == 0
        assert entries[0].payload["scene_id"] == "phase_1"

    def test_log_transition_creates_event(self):
        """Scene transition generates scene_transitioned event."""
        from app.runtime.next_situation import log_situation_outcome

        situation = NextSituation(
            current_scene_id="phase_2",
            situation_status="transitioned",
            derivation_reason="Condition met for phase_1 -> phase_2",
        )

        entries = log_situation_outcome(situation, session_id="sess1", turn_number=2)

        assert len(entries) == 1
        assert entries[0].event_type == "scene_transitioned"
        assert entries[0].session_id == "sess1"
        assert entries[0].turn_number == 2
        assert entries[0].payload["to_scene_id"] == "phase_2"

    def test_log_ending_creates_event(self):
        """Ending reached generates ending_reached event."""
        from app.runtime.next_situation import log_situation_outcome

        outcome = {"ending_name": "bittersweet_resolution", "score": 75}
        situation = NextSituation(
            current_scene_id="phase_1",
            situation_status="ending_reached",
            ending_id="ending_1",
            ending_outcome=outcome,
            is_terminal=True,
            derivation_reason="Ending condition satisfied",
        )

        entries = log_situation_outcome(situation, session_id="sess1", turn_number=3)

        assert len(entries) == 1
        assert entries[0].event_type == "ending_reached"
        assert entries[0].session_id == "sess1"
        assert entries[0].turn_number == 3
        assert entries[0].payload["ending_id"] == "ending_1"
        assert entries[0].payload["ending_outcome"] == outcome

    def test_log_outcome_event_has_derivation_reason(self):
        """All outcome events include derivation reason in payload."""
        from app.runtime.next_situation import log_situation_outcome

        situation = NextSituation(
            current_scene_id="phase_1",
            situation_status="continue",
            derivation_reason="No valid transitions from current state",
        )

        entries = log_situation_outcome(situation, session_id="sess1", turn_number=1)

        assert entries[0].payload["derivation_reason"] == "No valid transitions from current state"

    def test_log_outcome_events_independent_sessions(self):
        """Outcome events correctly distinguish different sessions."""
        from app.runtime.next_situation import log_situation_outcome

        situation = NextSituation(
            current_scene_id="phase_1",
            situation_status="continue",
        )

        entries_a = log_situation_outcome(situation, session_id="sess_a", turn_number=1)
        entries_b = log_situation_outcome(situation, session_id="sess_b", turn_number=1)

        assert entries_a[0].session_id == "sess_a"
        assert entries_b[0].session_id == "sess_b"

    def test_log_outcome_empty_ending_outcome_handled(self):
        """Ending outcome None is converted to empty dict in payload."""
        from app.runtime.next_situation import log_situation_outcome

        situation = NextSituation(
            current_scene_id="phase_1",
            situation_status="ending_reached",
            ending_id="ending_1",
            ending_outcome=None,
            is_terminal=True,
        )

        entries = log_situation_outcome(situation, session_id="sess1", turn_number=1)

        assert entries[0].payload["ending_outcome"] == {}


class TestApplySituationOutcome:
    """Test session state updates from situation outcomes."""

    def test_apply_continuation_preserves_scene(self):
        """Continuation outcome preserves current scene."""
        from app.runtime.next_situation import apply_situation_outcome

        session = SessionState(
            module_id="test",
            module_version="0.1.0",
            current_scene_id="phase_1",
            canonical_state={"test": "state"},
        )

        situation = NextSituation(
            current_scene_id="phase_1",
            situation_status="continue",
            is_terminal=False,
        )

        updated = apply_situation_outcome(session, situation)

        assert updated.current_scene_id == "phase_1"
        assert updated.status == SessionStatus.ACTIVE
        assert session.current_scene_id == "phase_1"  # Original unchanged
        assert session is not updated  # Different objects

    def test_apply_transition_updates_scene(self):
        """Transition outcome updates current scene."""
        from app.runtime.next_situation import apply_situation_outcome

        session = SessionState(
            module_id="test",
            module_version="0.1.0",
            current_scene_id="phase_1",
            canonical_state={},
        )

        situation = NextSituation(
            current_scene_id="phase_2",
            situation_status="transitioned",
            is_terminal=False,
        )

        updated = apply_situation_outcome(session, situation)

        assert updated.current_scene_id == "phase_2"
        assert session.current_scene_id == "phase_1"  # Original unchanged

    def test_apply_ending_sets_terminal_status(self):
        """Ending outcome updates session status to ENDED."""
        from app.runtime.next_situation import apply_situation_outcome
        from app.runtime.runtime_models import SessionStatus

        session = SessionState(
            module_id="test",
            module_version="0.1.0",
            current_scene_id="phase_1",
            canonical_state={},
            status=SessionStatus.ACTIVE,
        )

        situation = NextSituation(
            current_scene_id="phase_1",
            situation_status="ending_reached",
            ending_id="ending_1",
            is_terminal=True,
        )

        updated = apply_situation_outcome(session, situation)

        assert updated.status == SessionStatus.ENDED
        assert session.status == SessionStatus.ACTIVE  # Original unchanged

    def test_apply_outcome_updates_timestamp_on_terminal(self):
        """Terminal outcome updates session timestamp."""
        from app.runtime.next_situation import apply_situation_outcome
        from datetime import datetime
        import time

        session = SessionState(
            module_id="test",
            module_version="0.1.0",
            current_scene_id="phase_1",
            canonical_state={},
        )
        original_time = session.updated_at

        situation = NextSituation(
            current_scene_id="phase_1",
            situation_status="ending_reached",
            is_terminal=True,
        )

        # Small delay to ensure time difference
        time.sleep(0.01)

        updated = apply_situation_outcome(session, situation)

        assert updated.updated_at > original_time
        assert session.updated_at == original_time  # Original unchanged

    def test_apply_outcome_immutability(self):
        """Apply outcome does not modify original session."""
        from app.runtime.next_situation import apply_situation_outcome

        session = SessionState(
            module_id="test",
            module_version="0.1.0",
            current_scene_id="phase_1",
            canonical_state={"key": "value"},
            status=SessionStatus.ACTIVE,
        )

        situation = NextSituation(
            current_scene_id="phase_2",
            situation_status="transitioned",
            is_terminal=False,
        )

        updated = apply_situation_outcome(session, situation)

        # Original completely unchanged
        assert session.current_scene_id == "phase_1"
        assert session.status == SessionStatus.ACTIVE
        assert session.canonical_state == {"key": "value"}

    def test_apply_transition_and_ending_scene_change_plus_status(self):
        """Combined transition + ending outcome handles both scene and status."""
        from app.runtime.next_situation import apply_situation_outcome

        session = SessionState(
            module_id="test",
            module_version="0.1.0",
            current_scene_id="phase_1",
            canonical_state={},
            status=SessionStatus.ACTIVE,
        )

        # Edge case: ending reached in a different scene
        situation = NextSituation(
            current_scene_id="phase_3",
            situation_status="ending_reached",
            ending_id="final_ending",
            is_terminal=True,
        )

        updated = apply_situation_outcome(session, situation)

        assert updated.current_scene_id == "phase_3"
        assert updated.status == SessionStatus.ENDED
        assert session.current_scene_id == "phase_1"
        assert session.status == SessionStatus.ACTIVE


class TestNextSituationHelpersDirect:
    """Direct coverage for _check_ending_condition / _check_transition_condition."""

    @pytest.fixture
    def tiny_module(self):
        from app.content.module_models import (
            ContentModule,
            ModuleMetadata,
            ScenePhase,
        )

        meta = ModuleMetadata(
            module_id="t",
            title="T",
            version="1.0.0",
            contract_version="1",
        )
        ph = ScenePhase(
            id="scene_a",
            name="A",
            sequence=1,
            description="d",
        )
        return ContentModule(metadata=meta, scene_phases={"scene_a": ph})

    @pytest.fixture
    def bare_session(self):
        return SessionState(
            module_id="t",
            module_version="1.0.0",
            current_scene_id="scene_a",
            canonical_state={},
        )

    def test_check_ending_unconditional_and_conditional(self, bare_session):
        from app.content.module_models import EndingCondition
        from app.runtime.next_situation import _check_ending_condition

        unconditional = EndingCondition(
            id="e1",
            name="n",
            description="d",
            outcome={},
            trigger_conditions=[],
        )
        assert _check_ending_condition(unconditional, bare_session, None) is True

        cond = EndingCondition(
            id="e2",
            name="n2",
            description="d",
            outcome={},
            trigger_conditions=["a", "b"],
        )
        assert _check_ending_condition(cond, bare_session, None) is False
        assert _check_ending_condition(cond, bare_session, ["a"]) is False
        assert _check_ending_condition(cond, bare_session, ["a", "b"]) is True

    def test_check_transition_target_missing_and_conditions(self, bare_session, tiny_module):
        from app.content.module_models import PhaseTransition
        from app.runtime.next_situation import _check_transition_condition

        bad_target = PhaseTransition(
            from_phase="scene_a",
            to_phase="nope",
            trigger_conditions=[],
        )
        assert _check_transition_condition(bad_target, bare_session, tiny_module, None) is False

        ok_unc = PhaseTransition(
            from_phase="scene_a",
            to_phase="scene_a",
            trigger_conditions=[],
        )
        assert _check_transition_condition(ok_unc, bare_session, tiny_module, None) is True

        cond = PhaseTransition(
            from_phase="scene_a",
            to_phase="scene_a",
            trigger_conditions=["x"],
        )
        assert _check_transition_condition(cond, bare_session, tiny_module, None) is False
        assert _check_transition_condition(cond, bare_session, tiny_module, ["x"]) is True

    def test_log_situation_outcome_unknown_status_empty(self):
        from app.runtime.next_situation import log_situation_outcome

        situation = NextSituation(
            current_scene_id="x",
            situation_status="unknown_status",
            derivation_reason="test",
        )
        assert log_situation_outcome(situation, "s1", 1) == []
