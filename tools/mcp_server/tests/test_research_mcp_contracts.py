from __future__ import annotations

from unittest.mock import patch

from tools.mcp_server.tools_registry import create_default_registry


def test_research_tools_are_registered_and_implemented():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            registry = create_default_registry()
            names = set(registry.list_tool_names())
            assert "wos.research.explore" in names
            assert "wos.research.bundle.build" in names
            assert "wos.canon.improvement.propose" in names
            for tool_name in (
                "wos.research.source.inspect",
                "wos.research.aspect.extract",
                "wos.research.claim.list",
                "wos.research.run.get",
                "wos.research.exploration.graph",
                "wos.canon.issue.inspect",
                "wos.research.explore",
                "wos.research.validate",
                "wos.research.bundle.build",
                "wos.canon.improvement.propose",
                "wos.canon.improvement.preview",
            ):
                tool = registry.get(tool_name)
                assert tool is not None
                assert tool.descriptor.implementation_status.value == "implemented"


def test_research_explore_requires_budget_contract():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            registry = create_default_registry()
            tool = registry.get("wos.research.explore")
            assert tool is not None
            result = tool.handler(
                {
                    "work_id": "god_of_carnage",
                    "module_id": "god_of_carnage",
                    "source_inputs": [{"source_type": "note", "title": "x", "raw_text": "test"}],
                }
            )
            assert result["error"] == "budget object required"
