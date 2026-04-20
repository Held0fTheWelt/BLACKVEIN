"""MCP tool registry."""

from typing import Dict, Callable, Any
from dataclasses import dataclass


@dataclass
class ToolSpec:
    """Tool specification."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    handler: Callable


class MCPRegistry:
    """Registry of available MCP tools."""

    def __init__(self):
        """Initialize registry."""
        self._tools: Dict[str, ToolSpec] = {}

    def register_tool(self, spec: ToolSpec) -> None:
        """Register a tool."""
        self._tools[spec.name] = spec

    def get_tool(self, tool_name: str) -> Any:
        """Get tool spec by name."""
        return self._tools.get(tool_name)

    def list_tools(self) -> Dict[str, ToolSpec]:
        """List all registered tools."""
        return dict(self._tools)

    def call_tool(self, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool by name."""
        spec = self.get_tool(tool_name)
        if not spec:
            return {"success": False, "error": f"Tool {tool_name} not found"}

        try:
            result = spec.handler(input_data)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
