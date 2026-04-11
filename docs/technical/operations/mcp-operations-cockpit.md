# MCP Operations Cockpit (implemented MVP)

English operations reference for the bounded MCP observability surface in the **administration-tool** and the backing **backend** APIs.

## Purpose

- Make MCP **visible** (suites, tools/resources/prompts counts, recent tool activity).
- Make failures **diagnosable** (structured logs + diagnostic cases).
- Support **bounded actions** (catalog alignment, audit bundle, case reclassify, diagnostic rebuild).

This is **not** a second MCP runtime and **not** a platform for broad writes.

## Administration UI

| Item | Value |
|------|--------|
| URL | `/manage/mcp-operations` |
| Nav label | MCP Operations |
| Feature flag | `manage.mcp_operations` (moderator + admin, area rules same as other manage features) |

Tabs: **Overview**, **Activity**, **Diagnostics**, **Logs**, **Actions**.

## Backend APIs

All admin routes require JWT (moderator or admin) + `manage.mcp_operations`.

| Method | Path | Role |
|--------|------|------|
| GET | `/api/v1/admin/mcp/overview` | Aggregated situation + registry rows |
| GET | `/api/v1/admin/mcp/suites` | Suite registry detail |
| GET | `/api/v1/admin/mcp/activity` | Tool-call projection (query: `page`, `limit`, `suite`, `trace_id`, `errors_only`) |
| GET | `/api/v1/admin/mcp/logs` | Full telemetry projection (add `log_level`, `session_id`, `date_from`, `date_to`, …) |
| GET | `/api/v1/admin/mcp/diagnostics` | Diagnostic cases |
| POST | `/api/v1/admin/mcp/diagnostics/manual` | Create manual case (`case_type`, `summary`, optional `suite_name`) |
| POST | `/api/v1/admin/mcp/actions/refresh-catalog` | Read-only alignment + operator truth |
| POST | `/api/v1/admin/mcp/actions/retry-job` | Rebuild **auto_rule** diagnostic cases from telemetry window (`since_days` in body, default 30) |
| POST | `/api/v1/admin/mcp/actions/generate-audit-bundle` | JSON bundle of recent telemetry + cases + registry |
| POST | `/api/v1/admin/mcp/actions/reclassify-diagnostic` | Update case (`case_id`, optional `suite_display_override`, `status`, `case_type`) |

## Telemetry ingest (service token)

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/v1/operator/mcp-telemetry/ingest` | `Authorization: Bearer <MCP_SERVICE_TOKEN>` |

Body: `{"records":[...]}` — each record matches the JSON lines emitted by `tools/mcp_server/logging_utils.py` (`type`: `request` \| `response` \| `tool_call`), plus optional `wos_mcp_suite`.

Limits: max **64 KB** body, max **200** records per request; rows are pruned by retention (see below).

## MCP server → backend (E2E)

1. Configure backend with `MCP_SERVICE_TOKEN` and run migrations (table `mcp_ops_telemetry`, `mcp_diagnostic_cases`).
2. Set on the MCP host:
   - `WOS_MCP_TELEMETRY_INGEST_URL=http://<backend-host>:<port>/api/v1/operator/mcp-telemetry/ingest`
   - `MCP_SERVICE_TOKEN=<same value>`
3. Run `python -m tools.mcp_server.server` and send a JSON-RPC line (e.g. `tools/call` `wos.system.health`).
4. Sign in to the administration-tool, open **MCP Operations** → **Activity**; the new row should share the same `trace_id` as in the ingest payload. Verify with `GET /api/v1/admin/mcp/activity` using a moderator JWT.

## Data model (high level)

- **Activity** = projection of `tool_call` telemetry rows (operator timeline).
- **Logs** = all ingested `request` / `response` / `tool_call` rows (forensics).
- **Diagnostic cases** = auto rules on ingest + manual cases; `suite_display_override` wins in the API for display.

## Auto diagnostic rules (MVP)

1. `tool_call` + `status=error` → case `failed_tool_call` (dedupe: trace + tool).
2. `response` + `method=tools/call` + `error_code=PERMISSION_DENIED` → case `policy_rejection` (dedupe: trace).

## Retention and payload safety

- Env `WOS_MCP_TELEMETRY_RETENTION_DAYS` (default **30**): best-effort batch delete of old telemetry on ingest.
- No full tool arguments or player content stored; payload keys are allow-listed and capped (~16 KB JSON per row).

## Normative product spec

See [ROADMAP_MVP_MCP_OPERATIONS_COCKPIT_WOS.md](../../ROADMAP_MVP_MCP_OPERATIONS_COCKPIT_WOS.md).
