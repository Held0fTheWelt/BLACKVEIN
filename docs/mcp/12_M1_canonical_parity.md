# MCP M1 — Canonical surface parity & governance

## Single truth strand

- **Authoritative descriptors:** `ai_stack/mcp_canonical_surface.py` → `CANONICAL_MCP_TOOL_DESCRIPTORS`.
- **Registry:** `tools/mcp_server/tools_registry.py` registers exactly those tools (no parallel MCP-only list).
- **Capabilities:** Internal names and modes come from `capability_catalog()`; MCP exposes them only via `wos.capabilities.catalog`, which returns `capability_records_for_mcp()` (enriched rows, same names).

## Strict translation

| MCP tool | Internal / authority |
|----------|----------------------|
| `wos.capabilities.catalog` | Read-only mirror of `capability_catalog()` + governance metadata |
| `wos.session.create` | Backend HTTP `POST /api/v1/sessions` (authority-respecting flow; not manuscript publish) |
| `wos.system.health` | Backend HTTP `GET /api/v1/health` |
| `wos.goc.*`, `wos.content.search` | Repository filesystem read under `Config.repo_root` |
| `wos.mcp.operator_truth` | Derived compact legibility from registry + profile + optional `probe_backend` |
| `wos.session.execute_turn` (stub) | **Not** a capability invoke path — deferred; runtime guard/commit paths stay authoritative |
| `wos.session.diag` (stub) | Deferred diagnostics surface; review-bound and non-authoritative in M1 |

There is **no** MCP exposure of `CapabilityRegistry.invoke` or direct narrative mutation.

## Tool classes

- `read_only` — no mutating side effects on controlled stores via this tool.
- `review_bound` — preview / observability / deferred stubs; must not silently act as writes.
- `write_capable` — may initiate an authority-respecting mutating flow (`session.create` only today). Denied unless `WOS_MCP_OPERATING_PROFILE=healthy`.

## Operating profiles (`WOS_MCP_OPERATING_PROFILE`)

| Profile | Effect |
|---------|--------|
| `healthy` | `write_capable` allowed (subject to backend success). |
| `review_safe` | `write_capable` denied at `tools/call`. |
| `test_isolated` | Operator-truth marks test posture; writes still denied (not `healthy`). |
| `degraded` | Invalid env value maps here; operator-truth reports degraded/misconfigured honestly. |

## Operator truth

Call `wos.mcp.operator_truth` with optional `probe_backend: true` to set `backend_reachable` from a live health check; default omits probe for reproducible tests.

## Tests

Primary M1 gates:
- `tools/mcp_server/tests/test_mcp_m1_gates.py` (G-MCP-01 … G-MCP-07)
- `ai_stack/tests/test_mcp_canonical_surface.py`
- `backend/tests/runtime/test_mcp_enrichment.py` (canonical name parity on enrichment preflight)

Closure evidence is published in `tests/reports/MCP_M1_CLOSURE_REPORT.md`.
