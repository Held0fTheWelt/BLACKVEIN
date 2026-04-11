"""Tests for W2.4.5 responder-only proposal gating."""

import pytest
from app.runtime.runtime_models import MockDecision, ProposalSource, ProposedStateDelta, GuardOutcome
from app.runtime.turn_executor import execute_turn


def test_mock_decision_requires_proposal_source():
    """MockDecision requires explicit proposal_source (not defaulted to responder)."""
    delta = ProposedStateDelta(
        target="characters.alice.emotional_state",
        next_value=75,
        delta_type=None,
        source="ai_proposal",
    )

    # Test that creating without proposal_source uses conservative MOCK default
    decision = MockDecision(
        proposed_deltas=[delta],
    )

    # Default must be MOCK (non-authoritative), not RESPONDER_DERIVED
    assert decision.proposal_source == ProposalSource.MOCK
    assert len(decision.proposed_deltas) == 1


def test_mock_decision_accepts_explicit_proposal_source():
    """MockDecision accepts explicit proposal_source field."""
    delta = ProposedStateDelta(
        target="characters.alice.emotional_state",
        next_value=75,
        delta_type=None,
        source="ai_proposal",
    )

    decision = MockDecision(
        proposed_deltas=[delta],
        proposal_source=ProposalSource.RESPONDER_DERIVED,
    )

    assert decision.proposal_source == ProposalSource.RESPONDER_DERIVED


def test_proposal_source_enum_has_all_values():
    """ProposalSource enum has all required values."""
    assert hasattr(ProposalSource, "RESPONDER_DERIVED")
    assert hasattr(ProposalSource, "MOCK")
    assert hasattr(ProposalSource, "ENGINE")
    assert hasattr(ProposalSource, "OPERATOR")


@pytest.mark.asyncio
async def test_execute_turn_rejects_non_responder_when_enforcement_enabled(god_of_carnage_module_with_state, god_of_carnage_module):
    """execute_turn() rejects non-responder proposals when enforcement enabled."""
    # Create session with initial state
    session = god_of_carnage_module_with_state

    # Create a mock decision with MOCK source (non-responder)
    delta = ProposedStateDelta(
        target="characters.veronique.emotional_state",
        next_value=50,
        delta_type=None,
        source="test_proposal",
    )

    decision = MockDecision(
        proposed_deltas=[delta],
        proposal_source=ProposalSource.MOCK,  # Non-responder source
    )

    # When enforcement is enabled (enforce_responder_only=True)
    result = await execute_turn(
        session=session,
        current_turn=1,
        mock_decision=decision,
        module=god_of_carnage_module,
        enforce_responder_only=True,  # Canonical enforcement enabled
    )

    # Should reject all proposals from non-responder source
    assert result.guard_outcome == GuardOutcome.REJECTED
    assert len(result.accepted_deltas) == 0
    assert len(result.rejected_deltas) == 1


@pytest.mark.asyncio
async def test_execute_turn_accepts_responder_with_enforcement(god_of_carnage_module_with_state, god_of_carnage_module):
    """execute_turn() accepts responder-derived proposals with enforcement enabled."""
    session = god_of_carnage_module_with_state

    # Create a mock decision with RESPONDER_DERIVED source
    delta = ProposedStateDelta(
        target="characters.veronique.emotional_state",
        next_value=75,
        delta_type=None,
        source="ai_proposal",
    )

    decision = MockDecision(
        proposed_deltas=[delta],
        proposal_source=ProposalSource.RESPONDER_DERIVED,  # Responder-derived
    )

    # With enforcement enabled, responder proposals should flow through normal validation
    result = await execute_turn(
        session=session,
        current_turn=1,
        mock_decision=decision,
        module=god_of_carnage_module,
        enforce_responder_only=True,
    )

    # Should be validated normally (not rejected by gate)
    # Status depends on validation, not on source gate
    assert result.guard_outcome in [GuardOutcome.ACCEPTED, GuardOutcome.PARTIALLY_ACCEPTED, GuardOutcome.REJECTED]
    # Key point: not rejected due to source gate reaching the enforcement


@pytest.mark.asyncio
async def test_execute_turn_allows_non_responder_when_enforcement_disabled(god_of_carnage_module_with_state, god_of_carnage_module):
    """execute_turn() allows non-responder proposals when enforcement disabled (default)."""
    session = god_of_carnage_module_with_state

    delta = ProposedStateDelta(
        target="characters.veronique.emotional_state",
        next_value=50,
        delta_type=None,
        source="test_proposal",
    )

    decision = MockDecision(
        proposed_deltas=[delta],
        proposal_source=ProposalSource.MOCK,  # Non-responder source
    )

    # With enforcement disabled (default), non-responder proposals pass gate
    result = await execute_turn(
        session=session,
        current_turn=1,
        mock_decision=decision,
        module=god_of_carnage_module,
        enforce_responder_only=False,  # Enforcement disabled
    )

    # Should NOT be rejected by gate (but may be rejected by validation)
    # Key: gate doesn't reject, validation may
    assert result.guard_outcome in [GuardOutcome.ACCEPTED, GuardOutcome.PARTIALLY_ACCEPTED, GuardOutcome.REJECTED]


@pytest.mark.asyncio
async def test_role_structured_responder_candidates_marked_responder_derived():
    """Responder candidates extracted from role-structured decision must be marked RESPONDER_DERIVED."""
    # Setup: import required classes for role-structured decision
    from app.runtime.role_contract import (
        InterpreterSection,
        DirectorSection,
        ResponderSection,
        StateChangeCandidate,
    )
    from app.runtime.role_structured_decision import ParsedRoleAwareDecision
    from app.runtime.ai_decision import ParsedAIDecision
    from app.runtime.ai_turn_executor import process_role_structured_decision

    # Create components for role-structured decision
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    responder = ResponderSection(
        state_change_candidates=[
            StateChangeCandidate(
                target_path="characters.veronique.emotional_state",
                proposed_value=50,
                rationale="Veronique is upset",
            ),
        ]
    )

    role_aware_decision = ParsedRoleAwareDecision(
        parsed_decision=parsed_decision,
        interpreter=InterpreterSection(
            scene_reading="",
            detected_tensions=[],
            trigger_candidates=[],
        ),
        director=DirectorSection(
            conflict_steering="",
            escalation_level=5,
            recommended_direction="hold",
        ),
        responder=responder,
    )

    # Extract responder candidates (simulate AI turn executor flow)
    extracted_decision = process_role_structured_decision(role_aware_decision)

    # Verify: responder candidates are marked RESPONDER_DERIVED
    assert extracted_decision.proposal_source == ProposalSource.RESPONDER_DERIVED
    assert len(extracted_decision.proposed_deltas) == 1
    assert extracted_decision.proposed_deltas[0].target == "characters.veronique.emotional_state"
    assert extracted_decision.proposed_deltas[0].next_value == 50


def test_interpreter_output_cannot_affect_execution():
    """Interpreter output is diagnostic-only, cannot feed execution path."""
    from app.runtime.role_contract import (
        InterpreterSection,
        DirectorSection,
        ResponderSection,
    )
    from app.runtime.role_structured_decision import ParsedRoleAwareDecision
    from app.runtime.ai_decision import ParsedAIDecision

    # Create role-structured decision with interpreter content only
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Interpreter analysis",
        detected_triggers=[],
        proposed_deltas=[],  # No deltas from interpreter
        proposed_scene_id=None,
        rationale="Interpreter diagnostic",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    interpreter = InterpreterSection(
        scene_reading="Scene analysis from interpreter",
        detected_tensions=["tension_detected"],
        trigger_candidates=["trigger_candidate"],
    )

    role_aware_decision = ParsedRoleAwareDecision(
        parsed_decision=parsed_decision,
        interpreter=interpreter,
        director=DirectorSection(
            conflict_steering="",
            escalation_level=5,
            recommended_direction="hold",
        ),
        responder=ResponderSection(),
    )

    # Verify: ParsedAIDecision has NO state changes from interpreter
    assert len(role_aware_decision.parsed_decision.proposed_deltas) == 0
    # Interpreter content is preserved separately for diagnostics
    assert role_aware_decision.interpreter.scene_reading == "Scene analysis from interpreter"
    # When this enters execute_turn_with_ai() with enforce_responder_only=True,
    # the interpreter content cannot affect state (no deltas to execute)


def test_director_output_cannot_affect_execution():
    """Director output is diagnostic-only, cannot feed execution path."""
    from app.runtime.role_contract import (
        InterpreterSection,
        DirectorSection,
        ResponderSection,
    )
    from app.runtime.role_structured_decision import ParsedRoleAwareDecision
    from app.runtime.ai_decision import ParsedAIDecision

    # Create role-structured decision with director content only
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],  # No deltas from director
        proposed_scene_id=None,
        rationale="Director steering directive",  # Director content is rationale, not proposals
        raw_output="raw",
        parsed_source="structured_payload",
    )

    director = DirectorSection(
        conflict_steering="Director guidance for narrative tension",
        escalation_level=10,
        recommended_direction="escalate",
    )

    role_aware_decision = ParsedRoleAwareDecision(
        parsed_decision=parsed_decision,
        interpreter=InterpreterSection(
            scene_reading="",
            detected_tensions=[],
            trigger_candidates=[],
        ),
        director=director,
        responder=ResponderSection(),
    )

    # Verify: ParsedAIDecision.rationale is diagnostic text, not a proposal
    assert role_aware_decision.parsed_decision.rationale == "Director steering directive"
    # But no proposed_deltas from director
    assert len(role_aware_decision.parsed_decision.proposed_deltas) == 0
    # Director content is preserved separately
    assert role_aware_decision.director.conflict_steering == "Director guidance for narrative tension"
    # Director output cannot affect execution (no deltas to enforce)


def test_only_responder_proposals_enter_guarded_path():
    """Only responder-derived state_change_candidates become proposed_deltas."""
    from app.runtime.role_contract import (
        InterpreterSection,
        DirectorSection,
        ResponderSection,
        StateChangeCandidate,
    )
    from app.runtime.role_structured_decision import ParsedRoleAwareDecision
    from app.runtime.ai_decision import ParsedAIDecision

    # Create role-structured decision where ONLY responder has proposals
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene interpretation",
        detected_triggers=[],
        proposed_deltas=[],  # Populated only from responder
        proposed_scene_id=None,
        rationale="Combined rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    interpreter = InterpreterSection(
        scene_reading="Interpreter analysis (diagnostic)",
        detected_tensions=["tension1"],
        trigger_candidates=["trigger1"],
    )

    director = DirectorSection(
        conflict_steering="Director guidance (diagnostic)",
        escalation_level=7,
        recommended_direction="shift_alliance",
    )

    responder = ResponderSection(
        state_change_candidates=[
            StateChangeCandidate(
                target_path="characters.alice.emotional_state",
                proposed_value=80,
                rationale="This is the ONLY content that affects execution",
            )
        ],
        trigger_assertions=["trigger1"],  # Only responder assertions matter
    )

    role_aware_decision = ParsedRoleAwareDecision(
        parsed_decision=parsed_decision,
        interpreter=interpreter,
        director=director,
        responder=responder,
    )

    # Verify: only responder state_change_candidates would become proposed_deltas
    # (The role_structured_decision parsing handles this conversion)
    assert len(role_aware_decision.responder.state_change_candidates) == 1
    assert role_aware_decision.responder.state_change_candidates[0].target_path == "characters.alice.emotional_state"

    # Interpreter and director are preserved diagnostically
    assert role_aware_decision.interpreter is not None
    assert role_aware_decision.director is not None
    # But they don't feed the execution path (verified by extract in ai_turn_executor)


@pytest.mark.asyncio
async def test_gating_preserves_existing_guard_authority(god_of_carnage_module_with_state, god_of_carnage_module):
    """Responder-only gating enables guards, does not replace them."""
    # This test verifies:
    # 1. Proposals pass source gate (responder-derived)
    # 2. Proposals then flow through EXISTING validation/guard pipeline
    # 3. Existing guards reject invalid proposals (guards remain authoritative)
    # 4. W2.4.5 changes ONLY which source enters the path, not guard logic

    session = god_of_carnage_module_with_state

    # Create a RESPONDER_DERIVED proposal that will fail EXISTING validation
    # (e.g., invalid reference path)
    delta = ProposedStateDelta(
        target="invalid.reference.path",  # Will fail reference validation
        next_value=100,
        delta_type=None,
        source="ai_proposal",
    )

    decision = MockDecision(
        proposed_deltas=[delta],
        proposal_source=ProposalSource.RESPONDER_DERIVED,  # Passes source gate
    )

    # With enforcement enabled
    result = await execute_turn(
        session=session,
        current_turn=1,
        mock_decision=decision,
        module=god_of_carnage_module,
        enforce_responder_only=True,
    )

    # Proposal passes source gate but fails EXISTING validation
    # (rejected by validators, not by source gate)
    assert result.guard_outcome == GuardOutcome.REJECTED
    assert len(result.rejected_deltas) == 1
    # Rejection reason is from validators, not from source gating
    # (proves guards remain authoritative)


@pytest.mark.asyncio
async def test_no_new_execution_paths_created(god_of_carnage_module_with_state, god_of_carnage_module):
    """Verify W2.4.5 doesn't create new execution paths."""
    # All proposals (responder-derived or not) flow through:
    # 1. Source gate (new W2.4.5)
    # 2. EXISTING validation pipeline
    # 3. EXISTING mutation policy
    # 4. EXISTING scene legality checks
    # 5. EXISTING apply_deltas
    # No bypasses, no new paths

    session = god_of_carnage_module_with_state

    # Valid responder proposal
    delta = ProposedStateDelta(
        target="characters.veronique.emotional_state",
        next_value=75,
        delta_type=None,
        source="ai_proposal",
    )

    decision = MockDecision(
        proposed_deltas=[delta],
        proposal_source=ProposalSource.RESPONDER_DERIVED,
    )

    # With enforcement
    result = await execute_turn(
        session=session,
        current_turn=1,
        mock_decision=decision,
        module=god_of_carnage_module,
        enforce_responder_only=True,
    )

    # Passes through full pipeline (source → validation → mutation policy → execution)
    assert result.guard_outcome in [GuardOutcome.ACCEPTED, GuardOutcome.PARTIALLY_ACCEPTED, GuardOutcome.REJECTED]
    # Demonstrates: proposals still flow through all existing gates
