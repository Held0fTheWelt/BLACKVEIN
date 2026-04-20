# M0 Observability · MCP Calls

## Goals

- Every MCP tool call is traceable.
- Tool calls can explain turns (why guard accept/reject).
- Foundation for later B/C agentics.

## Trace IDs

- `trace_id`: UUID per MCP request
- `session_id`: optional, if tool is session-related
- `turn_id`: optional, if tool is turn-related

## Logging Fields (MCP Server)

- `timestamp`
- `trace_id`
- `tool`
- `duration_ms`
- `status` (ok/error)
- `args_hash` (SHA-256)
- `response_hash` (SHA-256)
- `backend_url` (if HTTP)

## Backend Headers (optional, recommended)

- `X-WoS-Trace-Id: <uuid>`
- `X-WoS-Client: mcp-operator`

## Minimal Export (optional)

- `wos.session.export_bundle(session_id)` produces:
  - session snapshot
  - last_turn_execution_result
  - last_ai_decision_log (if available)
  - tool call transcript (if available host-side)
