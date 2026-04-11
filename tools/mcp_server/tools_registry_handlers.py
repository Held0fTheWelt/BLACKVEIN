"""Compose domain MCP handler bundles into the default registry handler map."""

from __future__ import annotations

from typing import Any, Callable

from tools.mcp_server.backend_client import BackendClient
from tools.mcp_server.fs_tools import FileSystemTools
from tools.mcp_server.tools_registry_handlers_backend_session import (
    build_backend_session_mcp_handlers,
)
from tools.mcp_server.tools_registry_handlers_deferred import deferred_stub_handler_factory
from tools.mcp_server.tools_registry_handlers_filesystem import build_filesystem_mcp_handlers
from tools.mcp_server.tools_registry_handlers_governance import build_governance_mcp_handlers
from tools.mcp_server.tools_registry_handlers_protocol import RegistryListToolNames
from tools.mcp_server.tools_registry_handlers_research import build_research_mcp_handlers


def build_default_mcp_tool_handlers(
    backend: BackendClient,
    fs: FileSystemTools,
    registry: RegistryListToolNames,
    *,
    research_store: Any,
) -> tuple[
    dict[str, Callable[..., dict[str, Any]]],
    Callable[[str], Callable[[dict], dict]],
]:
    handlers: dict[str, Callable[..., dict[str, Any]]] = {}
    handlers.update(build_filesystem_mcp_handlers(fs))
    handlers.update(build_backend_session_mcp_handlers(backend))
    handlers.update(build_governance_mcp_handlers(backend, registry))
    handlers.update(build_research_mcp_handlers(research_store))
    return handlers, deferred_stub_handler_factory
