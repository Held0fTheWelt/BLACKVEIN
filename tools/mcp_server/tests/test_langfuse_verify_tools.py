from __future__ import annotations

import os
import sys
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
        preflight_proc = MagicMock()
        preflight_proc.returncode = 0
        preflight_proc.stdout = "import_ok=app.story_runtime\n"
        preflight_proc.stderr = ""
        world_engine_proc = MagicMock()
        world_engine_proc.returncode = 0
        world_engine_proc.stdout = "1 passed"
        world_engine_proc.stderr = ""
        ai_stack_proc = MagicMock()
        ai_stack_proc.returncode = 0
        ai_stack_proc.stdout = "1 passed"
        ai_stack_proc.stderr = ""
        run_mock.side_effect = [preflight_proc, world_engine_proc, ai_stack_proc]
        out = tool.handler({})
    assert run_mock.call_count == 3
    assert out["ok"] is True
    assert out["world_engine"]["ok"] is True
    assert out["ai_stack"]["ok"] is True
    assert out["world_engine"]["returncode"] == 0
    assert out["ai_stack"]["returncode"] == 0
    assert out["world_engine"]["command"][0] == sys.executable
    assert out["ai_stack"]["command"][0] == sys.executable
    assert out["world_engine"]["command"][1:5] == ["-m", "pytest", "tests/test_trace_middleware.py", "-q"]
    assert out["ai_stack"]["command"][1:5] == [
        "-m",
        "pytest",
        "ai_stack/tests/test_actor_lane_absence_governance.py",
        "-q",
    ]
    assert out["world_engine"]["cwd"].replace("\\", "/").endswith("/WorldOfShadows/world-engine")
    assert out["ai_stack"]["cwd"].replace("\\", "/").endswith("/WorldOfShadows")
    assert "world-engine" in out["world_engine"]["pythonpath"]
    assert "world-engine" not in out["ai_stack"]["pythonpath"].split(os.pathsep)[0]
    assert "1 passed" in out["world_engine"]["stdout_tail"]
    assert "1 passed" in out["ai_stack"]["stdout_tail"]
    assert run_mock.call_args_list[0].args[0][0] == sys.executable
    assert run_mock.call_args_list[1].args[0][0] == sys.executable
    assert run_mock.call_args_list[2].args[0][0] == sys.executable
    assert run_mock.call_args_list[0].kwargs["cwd"].replace("\\", "/").endswith("/WorldOfShadows/world-engine")
    assert run_mock.call_args_list[1].kwargs["cwd"].replace("\\", "/").endswith("/WorldOfShadows/world-engine")
    assert run_mock.call_args_list[2].kwargs["cwd"].replace("\\", "/").endswith("/WorldOfShadows")


def test_run_projection_tests_returns_preflight_diagnostics_on_import_error():
    registry = _registry()
    tool = registry.get("run_projection_tests")
    with patch("tools.mcp_server.tools_registry_handlers_langfuse_verify.subprocess.run") as run_mock:
        preflight_proc = MagicMock()
        preflight_proc.returncode = 1
        preflight_proc.stdout = ""
        preflight_proc.stderr = "ModuleNotFoundError: No module named 'app.story_runtime'"
        run_mock.return_value = preflight_proc
        out = tool.handler({})
    assert run_mock.call_count == 1
    assert out["ok"] is False
    assert out["world_engine"]["ok"] is False
    assert out["world_engine"]["command"][0] == sys.executable
    assert out["world_engine"]["cwd"].replace("\\", "/").endswith("/WorldOfShadows/world-engine")
    assert "world-engine" in out["world_engine"]["pythonpath"]
    assert "ModuleNotFoundError" in out["world_engine"]["stderr_tail"]
    assert out["ai_stack"]["ok"] is False
    assert out["ai_stack"]["returncode"] is None
    assert "skipped_due_to_world_engine_preflight_failure" in out["ai_stack"]["stderr_tail"]


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

