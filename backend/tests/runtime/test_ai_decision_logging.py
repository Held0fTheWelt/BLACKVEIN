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
from app.runtime.w2_models import (
    AIDecisionLog,
    AIValidationOutcome,
    DirectorDiagnosticSummary,
    GuardOutcome,
    InterpreterDiagnosticSummary,
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
