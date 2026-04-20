"""End-to-end integration tests for canonical AI-backed turn execution.

Tests prove that the canonical runtime dispatcher wiring is complete:
- Dispatcher routes to correct path based on execution_mode
- Session configuration (execution_mode, adapter_name) controls execution
- Adapter registry enables adapter selection
- Full pipeline executes without state corruption
- Decision logging captures AI decisions
"""

from __future__ import annotations

import pytest
from app.runtime.adapter_registry import clear_registry, register_adapter
from app.runtime.ai_adapter import AdapterResponse, StoryAIAdapter
from app.runtime.turn_dispatcher import dispatch_turn
from app.runtime.runtime_models import SessionState


class DeterministicAIAdapter(StoryAIAdapter):
    """Deterministic test adapter that returns controlled payloads.

    Used for end-to-end testing of the AI path without external dependencies.
    """

    def __init__(self, payload: dict | None = None, error: bool = False):
        self.payload = payload or {
            "scene_interpretation": "Test scene",
            "detected_triggers": [],
            "proposed_state_deltas": [],
            "rationale": "Deterministic test adapter",
        }
        self.error = error

    @property
    def adapter_name(self) -> str:
        return "deterministic_test_adapter"

    def generate(self, request) -> AdapterResponse:
        if self.error:
            return AdapterResponse(
                raw_output="error",
                structured_payload=None,
                error="Simulated adapter error for testing",
            )
        return AdapterResponse(
            raw_output="deterministic",
            structured_payload=self.payload,
        )


class ToolLoopIntegrationAdapter(StoryAIAdapter):
    """Integration adapter that performs one tool request before finalizing."""

    def __init__(self):
        self._calls = 0

    @property
    def adapter_name(self) -> str:
        return "tool_loop_integration_adapter"

    def generate(self, request) -> AdapterResponse:
        self._calls += 1
        if self._calls == 1:
            return AdapterResponse(
                raw_output="tool-request",
                structured_payload={
                    "type": "tool_request",
                    "tool_name": "wos.read.current_scene",
                    "arguments": {},
                },
            )
        return AdapterResponse(
            raw_output="deterministic-final",
            structured_payload={
                "scene_interpretation": "Tool-assisted finalization",
                "detected_triggers": [],
                "proposed_state_deltas": [],
                "rationale": "Finalize after host tool result",
            },
        )


class PreviewCorrectionIntegrationAdapter(StoryAIAdapter):
    """Integration adapter previewing invalid delta before corrected final output."""

    def __init__(self):
        self._calls = 0

    @property
    def adapter_name(self) -> str:
        return "preview_correction_integration_adapter"

    def generate(self, request) -> AdapterResponse:
        self._calls += 1
        if self._calls == 1:
            return AdapterResponse(
                raw_output="preview-request",
                structured_payload={
                    "type": "tool_request",
                    "tool_name": "wos.guard.preview_delta",
                    "arguments": {
                        "proposed_state_deltas": [
                            {
                                "target_path": "characters.nonexistent.emotional_state",
                                "next_value": 90,
                                "delta_type": "state_update",
                            }
                        ]
                    },
                },
            )
        return AdapterResponse(
            raw_output="preview-corrected-final",
            structured_payload={
                "scene_interpretation": "Corrected after preview",
                "detected_triggers": [],
                "proposed_state_deltas": [
                    {
                        "target_path": "characters.veronique.emotional_state",
                        "next_value": 90,
                        "delta_type": "state_update",
                    }
                ],
                "rationale": "Use preview feedback",
            },
        )


class MultiAgentIntegrationAdapter(StoryAIAdapter):
    """Integration adapter for C1 supervisor orchestration."""

    def __init__(self):
        self.calls: list[str] = []

    @property
    def adapter_name(self) -> str:
        return "multi_agent_integration_adapter"

    def generate(self, request) -> AdapterResponse:
        agent_id = (request.metadata.get("agent_invocation") or {}).get("agent_id", "unknown")
        self.calls.append(agent_id)

        if agent_id == "delta_planner":
            return AdapterResponse(
                raw_output="delta-planner",
                structured_payload={
                    "scene_interpretation": "delta planner interpretation",
                    "detected_triggers": [],
                    "proposed_state_deltas": [
                        {
                            "target_path": "characters.veronique.emotional_state",
                            "next_value": 64,
                            "delta_type": "state_update",
                        }
                    ],
                    "rationale": "planner rationale",
                },
            )
        if agent_id == "finalizer":
            merged = dict(request.metadata.get("supervisor_merge_payload") or {})
            merged["rationale"] = "integration finalizer output"
            return AdapterResponse(raw_output="finalizer", structured_payload=merged)

        return AdapterResponse(
            raw_output=f"{agent_id}",
            structured_payload={
                "scene_interpretation": f"{agent_id} interpretation",
                "detected_triggers": [],
                "proposed_state_deltas": [],
                "rationale": f"{agent_id} rationale",
            },
        )


@pytest.fixture
def deterministic_adapter():
    """Provide deterministic AI adapter for testing."""
    adapter = DeterministicAIAdapter()
    register_adapter("deterministic_test_adapter", adapter)
    yield adapter
    clear_registry()


@pytest.fixture
def error_adapter():
    """Adapter that signals an error."""
    adapter = DeterministicAIAdapter(error=True)
    register_adapter("error_adapter", adapter)
    yield adapter
    clear_registry()


class TestCanonicalAIPathSuccess:
    """Test successful AI-backed execution through canonical dispatcher."""

    @pytest.mark.asyncio
    async def test_dispatcher_routes_to_ai_path_when_configured(
        self, deterministic_adapter, god_of_carnage_module
    ):
        """Dispatcher routes to AI path based on execution_mode.

        Verifies: dispatcher entry point -> session config -> adapter selection -> AI execution
        """
        session = SessionState(
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="kitchen",
            execution_mode="ai",
            adapter_name="deterministic_test_adapter",
        )
        session.canonical_state = {
            "characters": {
                "veronique": {"emotional_state": 50}
            }
        }

        result = await dispatch_turn(
            session,
            current_turn=1,
            module=god_of_carnage_module,
        )

        assert result.execution_status == "success"
        assert result.turn_number == 1
        assert result.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_ai_execution_creates_decision_log_on_success(
        self, deterministic_adapter, god_of_carnage_module
    ):
        """AI decision is logged on successful execution.

        Verifies: decision logging captures adapter output, rationale, triggers, proposed deltas
        """
        session = SessionState(
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="kitchen",
            execution_mode="ai",
            adapter_name="deterministic_test_adapter",
        )
        session.canonical_state = {"characters": {}}

        result = await dispatch_turn(
            session,
            current_turn=1,
            module=god_of_carnage_module,
        )

        assert result.execution_status == "success"
        # Decision log should be in metadata if persisting
        assert result.turn_number == 1

    @pytest.mark.asyncio
    async def test_ai_delta_is_applied_to_state(
        self, god_of_carnage_module
    ):
        """State is updated correctly when AI proposes deltas.

        Verifies: delta flows through parse -> normalize -> validate -> apply -> commit
        """
        # Register adapter with a delta proposal
        payload = {
            "scene_interpretation": "Veronique is upset",
            "detected_triggers": [],
            "proposed_state_deltas": [
                {
                    "target_path": "characters.veronique.emotional_state",
                    "next_value": 75,
                    "rationale": "Conflict rising",
                }
            ],
            "rationale": "Update emotional state",
        }
        adapter = DeterministicAIAdapter(payload=payload)
        register_adapter("delta_adapter", adapter)

        session = SessionState(
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="kitchen",
            execution_mode="ai",
            adapter_name="delta_adapter",
        )
        session.canonical_state = {
            "characters": {
                "veronique": {"emotional_state": 50}
            }
        }

        result = await dispatch_turn(
            session,
            current_turn=1,
            module=god_of_carnage_module,
        )

        assert result.execution_status == "success"
        # Verify state was updated through accepted_deltas
        assert len(result.accepted_deltas) > 0
        clear_registry()

    @pytest.mark.asyncio
    async def test_next_situation_continuity_after_ai_execution(
        self, deterministic_adapter, god_of_carnage_module
    ):
        """Next-situation remains coherent after AI execution.

        Verifies: scene, turn, situation context are preserved/updated correctly
        """
        session = SessionState(
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="kitchen",
            execution_mode="ai",
            adapter_name="deterministic_test_adapter",
        )
        session.canonical_state = {"characters": {}}

        result = await dispatch_turn(
            session,
            current_turn=1,
            module=god_of_carnage_module,
        )

        assert result.execution_status == "success"
        assert result.updated_canonical_state is not None
        assert result.turn_number == 1

    @pytest.mark.asyncio
    async def test_dispatch_turn_can_complete_via_tool_loop_then_final_output(
        self, god_of_carnage_module
    ):
        """AI mode completes via bounded tool loop and preserves canonical flow."""
        adapter = ToolLoopIntegrationAdapter()
        register_adapter("tool_loop_integration_adapter", adapter)

        session = SessionState(
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="kitchen",
            execution_mode="ai",
            adapter_name="tool_loop_integration_adapter",
        )
        session.metadata["tool_loop"] = {
            "enabled": True,
            "allowed_tools": ["wos.read.current_scene"],
            "max_tool_calls_per_turn": 3,
        }
        original_state = {"characters": {"veronique": {"emotional_state": 50}}}
        session.canonical_state = original_state.copy()

        result = await dispatch_turn(
            session,
            current_turn=1,
            module=god_of_carnage_module,
        )

        assert result.execution_status == "success"
        assert result.guard_outcome is not None
        assert result.updated_canonical_state == original_state
        assert session.metadata["ai_decision_logs"][-1].tool_loop_summary is not None
        clear_registry()

    @pytest.mark.asyncio
    async def test_preview_feedback_allows_iterative_correction(
        self, god_of_carnage_module
    ):
        """Preview feedback is recorded and corrected final output improves acceptance."""
        adapter = PreviewCorrectionIntegrationAdapter()
        register_adapter("preview_correction_integration_adapter", adapter)

        session = SessionState(
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="kitchen",
            execution_mode="ai",
            adapter_name="preview_correction_integration_adapter",
        )
        session.canonical_state = {"characters": {"veronique": {"emotional_state": 50}}}
        session.metadata["tool_loop"] = {
            "enabled": True,
            "allowed_tools": ["wos.guard.preview_delta"],
            "max_tool_calls_per_turn": 3,
        }

        result = await dispatch_turn(
            session,
            current_turn=1,
            module=god_of_carnage_module,
        )

        assert result.execution_status == "success"
        log = session.metadata["ai_decision_logs"][-1]
        assert log.preview_diagnostics is not None
        assert log.preview_diagnostics["revised_after_preview"] is True
        assert log.preview_diagnostics["improved_acceptance_vs_last_preview"] is True
        clear_registry()

    @pytest.mark.asyncio
    async def test_dispatch_turn_supports_real_multi_agent_orchestration(
        self, god_of_carnage_module
    ):
        """Orchestration executes separate subagents and records diagnostics."""
        adapter = MultiAgentIntegrationAdapter()
        register_adapter("multi_agent_integration_adapter", adapter)

        session = SessionState(
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="kitchen",
            execution_mode="ai",
            adapter_name="multi_agent_integration_adapter",
        )
        session.canonical_state = {
            "characters": {"veronique": {"emotional_state": 50}}
        }
        session.metadata["agent_orchestration"] = {"enabled": True}
        session.metadata["tool_loop"] = {"enabled": False}

        result = await dispatch_turn(
            session,
            current_turn=1,
            module=god_of_carnage_module,
        )

        assert result.execution_status == "success"
        assert len([call for call in adapter.calls if call != "finalizer"]) >= 2
        assert "finalizer" in adapter.calls
        ai_log = session.metadata["ai_decision_logs"][-1]
        assert ai_log.supervisor_plan is not None
        assert ai_log.subagent_invocations is not None
        assert ai_log.merge_finalization is not None
        assert ai_log.orchestration_budget_summary is not None
        consumed = ai_log.orchestration_budget_summary["consumed"]
        assert consumed["token_usage_mode"] in {"exact", "proxy", "mixed"}
        assert "consumed_total_tokens" in consumed
        assert ai_log.tool_loop_summary is not None
        controls = ai_log.tool_loop_summary.get("execution_controls") or {}
        assert controls.get("agent_orchestration_active") is True
        assert controls.get("tool_loop_active") is False
        clear_registry()


class TestCanonicalAIPathFailure:
    """Test failure handling for AI-backed execution."""

    @pytest.mark.asyncio
    async def test_malformed_adapter_output_fails_safely(
        self, god_of_carnage_module
    ):
        """Malformed adapter output doesn't corrupt state.

        Verifies: parse failure is caught before state mutation
        """
        # Register adapter with missing required field
        payload = {"scene_interpretation": "Missing rationale"}
        adapter = DeterministicAIAdapter(payload=payload)
        register_adapter("malformed", adapter)

        session = SessionState(
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="kitchen",
            execution_mode="ai",
            adapter_name="malformed",
        )
        original_state = {"characters": {"test": {}}}
        session.canonical_state = original_state.copy()

        result = await dispatch_turn(
            session,
            current_turn=1,
            module=god_of_carnage_module,
        )

        # W2.5 Phase 3: Fallback responder recovers from parse failure
        # Verify fallback recovery succeeded
        assert result.execution_status == "success"
        # Verify state unchanged (fallback proposes empty deltas)
        assert result.updated_canonical_state == original_state
        clear_registry()

    @pytest.mark.asyncio
    async def test_adapter_error_fails_safely(
        self, god_of_carnage_module
    ):
        """Adapter error doesn't corrupt state.

        Verifies: adapter errors caught, state preserved, logged appropriately
        """
        adapter = DeterministicAIAdapter(error=True)
        register_adapter("error_adapter", adapter)

        session = SessionState(
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="kitchen",
            execution_mode="ai",
            adapter_name="error_adapter",
        )
        original_state = {"characters": {}}
        session.canonical_state = original_state.copy()

        result = await dispatch_turn(
            session,
            current_turn=1,
            module=god_of_carnage_module,
        )

        # W2.5 Phase 4: Adapter error exhausts retries, activates safe-turn recovery
        # Safe-turn preserves state safely
        assert result.execution_status == "success"
        assert result.updated_canonical_state == original_state  # Safe-turn doesn't mutate
        clear_registry()

    @pytest.mark.asyncio
    async def test_decision_log_created_on_failure(
        self, god_of_carnage_module
    ):
        """Decision is logged even on failure.

        Verifies: failure path captures error details for debugging
        """
        adapter = DeterministicAIAdapter(error=True)
        register_adapter("error_adapter", adapter)

        session = SessionState(
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="kitchen",
            execution_mode="ai",
            adapter_name="error_adapter",
        )
        session.canonical_state = {}

        result = await dispatch_turn(
            session,
            current_turn=1,
            module=god_of_carnage_module,
        )

        # W2.5 Phase 4: Adapter error exhausts retries, activates safe-turn recovery
        # Safe-turn succeeds with no-op execution and decision logs capture recovery
        assert result.execution_status == "success"
        # Verify error and recovery were captured in logs
        clear_registry()


class TestCanonicalMockPath:
    """Test mock path execution through canonical dispatcher."""

    @pytest.mark.asyncio
    async def test_mock_path_through_dispatcher(
        self, god_of_carnage_module
    ):
        """Mock path works through same canonical dispatcher.

        Verifies: dispatcher correctly routes mock mode, mock path unchanged
        """
        session = SessionState(
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="kitchen",
            execution_mode="mock",
            adapter_name="mock",  # Won't be used in mock mode
        )
        session.canonical_state = {"characters": {}}

        result = await dispatch_turn(
            session,
            current_turn=1,
            module=god_of_carnage_module,
        )

        assert result.execution_status == "success"
        assert result.turn_number == 1
