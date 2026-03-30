import pytest
from unittest.mock import patch, MagicMock
from tools.mcp_server.tools_registry import create_default_registry


@pytest.fixture
def registry():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            return create_default_registry()


def test_tools_list_includes_9_tools(registry):
    tools = registry.list_tools()
    assert len(tools) == 9


def test_tools_list_has_permissions():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            registry = create_default_registry()
            tools = registry.list_tools()
            for tool in tools:
                assert "permission" in tool
                assert tool["permission"] in ("read", "preview")


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
            mock_fs.get_module.return_value = {"name": "god_of_carnage", "path": "/repo/content/modules/god_of_carnage", "files": ["scenes.yaml", "lore.md"]}
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
                    {"file": "content/modules/god_of_carnage/lore.md", "line": 1, "text": "The god of carnage"}
                ]
            }
            registry = create_default_registry()
            tool = registry.get("wos.content.search")
            result = tool.handler({"pattern": "god"})
            assert result["hits"] == 2


def test_blocked_tool_returns_not_implemented():
    with patch("tools.mcp_server.tools_registry.BackendClient"):
        with patch("tools.mcp_server.tools_registry.FileSystemTools"):
            registry = create_default_registry()
            tool = registry.get("wos.session.get")
            result = tool.handler({})
            assert result.get("code") == "NOT_IMPLEMENTED"
