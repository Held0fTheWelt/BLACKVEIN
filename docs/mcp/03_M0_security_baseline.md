# M0 Security Baseline · Phase A (read-only)

## Goals

- MCP may **only read** in Phase A (inspect/debug) and provide at most “preview.”
- No state changes without guard/policy.
- No sensitive tokens/cookies in logs.

## Decision (Phase A)

1. **Tool Permission Levels**
   - `read`: standard (allowed)
   - `preview`: allowed, but only guard-preview/explain (no write)
   - `write`: **forbidden** in Phase A (no write tools)

2. **Auth MCP → Backend**
   - Default: `Authorization: Bearer <SERVICE_TOKEN>`
   - Token stored locally and securely (not in repo).
   - Backend side: endpoints should protect “service/admin” medium-term.
     - For M0, documented as **gap** if currently open.

3. **Rate Limiting**
   - MCP server: max **30 calls/min** per token (locally enforced).
   - Backend: use if available; otherwise add later.

4. **Logging/PII**
   - Logs never contain: passwords, cookies, JWT refresh tokens
   - Request bodies logged as hashable (`args_hash`) not raw

## Minimal Policy for Tools

- Tools access only:
  - explicit debug/session/content read endpoints
  - or local content files (repo)
- No tool may execute “execute” or “apply delta.”

