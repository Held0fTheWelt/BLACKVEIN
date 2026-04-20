"""Tests for W2.1.3 parse, normalize, and pre-validate AI output pipeline.

Verifies that:
- Raw adapter output can be parsed into StructuredAIStoryOutput
- Parsed output can be normalized into ParsedAIDecision
- Pre-validation catches obvious errors before runtime validation
- Diagnostics (raw output, parse source) are preserved throughout
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.runtime.ai_adapter import AdapterResponse
from app.runtime.ai_decision import (
    ParseResult,
    ParsedAIDecision,
    parse_adapter_response,
    prevalidate_decision,
    normalize_structured_output,
    process_adapter_response,
)
from app.runtime.ai_output import (
    ConflictVector,
    DialogueImpulse,
    ProposedDelta,
    StructuredAIStoryOutput,
)


class TestParseAdapterResponse:
    """Test parse_adapter_response() for parsing raw adapter output."""

    def test_parse_valid_structured_payload_succeeds(self):
        """Valid structured payload parses into ParseResult with success=True."""
        payload = {
            "scene_interpretation": "Scene interpretation text",
            "detected_triggers": ["trigger1", "trigger2"],
            "proposed_state_deltas": [],
            "rationale": "Rationale text",
        }
        response = AdapterResponse(
            raw_output="raw text",
            structured_payload=payload,
        )

        result = parse_adapter_response(response)

        assert result.success is True
        assert result.decision is not None
        assert result.errors == []
        assert result.raw_output == "raw text"

    def test_parse_returns_parsed_decision_on_success(self):
        """Successful parse returns ParsedAIDecision in result.decision."""
        payload = {
            "scene_interpretation": "Scene text",
            "detected_triggers": ["trigger1"],
            "proposed_state_deltas": [],
            "rationale": "Rationale text",
        }
        response = AdapterResponse(
            raw_output="raw",
            structured_payload=payload,
        )

        result = parse_adapter_response(response)

        assert isinstance(result.decision, ParsedAIDecision)
        assert result.decision.scene_interpretation == "Scene text"
        assert result.decision.detected_triggers == ["trigger1"]
        assert result.decision.rationale == "Rationale text"

    def test_parse_adapter_error_fails_immediately(self):
        """Adapter error response fails with is_error=True."""
        response = AdapterResponse(
            raw_output="raw",
            error="Adapter failed",
        )

        result = parse_adapter_response(response)

        assert result.success is False
        assert result.decision is None
        assert len(result.errors) == 1
        assert "Adapter error" in result.errors[0]

    def test_parse_none_structured_payload_fails(self):
        """None structured_payload fails with clear error."""
        response = AdapterResponse(
            raw_output="raw",
            structured_payload=None,
        )

        result = parse_adapter_response(response)

        assert result.success is False
        assert result.decision is None
        assert "No structured_payload" in result.errors[0]

    def test_parse_non_dict_structured_payload_fails(self):
        """Non-dict structured_payload rejected by AdapterResponse at construction."""
        # Pydantic validates dict type at AdapterResponse construction,
        # so we test that it rejects non-dict input
        with pytest.raises(ValidationError):
            AdapterResponse(
                raw_output="raw",
                structured_payload="not a dict",
            )

    def test_parse_missing_required_field_scene_interpretation(self):
        """Missing scene_interpretation field caught in pre-validation."""
        payload = {
            "detected_triggers": [],
            "proposed_state_deltas": [],
            "rationale": "Rationale",
        }
        response = AdapterResponse(
            raw_output="raw",
            structured_payload=payload,
        )

        result = parse_adapter_response(response)

        # Pydantic will catch missing required field
        assert result.success is False
        assert result.decision is None
        assert len(result.errors) > 0

    def test_parse_missing_required_field_rationale(self):
        """Missing rationale field caught in parsing."""
        payload = {
            "scene_interpretation": "Scene",
            "detected_triggers": [],
            "proposed_state_deltas": [],
        }
        response = AdapterResponse(
            raw_output="raw",
            structured_payload=payload,
        )

        result = parse_adapter_response(response)

        assert result.success is False
        assert result.decision is None
        assert len(result.errors) > 0

    def test_parse_wrong_field_type_detected_triggers_not_list(self):
        """Wrong field type (detected_triggers not list) caught by Pydantic."""
        payload = {
            "scene_interpretation": "Scene",
            "detected_triggers": "not a list",
            "proposed_state_deltas": [],
            "rationale": "Rationale",
        }
        response = AdapterResponse(
            raw_output="raw",
            structured_payload=payload,
        )

        result = parse_adapter_response(response)

        assert result.success is False
        assert result.decision is None
        assert len(result.errors) > 0

    def test_parse_raw_output_preserved_on_success(self):
        """raw_output preserved in ParseResult on successful parse."""
        payload = {
            "scene_interpretation": "Scene",
            "detected_triggers": [],
            "proposed_state_deltas": [],
            "rationale": "Rationale",
        }
        response = AdapterResponse(
            raw_output="original raw output text",
            structured_payload=payload,
        )

        result = parse_adapter_response(response)

        assert result.raw_output == "original raw output text"

    def test_parse_raw_output_preserved_on_failure(self):
        """raw_output preserved in ParseResult on parse failure."""
        response = AdapterResponse(
            raw_output="original raw output",
            structured_payload=None,
        )

        result = parse_adapter_response(response)

        assert result.raw_output == "original raw output"
        assert result.success is False


class TestNormalizeStructuredOutput:
    """Test normalize_structured_output() for normalization logic."""

    def test_normalize_strips_whitespace_from_scene_interpretation(self):
        """Whitespace stripped from scene_interpretation."""
        structured = StructuredAIStoryOutput(
            scene_interpretation="  Scene with spaces  ",
            detected_triggers=[],
            proposed_state_deltas=[],
            rationale="Rationale",
        )

        decision = normalize_structured_output(structured, "raw")

        assert decision.scene_interpretation == "Scene with spaces"

    def test_normalize_strips_whitespace_from_rationale(self):
        """Whitespace stripped from rationale."""
        structured = StructuredAIStoryOutput(
            scene_interpretation="Scene",
            detected_triggers=[],
            proposed_state_deltas=[],
            rationale="  Rationale with spaces  ",
        )

        decision = normalize_structured_output(structured, "raw")

        assert decision.rationale == "Rationale with spaces"

    def test_normalize_dialogue_impulses_preserved_when_empty(self):
        """Empty dialogue_impulses list preserved during normalization."""
        structured = StructuredAIStoryOutput(
            scene_interpretation="Scene",
            detected_triggers=[],
            proposed_state_deltas=[],
            rationale="Rationale",
            dialogue_impulses=[],
        )

        decision = normalize_structured_output(structured, "raw")

        assert decision.dialogue_impulses == []

    def test_normalize_proposed_scene_id_none_passes_through(self):
        """proposed_scene_id=None preserved."""
        structured = StructuredAIStoryOutput(
            scene_interpretation="Scene",
            detected_triggers=[],
            proposed_state_deltas=[],
            rationale="Rationale",
            proposed_scene_id=None,
        )

        decision = normalize_structured_output(structured, "raw")

        assert decision.proposed_scene_id is None

    def test_normalize_conflict_vector_none_passes_through(self):
        """conflict_vector=None preserved."""
        structured = StructuredAIStoryOutput(
            scene_interpretation="Scene",
            detected_triggers=[],
            proposed_state_deltas=[],
            rationale="Rationale",
            conflict_vector=None,
        )

        decision = normalize_structured_output(structured, "raw")

        assert decision.conflict_vector is None

    def test_normalize_parsed_source_set_to_structured_payload(self):
        """parsed_source set to 'structured_payload'."""
        structured = StructuredAIStoryOutput(
            scene_interpretation="Scene",
            detected_triggers=[],
            proposed_state_deltas=[],
            rationale="Rationale",
        )

        decision = normalize_structured_output(structured, "raw output text")

        assert decision.parsed_source == "structured_payload"
        assert decision.raw_output == "raw output text"


class TestPrevalidateDecision:
    """Test prevalidate_decision() for pre-validation logic."""

    def test_prevalidate_empty_scene_interpretation_returns_error(self):
        """Empty scene_interpretation returns error."""
        decision = ParsedAIDecision(
            scene_interpretation="",
            detected_triggers=[],
            proposed_deltas=[],
            proposed_scene_id=None,
            rationale="Rationale",
            raw_output="raw",
            parsed_source="structured_payload",
        )

        errors = prevalidate_decision(decision)

        assert len(errors) > 0
        assert any("scene_interpretation" in e for e in errors)

    def test_prevalidate_whitespace_only_scene_interpretation_returns_error(self):
        """Whitespace-only scene_interpretation returns error."""
        decision = ParsedAIDecision(
            scene_interpretation="   ",
            detected_triggers=[],
            proposed_deltas=[],
            proposed_scene_id=None,
            rationale="Rationale",
            raw_output="raw",
            parsed_source="structured_payload",
        )

        errors = prevalidate_decision(decision)

        assert len(errors) > 0
        assert any("scene_interpretation" in e for e in errors)

    def test_prevalidate_empty_rationale_returns_error(self):
        """Empty rationale returns error."""
        decision = ParsedAIDecision(
            scene_interpretation="Scene",
            detected_triggers=[],
            proposed_deltas=[],
            proposed_scene_id=None,
            rationale="",
            raw_output="raw",
            parsed_source="structured_payload",
        )

        errors = prevalidate_decision(decision)

        assert len(errors) > 0
        assert any("rationale" in e for e in errors)

    def test_prevalidate_empty_target_path_in_delta_returns_error(self):
        """Empty target_path in proposed_delta returns error."""
        delta = ProposedDelta(target_path="", next_value="value")
        decision = ParsedAIDecision(
            scene_interpretation="Scene",
            detected_triggers=[],
            proposed_deltas=[delta],
            proposed_scene_id=None,
            rationale="Rationale",
            raw_output="raw",
            parsed_source="structured_payload",
        )

        errors = prevalidate_decision(decision)

        assert len(errors) > 0
        assert any("target_path" in e for e in errors)

    def test_prevalidate_duplicate_trigger_ids_returns_error(self):
        """Duplicate trigger IDs in detected_triggers returns error."""
        decision = ParsedAIDecision(
            scene_interpretation="Scene",
            detected_triggers=["trigger1", "trigger2", "trigger1"],
            proposed_deltas=[],
            proposed_scene_id=None,
            rationale="Rationale",
            raw_output="raw",
            parsed_source="structured_payload",
        )

        errors = prevalidate_decision(decision)

        assert len(errors) > 0
        assert any("duplicate" in e for e in errors)

    def test_prevalidate_valid_decision_returns_empty_errors(self):
        """Valid decision returns empty error list."""
        delta = ProposedDelta(
            target_path="characters.veronique.state",
            next_value=50,
        )
        decision = ParsedAIDecision(
            scene_interpretation="Scene interpretation",
            detected_triggers=["trigger1", "trigger2"],
            proposed_deltas=[delta],
            proposed_scene_id="scene_2",
            rationale="Rationale text",
            raw_output="raw",
            parsed_source="structured_payload",
        )

        errors = prevalidate_decision(decision)

        assert errors == []


class TestProcessAdapterResponse:
    """Test process_adapter_response() convenience wrapper."""

    def test_process_full_pipeline_success(self):
        """process_adapter_response() runs full pipeline successfully."""
        payload = {
            "scene_interpretation": "Scene",
            "detected_triggers": ["trigger1"],
            "proposed_state_deltas": [],
            "rationale": "Rationale",
        }
        response = AdapterResponse(
            raw_output="raw",
            structured_payload=payload,
        )

        result = process_adapter_response(response)

        assert result.success is True
        assert result.decision is not None
        assert isinstance(result, ParseResult)

    def test_process_full_pipeline_failure_missing_fields(self):
        """process_adapter_response() fails on missing required fields."""
        payload = {
            "scene_interpretation": "Scene",
            # Missing detected_triggers, proposed_state_deltas, rationale
        }
        response = AdapterResponse(
            raw_output="raw",
            structured_payload=payload,
        )

        result = process_adapter_response(response)

        assert result.success is False
        assert result.decision is None
        assert len(result.errors) > 0

    def test_process_full_pipeline_failure_adapter_error(self):
        """process_adapter_response() fails on adapter error."""
        response = AdapterResponse(
            raw_output="raw",
            error="Adapter error message",
        )

        result = process_adapter_response(response)

        assert result.success is False
        assert "Adapter error" in result.errors[0]

    def test_process_raw_output_always_preserved(self):
        """raw_output preserved through full pipeline."""
        response = AdapterResponse(
            raw_output="preserved raw output",
            error="Some error",
        )

        result = process_adapter_response(response)

        assert result.raw_output == "preserved raw output"
