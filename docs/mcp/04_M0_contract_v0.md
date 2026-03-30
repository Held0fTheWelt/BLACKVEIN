# MCP Contract v0 · World of Shadows

Version: **0.1**  
Status: **M0 (frozen for A1 implementation)**

## Naming
- Global: `wos.*`
- God of Carnage: `wos.goc.*`
- Sessions: `wos.session.*`
- Content: `wos.content.*`
- System: `wos.system.*`

## Common Fields

### Request metadata (host-side)
- `trace_id` (UUID)
- `client` (e.g., `mcp-operator`)
- `timestamp` (ISO-8601)

### Response envelope

All tools deliver:

```json
{
  "ok": true,
  "trace_id": "uuid",
  "tool": "wos.session.get",
  "data": { ... },
  "warnings": []
}
```

Error:

```json
{
  "ok": false,
  "trace_id": "uuid",
  "tool": "wos.session.get",
  "error": {
    "code": "NOT_FOUND | UNAUTHORIZED | INVALID_INPUT | BACKEND_ERROR | TIMEOUT",
    "message": "human readable",
    "details": {}
  }
}
```

## Error Codes (Baseline)

- `INVALID_INPUT`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `NOT_FOUND`
- `BACKEND_ERROR`
- `TIMEOUT`
- `RATE_LIMITED`

## Determinism & Safety (Phase A)

- Tools are **read-only** or **preview-only**.
- No tool writes persistent story state.
- No tool bypasses guard/validation.

