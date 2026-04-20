import pytest
from unittest.mock import patch
from tools.mcp_server.tools_registry import create_default_registry
from ai_stack.mcp_canonical_surface import CANONICAL_MCP_TOOL_DESCRIPTORS


@pytest.fixture
def registry():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            return create_default_registry()


def test_tools_list_includes_all_canonical_tools(registry):
    tools = registry.list_tools()
    assert len(tools) == len(CANONICAL_MCP_TOOL_DESCRIPTORS)


def test_tools_list_has_tool_class_and_legacy_permission():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            reg = create_default_registry()
            tools = reg.list_tools()
            for tool in tools:
                assert "tool_class" in tool
                assert tool["tool_class"] in ("read_only", "review_bound", "write_capable")
                assert "permission" in tool
                assert tool["permission"] in ("read", "preview", "write")


def test_health_tool_handler_returns_dict():
    with patch("tools.mcp_server.tools_registry.BackendClient") as MockClient:
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            mock_instance = MockClient.return_value
            mock_instance.health.return_value = {"status": "ok"}
            registry = create_default_registry()
            tool = registry.get("wos.system.health")
            result = tool.handler({})
            assert result["status"] == "healthy"
            assert result["backend"]["status"] == "ok"


def test_session_create_tool_handler():
    with patch("tools.mcp_server.tools_registry.BackendClient") as MockClient:
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            mock_instance = MockClient.return_value
            mock_instance.create_session.return_value = {"session_id": "sess-456"}
            registry = create_default_registry()
            tool = registry.get("wos.session.create")
            result = tool.handler({"module_id": "god_of_carnage"})
            assert result["session_id"] == "sess-456"


def test_list_modules_tool_handler():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools") as MockFS:
            mock_fs = MockFS.return_value
            mock_fs.list_modules.return_value = ["god_of_carnage", "test_mod"]
            registry = create_default_registry()
            tool = registry.get("wos.goc.list_modules")
            result = tool.handler({})
            assert result["modules"] == ["god_of_carnage", "test_mod"]


def test_get_module_tool_handler():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools") as MockFS:
            mock_fs = MockFS.return_value
            mock_fs.get_module.return_value = {
                "name": "god_of_carnage",
                "path": "/repo/content/modules/god_of_carnage",
                "files": ["scenes.yaml", "lore.md"],
            }
            registry = create_default_registry()
            tool = registry.get("wos.goc.get_module")
            result = tool.handler({"module_id": "god_of_carnage"})
            assert result["name"] == "god_of_carnage"
            assert "scenes.yaml" in result["files"]


def test_search_content_tool_handler():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools") as MockFS:
            mock_fs = MockFS.return_value
            mock_fs.search_content.return_value = {
                "pattern": "god",
                "hits": 2,
                "results": [
                    {"file": "content/modules/god_of_carnage/scenes.yaml", "line": 5, "text": "god_of_carnage"},
                    {"file": "content/modules/god_of_carnage/lore.md", "line": 1, "text": "The god of carnage"},
                ],
            }
            registry = create_default_registry()
            tool = registry.get("wos.content.search")
            result = tool.handler({"pattern": "god"})
            assert result["hits"] == 2


def test_capability_catalog_tool_handler_enriched():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            registry = create_default_registry()
            tool = registry.get("wos.capabilities.catalog")
            result = tool.handler({})
            assert "capabilities" in result
            caps = result["capabilities"]
            row = next(c for c in caps if c["name"] == "wos.context_pack.build")
            assert row["tool_class"] == "read_only"
            assert "governance_posture" in row
            assert row["authority_source"] == "ai_stack_capability_registry_mirror"


def test_operator_truth_tool_handler():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            registry = create_default_registry()
            tool = registry.get("wos.mcp.operator_truth")
            result = tool.handler({})
            assert "operator_truth" in result
            assert "catalog_alignment" in result
            ot = result["operator_truth"]
            assert ot["grammar_version"] == "mcp_operator_truth_v1"
            assert "runtime_authority_preservation" in ot
            assert "available_vs_deferred" in ot
            assert ot["available_vs_deferred"]["available"] >= 0


def test_all_tools_are_implemented():
    """Verify all registered tools are implemented (no deferred stubs)."""
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            registry = create_default_registry()
            for tool_name in registry.list_tool_names():
                tool = registry.get(tool_name)
                assert tool.descriptor.implementation_status.value == "implemented"
