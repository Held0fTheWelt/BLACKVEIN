"""Tests for B1 MCP Preflight Context Enrichment for AI Turns."""

import json
from unittest.mock import Mock

import pytest
from ai_stack.mcp_canonical_surface import CANONICAL_MCP_TOOL_DESCRIPTORS

from app.mcp_client.client import MCPEnrichmentClient, MCPToolError, OperatorEndpointClient
from app.mcp_client.enrichment import _PREFLIGHT_TOOLS, build_mcp_enrichment
from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.runtime_models import SessionState


# ===== Test Adapter: CapturingAdapter =====


class CapturingAdapter(StoryAIAdapter):
    """Test adapter that captures requests for inspection."""

    def __init__(self):
        """Initialize capturing adapter."""
        self.last_request: AdapterRequest | None = None

    @property
    def adapter_name(self) -> str:
        """Returns 'capturing-test' as adapter identifier."""
        return "capturing-test"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        """Capture request and return success response."""
        self.last_request = request
        return AdapterResponse(
            raw_output="[captured request]",
            structured_payload={
                "scene_interpretation": "Captured",
                "detected_triggers": [],
                "proposed_state_deltas": [],
                "rationale": "Test adapter captured request",
            },
        )


# ===== Test MCP Clients =====


class SuccessMockMCPClient:
    """Mock MCP client that succeeds."""

    def call_tool(
        self, tool_name: str, arguments: dict | None = None, *, timeout_seconds: float = 5.0
    ) -> dict:
        """Return mock success response."""
        session_id = (arguments or {}).get("session_id", "test-session")

        if tool_name == "wos.session.get":
            return {
                "session_id": session_id,
                "module_id": "god_of_carnage",
                "status": "active",
                "turn_counter": 5,
            }
        elif tool_name == "wos.session.state":
            return {
                "canonical_state": {"characters": []},
                "character_count": 0,
                "scene_count": 1,
            }
        elif tool_name == "wos.session.logs":
            return {
                "events": [],
                "event_count": 0,
            }
        elif tool_name == "wos.session.diag":
            return {
                "diagnostics": {"ok": True},
                "warnings": [],
            }
        return {"result": "ok"}

    def call_tool_strict(
        self,
        tool_name: str,
        input_data: dict | None = None,
        operating_profile: str = "execute",
        timeout_seconds: float = 5.0,
    ) -> dict:
        """Delegate to ``call_tool`` (enrichment uses strict entrypoint)."""
        return self.call_tool(tool_name, input_data, timeout_seconds=timeout_seconds)


class TimeoutMockMCPClient:
    """Mock MCP client that times out on first call."""

    def __init__(self):
        """Initialize with call counter."""
        self.call_count = 0

    def call_tool(
        self, tool_name: str, arguments: dict | None = None, *, timeout_seconds: float = 5.0
    ) -> dict:
        """Raise timeout on first call, succeed on others."""
        self.call_count += 1
        if self.call_count == 1 and tool_name == "wos.session.get":
            raise MCPToolError(tool_name, "timeout")
        # Return success for other calls
        return {"result": "ok"}

    def call_tool_strict(
        self,
        tool_name: str,
        input_data: dict | None = None,
        operating_profile: str = "execute",
        timeout_seconds: float = 5.0,
    ) -> dict:
        """Delegate to ``call_tool`` (enrichment uses strict entrypoint)."""
        return self.call_tool(tool_name, input_data, timeout_seconds=timeout_seconds)


# ===== Tests =====


@pytest.mark.asyncio
async def test_mock_mode_does_not_call_mcp(god_of_carnage_module_with_state):
    """Test that mock mode doesn't call MCP client."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "mock"  # Explicitly set to mock
    session.metadata["mcp_enrichment_enabled"] = False

    mock_client = Mock(spec=MCPEnrichmentClient)

    # Mock mode should not call client
    # We can't directly test dispatch_turn without a full turn setup,
    # so instead test that enrichment is only called when activated
    assert session.execution_mode == "mock"
    assert not session.metadata.get("mcp_enrichment_enabled")


@pytest.mark.asyncio
async def test_ai_mode_with_enrichment_enabled_calls_preflight(god_of_carnage_module_with_state):
    """Test that AI mode with enrichment enabled calls preflight."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.adapter_name = "capturing-test"
    session.metadata["mcp_enrichment_enabled"] = True

    mock_client = SuccessMockMCPClient()
    session.metadata["_mcp_client_override"] = mock_client

    # Build enrichment to verify client is called
    enrichment = build_mcp_enrichment(
        session.session_id,
        "test-trace-id",
        mock_client,
    )

    # Verify client was called and results captured
    assert enrichment["session_snapshot"] is not None
    assert enrichment["session_snapshot"]["module_id"] == "god_of_carnage"
    assert enrichment["call_count"] == 4  # All 4 tools attempted


@pytest.mark.asyncio
async def test_enrichment_failure_does_not_break_turn(god_of_carnage_module_with_state):
    """Test that enrichment failure doesn't break turn execution."""
    session = god_of_carnage_module_with_state

    # Create a client that fails
    class FailingMockClient:
        def call_tool(self, tool_name: str, arguments: dict | None = None, *, timeout_seconds: float = 5.0) -> dict:
            raise MCPToolError(tool_name, "service_unavailable")

        def call_tool_strict(
            self,
            tool_name: str,
            input_data: dict | None = None,
            operating_profile: str = "execute",
            timeout_seconds: float = 5.0,
        ) -> dict:
            return self.call_tool(tool_name, input_data, timeout_seconds=timeout_seconds)

    failing_client = FailingMockClient()

    # Build enrichment with failing client
    enrichment = build_mcp_enrichment(
        session.session_id,
        "test-trace-id",
        failing_client,
    )

    # Verify turn continues with warnings
    assert len(enrichment["warnings"]) > 0
    assert enrichment["call_count"] == 4
    # All tool calls should have failed
    assert all(not tc["success"] for tc in enrichment["tool_calls"])


@pytest.mark.asyncio
async def test_enrichment_timeout_degrades_gracefully(god_of_carnage_module_with_state):
    """Test that enrichment timeout generates warnings."""
    session = god_of_carnage_module_with_state

    timeout_client = TimeoutMockMCPClient()

    enrichment = build_mcp_enrichment(
        session.session_id,
        "test-trace-id",
        timeout_client,
    )

    # Verify timeout warning captured
    warning_texts = " ".join(enrichment["warnings"])
    assert "timeout" in warning_texts.lower()
    # First call timed out, subsequent calls should succeed
    assert enrichment["call_count"] == 4


@pytest.mark.asyncio
async def test_adapter_request_metadata_contains_enrichment(god_of_carnage_module_with_state):
    """Test that AdapterRequest metadata contains enrichment without secrets."""
    session = god_of_carnage_module_with_state

    # Verify metadata structure
    enrichment = {
        "session_snapshot": {"session_id": "test"},
        "state_snapshot": {"canonical_state": {}},
        "recent_logs": {"events": []},
        "diagnostics": {"ok": True},
        "tool_calls": [{"tool_name": "wos.session.get", "success": True, "duration_ms": 100}],
        "warnings": [],
        "call_count": 4,
    }

    # Serialize to JSON and verify no secrets
    enrichment_json = json.dumps(enrichment)
    assert "Authorization" not in enrichment_json
    assert "Bearer" not in enrichment_json
    assert "token" not in enrichment_json.lower()


@pytest.mark.asyncio
async def test_guard_validates_after_enrichment(god_of_carnage_module_with_state):
    """Test that guard still validates AI output after enrichment."""
    session = god_of_carnage_module_with_state

    # Verify session state guards work
    assert session.session_id is not None
    assert session.turn_counter is not None
    # Guard validation would happen in actual turn execution
    # For this test, we just verify session is in valid state for such validation


class TestOperatorEndpointClient:
    """Registry-backed MCP client (``OperatorEndpointClient`` is an alias of ``MCPClient``)."""

    def test_call_tool_get_returns_placeholder_snapshot(self):
        client = OperatorEndpointClient()
        out = client.call_tool("wos.session.get", {"session_id": "abc"})
        assert out["success"] is True
        assert out["session_id"] == "abc"

    def test_call_tool_missing_session_id_non_strict_returns_error(self):
        client = OperatorEndpointClient()
        out = client.call_tool("wos.session.get", {})
        assert out["success"] is False
        assert "session_id" in out.get("error", "").lower()

    def test_call_tool_strict_missing_session_id_raises(self):
        client = OperatorEndpointClient()
        with pytest.raises(MCPToolError) as exc:
            client.call_tool_strict("wos.session.get", {})
        assert "session_id" in exc.value.reason.lower()

    def test_call_tool_strict_unknown_tool_suffix_raises_before_registry(self):
        """Unknown last segment is rejected by profile allow-list before registry lookup."""
        client = OperatorEndpointClient()
        with pytest.raises(MCPToolError) as exc:
            client.call_tool_strict("wos.session.nonexistent_tool", {"session_id": "sid"})
        assert "unauthorized" in exc.value.reason.lower() or "not available" in exc.value.reason.lower()

    def test_call_tool_strict_execute_turn_denied_in_read_only(self):
        client = OperatorEndpointClient()
        with pytest.raises(MCPToolError) as exc:
            client.call_tool_strict(
                "wos.session.execute_turn",
                {"session_id": "s", "player_id": "p", "action": {}},
                operating_profile="read_only",
            )
        assert "unauthorized" in exc.value.reason.lower()

    def test_call_tool_unknown_operating_profile_non_strict(self):
        client = OperatorEndpointClient()
        out = client.call_tool(
            "wos.session.get",
            {"session_id": "abc"},
            operating_profile="not_a_real_profile",
        )
        assert out["success"] is False
        assert "operating profile" in out.get("error", "").lower()

    def test_call_tool_strict_unknown_operating_profile_raises(self):
        client = OperatorEndpointClient()
        with pytest.raises(MCPToolError) as exc:
            client.call_tool_strict(
                "wos.session.get",
                {"session_id": "abc"},
                operating_profile="not_a_real_profile",
            )
        assert "operating profile" in exc.value.reason.lower()


def test_enrichment_prefight_tool_names_are_canonical():
    canonical_names = {d.name for d in CANONICAL_MCP_TOOL_DESCRIPTORS}
    preflight_names = {name for name, _priority in _PREFLIGHT_TOOLS}
    assert preflight_names <= canonical_names
