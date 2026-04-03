"""Tests for W2.4.4 AI decision logging with role diagnostics."""

import pytest
from app.runtime.ai_decision import ParsedAIDecision
from app.runtime.ai_decision_logging import construct_ai_decision_log
from app.runtime.role_contract import (
    DirectorSection,
    InterpreterSection,
    ResponderSection,
)
from app.runtime.role_structured_decision import ParsedRoleAwareDecision
from app.runtime.runtime_models import (
    AIDecisionLog,
    AIValidationOutcome,
    DirectorDiagnosticSummary,
    DeltaType,
    GuardOutcome,
    InterpreterDiagnosticSummary,
    StateDelta,
)


def test_interpreter_diagnostic_summary_creation():
    """InterpreterDiagnosticSummary can be created with scene_reading and detected_tensions."""
    summary = InterpreterDiagnosticSummary(
        scene_reading="The characters are in conflict over resources.",
        detected_tensions=["resource_competition", "power_struggle"],
    )

    assert summary.scene_reading == "The characters are in conflict over resources."
    assert summary.detected_tensions == ["resource_competition", "power_struggle"]


def test_director_diagnostic_summary_creation():
    """DirectorDiagnosticSummary can be created with conflict_steering and recommended_direction."""
    summary = DirectorDiagnosticSummary(
        conflict_steering="Escalate the tension to force a confrontation.",
        recommended_direction="escalate",
    )

    assert summary.conflict_steering == "Escalate the tension to force a confrontation."
    assert summary.recommended_direction == "escalate"


def test_director_diagnostic_summary_validates_direction_enum():
    """DirectorDiagnosticSummary only accepts valid recommended_direction values."""
    valid_directions = ["escalate", "stabilize", "shift_alliance", "redirect", "hold"]

    for direction in valid_directions:
        summary = DirectorDiagnosticSummary(
            conflict_steering="text",
            recommended_direction=direction,
        )
        assert summary.recommended_direction == direction


def test_ai_decision_log_accepts_role_fields():
    """AIDecisionLog accepts interpreter_output, director_output, responder_output, guard_outcome."""
    interpreter = InterpreterDiagnosticSummary(
        scene_reading="Scene reading",
        detected_tensions=["tension1"],
    )
    director = DirectorDiagnosticSummary(
        conflict_steering="Steering text",
        recommended_direction="hold",
    )

    log = AIDecisionLog(
        session_id="sess1",
        turn_number=1,
        raw_output="mock output",
        guard_outcome=GuardOutcome.ACCEPTED,
        interpreter_output=interpreter,
        director_output=director,
        responder_output=None,
    )

    assert log.interpreter_output == interpreter
    assert log.director_output == director
    assert log.responder_output is None
    assert log.guard_outcome == GuardOutcome.ACCEPTED


def test_construct_log_legacy_parsing_has_none_role_fields():
    """Legacy ParsedAIDecision only → role fields = None."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene interpretation",
        detected_triggers=["trigger1"],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale text",
        raw_output="raw output",
        parsed_source="structured_payload",
    )

    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw output",
        role_aware_decision=None,  # Legacy path
        guard_outcome=GuardOutcome.ACCEPTED,
    )

    assert log.session_id == "sess1"
    assert log.turn_number == 1
    assert log.interpreter_output is None  # Legacy → None
    assert log.director_output is None     # Legacy → None
    assert log.responder_output is None    # Legacy → None
    assert log.guard_outcome == GuardOutcome.ACCEPTED


def test_construct_log_role_structured_parsing_populates_role_fields():
    """ParsedRoleAwareDecision present → role fields populated."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=["trigger1"],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    # Create mock role-aware decision with all required fields
    role_aware = ParsedRoleAwareDecision(
        interpreter=InterpreterSection(
            scene_reading="Scene reading from interpreter",
            detected_tensions=["tension1", "tension2"],
            trigger_candidates=["candidate1"],  # Required field
        ),
        director=DirectorSection(
            conflict_steering="Steering rationale",
            escalation_level=5,
            recommended_direction="escalate",
        ),
        responder=ResponderSection(),  # Has defaults for optional fields
        parsed_decision=parsed_decision,
    )

    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=role_aware,
        guard_outcome=GuardOutcome.ACCEPTED,
    )

    # Role fields should be populated
    assert log.interpreter_output is not None
    assert log.interpreter_output.scene_reading == "Scene reading from interpreter"
    assert log.interpreter_output.detected_tensions == ["tension1", "tension2"]

    assert log.director_output is not None
    assert log.director_output.conflict_steering == "Steering rationale"
    assert log.director_output.recommended_direction == "escalate"

    assert log.responder_output is not None


def test_validation_outcome_mapping_accepted():
    """GuardOutcome.ACCEPTED → AIValidationOutcome.ACCEPTED."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,
        guard_outcome=GuardOutcome.ACCEPTED,
    )

    assert log.validation_outcome == AIValidationOutcome.ACCEPTED


def test_validation_outcome_mapping_rejected():
    """GuardOutcome.REJECTED → AIValidationOutcome.REJECTED."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,
        guard_outcome=GuardOutcome.REJECTED,
    )

    assert log.validation_outcome == AIValidationOutcome.REJECTED


def test_validation_outcome_mapping_partially_accepted():
    """GuardOutcome.PARTIALLY_ACCEPTED → AIValidationOutcome.PARTIAL."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,
        guard_outcome=GuardOutcome.PARTIALLY_ACCEPTED,
    )

    assert log.validation_outcome == AIValidationOutcome.PARTIAL


def test_validation_outcome_mapping_structurally_invalid():
    """GuardOutcome.STRUCTURALLY_INVALID → AIValidationOutcome.ERROR."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,
        guard_outcome=GuardOutcome.STRUCTURALLY_INVALID,
    )

    assert log.validation_outcome == AIValidationOutcome.ERROR


def test_role_fields_do_not_affect_delta_validation():
    """Role fields present or absent should not change delta acceptance/rejection."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=["trigger1"],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    mock_delta = StateDelta(
        delta_type=DeltaType.CHARACTER_STATE,
        target_path="characters.alice.emotional_state",
        previous_value=50,
        next_value=75,
        source="ai_proposal",
    )

    # Create role-aware decision
    role_aware = ParsedRoleAwareDecision(
        interpreter=InterpreterSection(
            scene_reading="Scene", detected_tensions=[], trigger_candidates=[]
        ),
        director=DirectorSection(
            conflict_steering="Steering", escalation_level=5, recommended_direction="hold"
        ),
        responder=ResponderSection(),
        parsed_decision=parsed_decision,
    )

    # Log WITH role fields
    log_with_roles = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=role_aware,  # Role fields POPULATED
        guard_outcome=GuardOutcome.ACCEPTED,
        accepted_deltas=[mock_delta],
    )

    # Log WITHOUT role fields
    log_without_roles = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,  # Role fields NOT populated
        guard_outcome=GuardOutcome.ACCEPTED,
        accepted_deltas=[mock_delta],
    )

    # Both logs must have identical delta collections despite different role fields
    assert log_with_roles.accepted_deltas == log_without_roles.accepted_deltas
    assert len(log_with_roles.accepted_deltas) == len(log_without_roles.accepted_deltas)


def test_guard_outcome_remains_canonical():
    """guard_outcome is the sole canonical validation result, not overridden."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    # Test all guard_outcome values
    for guard_outcome in [
        GuardOutcome.ACCEPTED,
        GuardOutcome.PARTIALLY_ACCEPTED,
        GuardOutcome.REJECTED,
        GuardOutcome.STRUCTURALLY_INVALID,
    ]:
        log = construct_ai_decision_log(
            session_id="sess1",
            turn_number=1,
            parsed_decision=parsed_decision,
            raw_output="raw",
            role_aware_decision=None,
            guard_outcome=guard_outcome,
        )

        # guard_outcome must be preserved exactly
        assert log.guard_outcome == guard_outcome


def test_backward_compatibility_legacy_decisions_still_work():
    """Legacy decisions (ParsedAIDecision only) work unchanged."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    # Create log as if from W2.4.3 parsing (no role-structured output)
    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,  # Legacy path
        guard_outcome=GuardOutcome.ACCEPTED,
    )

    # Log should be created successfully
    assert log.id is not None
    assert log.session_id == "sess1"
    assert log.turn_number == 1

    # Legacy logs have no role fields
    assert log.interpreter_output is None
    assert log.director_output is None
    assert log.responder_output is None

    # Guard outcome preserved
    assert log.guard_outcome == GuardOutcome.ACCEPTED


def test_parsed_ai_decision_fields_unchanged():
    """Verify ParsedAIDecision model was not modified by W2.4.4."""
    from app.runtime.ai_decision import ParsedAIDecision

    # Expected fields from W2.1.3 spec (should not change in W2.4.4)
    expected_fields = {
        "scene_interpretation",
        "detected_triggers",
        "proposed_deltas",
        "proposed_scene_id",
        "rationale",
        "dialogue_impulses",
        "conflict_vector",
        "confidence",
        "raw_output",
        "parsed_source",
    }

    actual_fields = set(ParsedAIDecision.model_fields.keys())
    assert actual_fields == expected_fields, (
        f"ParsedAIDecision should not be modified in W2.4.4. "
        f"Expected {expected_fields}, got {actual_fields}"
    )


def test_guard_outcome_and_validation_outcome_semantics():
    """Verify guard_outcome is sole canonical validation truth, validation_outcome derived."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    # For each guard_outcome state, validation_outcome must be correctly derived
    test_cases = [
        (GuardOutcome.ACCEPTED, AIValidationOutcome.ACCEPTED),
        (GuardOutcome.PARTIALLY_ACCEPTED, AIValidationOutcome.PARTIAL),
        (GuardOutcome.REJECTED, AIValidationOutcome.REJECTED),
        (GuardOutcome.STRUCTURALLY_INVALID, AIValidationOutcome.ERROR),
    ]

    for guard_outcome, expected_validation_outcome in test_cases:
        log = construct_ai_decision_log(
            session_id="sess1",
            turn_number=1,
            parsed_decision=parsed_decision,
            raw_output="raw",
            role_aware_decision=None,
            guard_outcome=guard_outcome,
        )

        # guard_outcome preserved as-is
        assert log.guard_outcome == guard_outcome
        # validation_outcome derived from guard_outcome
        assert log.validation_outcome == expected_validation_outcome


def test_construct_log_accepts_optional_tool_loop_fields():
    """construct_ai_decision_log stores optional tool-loop diagnostics."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,
        guard_outcome=GuardOutcome.ACCEPTED,
        tool_loop_summary={"enabled": True, "total_calls": 1},
        tool_call_transcript=[{"tool_name": "wos.read.current_scene", "status": "success"}],
        tool_influence={"influencing_tool_sequence": 1},
    )

    assert log.tool_loop_summary == {"enabled": True, "total_calls": 1}
    assert isinstance(log.tool_call_transcript, list)
    assert log.tool_influence == {"influencing_tool_sequence": 1}


def test_construct_log_accepts_preview_diagnostics():
    """construct_ai_decision_log stores optional preview diagnostics."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )
    preview_diagnostics = {
        "preview_count": 1,
        "last_preview": {"guard_outcome": "rejected", "accepted_delta_count": 0, "rejected_delta_count": 1},
        "revised_after_preview": True,
        "improved_acceptance_vs_last_preview": True,
    }

    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,
        guard_outcome=GuardOutcome.ACCEPTED,
        preview_diagnostics=preview_diagnostics,
    )
    assert log.preview_diagnostics == preview_diagnostics
