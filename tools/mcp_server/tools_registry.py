"""Tool registry and metadata."""

from typing import Any, Callable, Optional

from tools.mcp_server.backend_client import BackendClient
from tools.mcp_server.config import Config
from tools.mcp_server.errors import JsonRpcError
from tools.mcp_server.fs_tools import FileSystemTools


class ToolDefinition:
    """Tool metadata and permission."""

    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable,
        input_schema: dict[str, Any],
        permission: str = "read",
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.input_schema = input_schema
        self.permission = permission  # "read" or "preview"

    def to_dict(self) -> dict[str, Any]:
        """Convert to MCP tool definition dict."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "permission": self.permission,
        }


class ToolRegistry:
    """Central registry of available tools."""

    def __init__(self):
        self.tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all tools as MCP dicts."""
        return [tool.to_dict() for tool in self.tools.values()]


def create_default_registry() -> ToolRegistry:
    """Create registry with A1.2 tools: 2 P0 (backend) + 3 P1 (filesystem) + 4 blocked."""
    registry = ToolRegistry()
    config = Config()
    backend = BackendClient(base_url=config.backend_url, bearer_token=config.bearer_token)
    fs = FileSystemTools(config)

    # P0: Backend integration
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
            result = backend.create_session(module_id=module_id, trace_id=trace_id, module_version=module_version)
            return result
        except JsonRpcError as e:
            return {"error": e.message}

    # P1: Filesystem utilities
    def handle_list_modules(arguments: dict) -> dict:
        modules = fs.list_modules()
        return {"modules": modules}

    def handle_get_module(arguments: dict) -> dict:
        module_id = arguments.get("module_id")
        return fs.get_module(module_id)

    def handle_search_content(arguments: dict) -> dict:
        pattern = arguments.get("pattern", "")
        case_sensitive = arguments.get("case_sensitive", False)
        return fs.search_content(pattern, case_sensitive)

    # Blocked tools (deferred)
    def handle_blocked(name: str):
        def handler(arguments: dict) -> dict:
            return {
                "code": "NOT_IMPLEMENTED",
                "reason": f"{name} is not available in this phase",
            }
        return handler

    # Register P0 tools
    registry.register(
        ToolDefinition(
            name="wos.system.health",
            description="Check backend system health status",
            handler=handle_system_health,
            input_schema={"type": "object", "properties": {}, "required": []},
            permission="read",
        )
    )

    registry.register(
        ToolDefinition(
            name="wos.session.create",
            description="Create a new session for a module",
            handler=handle_session_create,
            input_schema={
                "type": "object",
                "properties": {
                    "module_id": {"type": "string"},
                    "module_version": {"type": "string"},
                },
                "required": ["module_id"],
            },
            permission="read",
        )
    )

    # Register P1 tools
    registry.register(
        ToolDefinition(
            name="wos.goc.list_modules",
            description="List available modules",
            handler=handle_list_modules,
            input_schema={"type": "object", "properties": {}, "required": []},
            permission="read",
        )
    )

    registry.register(
        ToolDefinition(
            name="wos.goc.get_module",
            description="Get module metadata and file list",
            handler=handle_get_module,
            input_schema={
                "type": "object",
                "properties": {"module_id": {"type": "string"}},
                "required": ["module_id"],
            },
            permission="read",
        )
    )

    registry.register(
        ToolDefinition(
            name="wos.content.search",
            description="Search content with regex pattern",
            handler=handle_search_content,
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "case_sensitive": {"type": "boolean"},
                },
                "required": ["pattern"],
            },
            permission="read",
        )
    )

    # Register blocked tools
    for blocked_name in [
        "wos.session.get",
        "wos.session.execute_turn",
        "wos.session.logs",
        "wos.session.state",
    ]:
        registry.register(
            ToolDefinition(
                name=blocked_name,
                description=f"{blocked_name} (not implemented)",
                handler=handle_blocked(blocked_name),
                input_schema={"type": "object", "properties": {}, "required": []},
                permission="read",
            )
        )

    return registry
