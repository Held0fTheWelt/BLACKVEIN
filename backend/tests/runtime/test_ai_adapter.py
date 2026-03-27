"""Tests for W2.1.1 canonical AI adapter contract.

Verifies that:
- AdapterRequest and AdapterResponse have correct shape
- StoryAIAdapter abstract base class enforces contract
- MockStoryAIAdapter satisfies contract with deterministic behavior
- Adapter interface is provider-agnostic
"""

from __future__ import annotations

import pytest

from app.runtime.ai_adapter import (
    AdapterRequest,
    AdapterResponse,
    MockStoryAIAdapter,
    StoryAIAdapter,
)


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
