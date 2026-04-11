# MCP server developer guide

Wrapper and **security-focused** notes for `tools/mcp_server/`. Full tool catalog: repository file `tools/mcp_server/README.md` (outside `docs/`, not included in the MkDocs site).

## Purpose

The MCP server exposes **stdio** tools for:

- Backend health and **session creation** (as implemented).
- Filesystem reads under the repo: **list modules**, **module metadata**, **content search**.
- Capability catalog mirroring (governance-enriched surface).

## Configuration

| Variable | Meaning |
|----------|---------|
| `REPO_ROOT` | Directory containing `content/` — auto-detected if unset |
| `BACKEND_BASE_URL` | Backend URL for HTTP tools |
| `BACKEND_BEARER_TOKEN` | Optional JWT for authenticated backend calls |

**Never** commit bearer tokens. Use local env or secret stores.

## Safety model

- Filesystem tools enforce **read-only** semantics and **size/result limits** (see MCP README).
- Write-capable tools (if introduced later) must pass **explicit** governance review.

## Relationship to runtime authority

MCP tools **do not** replace the play service’s **authoritative** session execution. Deferred tools in the MCP README (session get, execute turn, logs) are explicitly **not implemented** in early phases—do not assume parity with world-engine internals.

## Cross-links

- Canonical MCP governance docs under `docs/mcp/` (some are **execution-control** — read titles carefully).
- Operator-oriented overview: [How AI fits the platform](../../start-here/how-ai-fits-the-platform.md)

## Related

- `tools/mcp_server/README.md` (repository root)
- `docs/mcp/04_M0_contract_v0.md` (governance context)
