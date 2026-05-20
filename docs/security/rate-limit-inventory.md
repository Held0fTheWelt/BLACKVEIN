# Rate-limit inventory

This document describes the shared rate-limit inventory for HTTP/API routes, Auth routes, and MCP tools. The goal is to keep runtime enforcement, info views, and tests aligned around one inspectable model instead of scattered prose.

## Source of truth

| Surface | Runtime enforcement | Inventory source | Operator view |
|---------|---------------------|------------------|---------------|
| HTTP/API routes | Flask-Limiter route decorators and default limiter config | `ai_stack/quality_lab/limit_inventory.py`, `backend/app/info/api_catalog.py` | `/backend/api`, `/backend/api-explorer`, `/backend/security-features` |
| Auth routes | Flask-Limiter route decorators and default limiter config | `ai_stack/quality_lab/limit_inventory.py`, API catalog metadata | `/backend/auth`, `/backend/security-features` |
| Admin-sensitive route policy | `admin_security(..., rate_limit=...)` wrappers | `ai_stack/quality_lab/limit_inventory.py` layer extraction | `/backend/security-features`, API catalog detail |
| MCP JSON-RPC dispatch | MCP `RateLimiter` in `tools/mcp_server/server.py` | shared constants from `ai_stack/quality_lab/limit_inventory.py` | `/backend/mcp`, `/backend/security-features`, MCP `tools/list` |

The current shared defaults are:

| Area | Limit | Notes |
|------|-------|-------|
| API fallback | `100 per minute` | Used when a route does not expose a more specific decorator/policy limit. |
| MCP dispatch/tool metadata | `30 per minute` | Conservative local JSON-RPC limit shared by dispatch and `tools/list` metadata. |

## Inventory fields

HTTP/API route entries expose a structured `rate_limit` object through the backend API catalog. MCP tools expose a compatible object through the tool registry metadata.

| Field | Meaning |
|-------|---------|
| `limit` | Human-readable limit label such as `100 per minute` or `30 per minute`. |
| `source` | Where the effective limit came from, for example `route_decorator`, `default`, `admin_security`, or `mcp_json_rpc_dispatch`. |
| `key` | Limiter keying scope, such as JWT user id, remote address fallback, or MCP bearer token/local stdio scope. |
| `max_calls` | Parsed request/tool-call count when the label can be normalized. |
| `period` / `window_seconds` | Parsed time window for normalized labels. |
| `layers` | Route-level evidence extracted from known wrappers. |
| `additional_policy_limits` | Extra policy layers that apply in addition to the effective route/default limit. |

## HTTP route rules

Route-specific limiter decorators provide the most specific HTTP evidence. When a route does not define an explicit decorator, the inventory records the configured Flask-Limiter default as the fallback policy.

Known `admin_security(..., rate_limit=...)` wrappers are recorded as additional route policy layers. They do not replace Flask-Limiter ownership of HTTP enforcement; they make admin-sensitive limits visible alongside the API route inventory.

## MCP tool rules

MCP JSON-RPC calls are throttled by the dispatch limiter, not by separate per-tool buckets. The registry mirrors the shared dispatch limit into every tool descriptor so clients and operators can see the same conservative boundary during `tools/list` discovery.

The MCP keying scope is token-oriented where a bearer token is present, with local stdio/dev operation treated as a local scope. The inventory intentionally avoids documenting raw token material.

## Operator views

Use these views to inspect current coverage:

- `/backend/security-features` - combined security posture with API/Auth/MCP inventory summary.
- `/backend/api` - HTTP route inventory summary and examples.
- `/backend/auth` - Auth-focused route limits.
- `/backend/mcp` - MCP dispatch and tool inventory.
- `/backend/api-explorer` - searchable route catalog; use `limit:` or `rate:` terms to filter by limit/source.

## Production tuning and telemetry

The current inventory is repository evidence. It shows which routes and MCP tools have limits, but it is not enough to tune production limits by itself. Production tuning requires live or staging telemetry that proves request pressure, blocked-call rates, false positives, and edge/gateway behavior.

Current readiness: `inventory_only`. API/Auth/MCP coverage is visible, but production 429/MCP hit telemetry is not yet claimed by this repository.

Required telemetry signals:

| Signal | Source | Purpose | Privacy rule |
|--------|--------|---------|--------------|
| `rate_limit_requests_total` | HTTP route and MCP dispatch observations | Baseline request/tool-call volume before changing quotas | Route, method, auth kind, and tool labels only |
| `rate_limit_hits_total` | HTTP 429 handler and MCP `RateLimitedError` | Count blocked calls by route/tool, limit source, and environment | Use hashed limiter key buckets; never raw tokens or cookies |
| `rate_limit_quota_utilization_ratio` | Limiter backend or edge/gateway counters | Find hot routes before users hit hard blocks | Aggregate by route/tool class and deployment tier |
| `rate_limit_retry_after_seconds` | HTTP response headers and MCP error metadata | Tune client backoff and operator alerts | No request body, prompt, email address, or bearer value |
| `edge_throttle_events_total` | CDN/WAF/API gateway | Separate app limiter pressure from perimeter throttling | Provider event id plus coarse rule/category labels |

Tuning workflow:

1. Baseline: collect at least 7 days of production or staging traffic before changing route/tool limits.
2. Segment: separate public reads, auth flows, admin writes, service-token traffic, and MCP tool calls.
3. Shadow-Tuning: evaluate proposed limits against telemetry without blocking additional traffic first.
4. Canary: roll out stricter or looser limits to one tier, tenant, or client class before global enforcement.
5. Review: update the inventory, ADR notes, alerts, and rollback threshold with every production tuning change.

Privacy and confidentiality rules:

- Store only hashed limiter key values; never raw bearer tokens, cookies, IP addresses, or email addresses.
- Do not record request bodies, prompts, passwords, reset tokens, or provider credentials in rate-limit events.
- Keep local/dev telemetry labeled as local evidence; do not use it as production tuning proof.
- Treat CDN/WAF counters as perimeter evidence and app/MCP counters as application evidence.

## Testing

The inventory is guarded by backend info and MCP registry/rate-limit tests:

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_backend_info_routes.py -q --tb=short --no-cov
PYTHONPATH=backend python -m pytest backend/tests/test_backend_info_routes.py tools/mcp_server/tests/test_rate_limit.py tools/mcp_server/tests/test_registry.py -q --tb=short --no-cov
python -m pytest tools/mcp_server/tests/test_mcp_operational_parity_and_registry.py -q --tb=short --no-cov
```

## Limits and non-goals

The inventory is local repository evidence. It does not claim production DDoS protection, CDN/WAF throttling, or live traffic telemetry. The telemetry contract above defines what must exist before production tuning can be claimed.

The inventory also does not yet replace the CSRF matrix, role matrix, service-token policy, or secret-management evidence. It can be extended with those dimensions later if a broader security control inventory becomes useful.
