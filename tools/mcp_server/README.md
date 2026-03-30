# World of Shadows MCP Server - Phase A1.1 Skeleton

## Overview

Minimal Model Context Protocol (MCP) server skeleton supporting `tools/list` and `tools/call` via stdio transport.

**Features:**
- Single-process JSON-RPC server (handwritten, no external MCP library)
- Structured logging with trace IDs and performance metrics
- Rate limiting (30 calls/min, token bucket)
- Input validation via Pydantic schemas
- 3 placeholder read-only tools
- JSON-RPC 2.0 error envelope compliance

## Running the Server

### Prerequisites

```bash
python -m pip install -r requirements.txt
```

### Start Server

```bash
python -m tools.mcp_server.server
```

The server reads JSON-RPC requests from stdin and writes responses to stdout.

## Sample I/O

### Request: tools/list

**Input (stdin):**
```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
```

**Output (stdout):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "read_placeholder_1",
        "description": "Placeholder tool for reading data",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": {"type": "string"}
          },
          "required": ["query"]
        }
      },
      {
        "name": "read_placeholder_2",
        "description": "Placeholder tool for reading configuration",
        "inputSchema": {
          "type": "object",
          "properties": {
            "key": {"type": "string"}
          },
          "required": ["key"]
        }
      },
      {
        "name": "read_placeholder_3",
        "description": "Placeholder tool for reading metadata",
        "inputSchema": {
          "type": "object",
          "properties": {
            "entity_id": {"type": "string"}
          },
          "required": ["entity_id"]
        }
      }
    ]
  }
}
```

### Request: tools/call (Success)

**Input (stdin):**
```json
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "read_placeholder_1", "arguments": {"query": "test"}}}
```

**Output (stdout):**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "read_placeholder_1: executed with query=test"
      }
    ]
  }
}
```

### Request: tools/call (Missing Required Field)

**Input (stdin):**
```json
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "read_placeholder_1", "arguments": {}}}
```

**Output (stdout):**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "error": {
    "code": -32602,
    "message": "Invalid request",
    "data": {
      "detail": "Missing required fields: query"
    }
  }
}
```

### Request: tools/call (Tool Not Found)

**Input (stdin):**
```json
{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "nonexistent_tool", "arguments": {}}}
```

**Output (stdout):**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": {
      "detail": "Tool 'nonexistent_tool' not found"
    }
  }
}
```

### Request: Unknown Method

**Input (stdin):**
```json
{"jsonrpc": "2.0", "id": 5, "method": "unknown/method", "params": {}}
```

**Output (stdout):**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": {
      "detail": "Method 'unknown/method' not found"
    }
  }
}
```

### Request: Rate Limit Exceeded

**Input (stdin) - 31st request within 60 seconds:**
```json
{"jsonrpc": "2.0", "id": 31, "method": "tools/list", "params": {}}
```

**Output (stdout):**
```json
{
  "jsonrpc": "2.0",
  "id": 31,
  "error": {
    "code": -32600,
    "message": "Invalid request",
    "data": {
      "detail": "Rate limit exceeded: 30 calls per minute allowed"
    }
  }
}
```

## Architecture

```
server.py          → Main JSON-RPC loop, dispatch, handlers
tools_registry.py  → Tool definitions, list handler
logging_utils.py   → Structured logging (trace_id, duration)
rate_limiter.py    → Token bucket rate limiter
errors.py          → Error codes and JSON-RPC envelope
```

## Testing

```bash
pytest tests/ -v
```

Expected: 13/13 tests passing
- 4 registry tests (tools/list structure, retrieval)
- 3 RPC tests (success, unknown method, initialize)
- 3 rate limit tests (under limit, over limit, per-token)
- 3 validation tests (missing required fields)

## Notes

- All tools are read-only (permission="read")
- No external tools or write operations
- Logs include: trace_id, method, status, duration_ms
- JSON-RPC 2.0 compliant error envelope
