from __future__ import annotations

from unittest.mock import MagicMock, patch

from tools.mcp_server.tools_registry import create_default_registry


def _registry():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            return create_default_registry()


def test_langfuse_verify_tools_registered():
    registry = _registry()
    assert registry.get("run_projection_tests") is not None
    assert registry.get("fetch_langfuse_trace") is not None
    assert registry.get("query_langfuse_traces") is not None
    assert registry.get("assert_langfuse_opening_contract") is not None
    assert registry.get("summarize_live_opening_matrix") is not None


def test_run_projection_tests_returns_structured_result():
    registry = _registry()
    tool = registry.get("run_projection_tests")
    with patch("tools.mcp_server.tools_registry_handlers_langfuse_verify.subprocess.run") as run_mock:
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "2 passed"
        proc.stderr = ""
        run_mock.return_value = proc
        out = tool.handler({})
    assert out["ok"] is True
    assert out["returncode"] == 0
    assert "pytest" in out["command"]
    assert "2 passed" in out["stdout_tail"]


def test_assert_live_opening_contract_reports_missing_field():
    registry = _registry()
    tool = registry.get("assert_langfuse_opening_contract")
    trace_payload = {
        "id": "lf-live-1",
        "metadata": {
            "trace_origin": "live_ui",
            "execution_tier": "live",
            "canonical_player_flow": True,
            "selected_player_role": "annette",
            "human_actor_id": "annette",
            "final_adapter": "openai",
            "quality_class": "healthy",
        },
        "scores": [
            {"name": "opening_shape_contract_pass", "value": 1.0},
            {"name": "live_runtime_contract_pass", "value": 1.0},
            {"name": "live_opening_contract_pass", "value": 0.0},
        ],
    }
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_get_trace",
        return_value=trace_payload,
    ):
        out = tool.handler({"mode": "live", "langfuse_trace_id": "lf-live-1"})
    assert out["ok"] is False
    assert any(f["missing_field"] == "scores.live_opening_contract_pass" for f in out["failures"])


def test_query_langfuse_traces_filters_canonical_player_flow_false():
    registry = _registry()
    tool = registry.get("query_langfuse_traces")
    rows = [
        {
            "id": "lf-pytest-1",
            "metadata": {"trace_origin": "pytest", "canonical_player_flow": False},
            "scores": [{"name": "live_opening_contract_pass", "value": 0.0}],
        },
        {
            "id": "lf-live-1",
            "metadata": {"trace_origin": "live_ui", "canonical_player_flow": True},
            "scores": [{"name": "live_opening_contract_pass", "value": 1.0}],
        },
    ]
    with patch(
        "tools.mcp_server.tools_registry_handlers_langfuse_verify._langfuse_query_traces",
        return_value=[rows[0]],
    ):
        out = tool.handler({"trace_origin": "pytest", "canonical_player_flow": False, "limit": 10})
    assert out["ok"] is True
    assert out["count"] == 1
    assert out["traces"][0]["metadata"]["canonical_player_flow"] is False

