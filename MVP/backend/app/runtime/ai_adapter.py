"""W2.1.1 — Reusable AI adapter contract for the in-process W2 session pipeline.

Defines stable request/response shapes between **backend-local** turn code and model
providers. Provider-agnostic (Claude, GPT, local, …). This is **not** the World Engine
live runtime boundary; it supports tests and tooling inside this repo.

The adapter contract defines:
- AdapterRequest: normalized input to any story AI adapter
- AdapterResponse: normalized output from any story AI adapter
- StoryAIAdapter: abstract base class (protocol) for all adapters
- MockStoryAIAdapter: deterministic mock implementation for testing
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

# W2.4.2: Import role contract (W2.4.1)
from app.runtime.input_interpreter import InputInterpretationEnvelope
from app.runtime.role_contract import AIRoleContract
from app.runtime.runtime_models import TokenUsageRecord


class AdapterRequest(BaseModel):
    """Input to an AI adapter from the in-process W2 session pipeline.

    Attributes:
        session_id: Session identifier
        turn_number: Current turn number (0-based or 1-based, depends on session start)
        current_scene_id: Active scene/phase identifier
        canonical_state: Complete world state snapshot (dict)
        recent_events: List of recent events as plain dicts (not Pydantic objects)
        operator_input: Optional operator instruction or context
        input_interpretation: Deterministic pre-AI diagnostic envelope (Task 1A); not authoritative state.
        continuity_context: Task 1C/1D — JSON-safe snapshots from ``session.context_layers``
            only (W2.3 layers plus ``active_narrative_threads``; no raw history or metadata dumps).
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
    input_interpretation: InputInterpretationEnvelope | None = None
    continuity_context: dict[str, Any] | None = None
    request_role_structured_output: bool = Field(default=False)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdapterResponse(BaseModel):
    """Output from an AI adapter to the in-process W2 session pipeline.

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

    This class defines the stable contract that in-process turn code depends on.
    """

    @abstractmethod
    def generate(self, request: AdapterRequest) -> AdapterResponse:
        """Generate a structured story decision from session-shaped context.

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


def generate_with_timeout(
    *,
    adapter: StoryAIAdapter,
    request: AdapterRequest,
    timeout_ms: int,
) -> AdapterResponse:
    """Run adapter.generate with bounded wait-time containment.

    This is a containment boundary only. For sync adapter APIs we cannot hard-cancel
    a provider call that is already running; we return a timeout error and continue.
    """
    bounded_timeout_ms = max(int(timeout_ms), 1)
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(adapter.generate, request)
    try:
        return future.result(timeout=bounded_timeout_ms / 1000.0)
    except FutureTimeoutError:
        future.cancel()
        return AdapterResponse(
            raw_output="",
            structured_payload=None,
            backend_metadata={
                "adapter": adapter.adapter_name,
                "timeout_ms": bounded_timeout_ms,
                "timeout_mode": "thread_containment_no_hard_cancel",
            },
            error=f"adapter_generate_timeout:{bounded_timeout_ms}ms",
        )
    except Exception as exc:  # pragma: no cover - defensive adapter boundary
        return AdapterResponse(
            raw_output="",
            structured_payload=None,
            backend_metadata={"adapter": adapter.adapter_name},
            error=f"adapter_generate_exception:{exc}",
        )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _to_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_token_usage(response: AdapterResponse) -> TokenUsageRecord | None:
    """Normalize provider usage metadata into canonical exact token usage.

    Returns None when exact usage metadata is unavailable or incomplete enough
    that we cannot derive a trustworthy total token count.
    """
    metadata = response.backend_metadata if isinstance(response.backend_metadata, dict) else {}
    usage = metadata.get("usage")
    usage_dict = usage if isinstance(usage, dict) else metadata

    input_tokens = _to_int_or_none(
        usage_dict.get("input_tokens", usage_dict.get("prompt_tokens"))
    )
    output_tokens = _to_int_or_none(
        usage_dict.get("output_tokens", usage_dict.get("completion_tokens"))
    )
    total_tokens = _to_int_or_none(usage_dict.get("total_tokens"))

    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    if total_tokens is None:
        return None

    provider_name = metadata.get("provider_name", metadata.get("provider"))
    model_name = metadata.get("model_name", metadata.get("model"))
    raw_usage = usage if isinstance(usage, dict) else None

    return TokenUsageRecord(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=max(total_tokens, 0),
        provider_name=str(provider_name) if provider_name is not None else None,
        model_name=str(model_name) if model_name is not None else None,
        usage_mode="exact",
        raw_usage=raw_usage,
    )


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

        # Task 1: bounded stage payloads for multi-stage Runtime orchestration tests (metadata-driven).
        stage = (request.metadata or {}).get("runtime_stage")
        if stage == "preflight":
            structured_payload = {
                "runtime_stage": "preflight",
                "ambiguity_score": 0.1,
                "trigger_signals": [],
                "repetition_risk": "low",
                "classification_label": "mock",
                "preflight_ok": True,
            }
            return AdapterResponse(
                raw_output=raw,
                structured_payload=structured_payload,
                backend_metadata={
                    "adapter": "mock",
                    "deterministic": True,
                    "latency_ms": 0,
                    "runtime_stage": "preflight",
                },
                error=None,
            )
        if stage == "signal_consistency":
            structured_payload = {
                "runtime_stage": "signal_consistency",
                "needs_llm_synthesis": True,
                "skip_synthesis_reason": None,
                "narrative_summary": "[mock] signal narrative summary",
                "consistency_notes": "mock stable",
                "consistency_flags": [],
            }
            return AdapterResponse(
                raw_output=raw,
                structured_payload=structured_payload,
                backend_metadata={
                    "adapter": "mock",
                    "deterministic": True,
                    "latency_ms": 0,
                    "runtime_stage": "signal_consistency",
                },
                error=None,
            )
        if stage == "ranking":
            structured_payload = {
                "runtime_stage": "ranking",
                "ranked_hypotheses": ["[mock] primary interpretation", "[mock] alternate"],
                "preferred_hypothesis_index": 0,
                "recommend_skip_synthesis": False,
                "skip_synthesis_after_ranking_reason": None,
                "synthesis_recommended": True,
                "ambiguity_residual": 0.25,
                "ranking_confidence": 0.72,
                "ranking_notes": [],
            }
            return AdapterResponse(
                raw_output=raw,
                structured_payload=structured_payload,
                backend_metadata={
                    "adapter": "mock",
                    "deterministic": True,
                    "latency_ms": 0,
                    "runtime_stage": "ranking",
                },
                error=None,
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
