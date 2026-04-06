# World of Shadows MCP Server - Phase A1.2 Read-Only Tool Set

## Overview

Model Context Protocol (MCP) server implementing Phase A1.2: read-only operator/developer tooling via stdio transport.

**Features:**
- Canonical descriptor-derived tool registry (`ai_stack/mcp_canonical_surface.py`)
- Explicit tool classes: `read_only`, `review_bound`, `write_capable`
- Compact operator truth tool (`wos.mcp.operator_truth`)
- 2 backend tools: system health, session creation
- 3 filesystem tools: list modules, get module metadata, search content
- 1 capability mirror tool: canonical governance-enriched capability catalog
- 5 deferred stubs (NOT_IMPLEMENTED in M1): session runtime/observability follow-ups
- HTTP client with 5-second timeout and automatic retry
- Configuration from environment variables
- Filesystem utilities with safety limits (10MB files, 100 search hits)
- 43 comprehensive unit tests (TDD)

## Environment Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `BACKEND_BASE_URL` | `https://yvesthx.pythonanywhere.com` | Backend API endpoint |
| `BACKEND_BEARER_TOKEN` | (empty) | Optional bearer token for authentication |
| `REPO_ROOT` | (auto-detected) | Repository root directory containing `content/` |

## Tools Available (M1 Canonical Surface)

### P0: Backend Integration

| Tool | Input | Purpose |
|------|-------|---------|
| `wos.system.health` | (none) | Check backend health status |
| `wos.session.create` | `module_id`, `module_version?` | Create new game session |

### P1: Filesystem Utilities

| Tool | Input | Purpose |
|------|-------|---------|
| `wos.goc.list_modules` | (none) | List available modules |
| `wos.goc.get_module` | `module_id` | Get module metadata and file list |
| `wos.content.search` | `pattern`, `case_sensitive?` | Search content with regex |

### Blocked (NOT_IMPLEMENTED)

- `wos.session.get` — Deferred to later phase
- `wos.session.execute_turn` — Deferred to later phase
- `wos.session.logs` — Deferred to later phase
- `wos.session.state` — Deferred to later phase
- `wos.session.diag` — Deferred to later phase

## Running the Server

### Prerequisites

```bash
python -m pip install requests
```

### Start Server

```bash
python -m tools.mcp_server.server
```

The server reads JSON-RPC requests from stdin and writes responses to stdout.

## Example Calls

### tools/list

**Request:**
```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
```

**Response:** Shows all canonical M1 tools (descriptor-derived; no shadow list)

### tools/call: System Health

**Request:**
```json
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "wos.system.health", "arguments": {}}}
```

**Response:**
```json
{"jsonrpc": "2.0", "id": 2, "result": {"status": "healthy", "backend": {"status": "ok"}}}
```

### tools/call: Create Session

**Request:**
```json
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "wos.session.create", "arguments": {"module_id": "god_of_carnage"}}}
```

**Response:**
```json
{"jsonrpc": "2.0", "id": 3, "result": {"session_id": "sess-12345", "module_id": "god_of_carnage"}}
```

### tools/call: List Modules

**Request:**
```json
{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "wos.goc.list_modules", "arguments": {}}}
```

**Response:**
```json
{"jsonrpc": "2.0", "id": 4, "result": {"modules": ["god_of_carnage"]}}
```

### tools/call: Search Content

**Request:**
```json
{"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "wos.content.search", "arguments": {"pattern": "god of carnage"}}}
```

**Response:**
```json
{"jsonrpc": "2.0", "id": 5, "result": {"pattern": "god of carnage", "hits": 2, "results": [...]}}
```

## Architecture

```
config.py              → Environment configuration + repo root detection
backend_client.py      → HTTP client (5s timeout, auto-retry)
fs_tools.py            → Filesystem utilities (list, get, search)
tools_registry.py      → Tool definitions + handlers
server.py              → JSON-RPC main loop
logging_utils.py       → Structured logging
rate_limiter.py        → Token bucket rate limiting
errors.py              → Error codes + JSON-RPC envelope
```

## Testing

```bash
pytest tools/mcp_server/tests/ -v
```

**Results:** run the MCP suites from repo root:
- `python -m pytest tools/mcp_server/tests/test_mcp_m1_gates.py ai_stack/tests/test_mcp_canonical_surface.py tools/mcp_server/tests/test_rpc.py backend/tests/runtime/test_mcp_enrichment.py -q --tb=short --no-cov`
- 8 backend client tests
- 7 config tests
- 7 filesystem tests
- 8 tool handler tests
- 4 registry tests
- 5 RPC tests
- 3 rate limit tests
- 1 validation test

## Notes

- Legacy `permission` is compatibility metadata only; policy enforcement is class/profile-based
- `write_capable` tools are denied unless `WOS_MCP_OPERATING_PROFILE=healthy`
- HTTP timeout: 5 seconds with automatic 1x retry
- Search limits: 10MB per file, 100 hits per query
- Configuration from environment variables with defaults
- Repo root auto-detected by finding content/ folder
