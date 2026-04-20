"""Test that ai_stack.mcp_canonical_surface can be imported without numpy.

This validates that the lightweight import path is truly lightweight and
does not leak heavy optional dependencies.
"""

import sys


class BlockNumpy:
    """Meta path hook to block numpy imports (for testing lightweight imports)."""

    def find_spec(self, fullname, path, target=None):
        if fullname == "numpy" or fullname.startswith("numpy."):
            raise ModuleNotFoundError(f"numpy is blocked for lightweight import test")
        return None


def test_mcp_canonical_surface_imports_without_numpy():
    """Verify mcp_canonical_surface can be imported when numpy is unavailable."""
    blocker = BlockNumpy()
    sys.meta_path.insert(0, blocker)

    modules_to_remove = [k for k in sys.modules.keys() if "ai_stack" in k or "numpy" in k]
    cached_modules = {k: sys.modules.pop(k) for k in modules_to_remove}

    try:
        from ai_stack.mcp_canonical_surface import (
            CANONICAL_MCP_TOOL_DESCRIPTORS,
            McpOperatingProfile,
            build_compact_mcp_operator_truth,
        )

        assert len(CANONICAL_MCP_TOOL_DESCRIPTORS) > 0
        assert hasattr(McpOperatingProfile, "healthy")
        assert callable(build_compact_mcp_operator_truth)

    finally:
        sys.meta_path.remove(blocker)
        sys.modules.update(cached_modules)


def test_mcp_server_tools_list_without_numpy():
    """Verify MCP server can list tools without numpy being imported."""
    blocker = BlockNumpy()
    sys.meta_path.insert(0, blocker)

    modules_to_remove = [k for k in sys.modules.keys() if "ai_stack" in k or "numpy" in k or "tools" in k]
    cached_modules = {k: sys.modules.pop(k) for k in modules_to_remove}

    try:
        from tools.mcp_server.server import McpServer

        server = McpServer()
        tools = server.registry.list_tools()

        assert len(tools) > 0
        assert any(t["name"] == "wos.system.health" for t in tools)

    finally:
        sys.meta_path.remove(blocker)
        sys.modules.update(cached_modules)


def test_capabilities_imports_without_numpy():
    """Verify capabilities.py can be imported when numpy is unavailable."""
    blocker = BlockNumpy()
    sys.meta_path.insert(0, blocker)

    modules_to_remove = [k for k in sys.modules.keys() if "ai_stack" in k or "numpy" in k]
    cached_modules = {k: sys.modules.pop(k) for k in modules_to_remove}

    try:
        from ai_stack import capabilities

        assert hasattr(capabilities, "capability_catalog")
        assert callable(capabilities.capability_catalog)

    finally:
        sys.meta_path.remove(blocker)
        sys.modules.update(cached_modules)
