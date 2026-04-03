"""Integration tests for W2.2.4: Scene and ending legality coherence.

Validates that scene transition and ending legality are consistent across
AI proposal validation (validators.py) and canonical situation derivation (next_situation.py).

These tests ensure both paths use SceneTransitionLegality for coherent decisions.
"""

import pytest
from app.content.module_models import (
    ContentModule,
    EndingCondition,
    ModuleMetadata,
    PhaseTransition,
    ScenePhase,
)
from app.runtime.next_situation import derive_next_situation
from app.runtime.scene_legality import SceneTransitionLegality, SceneLegalityDecision
from app.runtime.validators import validate_decision
from app.runtime.runtime_models import SessionState, SessionStatus


class TestSceneTransitionLegalityCoherence:
    """Both validation and derivation paths use SceneTransitionLegality."""

    @pytest.fixture
    def simple_module(self):
        """Module with basic transitions, no endings."""
        metadata = ModuleMetadata(
            module_id="simple",
            title="Simple Test",
            version="0.1.0",
            contract_version="1.0.0",
        )

        scenes = {
            "scene_a": ScenePhase(id="scene_a", name="A", sequence=1, description="Scene A"),
            "scene_b": ScenePhase(id="scene_b", name="B", sequence=2, description="Scene B"),
        }

        transitions = {
            "a_to_b": PhaseTransition(
                id="a_to_b",
                from_phase="scene_a",
                to_phase="scene_b",
                trigger_conditions=[],
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
    def session_a(self):
        """Session in scene_a."""
        return SessionState(
            session_id="test",
            module_id="simple",
            module_version="0.1.0",
            current_scene_id="scene_a",
            status=SessionStatus.ACTIVE,
            canonical_state={},
        )

    def test_self_transition_always_legal(self, simple_module, session_a):
        """Self-transition is legal via canonical rules."""
        legality = SceneTransitionLegality.check_transition_legal(
            "scene_a", "scene_a", simple_module
        )
        assert legality.allowed
        assert "Self-transition" in legality.reason

    def test_valid_transition_legal(self, simple_module, session_a):
        """Valid transition is legal via canonical rules."""
        legality = SceneTransitionLegality.check_transition_legal(
            "scene_a", "scene_b", simple_module
        )
        assert legality.allowed

    def test_unreachable_scene_illegal(self, simple_module, session_a):
        """Unreachable scene is illegal via canonical rules."""
        # Try to transition from scene_b to scene_a (no transition exists)
        legality = SceneTransitionLegality.check_transition_legal(
            "scene_b", "scene_a", simple_module
        )
        assert not legality.allowed
        assert "reachable" in legality.reason.lower()

    def test_unknown_scene_illegal(self, simple_module, session_a):
        """Unknown scene is illegal via canonical rules."""
        legality = SceneTransitionLegality.check_transition_legal(
            "scene_a", "unknown_scene", simple_module
        )
        assert not legality.allowed
        assert "not in module" in legality.reason

    def test_validator_uses_canonical_legality(self, simple_module, session_a):
        """Validator uses SceneTransitionLegality for checks."""
        from app.runtime.turn_executor import MockDecision

        # Valid transition
        decision = MockDecision(proposed_scene_id="scene_b", proposed_deltas=[])
        outcome = validate_decision(decision, session_a, simple_module)
        assert outcome.is_valid

        # Invalid scene
        decision = MockDecision(proposed_scene_id="unknown", proposed_deltas=[])
        outcome = validate_decision(decision, session_a, simple_module)
        assert not outcome.is_valid


class TestEndingLegalityCoherence:
    """Ending legality is checked via canonical SceneTransitionLegality."""

    @pytest.fixture
    def ending_module(self):
        """Module with one unconditional ending."""
        metadata = ModuleMetadata(
            module_id="ending_test",
            title="Ending Test",
            version="0.1.0",
            contract_version="1.0.0",
        )

        scenes = {
            "play": ScenePhase(id="play", name="Play", sequence=1, description="Gameplay"),
        }

        endings = {
            "end_default": EndingCondition(
                id="end_default",
                name="Default",
                description="Default ending",
                trigger_conditions=[],
                outcome={"type": "default"},
            ),
        }

        return ContentModule(
            metadata=metadata,
            scene_phases=scenes,
            phase_transitions={},
            ending_conditions=endings,
            characters={},
            relationship_axes={},
            triggers={},
            assertions={},
        )

    @pytest.fixture
    def session_in_play(self):
        """Session in play scene."""
        return SessionState(
            session_id="test",
            module_id="ending_test",
            module_version="0.1.0",
            current_scene_id="play",
            status=SessionStatus.ACTIVE,
            canonical_state={},
        )

    def test_unconditional_ending_legal(self, ending_module, session_in_play):
        """Unconditional ending is legal via canonical rules."""
        ending_id, legality = SceneTransitionLegality.check_ending_legal(
            ending_module, session=session_in_play, detected_triggers=[]
        )
        assert ending_id == "end_default"
        assert legality.allowed

    def test_no_ending_when_none_defined(self):
        """No ending available when module has no endings."""
        module = ContentModule(
            metadata=ModuleMetadata(
                module_id="no_endings",
                title="No Endings",
                version="0.1.0",
                contract_version="1.0.0",
            ),
            scene_phases={"s": ScenePhase(id="s", name="S", sequence=1, description="")},
            phase_transitions={},
            ending_conditions={},
            characters={},
            relationship_axes={},
            triggers={},
            assertions={},
        )
        ending_id, legality = SceneTransitionLegality.check_ending_legal(
            module, detected_triggers=[]
        )
        assert ending_id is None
        assert not legality.allowed


class TestConditionalTransitionCoherence:
    """Validator and derivation are coherent for conditional transitions."""

    @pytest.fixture
    def conditional_module(self):
        """Module with only conditional transition from s2 to s3."""
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

        # ONLY conditional transition from s2 to s3 (no unconditional path)
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
    def session_s2(self):
        """Session at s2."""
        return SessionState(
            session_id="test",
            module_id="conditional",
            module_version="0.1.0",
            current_scene_id="s2",
            status=SessionStatus.ACTIVE,
            canonical_state={},
        )

    def test_validator_rejects_conditional_without_evidence(
        self, conditional_module, session_s2
    ):
        """Validator rejects conditional transition when trigger evidence unavailable."""
        # Validator checks with detected_triggers=None (no trigger evidence)
        legality = SceneTransitionLegality.check_transition_legal(
            "s2", "s3", conditional_module, detected_triggers=None
        )
        assert not legality.allowed
        assert "undefined" in legality.reason.lower() or "cannot" in legality.reason.lower()

    def test_validator_rejects_conditional_without_triggers(
        self, conditional_module, session_s2
    ):
        """Validator rejects conditional transition when required triggers not detected."""
        # Validator checks with empty detected_triggers (triggers detected but not the one needed)
        legality = SceneTransitionLegality.check_transition_legal(
            "s2", "s3", conditional_module, detected_triggers=[]
        )
        assert not legality.allowed
        assert "missing" in legality.reason.lower()

    def test_validator_accepts_conditional_with_triggers(
        self, conditional_module, session_s2
    ):
        """Validator accepts conditional transition when all required triggers detected."""
        legality = SceneTransitionLegality.check_transition_legal(
            "s2", "s3", conditional_module, detected_triggers=["unlock"]
        )
        assert legality.allowed

    def test_derivation_coherent_with_validator(
        self, conditional_module, session_s2
    ):
        """Derivation reaches same conclusion as validator for conditional transition."""
        # Scenario 1: No trigger evidence (validator time)
        validator_legality = SceneTransitionLegality.check_transition_legal(
            "s2", "s3", conditional_module, detected_triggers=None
        )
        assert not validator_legality.allowed

        # Scenario 2: Trigger not detected (derivation with empty triggers)
        derivation_legality_no_trigger = SceneTransitionLegality.check_transition_legal(
            "s2", "s3", conditional_module, detected_triggers=[]
        )
        assert not derivation_legality_no_trigger.allowed

        # Scenario 3: Trigger detected (derivation with trigger)
        derivation_legality_with_trigger = SceneTransitionLegality.check_transition_legal(
            "s2", "s3", conditional_module, detected_triggers=["unlock"]
        )
        assert derivation_legality_with_trigger.allowed

    def test_validator_api_call_rejects_conditional(
        self, conditional_module, session_s2
    ):
        """validate_decision rejects conditional transition (validator path)."""
        from app.runtime.turn_executor import MockDecision

        # Validator calls with detected_triggers=None
        decision = MockDecision(proposed_scene_id="s3", proposed_deltas=[])
        outcome = validate_decision(decision, session_s2, conditional_module)
        assert not outcome.is_valid
        assert any("scene" in e.lower() for e in outcome.errors)


class TestNoIllegalNarrativeForcing:
    """Core requirement: AI cannot force illegal narrative progression."""

    @pytest.fixture
    def gated_module(self):
        """Module with mixed transitions (conditional and unconditional paths)."""
        metadata = ModuleMetadata(
            module_id="gated",
            title="Gated",
            version="0.1.0",
            contract_version="1.0.0",
        )

        scenes = {
            "s1": ScenePhase(id="s1", name="S1", sequence=1, description=""),
            "s2": ScenePhase(id="s2", name="S2", sequence=2, description=""),
            "s3": ScenePhase(id="s3", name="S3", sequence=3, description=""),
        }

        transitions = {
            "t": PhaseTransition(
                id="t",
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
    def session_s2(self):
        """Session at s2."""
        return SessionState(
            session_id="test",
            module_id="gated",
            module_version="0.1.0",
            current_scene_id="s2",
            status=SessionStatus.ACTIVE,
            canonical_state={},
        )

    def test_validator_rejects_unreachable_scene(self, gated_module, session_s2):
        """Validator blocks jump to unreachable scene (no direct transition)."""
        from app.runtime.turn_executor import MockDecision

        # No transition exists from s2 to s1
        decision = MockDecision(proposed_scene_id="s1", proposed_deltas=[])
        outcome = validate_decision(decision, session_s2, gated_module)
        assert not outcome.is_valid
        assert any("reachable" in e.lower() for e in outcome.errors)


class TestTurnExecutorLegalityEnforcement:
    """Verify actual turn execution enforces canonical legality (W2.2.4 runtime repair)."""

    @pytest.fixture
    def conditional_module(self):
        """Module with only conditional transition from s2 to s3."""
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
    def session_s2(self):
        """Session at s2."""
        return SessionState(
            session_id="test",
            module_id="conditional",
            module_version="0.1.0",
            current_scene_id="s2",
            status=SessionStatus.ACTIVE,
            canonical_state={},
        )

    def test_execute_turn_applies_legal_scene_transition(self, conditional_module, session_s2):
        """execute_turn applies scene transition when canonical legality check passes."""
        import asyncio
        from app.runtime.turn_executor import MockDecision, execute_turn

        # Propose transition s2->s3 with required trigger detected
        decision = MockDecision(
            proposed_scene_id="s3",
            proposed_deltas=[],
            detected_triggers=["unlock"],  # Provides required trigger evidence
        )

        result = asyncio.run(
            execute_turn(session_s2, 1, decision, module=conditional_module)
        )

        assert result.execution_status == "success"
        assert result.updated_scene_id == "s3"
        assert any(e.event_type == "scene_changed" for e in result.events)

    def test_execute_turn_blocks_illegal_scene_transition(self, conditional_module, session_s2):
        """execute_turn blocks scene transition when canonical legality check fails."""
        import asyncio
        from app.runtime.turn_executor import MockDecision, execute_turn

        # Propose transition s2->s3 WITHOUT required trigger
        decision = MockDecision(
            proposed_scene_id="s3",
            proposed_deltas=[],
            detected_triggers=[],  # Missing required "unlock" trigger
        )

        result = asyncio.run(
            execute_turn(session_s2, 1, decision, module=conditional_module)
        )

        assert result.execution_status == "success"
        # Scene should NOT change because legality check failed
        assert result.updated_scene_id == "s2"
        # Should log scene_transition_blocked event
        assert any(e.event_type == "scene_transition_blocked" for e in result.events)

    def test_execute_turn_allows_legal_conditional_transition(self, conditional_module, session_s2):
        """Validator and executor are now coherent: both use actual detected_triggers (W2.2.4 repair).

        With the W2.2.4 repair (Option A), validation-time scene legality checks are now
        trigger-aware. Both validator and executor use decision.detected_triggers,
        ensuring coherent semantics.
        """
        import asyncio
        from app.runtime.turn_executor import MockDecision, execute_turn

        # This transition is now legal at both validation time and execution time
        # because the validator uses the actual detected_triggers from the decision
        decision = MockDecision(
            proposed_scene_id="s3",
            proposed_deltas=[],
            detected_triggers=["unlock"],  # Available at both validation and execution time
        )

        # Validator now accepts this (uses actual triggers)
        from app.runtime.validators import validate_decision
        validation = validate_decision(decision, session_s2, conditional_module)
        assert validation.is_valid  # Validator accepts (coherent with executor)

        # Executor also accepts it (uses actual triggers)
        result = asyncio.run(
            execute_turn(session_s2, 1, decision, module=conditional_module)
        )
        assert result.execution_status == "success"
        assert result.updated_scene_id == "s3"  # Both agree: transition is legal

    def test_ending_legality_checked_in_execution(self, conditional_module, session_s2):
        """Turn execution checks ending legality and includes it in result."""
        import asyncio
        from app.runtime.turn_executor import MockDecision, execute_turn
        from app.content.module_models import EndingCondition

        # Create module with unconditional ending
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

        result = asyncio.run(
            execute_turn(session_s2, 1, decision, module=ending_module)
        )

        assert result.execution_status == "success"
        # Unconditional ending should be detected
        assert result.updated_ending_id == "end_default"
        assert any(e.event_type == "ending_triggered" for e in result.events)
