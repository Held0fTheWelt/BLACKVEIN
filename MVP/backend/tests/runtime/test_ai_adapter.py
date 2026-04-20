"""Tests for W2.1.1 canonical AI adapter contract.

Verifies that:
- AdapterRequest and AdapterResponse have correct shape
- StoryAIAdapter abstract base class enforces contract
- MockStoryAIAdapter satisfies contract with deterministic behavior
- Adapter interface is provider-agnostic
"""

from __future__ import annotations

import time

import pytest

from app.runtime.ai_adapter import (
    AdapterRequest,
    AdapterResponse,
    MockStoryAIAdapter,
    StoryAIAdapter,
    generate_with_timeout,
    normalize_token_usage,
)
from app.runtime.input_interpreter import InputPrimaryMode, interpret_operator_input


class TestAdapterRequest:
    """Test AdapterRequest model shape and behavior."""

    def test_adapter_request_required_fields(self):
        """AdapterRequest requires session_id, turn_number, current_scene_id, canonical_state, recent_events."""
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={"key": "value"},
            recent_events=[],
        )

        assert request.session_id == "sess1"
        assert request.turn_number == 1
        assert request.current_scene_id == "phase_1"
        assert request.canonical_state == {"key": "value"}
        assert request.recent_events == []

    def test_adapter_request_optional_fields_default(self):
        """AdapterRequest optional fields default correctly."""
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
        )

        assert request.operator_input is None
        assert request.input_interpretation is None
        assert request.metadata == {}

    def test_adapter_request_with_operator_input(self):
        """AdapterRequest accepts operator_input."""
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
            operator_input="focus on emotions",
        )

        assert request.operator_input == "focus on emotions"

    def test_adapter_request_with_metadata(self):
        """AdapterRequest accepts arbitrary metadata dict."""
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
            metadata={"context": "important", "tag": "test"},
        )

        assert request.metadata == {"context": "important", "tag": "test"}

    def test_adapter_request_accepts_input_interpretation(self):
        """First-class diagnostic envelope on AdapterRequest (Task 1A)."""
        interp = interpret_operator_input("I nod.")
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
            operator_input="I nod.",
            input_interpretation=interp,
        )
        assert request.input_interpretation is interp
        assert request.input_interpretation.primary_mode == InputPrimaryMode.REACTION


class TestAdapterResponse:
    """Test AdapterResponse model shape and behavior."""

    def test_adapter_response_required_raw_output(self):
        """AdapterResponse requires raw_output."""
        response = AdapterResponse(raw_output="test output")

        assert response.raw_output == "test output"

    def test_adapter_response_optional_fields_default(self):
        """AdapterResponse optional fields default correctly."""
        response = AdapterResponse(raw_output="output")

        assert response.structured_payload is None
        assert response.backend_metadata == {}
        assert response.error is None
        assert response.is_error is False

    def test_adapter_response_with_structured_payload(self):
        """AdapterResponse accepts structured_payload dict."""
        payload = {"key": "value", "count": 42}
        response = AdapterResponse(raw_output="output", structured_payload=payload)

        assert response.structured_payload == payload

    def test_adapter_response_with_error_sets_is_error_flag(self):
        """AdapterResponse with error string automatically sets is_error=True."""
        response = AdapterResponse(
            raw_output="", error="Model failed"
        )

        assert response.is_error is True
        assert response.error == "Model failed"

    def test_adapter_response_without_error_sets_is_error_false(self):
        """AdapterResponse without error keeps is_error=False."""
        response = AdapterResponse(raw_output="success", error=None)

        assert response.is_error is False


class TestStoryAIAdapterContract:
    """Test StoryAIAdapter abstract base class contract."""

    def test_cannot_instantiate_abstract_base_directly(self):
        """Cannot instantiate StoryAIAdapter directly (abstract class)."""
        with pytest.raises(TypeError):
            StoryAIAdapter()

    def test_subclass_without_generate_method_fails(self):
        """Subclass missing generate() method raises TypeError on instantiation."""
        class IncompleteAdapter(StoryAIAdapter):
            @property
            def adapter_name(self) -> str:
                return "incomplete"

        with pytest.raises(TypeError):
            IncompleteAdapter()

    def test_subclass_without_adapter_name_property_fails(self):
        """Subclass missing adapter_name property raises TypeError on instantiation."""
        class IncompleteAdapter(StoryAIAdapter):
            def generate(self, request: AdapterRequest) -> AdapterResponse:
                return AdapterResponse(raw_output="test")

        with pytest.raises(TypeError):
            IncompleteAdapter()


class TestMockStoryAIAdapter:
    """Test MockStoryAIAdapter implementation."""

    def test_mock_adapter_name(self):
        """MockStoryAIAdapter.adapter_name == 'mock'."""
        adapter = MockStoryAIAdapter()
        assert adapter.adapter_name == "mock"

    def test_mock_generate_returns_response(self):
        """MockStoryAIAdapter.generate() returns AdapterResponse."""
        adapter = MockStoryAIAdapter()
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
        )

        response = adapter.generate(request)

        assert isinstance(response, AdapterResponse)
        assert response.raw_output is not None
        assert response.error is None

    def test_mock_generate_deterministic_output(self):
        """MockStoryAIAdapter generates deterministic output."""
        adapter = MockStoryAIAdapter()
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
        )

        response1 = adapter.generate(request)
        response2 = adapter.generate(request)

        assert response1.raw_output == response2.raw_output
        assert response1.structured_payload == response2.structured_payload

    def test_mock_generate_includes_turn_and_scene_in_output(self):
        """MockStoryAIAdapter.generate() includes turn_number and scene_id in raw_output."""
        adapter = MockStoryAIAdapter()
        request = AdapterRequest(
            session_id="sess1",
            turn_number=5,
            current_scene_id="final_scene",
            canonical_state={},
            recent_events=[],
        )

        response = adapter.generate(request)

        assert "turn=5" in response.raw_output
        assert "final_scene" in response.raw_output

    def test_mock_generate_structured_payload_has_expected_keys(self):
        """MockStoryAIAdapter structured_payload includes required keys."""
        adapter = MockStoryAIAdapter()
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
        )

        response = adapter.generate(request)

        assert response.structured_payload is not None
        assert "detected_triggers" in response.structured_payload
        assert "proposed_deltas" in response.structured_payload
        assert "narrative_text" in response.structured_payload


class TestAdapterContractCoherence:
    """Test adapter contract coherence and provider-agnosticism."""

    def test_multiple_mock_adapters_are_independent(self):
        """Multiple adapter instances are independent."""
        adapter1 = MockStoryAIAdapter()
        adapter2 = MockStoryAIAdapter()

        assert adapter1 is not adapter2
        assert adapter1.adapter_name == adapter2.adapter_name

    def test_adapter_request_with_complex_canonical_state(self):
        """AdapterRequest accepts complex nested canonical_state."""
        complex_state = {
            "characters": {
                "veronique": {"emotional_state": 75},
                "michel": {"emotional_state": 50},
            },
            "relationships": {"veronique-michel": 80},
            "metadata": {"turn": 1},
        }

        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state=complex_state,
            recent_events=[],
        )

        assert request.canonical_state == complex_state

    def test_adapter_request_with_event_list(self):
        """AdapterRequest accepts list of event dicts."""
        events = [
            {"event_type": "turn_started", "turn_number": 1},
            {"event_type": "decision_validated", "status": "accepted"},
        ]

        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=events,
        )

        assert request.recent_events == events

    def test_adapter_response_backend_metadata_extensible(self):
        """AdapterResponse backend_metadata accepts any provider-specific data."""
        response = AdapterResponse(
            raw_output="output",
            backend_metadata={
                "model": "claude-3-sonnet",
                "latency_ms": 234,
                "input_tokens": 512,
                "output_tokens": 128,
                "temperature": 0.7,
            },
        )

        assert response.backend_metadata["model"] == "claude-3-sonnet"
        assert response.backend_metadata["latency_ms"] == 234


class TestAdapterRequestRoleStructured:
    """Test role-structured output request field."""

    def test_adapter_request_role_structured_defaults_to_false(self):
        """AdapterRequest.request_role_structured_output defaults to False (backward compat).

        W2.4.3 will update default to True when normalization is ready.
        """
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
        )
        assert request.request_role_structured_output is False

    def test_adapter_request_role_structured_can_be_set_true(self):
        """AdapterRequest.request_role_structured_output can be set to True to opt-in to new format."""
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
            request_role_structured_output=True,
        )
        assert request.request_role_structured_output is True


class TestMockAdapterRoleStructured:
    """Test MockStoryAIAdapter role-structured output."""

    def test_mock_adapter_returns_role_contract_shape_when_requested(self):
        """MockStoryAIAdapter returns AIRoleContract shape when request_role_structured_output=True."""
        adapter = MockStoryAIAdapter()
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
            request_role_structured_output=True,
        )

        response = adapter.generate(request)

        # Verify structure matches AIRoleContract shape
        payload = response.structured_payload
        assert payload is not None
        assert "interpreter" in payload
        assert "director" in payload
        assert "responder" in payload

        # Verify interpreter section
        assert "scene_reading" in payload["interpreter"]
        assert "detected_tensions" in payload["interpreter"]
        assert "trigger_candidates" in payload["interpreter"]

        # Verify director section
        assert "conflict_steering" in payload["director"]
        assert "escalation_level" in payload["director"]
        assert "recommended_direction" in payload["director"]

        # Verify responder section
        assert "response_impulses" in payload["responder"]
        assert "state_change_candidates" in payload["responder"]
        assert "trigger_assertions" in payload["responder"]

    def test_mock_adapter_returns_legacy_format_when_not_requested(self):
        """MockStoryAIAdapter returns legacy format when request_role_structured_output=False."""
        adapter = MockStoryAIAdapter()
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
            request_role_structured_output=False,
        )

        response = adapter.generate(request)

        # Verify legacy structure
        payload = response.structured_payload
        assert payload is not None
        assert "detected_triggers" in payload
        assert "proposed_deltas" in payload
        assert "proposed_scene_id" in payload
        assert "narrative_text" in payload

    def test_mock_adapter_metadata_reflects_role_structured_flag(self):
        """MockStoryAIAdapter backend_metadata includes role_structured flag."""
        adapter = MockStoryAIAdapter()
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
            request_role_structured_output=True,
        )

        response = adapter.generate(request)

        assert response.backend_metadata["role_structured"] is True

    def test_mock_adapter_role_structured_payload_has_canonical_keys(self):
        """MockStoryAIAdapter role-structured output has all three canonical top-level keys.

        When request_role_structured_output=True, structured_payload must contain
        exactly these top-level keys: interpreter, director, responder.
        This ensures the payload is recognized as role-structured format, not legacy.
        """
        adapter = MockStoryAIAdapter()
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
            request_role_structured_output=True,
        )

        response = adapter.generate(request)
        payload = response.structured_payload

        # Verify all three canonical keys are present
        assert isinstance(payload, dict)
        assert "interpreter" in payload
        assert "director" in payload
        assert "responder" in payload

        # Verify it's not legacy format (no legacy-specific keys as top level)
        assert "detected_triggers" not in payload  # Legacy format has this at top level
        assert "proposed_deltas" not in payload    # Legacy format has this at top level


class TestTokenUsageNormalization:
    """Test canonical token usage normalization from backend metadata."""

    def test_normalize_token_usage_reads_usage_block(self):
        response = AdapterResponse(
            raw_output="ok",
            backend_metadata={
                "provider": "anthropic",
                "model": "claude-3-5-sonnet",
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 30,
                    "total_tokens": 150,
                },
            },
        )

        usage = normalize_token_usage(response)

        assert usage is not None
        assert usage.usage_mode == "exact"
        assert usage.input_tokens == 120
        assert usage.output_tokens == 30
        assert usage.total_tokens == 150
        assert usage.provider_name == "anthropic"
        assert usage.model_name == "claude-3-5-sonnet"

    def test_normalize_token_usage_supports_prompt_completion_aliases(self):
        response = AdapterResponse(
            raw_output="ok",
            backend_metadata={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini",
                "usage": {
                    "prompt_tokens": 90,
                    "completion_tokens": 15,
                },
            },
        )

        usage = normalize_token_usage(response)

        assert usage is not None
        assert usage.usage_mode == "exact"
        assert usage.input_tokens == 90
        assert usage.output_tokens == 15
        assert usage.total_tokens == 105
        assert usage.provider_name == "openai"
        assert usage.model_name == "gpt-4o-mini"

    def test_normalize_token_usage_returns_none_when_exact_usage_missing(self):
        response = AdapterResponse(
            raw_output="ok",
            backend_metadata={"provider": "mock", "latency_ms": 3},
        )

        usage = normalize_token_usage(response)

        assert usage is None


class TestGenerateWithTimeout:
    """Direct unit tests for thread containment timeout helper (no executor integration)."""

    def test_returns_result_when_adapter_finishes_within_timeout(self):
        class FastAdapter(StoryAIAdapter):
            @property
            def adapter_name(self) -> str:
                return "fast-timeout-test"

            def generate(self, request: AdapterRequest) -> AdapterResponse:
                return AdapterResponse(raw_output="ok", structured_payload={"x": 1})

        request = AdapterRequest(
            session_id="s",
            turn_number=1,
            current_scene_id="sc",
            canonical_state={},
            recent_events=[],
        )
        out = generate_with_timeout(adapter=FastAdapter(), request=request, timeout_ms=5000)
        assert out.error is None
        assert out.raw_output == "ok"
        assert out.structured_payload == {"x": 1}

    def test_slow_adapter_yields_explicit_timeout_outcome_containment_not_cancel(self):
        """Waits are bounded; sync calls are not hard-cancelled (see backend_metadata)."""

        class SlowAdapter(StoryAIAdapter):
            @property
            def adapter_name(self) -> str:
                return "slow-timeout-test"

            def generate(self, request: AdapterRequest) -> AdapterResponse:
                time.sleep(0.15)
                return AdapterResponse(raw_output="late", structured_payload=None)

        request = AdapterRequest(
            session_id="s",
            turn_number=1,
            current_scene_id="sc",
            canonical_state={},
            recent_events=[],
        )
        out = generate_with_timeout(adapter=SlowAdapter(), request=request, timeout_ms=20)
        assert out.error is not None
        assert out.error.startswith("adapter_generate_timeout:")
        assert out.raw_output == ""
        assert out.structured_payload is None
        meta = out.backend_metadata or {}
        assert meta.get("timeout_mode") == "thread_containment_no_hard_cancel"
        assert meta.get("adapter") == "slow-timeout-test"
        assert "timeout_ms" in meta
