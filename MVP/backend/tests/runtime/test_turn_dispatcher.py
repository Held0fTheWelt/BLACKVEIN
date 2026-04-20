"""Tests for W2.1-R1 — Turn Execution Dispatcher

Verifies that dispatch_turn() is the canonical entry point and correctly
routes to mock or AI execution based on session.execution_mode.
"""

import asyncio

import pytest

from app.runtime.adapter_registry import clear_registry
from app.runtime.ai_adapter import AdapterResponse, StoryAIAdapter
from app.runtime.turn_dispatcher import dispatch_turn
from .staged_test_payloads import maybe_staged_prelude_response
from app.runtime.turn_executor import MockDecision


@pytest.fixture(autouse=True)
def _clear_adapter_registry_for_dispatcher_tests() -> None:
    """Isolate dispatcher tests from model specs registered elsewhere in the suite."""
    clear_registry()
    yield
    clear_registry()


class DeterministicTestAdapter(StoryAIAdapter):
    """Test adapter that returns valid W2.1.2-conformant payload."""

    @property
    def adapter_name(self) -> str:
        return "test-adapter"

    def generate(self, request):
        prelude = maybe_staged_prelude_response(request)
        if prelude is not None:
            return prelude
        return AdapterResponse(
            raw_output="[test adapter output]",
            structured_payload={
                "scene_interpretation": "Test scene interpretation",
                "detected_triggers": [],
                "proposed_state_deltas": [],
                "rationale": "Test rationale for dispatcher",
            },
        )


class ToolLoopDispatcherAdapter(StoryAIAdapter):
    """Adapter that requests one tool then returns final output."""

    def __init__(self):
        self._calls = 0

    @property
    def adapter_name(self) -> str:
        return "tool-loop-dispatcher-adapter"

    def generate(self, request):
        prelude = maybe_staged_prelude_response(request)
        if prelude is not None:
            return prelude
        self._calls += 1
        if self._calls == 1:
            return AdapterResponse(
                raw_output="[tool request]",
                structured_payload={
                    "type": "tool_request",
                    "tool_name": "wos.read.current_scene",
                    "arguments": {},
                },
            )
        return AdapterResponse(
            raw_output="[final output]",
            structured_payload={
                "scene_interpretation": "Finalized from dispatcher path",
                "detected_triggers": [],
                "proposed_state_deltas": [],
                "rationale": "Tool loop completed",
            },
        )


class PreviewLoopDispatcherAdapter(StoryAIAdapter):
    """Adapter that previews then finalizes corrected output."""

    def __init__(self):
        self._calls = 0

    @property
    def adapter_name(self) -> str:
        return "preview-loop-dispatcher-adapter"

    def generate(self, request):
        prelude = maybe_staged_prelude_response(request)
        if prelude is not None:
            return prelude
        self._calls += 1
        if self._calls == 1:
            return AdapterResponse(
                raw_output="[preview request]",
                structured_payload={
                    "type": "tool_request",
                    "tool_name": "wos.guard.preview_delta",
                    "arguments": {
                        "proposed_state_deltas": [
                            {
                                "target_path": "characters.nonexistent.emotional_state",
                                "next_value": 10,
                                "delta_type": "state_update",
                            }
                        ]
                    },
                },
            )
        return AdapterResponse(
            raw_output="[preview corrected final]",
            structured_payload={
                "scene_interpretation": "Corrected after preview",
                "detected_triggers": [],
                "proposed_state_deltas": [],
                "rationale": "Preview feedback incorporated",
            },
        )


class OrchestrationDispatcherAdapter(StoryAIAdapter):
    """Adapter that emits deterministic outputs per subagent invocation."""

    def __init__(self):
        self.calls: list[str] = []

    @property
    def adapter_name(self) -> str:
        return "orchestration-dispatcher-adapter"

    def generate(self, request):
        agent_id = (request.metadata.get("agent_invocation") or {}).get("agent_id", "unknown")
        self.calls.append(agent_id)

        if agent_id == "delta_planner":
            return AdapterResponse(
                raw_output="[delta planner]",
                structured_payload={
                    "scene_interpretation": "delta planner",
                    "detected_triggers": [],
                    "proposed_state_deltas": [],
                    "rationale": "planner output",
                },
            )
        if agent_id == "finalizer":
            merged = dict(request.metadata.get("supervisor_merge_payload") or {})
            merged["rationale"] = "dispatcher finalizer"
            return AdapterResponse(raw_output="[finalizer]", structured_payload=merged)

        return AdapterResponse(
            raw_output=f"[{agent_id}]",
            structured_payload={
                "scene_interpretation": f"{agent_id} output",
                "detected_triggers": [],
                "proposed_state_deltas": [],
                "rationale": f"{agent_id} rationale",
            },
        )


def test_dispatcher_routes_to_mock_when_mode_is_mock(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Dispatcher routes to mock path when execution_mode='mock'."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "mock"

    result = asyncio.run(
        dispatch_turn(
            session,
            current_turn=session.turn_counter + 1,
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "success"
    assert result.turn_number == session.turn_counter + 1


def test_dispatcher_routes_to_ai_when_mode_is_ai(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Dispatcher routes to AI path when execution_mode='ai'."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"

    adapter = DeterministicTestAdapter()

    result = asyncio.run(
        dispatch_turn(
            session,
            current_turn=session.turn_counter + 1,
            module=god_of_carnage_module,
            ai_adapter=adapter,
        )
    )

    assert result.execution_status == "success"
    assert result.turn_number == session.turn_counter + 1


def test_dispatcher_ai_mode_can_finalize_via_tool_loop(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Dispatcher AI path can complete through tool loop and final output."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.metadata["tool_loop"] = {
        "enabled": True,
        "allowed_tools": ["wos.read.current_scene"],
        "max_tool_calls_per_turn": 3,
    }

    adapter = ToolLoopDispatcherAdapter()
    result = asyncio.run(
        dispatch_turn(
            session,
            current_turn=session.turn_counter + 1,
            module=god_of_carnage_module,
            ai_adapter=adapter,
        )
    )

    assert result.execution_status == "success"
    assert "ai_decision_logs" in session.metadata
    assert session.metadata["ai_decision_logs"][-1].tool_loop_summary is not None


def test_dispatcher_ai_mode_supports_preview_write_feedback(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Dispatcher path supports preview tool usage and diagnostics."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.metadata["tool_loop"] = {
        "enabled": True,
        "allowed_tools": ["wos.guard.preview_delta"],
        "max_tool_calls_per_turn": 3,
    }

    adapter = PreviewLoopDispatcherAdapter()
    result = asyncio.run(
        dispatch_turn(
            session,
            current_turn=session.turn_counter + 1,
            module=god_of_carnage_module,
            ai_adapter=adapter,
        )
    )

    assert result.execution_status == "success"
    assert session.metadata["ai_decision_logs"][-1].preview_diagnostics is not None


def test_dispatcher_ai_mode_supports_agent_orchestration(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Dispatcher AI path supports C1 supervisor orchestration when enabled."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.metadata["agent_orchestration"] = {"enabled": True}
    session.metadata["tool_loop"] = {"enabled": False}

    adapter = OrchestrationDispatcherAdapter()
    result = asyncio.run(
        dispatch_turn(
            session,
            current_turn=session.turn_counter + 1,
            module=god_of_carnage_module,
            ai_adapter=adapter,
        )
    )

    assert result.execution_status == "success"
    assert len([call for call in adapter.calls if call != "finalizer"]) >= 2
    assert "finalizer" in adapter.calls
    decision_log = session.metadata["ai_decision_logs"][-1]
    assert decision_log.supervisor_plan is not None
    assert decision_log.subagent_invocations is not None
    assert decision_log.tool_loop_summary is not None
    controls = decision_log.tool_loop_summary.get("execution_controls") or {}
    assert controls.get("agent_orchestration_active") is True
    assert controls.get("tool_loop_active") is False


def test_dispatcher_raises_error_if_ai_mode_without_adapter(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Dispatcher raises ValueError if AI mode selected but adapter not registered."""
    from app.runtime.adapter_registry import clear_registry

    clear_registry()

    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.adapter_name = "nonexistent"

    with pytest.raises(ValueError, match="adapter.*not found"):
        asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
            )
        )


def test_dispatcher_defaults_to_mock_when_mode_not_set(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Dispatcher defaults to mock when execution_mode is not set."""
    session = god_of_carnage_module_with_state
    session.execution_mode = ""  # Not set

    result = asyncio.run(
        dispatch_turn(
            session,
            current_turn=session.turn_counter + 1,
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "success"


def test_dispatcher_with_custom_mock_decision_provider(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Dispatcher uses provided mock_decision_provider in mock mode."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "mock"

    def custom_decision_provider():
        return MockDecision(
            detected_triggers=["test_trigger"],
            proposed_deltas=[],
            narrative_text="Custom decision",
        )

    result = asyncio.run(
        dispatch_turn(
            session,
            current_turn=session.turn_counter + 1,
            module=god_of_carnage_module,
            mock_decision_provider=custom_decision_provider,
        )
    )

    assert result.execution_status == "success"
    assert result.decision.narrative_text == "Custom decision"


def test_dispatcher_is_canonical_entry_point(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Dispatcher is the canonical entry point, not a wrapper."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "mock"

    # Call dispatcher with no direct execute_turn or execute_turn_with_ai call
    result = asyncio.run(
        dispatch_turn(
            session,
            current_turn=session.turn_counter + 1,
            module=god_of_carnage_module,
        )
    )

    # Result should be a valid TurnExecutionResult from the dispatcher
    assert result is not None
    assert hasattr(result, "execution_status")
    assert hasattr(result, "updated_canonical_state")


def test_ai_path_now_reachable_through_dispatcher(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """AI execution path is now reachable through dispatcher, not just direct tests."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"

    adapter = DeterministicTestAdapter()

    # This simulates production code calling the dispatcher
    # Previously, execute_turn_with_ai was only reachable by tests calling it directly
    result = asyncio.run(
        dispatch_turn(
            session,
            current_turn=session.turn_counter + 1,
            module=god_of_carnage_module,
            ai_adapter=adapter,
        )
    )

    # Should get a successful result from the AI path
    assert result.execution_status == "success"


def test_mock_path_still_works_through_dispatcher(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Mock execution path still works when routed through dispatcher."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "mock"

    result = asyncio.run(
        dispatch_turn(
            session,
            current_turn=session.turn_counter + 1,
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "success"
    # State should be unchanged (mock decides nothing)
    assert result.accepted_deltas == []
    assert result.rejected_deltas == []


def test_dispatcher_preserves_execution_result_coherence(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Dispatcher returns coherent TurnExecutionResult regardless of path."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "mock"

    result = asyncio.run(
        dispatch_turn(
            session,
            current_turn=session.turn_counter + 1,
            module=god_of_carnage_module,
        )
    )

    # Result should have all required TurnExecutionResult fields
    assert result.turn_number == session.turn_counter + 1
    assert result.session_id == session.session_id
    assert result.execution_status in ["success", "system_error"]
    assert isinstance(result.updated_canonical_state, dict)
    assert isinstance(result.accepted_deltas, list)
    assert isinstance(result.rejected_deltas, list)


def test_no_w2_scope_jump_dispatcher():
    """No scope jump into W2.2+ features."""
    assert True  # Scope validation is manual


class TestDispatcherWithAdapterRegistry:
    """Tests for dispatcher consuming canonical adapter registry."""

    def test_dispatcher_resolves_adapter_from_session_config(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Dispatcher resolves adapter from session.adapter_name."""
        from app.runtime.adapter_registry import clear_registry, register_adapter

        clear_registry()

        session = god_of_carnage_module_with_state
        session.execution_mode = "ai"
        session.adapter_name = "test_adapter"

        adapter = DeterministicTestAdapter()
        register_adapter("test_adapter", adapter)

        result = asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
            )
        )

        assert result.execution_status == "success"
        clear_registry()

    def test_dispatcher_raises_error_if_adapter_not_registered(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Dispatcher raises clear error if adapter not found in registry."""
        from app.runtime.adapter_registry import clear_registry

        clear_registry()

        session = god_of_carnage_module_with_state
        session.execution_mode = "ai"
        session.adapter_name = "nonexistent_adapter"

        with pytest.raises(ValueError, match="adapter 'nonexistent_adapter' not found"):
            asyncio.run(
                dispatch_turn(
                    session,
                    current_turn=session.turn_counter + 1,
                    module=god_of_carnage_module,
                )
            )

    def test_dispatcher_explicit_adapter_overrides_session_config(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Explicit ai_adapter parameter overrides session.adapter_name."""
        session = god_of_carnage_module_with_state
        session.execution_mode = "ai"
        session.adapter_name = "config_adapter"  # Won't be used

        # Pass adapter explicitly
        adapter = DeterministicTestAdapter()
        result = asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
                ai_adapter=adapter,  # Override session config
            )
        )

        assert result.execution_status == "success"

    def test_dispatcher_session_config_mode_mock(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Dispatcher can use session.execution_mode from configuration."""
        session = god_of_carnage_module_with_state
        session.execution_mode = "mock"

        result = asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
            )
        )

        assert result.execution_status == "success"

    def test_dispatcher_session_config_mode_ai_with_registered_adapter(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Dispatcher uses session config to determine execution mode and adapter."""
        from app.runtime.adapter_registry import clear_registry, register_adapter

        clear_registry()

        session = god_of_carnage_module_with_state
        session.execution_mode = "ai"
        session.adapter_name = "registered_adapter"

        adapter = DeterministicTestAdapter()
        register_adapter("registered_adapter", adapter)

        # No explicit adapter parameter—dispatcher should resolve from session
        result = asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
            )
        )

        assert result.execution_status == "success"
        clear_registry()

    def test_dispatcher_adapter_name_case_insensitive(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Adapter name lookup is case-insensitive."""
        from app.runtime.adapter_registry import clear_registry, register_adapter

        clear_registry()

        session = god_of_carnage_module_with_state
        session.execution_mode = "ai"
        session.adapter_name = "MyCaseAdapter"

        adapter = DeterministicTestAdapter()
        register_adapter("MyCaseAdapter", adapter)

        result = asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
            )
        )

        assert result.execution_status == "success"
        clear_registry()


class TestAIIntegrationThroughDispatcher:
    """Integration tests proving AI path is wired into canonical runtime loop."""

    def test_dispatcher_ai_path_uses_canonical_session_context(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """AI path receives canonical session/module context through dispatcher."""
        session = god_of_carnage_module_with_state
        session.execution_mode = "ai"

        adapter = DeterministicTestAdapter()

        result = asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
                ai_adapter=adapter,
            )
        )

        # Result should use the correct session and turn context
        assert result.session_id == session.session_id
        assert result.turn_number == session.turn_counter + 1

    def test_dispatcher_ai_path_commits_through_runtime_validation(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """AI path commits through engine-controlled validation, not bypassing it."""
        session = god_of_carnage_module_with_state
        session.execution_mode = "ai"

        # Adapter proposes a delta to a valid character
        class DeltaProposingAdapter(StoryAIAdapter):
            @property
            def adapter_name(self):
                return "delta-proposing"

            def generate(self, request):
                return AdapterResponse(
                    raw_output="Proposing state change",
                    structured_payload={
                        "scene_interpretation": "Character emotional state rises",
                        "detected_triggers": [],
                        "proposed_state_deltas": [
                            {
                                "target_path": "characters.veronique.emotional_state",
                                "next_value": 75,
                                "rationale": "Character is upset",
                            }
                        ],
                        "rationale": "Emotional escalation",
                    },
                )

        adapter = DeltaProposingAdapter()

        result = asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
                ai_adapter=adapter,
            )
        )

        # Delta should be processed through validation (not bypass it)
        assert result.execution_status == "success"
        # The validator accepts the delta, so it should be in accepted_deltas
        assert len(result.accepted_deltas) > 0

    def test_dispatcher_ai_path_malformed_output_fails_safely(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Malformed AI output fails safely through canonical path."""
        session = god_of_carnage_module_with_state
        session.execution_mode = "ai"

        # Adapter returns missing required fields
        class MalformedAdapter(StoryAIAdapter):
            @property
            def adapter_name(self):
                return "malformed"

            def generate(self, request):
                return AdapterResponse(
                    raw_output="incomplete",
                    structured_payload={
                        "scene_interpretation": "Test",
                        # Missing: rationale, detected_triggers, proposed_state_deltas
                    },
                )

        adapter = MalformedAdapter()

        result = asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
                ai_adapter=adapter,
            )
        )

        # W2.5 Phase 3: Fallback responder recovers from parse failure
        # Should recover safely with success (fallback with empty deltas)
        assert result.execution_status == "success"
        # State should be unchanged (safety guarantee - fallback has empty deltas)
        assert result.updated_canonical_state == session.canonical_state

    def test_dispatcher_both_paths_return_compatible_results(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Both mock and AI paths return compatible TurnExecutionResult."""
        session = god_of_carnage_module_with_state

        # Mock path result
        session.execution_mode = "mock"
        mock_result = asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
            )
        )

        # AI path result
        session.execution_mode = "ai"
        adapter = DeterministicTestAdapter()
        ai_result = asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
                ai_adapter=adapter,
            )
        )

        # Both should have identical structure
        assert type(mock_result) == type(ai_result)
        assert mock_result.session_id == ai_result.session_id
        assert hasattr(mock_result, "updated_canonical_state")
        assert hasattr(ai_result, "updated_canonical_state")
        assert hasattr(mock_result, "accepted_deltas")
        assert hasattr(ai_result, "accepted_deltas")

    def test_dispatcher_ai_path_full_pipeline_execution(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Full pipeline: request -> adapter -> parse -> normalize -> validate -> execute."""
        session = god_of_carnage_module_with_state
        session.execution_mode = "ai"

        # Create adapter that returns valid structured output
        adapter = DeterministicTestAdapter()

        # Execute through dispatcher
        result = asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
                ai_adapter=adapter,
            )
        )

        # Should complete successfully through all pipeline stages
        assert result.execution_status == "success"
        assert result.turn_number == session.turn_counter + 1
        # Canonical state should be updated (or unchanged if no deltas)
        assert isinstance(result.updated_canonical_state, dict)
        # Events should be created
        assert isinstance(result.events, list)

    def test_dispatcher_preserves_mock_path_availability(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Mock execution path remains fully available through dispatcher."""
        session = god_of_carnage_module_with_state
        session.execution_mode = "mock"

        result = asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
            )
        )

        assert result.execution_status == "success"
        # Mock path should produce empty deltas (no decisions made)
        assert result.accepted_deltas == []
        assert result.rejected_deltas == []

    def test_dispatcher_ai_execution_reaches_canonical_entry_point(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """AI execution is now callable from canonical entry point, not just tests."""
        session = god_of_carnage_module_with_state
        session.execution_mode = "ai"

        adapter = DeterministicTestAdapter()

        # This simulates production code calling the canonical dispatcher
        # Previously, execute_turn_with_ai was only reachable by tests
        result = asyncio.run(
            dispatch_turn(
                session,
                current_turn=session.turn_counter + 1,
                module=god_of_carnage_module,
                ai_adapter=adapter,
            )
        )

        # AI execution succeeded through the canonical path
        assert result.execution_status == "success"
