"""Tool registry and metadata — derived from ai_stack canonical MCP descriptors."""

from typing import Any, Callable, Optional

from ai_stack.mcp_canonical_surface import (
    CANONICAL_MCP_TOOL_DESCRIPTORS,
    McpCanonicalToolDescriptor,
    McpImplementationStatus,
    build_compact_mcp_operator_truth,
    capability_records_for_mcp,
    descriptor_to_public_metadata,
    verify_catalog_names_alignment,
)
from tools.mcp_server.backend_client import BackendClient
from tools.mcp_server.config import Config
from tools.mcp_server.errors import JsonRpcError
from tools.mcp_server.fs_tools import FileSystemTools


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


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    config = Config()
    backend = BackendClient(base_url=config.backend_url, bearer_token=config.bearer_token)
    fs = FileSystemTools(config)

    def handle_system_health(arguments: dict) -> dict:
        try:
            import uuid

            trace_id = str(uuid.uuid4())
            result = backend.health(trace_id=trace_id)
            return {"status": "healthy", "backend": result}
        except JsonRpcError as e:
            return {"status": "error", "message": e.message}

    def handle_session_create(arguments: dict) -> dict:
        module_id = arguments.get("module_id")
        module_version = arguments.get("module_version")
        try:
            import uuid

            trace_id = str(uuid.uuid4())
            result = backend.create_session(
                module_id=module_id, trace_id=trace_id, module_version=module_version
            )
            return result
        except JsonRpcError as e:
            return {"error": e.message}

    def handle_list_modules(arguments: dict) -> dict:
        return {"modules": fs.list_modules()}

    def handle_get_module(arguments: dict) -> dict:
        module_id = arguments.get("module_id")
        return fs.get_module(module_id)

    def handle_search_content(arguments: dict) -> dict:
        pattern = arguments.get("pattern", "")
        case_sensitive = arguments.get("case_sensitive", False)
        return fs.search_content(pattern, case_sensitive)

    def handle_capability_catalog(arguments: dict) -> dict:
        return {"capabilities": capability_records_for_mcp()}

    def handle_operator_truth(arguments: dict) -> dict:
        probe = bool(arguments.get("probe_backend"))
        backend_reachable: bool | None = None
        if probe:
            try:
                import uuid

                backend.health(trace_id=str(uuid.uuid4()))
                backend_reachable = True
            except JsonRpcError:
                backend_reachable = False
        align = verify_catalog_names_alignment()
        truth = build_compact_mcp_operator_truth(
            backend_reachable=backend_reachable,
            catalog_alignment_ok=bool(align["aligned"]),
            registry_tool_names=registry.list_tool_names(),
        )
        return {"operator_truth": truth, "catalog_alignment": align}

    def handle_blocked(name: str) -> Callable[[dict], dict]:
        def handler(arguments: dict) -> dict:
            return {
                "code": "NOT_IMPLEMENTED",
                "reason": f"{name} is not available in this phase",
                "implementation_status": McpImplementationStatus.deferred_stub.value,
                "authority_note": "deferred_stub_non_authoritative",
            }

        return handler

    handlers: dict[str, Callable[..., dict[str, Any]]] = {
        "wos.system.health": handle_system_health,
        "wos.session.create": handle_session_create,
        "wos.goc.list_modules": handle_list_modules,
        "wos.goc.get_module": handle_get_module,
        "wos.content.search": handle_search_content,
        "wos.capabilities.catalog": handle_capability_catalog,
        "wos.mcp.operator_truth": handle_operator_truth,
    }

    descriptions: dict[str, str] = {
        "wos.system.health": "Check backend system health status",
        "wos.session.create": "Create a new session for a module (authority-respecting backend flow only)",
        "wos.goc.list_modules": "List available modules",
        "wos.goc.get_module": "Get module metadata and file list",
        "wos.content.search": "Search content with regex pattern",
        "wos.capabilities.catalog": "Canonical capability surface with governance metadata (read-only mirror)",
        "wos.mcp.operator_truth": "Compact MCP operator truth (profile, route, policy, no-eligible discipline)",
        "wos.session.get": "Session snapshot (deferred — not implemented on MCP)",
        "wos.session.execute_turn": "Execute turn (deferred — must use runtime authority, not MCP)",
        "wos.session.logs": "Session logs (deferred — not implemented on MCP)",
        "wos.session.state": "Session state (deferred — not implemented on MCP)",
        "wos.session.diag": "Session diagnostics (deferred — not implemented on MCP)",
    }

    schemas: dict[str, dict[str, Any]] = {
        "wos.system.health": {"type": "object", "properties": {}, "required": []},
        "wos.session.create": {
            "type": "object",
            "properties": {
                "module_id": {"type": "string"},
                "module_version": {"type": "string"},
            },
            "required": ["module_id"],
        },
        "wos.goc.list_modules": {"type": "object", "properties": {}, "required": []},
        "wos.goc.get_module": {
            "type": "object",
            "properties": {"module_id": {"type": "string"}},
            "required": ["module_id"],
        },
        "wos.content.search": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "case_sensitive": {"type": "boolean"},
            },
            "required": ["pattern"],
        },
        "wos.capabilities.catalog": {"type": "object", "properties": {}, "required": []},
        "wos.mcp.operator_truth": {
            "type": "object",
            "properties": {"probe_backend": {"type": "boolean"}},
            "required": [],
        },
        "wos.session.diag": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    }

    for desc in CANONICAL_MCP_TOOL_DESCRIPTORS:
        name = desc.name
        if name in handlers:
            handler_fn = handlers[name]
        else:
            handler_fn = handle_blocked(name)
        registry.register(
            ToolDefinition(
                descriptor=desc,
                description=descriptions.get(name, name),
                handler=handler_fn,
                input_schema=schemas.get(name, {"type": "object", "properties": {}, "required": []}),
            )
        )

    return registry
