"""MCP handlers backed by workspace filesystem tools (modules, content search)."""

from __future__ import annotations

from typing import Any, Callable

from tools.mcp_server.fs_tools import FileSystemTools


def build_filesystem_mcp_handlers(
    fs: FileSystemTools,
) -> dict[str, Callable[..., dict[str, Any]]]:
    def handle_list_modules(arguments: dict[str, Any]) -> dict[str, Any]:
        return {"modules": fs.list_modules()}

    def handle_get_module(arguments: dict[str, Any]) -> dict[str, Any]:
        module_id = arguments.get("module_id")
        return fs.get_module(module_id)

    def handle_search_content(arguments: dict[str, Any]) -> dict[str, Any]:
        pattern = arguments.get("pattern", "")
        case_sensitive = arguments.get("case_sensitive", False)
        return fs.search_content(pattern, case_sensitive)

    return {
        "wos.goc.list_modules": handle_list_modules,
        "wos.goc.get_module": handle_get_module,
        "wos.content.search": handle_search_content,
    }
