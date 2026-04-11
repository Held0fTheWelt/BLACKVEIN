"""Tool registry and metadata — derived from ai_stack canonical MCP descriptors."""

from typing import Any, Callable, Optional

from ai_stack.mcp_canonical_surface import (
    CANONICAL_MCP_TOOL_DESCRIPTORS,
    McpCanonicalToolDescriptor,
    McpSuite,
    descriptor_to_public_metadata,
)
from tools.mcp_server.backend_client import BackendClient
from tools.mcp_server.config import Config
from tools.mcp_server.fs_tools import FileSystemTools
from tools.mcp_server.tools_registry_handlers import build_default_mcp_tool_handlers
from tools.mcp_server.tools_registry_metadata import (
    MCP_DEFAULT_TOOL_DESCRIPTIONS,
    MCP_DEFAULT_TOOL_INPUT_SCHEMAS,
)


class ToolDefinition:
    """Tool metadata: canonical strand + handler (permission_legacy for older clients)."""

    def __init__(
        self,
        descriptor: McpCanonicalToolDescriptor,
        description: str,
        handler: Callable[..., dict[str, Any]],
        input_schema: dict[str, Any],
    ):
        self.descriptor = descriptor
        self.name = descriptor.name
        self.description = description
        self.handler = handler
        self.input_schema = input_schema
        self.tool_class = descriptor.tool_class
        self.authority_source = descriptor.authority_source
        self.implementation_status = descriptor.implementation_status
        self.permission = descriptor.permission_legacy

    def to_dict(self) -> dict[str, Any]:
        meta = descriptor_to_public_metadata(self.descriptor)
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "permission": self.permission,
            "tool_class": meta["tool_class"],
            "authority_source": meta["authority_source"],
            "implementation_status": meta["implementation_status"],
            "governance": meta["governance"],
            "narrative_mutation_risk": meta["narrative_mutation_risk"],
            "mcp_suite": meta["mcp_suite"],
        }


class ToolRegistry:
    """Central registry of available tools."""

    def __init__(self) -> None:
        self.tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self.tools.get(name)

    def list_tool_names(self) -> list[str]:
        return sorted(self.tools.keys())

    def list_tools(self) -> list[dict[str, Any]]:
        return [tool.to_dict() for tool in self.tools.values()]


def create_default_registry(
    suite_filter: Optional[McpSuite] = None,
    *,
    backend: Optional[BackendClient] = None,
    fs: Optional[FileSystemTools] = None,
) -> ToolRegistry:
    registry = ToolRegistry()
    config = Config()
    if backend is None:
        backend = BackendClient(base_url=config.backend_url, bearer_token=config.bearer_token)
    if fs is None:
        fs = FileSystemTools(config)
    from ai_stack.research_langgraph import research_store_from_repo_root

    research_store = research_store_from_repo_root(config.repo_root)
    handlers, make_blocked = build_default_mcp_tool_handlers(
        backend, fs, registry, research_store=research_store
    )

    for desc in CANONICAL_MCP_TOOL_DESCRIPTORS:
        if suite_filter is not None and desc.mcp_suite != suite_filter:
            continue
        name = desc.name
        if name in handlers:
            handler_fn = handlers[name]
        else:
            handler_fn = make_blocked(name)
        registry.register(
            ToolDefinition(
                descriptor=desc,
                description=MCP_DEFAULT_TOOL_DESCRIPTIONS.get(name, name),
                handler=handler_fn,
                input_schema=MCP_DEFAULT_TOOL_INPUT_SCHEMAS.get(
                    name, {"type": "object", "properties": {}, "required": []}
                ),
            )
        )

    return registry
