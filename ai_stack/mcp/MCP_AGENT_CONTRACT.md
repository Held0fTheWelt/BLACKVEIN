# MCP Agent Interface Contract

## Overview

The MCP Agent Interface provides a safe, fail-closed wrapper for LangGraph AI agents to call MCP tools without direct access to the MCP client. All tool calls are validated, logged, and return dictionaries (never raise exceptions).

**Constitutional Laws:**
- Law 9: AI composition bounds - AI acts only through MCP tools
- Law 6: Fail closed on authority seams - unknown response → error dict
- Law 10: Runtime catastrophic failure - tool errors don't crash system

## Interface Contract

### MCPAgentInterface Class

```python
from ai_stack.mcp.mcp_agent_interface import MCPAgentInterface

# Initialize with MCP client
interface = MCPAgentInterface(mcp_client=mcp_client)

# OR initialize without client (graceful degradation)
interface = MCPAgentInterface(mcp_client=None)
```

## Method Signatures

### Generic Tool Call

```python
def call_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Call any MCP tool with fail-closed error handling.

    Args:
        tool_name: Name of MCP tool (e.g., "session_get")
        params: Tool parameters as dict

    Returns:
        {
            "success": bool,
            "data": <tool result>,  # if success=True
            "error": str,           # if success=False
        }

    Guarantees:
    - Never raises exceptions
    - Always returns dict
    - All exceptions caught and logged
    - Call history recorded for diagnostics
    """
```

### Session Management Tools

#### session_get

```python
result = interface.call_session_get(session_id: str) -> Dict[str, Any]

# Response format (success case)
{
    "success": True,
    "data": {
        "session_id": str,
        "player_id": int,
        "created_at": str,
        # ... other session fields
    }
}

# Response format (error case)
{
    "success": False,
    "error": "Session not found"
}
```

#### session_state

```python
result = interface.call_session_state(session_id: str) -> Dict[str, Any]

# Response format (success case)
{
    "success": True,
    "data": {
        "world_state": {
            # ... game world state
        },
        "player_status": {
            # ... current player status
        }
    }
}
```

#### execute_turn

```python
result = interface.call_execute_turn(
    session_id: str,
    player_id: int,
    action: str
) -> Dict[str, Any]

# Response format (success case)
{
    "success": True,
    "data": {
        "turn_number": int,
        "result": "success" | "failure" | "degraded",
        "world_state": {},
        "player_status": {},
        "narrative": str,  # player-facing narrative
    }
}
```

#### session_logs

```python
result = interface.call_session_logs(session_id: str) -> Dict[str, Any]

# Response format (success case)
{
    "success": True,
    "data": {
        "logs": [
            {
                "timestamp": str,
                "type": str,  # "action", "state_change", "error", etc.
                "message": str,
                "context": {}
            }
        ]
    }
}
```

#### session_diag

```python
result = interface.call_session_diag(session_id: str) -> Dict[str, Any]

# Response format (success case)
{
    "success": True,
    "data": {
        "diagnostics": {
            "session_health": str,  # "healthy", "degraded", "error"
            "mcp_status": str,      # "connected", "timeout", "error"
            "last_call": str,       # ISO timestamp
            "error_count": int,
            "warning_count": int,
            # ... other diagnostics
        }
    }
}
```

## Error Handling

### Error Response Format

All errors return a dict with `success=False`:

```python
{
    "success": False,
    "error": "Description of what went wrong"
}
```

### Error Types

| Error | Cause | Example |
|-------|-------|---------|
| ValueError | Invalid parameters or missing MCP client | `"MCP client not initialized"` |
| ConnectionError | MCP connection lost | `"ConnectionError: Connection reset"` |
| TimeoutError | Tool call took too long | `"TimeoutError: Tool call timeout"` |
| TypeError | Invalid parameter types | `"TypeError: Missing required params"` |
| Generic Exception | Unexpected error | `"Unexpected error: ..."` |

### Fail-Closed Guarantees

1. **No Exceptions Propagate:** All errors caught and returned as dicts
2. **Always Returns Dict:** Even on catastrophic failure
3. **Logging:** All errors logged with context for debugging
4. **Diagnostics:** Call history preserved for audit trail

## Diagnostics and Logging

### Call History

```python
# Get diagnostics for session
diag = interface.get_diagnostics()

# Returns
{
    "call_count": 5,
    "success_count": 4,
    "error_count": 1,
    "call_history": [
        {
            "timestamp": "2026-04-20T15:30:45.123Z",
            "tool_name": "session_get",
            "params": {"session_id": "abc123"},
            "result": {...},
            "success": True,
            "error": None
        },
        # ... more calls
    ]
}
```

### Reset Diagnostics

```python
# Clear call history (useful between turns)
interface.reset_diagnostics()
```

## Usage Examples

### Basic Turn Execution

```python
from ai_stack.mcp.mcp_agent_interface import MCPAgentInterface

interface = MCPAgentInterface(mcp_client=mcp_client)

# Get current state
state_result = interface.call_session_state("session123")
if not state_result.get("success"):
    # Handle error
    print(f"Error: {state_result.get('error')}")
    return

world_state = state_result["data"]["world_state"]

# Execute action
exec_result = interface.call_execute_turn("session123", 1, "attack_north")
if not exec_result.get("success"):
    # Handle error
    print(f"Action failed: {exec_result.get('error')}")
    return

turn_result = exec_result["data"]
print(f"Turn {turn_result['turn_number']}: {turn_result['narrative']}")
```

### Error Handling Pattern

```python
# All tool calls return dicts - no exception handling needed
result = interface.call_session_get("session123")

# Check success field
if result.get("success"):
    session_data = result["data"]
    # Use session_data
else:
    error = result.get("error", "Unknown error")
    # Handle error gracefully
    logger.error(f"Tool call failed: {error}")
```

### Diagnostic Collection

```python
# Collect diagnostics after AI reasoning
interface.reset_diagnostics()

# Make multiple tool calls
interface.call_session_state("session123")
interface.call_session_logs("session123")

# Get diagnostic report
diag = interface.get_diagnostics()
print(f"Made {diag['call_count']} tool calls")
print(f"Success rate: {diag['success_count']}/{diag['call_count']}")

# Log details of failures
for call in diag["call_history"]:
    if not call["success"]:
        print(f"Failed: {call['tool_name']} - {call['error']}")
```

## Implementation Notes

### Immutability

The interface does not modify session state. All state reads are mirrors, all writes go through `execute_turn`.

### Thread Safety

Current implementation is not thread-safe. Use one MCPAgentInterface per AI agent/thread.

### Timeout Handling

Tool call timeouts (from MCP client) are caught and returned as error dicts.

### Logging

All tool calls logged at:
- INFO level: successful calls
- WARNING level: failed calls
- Logger: `ai_stack.mcp.mcp_agent_interface`

## Testing

### Mock MCP Client

```python
from unittest.mock import Mock

# Create mock MCP client
mock_client = Mock()
mock_client.call_tool.return_value = {
    "success": True,
    "data": {"session_id": "abc123"}
}

interface = MCPAgentInterface(mcp_client=mock_client)

result = interface.call_session_get("abc123")
assert result.get("success") is True
```

### Test Error Paths

```python
# Test timeout handling
mock_client.call_tool.side_effect = TimeoutError("MCP timeout")
result = interface.call_tool("session_get", {"session_id": "abc"})
assert result.get("success") is False
assert "error" in result
```

## References

- **Implementation:** `ai_stack/mcp/mcp_agent_interface.py`
- **Tests:** `ai_stack/tests/test_mcp_agent_interface.py`
- **LangGraph Integration:** `ai_stack/langgraph/langgraph_agent_nodes.py`
- **MCP Surface:** `ai_stack/mcp/mcp_canonical_surface.py`
