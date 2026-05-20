"""Tool registry and metadata — derived from ai_stack canonical MCP descriptors.

Naming model (see ``docs/mcp/12_M1_canonical_parity.md`` and the registry-alias
unit tests):

* Canonical identity is the dotted ``wos.<group>.<name>`` form carried on the
  ``McpCanonicalToolDescriptor`` and referenced from every governance artifact
  (suite map, ADRs, contract v0). It stays the source of truth.
* Wire identity emitted by ``tools/list`` is the underscored ``cursor_safe``
  form (``wos_<group>_<name>``). MCP hosts that constrain tool names to
  ``^[A-Za-z0-9_]+$`` (Cursor) accept it; hosts that already handle dots see
  the unchanged underscored form too.
* ``tools/call`` accepts either form. ``ToolRegistry.get(name)`` resolves the
  wire form via an alias map back to the canonical entry.
"""

import re
from typing import Any, Callable, Optional

from ai_stack.mcp.mcp_canonical_surface import (
    CANONICAL_MCP_TOOL_DESCRIPTORS,
    McpCanonicalToolDescriptor,
    McpSuite,
    descriptor_to_public_metadata,
)
from ai_stack.quality_lab.limit_inventory import mcp_tool_rate_limit_metadata
from tools.mcp_server.backend_client import BackendClient
from tools.mcp_server.config import Config
from tools.mcp_server.fs_tools import FileSystemTools
from tools.mcp_server.handlers.tools_registry_handlers import build_default_mcp_tool_handlers
from tools.mcp_server.tools_registry_metadata import (
    MCP_DEFAULT_TOOL_DESCRIPTIONS,
    MCP_DEFAULT_TOOL_INPUT_SCHEMAS,
)

CURSOR_SAFE_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


def cursor_safe_name(name: str) -> str:
    """Return the wire-format name for an MCP tool.

    Maps the canonical dotted form (``wos.system.health``) to the underscored
    form accepted by hosts whose tool-name regex is ``^[A-Za-z0-9_]+$``.
    Names that already satisfy the regex pass through unchanged. The mapping
    is a pure ``.``-to-``_`` substitution; bijection across the canonical
    descriptor set is asserted by ``test_tools_registry_aliases``.
    """
    return name.replace(".", "_")


class ToolDefinition:
    """Tool metadata: canonical strand + handler."""

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
        self.permission = descriptor.permission_scope

    def to_dict(self) -> dict[str, Any]:
        meta = descriptor_to_public_metadata(self.descriptor)
        return {
            "name": cursor_safe_name(self.name),
            "canonical_name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "permission": self.permission,
            "tool_class": meta["tool_class"],
            "authority_source": meta["authority_source"],
            "implementation_status": meta["implementation_status"],
            "governance": meta["governance"],
            "narrative_mutation_risk": meta["narrative_mutation_risk"],
            "mcp_suite": meta["mcp_suite"],
            "rate_limit": mcp_tool_rate_limit_metadata(self.name),
        }


class ToolRegistry:
    """Central registry of available tools."""

    def __init__(self) -> None:
        self.tools: dict[str, ToolDefinition] = {}
        self.aliases: dict[str, str] = {}

    def register(self, tool: ToolDefinition) -> None:
        self.tools[tool.name] = tool
        wire_name = cursor_safe_name(tool.name)
        if wire_name != tool.name:
            existing = self.aliases.get(wire_name)
            if existing is not None and existing != tool.name:
                raise ValueError(
                    f"Cursor-safe alias collision: {wire_name!r} already maps to "
                    f"{existing!r}, cannot also map to {tool.name!r}"
                )
            self.aliases[wire_name] = tool.name

    def get(self, name: str) -> Optional[ToolDefinition]:
        direct = self.tools.get(name)
        if direct is not None:
            return direct
        canonical = self.aliases.get(name)
        if canonical is not None:
            return self.tools.get(canonical)
        return None

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
    from ai_stack.research.research_langgraph import research_store_from_repo_root

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
