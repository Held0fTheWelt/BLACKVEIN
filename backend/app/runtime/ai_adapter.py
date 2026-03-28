"""W2.1.1 — Canonical AI Adapter Contract

Establishes the interface boundary between the story runtime and AI model integration.

The adapter contract defines:
- AdapterRequest: canonical input to any AI adapter
- AdapterResponse: canonical output from any AI adapter
- StoryAIAdapter: abstract base class (protocol) for all adapters
- MockStoryAIAdapter: deterministic mock implementation for testing

This contract is provider-agnostic: Claude, GPT, local models, etc. all implement
the same interface. The runtime depends on this contract, not on specific providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

# W2.4.2: Import role contract (W2.4.1)
from app.runtime.role_contract import AIRoleContract


class AdapterRequest(BaseModel):
    """Input to an AI adapter from the canonical story runtime.

    Attributes:
        session_id: Session identifier
        turn_number: Current turn number (0-based or 1-based, depends on session start)
        current_scene_id: Active scene/phase identifier
        canonical_state: Complete world state snapshot (dict)
        recent_events: List of recent events as plain dicts (not Pydantic objects)
        operator_input: Optional operator instruction or context
        request_role_structured_output: If True, request output as AIRoleContract shape (W2.4.2+).
                                        Defaults to False for backward compatibility.
                                        W2.4.3 will update default to True when normalization is ready.
        metadata: Extensible metadata dict for future use
    """

    session_id: str
    turn_number: int
    current_scene_id: str
    canonical_state: dict[str, Any]
    recent_events: list[dict[str, Any]] = Field(default_factory=list)
    operator_input: str | None = None
    request_role_structured_output: bool = Field(default=False)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdapterResponse(BaseModel):
    """Output from an AI adapter to the canonical story runtime.

    Attributes:
        raw_output: Raw text output from the AI model (empty string if error occurred)
        structured_payload: Parsed structured output (if available), None otherwise
        backend_metadata: Metadata about model, latency, tokens, etc. (provider-specific)
        error: Error message if generation failed, None otherwise
        is_error: Convenience boolean flag (True if error is not None)
    """

    raw_output: str
    structured_payload: dict[str, Any] | None = None
    backend_metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    is_error: bool = False

    def model_post_init(self, __context: Any) -> None:
        """Set is_error based on error field."""
        self.is_error = self.error is not None


class StoryAIAdapter(ABC):
    """Abstract base class for story AI adapters.

    All AI adapter implementations (Claude, GPT, local models, etc.) must inherit
    from this class and implement the required methods.

    This class defines the canonical contract that the story runtime depends on.
    """

    @abstractmethod
    def generate(self, request: AdapterRequest) -> AdapterResponse:
        """Generate a structured story decision from canonical runtime context.

        Args:
            request: AdapterRequest with session, state, and context

        Returns:
            AdapterResponse with raw output, structured payload, and metadata

        Raises:
            Any exception should be caught and returned in AdapterResponse.error
        """
        pass

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Stable identifier for this adapter implementation.

        Returns:
            String name (e.g., "mock", "claude-3-sonnet", "gpt-4")
        """
        pass


def _create_mock_role_contract() -> dict[str, Any]:
    """Create a mock AIRoleContract shape for deterministic testing.

    Returns:
        Dict matching AIRoleContract structure (interpreter, director, responder).
    """
    return {
        "interpreter": {
            "scene_reading": "[mock] Scene interpretation - generic analysis of current state",
            "detected_tensions": ["mock_tension_1"],
            "trigger_candidates": ["mock_trigger_candidate"],
            "uncertainty_markers": None,
        },
        "director": {
            "conflict_steering": "[mock] Recommended conflict direction for this turn",
            "escalation_level": 5,
            "recommended_direction": "hold",
            "pressure_movement": None,
        },
        "responder": {
            "response_impulses": [],
            "state_change_candidates": [],
            "dialogue_impulses": None,
            "trigger_assertions": [],
            "scene_transition_candidate": None,
        },
    }


class MockStoryAIAdapter(StoryAIAdapter):
    """Deterministic mock AI adapter for testing.

    Always returns stable, predictable output based on request fields.
    Useful for unit tests that need reproducible behavior without calling a real model.

    Output structure:
    - raw_output: "[mock] turn={turn_number} scene={scene_id}"
    - structured_payload: Contains detected_triggers, proposed_deltas, narrative_text
    - backend_metadata: Marks itself as mock and deterministic
    """

    @property
    def adapter_name(self) -> str:
        """Returns 'mock' as the adapter identifier."""
        return "mock"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        """Generate deterministic mock output from request.

        If request.request_role_structured_output is True, returns output in AIRoleContract shape
        (interpreter, director, responder). Otherwise, returns legacy structure.

        Args:
            request: AdapterRequest (fields used to construct deterministic output)

        Returns:
            AdapterResponse with role-structured or legacy mock data
        """
        raw = (
            f"[mock adapter] turn={request.turn_number} "
            f"scene={request.current_scene_id} "
            f"session={request.session_id[:8]}"
        )

        # If role-structured output requested, return AIRoleContract shape
        if request.request_role_structured_output:
            structured_payload = _create_mock_role_contract()
        else:
            # Legacy fallback for backward compatibility
            structured_payload = {
                "detected_triggers": [],
                "proposed_deltas": [],
                "proposed_scene_id": None,
                "narrative_text": "[mock narrative - no real AI involved]",
                "rationale": "[mock rationale]",
            }

        return AdapterResponse(
            raw_output=raw,
            structured_payload=structured_payload,
            backend_metadata={
                "adapter": "mock",
                "deterministic": True,
                "latency_ms": 0,
                "role_structured": request.request_role_structured_output,
            },
            error=None,
        )
