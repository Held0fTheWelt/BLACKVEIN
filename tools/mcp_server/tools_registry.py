"""Tool registry and metadata."""

from typing import Any, Callable, Optional


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


# Placeholder tool handlers
def handle_system_health(arguments: dict) -> dict:
    """Placeholder: system health."""
    return {"status": "ok", "note": "placeholder"}


def handle_session_create(arguments: dict) -> dict:
    """Placeholder: session creation."""
    module_id = arguments.get("module_id", "unknown")
    return {"note": "placeholder - not calling backend yet", "module_id": module_id}


def handle_content_search(arguments: dict) -> dict:
    """Placeholder: content search."""
    query = arguments.get("query", "")
    return {"note": "placeholder - not calling backend yet", "query": query}


# Default registry with placeholder tools
def create_default_registry() -> ToolRegistry:
    """Create registry with default placeholder tools."""
    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            name="wos.system.health",
            description="Check backend health (placeholder)",
            handler=handle_system_health,
            input_schema={"type": "object", "properties": {}, "required": []},
            permission="read",
        )
    )

    registry.register(
        ToolDefinition(
            name="wos.session.create",
            description="Create session (placeholder)",
            handler=handle_session_create,
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
            description="Search content (placeholder)",
            handler=handle_content_search,
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            permission="read",
        )
    )

    return registry
