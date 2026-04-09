# MCP integration (capability layer)

**Objective:** Expose a **governed capability surface** with explicit schemas, **mode** boundaries, audit semantics, and typed denial behavior. This aligns the in-repo **MCP server** (`tools/mcp_server/`) with `ai_stack` capabilities.

## Capability categories

- **Retrieval:** `wos.context_pack.build`, `wos.transcript.read`
- **Action:** `wos.review_bundle.build`

Retrieval and action capabilities are separated by explicit `kind` metadata and mode gates.

## Modes

Allowed boundaries include:

- `runtime` — retrieval-only for authoritative turn support
- `writers_room` — retrieval + review bundle generation
- `improvement` — retrieval + review bundle generation
- `admin` — transcript and governance-facing access patterns

Denied invocations raise `CapabilityAccessDeniedError` and are **always** audited.

## Contract shape

Each capability defines: name, input schema, result schema, allowed modes, audit requirement, failure semantics. Implementation: `ai_stack/capabilities.py`.

## Audit

Invocations record timestamp, capability name, mode, actor, outcome (`allowed` | `denied` | `error`), trace id, and error detail. Rows appear in runtime graph diagnostics and governance API responses. Backend exposes `GET /api/v1/sessions/<session_id>/capability-audit` for inspection.

## Where capabilities run

- **Runtime turn path:** `RuntimeTurnGraphExecutor` invokes `wos.context_pack.build` in `runtime` mode.
- **Writers’ Room:** `writers_room_service` invokes context pack and `wos.review_bundle.build` in `writers_room` mode.
- **Improvement:** experiment endpoint invokes the same capabilities in `improvement` mode; failures surface as explicit `502 capability_workflow_failed` with audit rows when applicable.

## MCP server alignment

`tools/mcp_server/tools_registry.py` derives tools from `ai_stack/mcp_canonical_surface.py`, including `wos.capabilities.catalog` and operator-facing summaries. **Contributor setup:** [`docs/dev/tooling/mcp-server-developer-guide.md`](../../dev/tooling/mcp-server-developer-guide.md).

## Intentionally out of scope

- Signed immutable long-term audit storage
- External policy engines with environment-level delegation
- Broad write actions outside governed recommendation workflows
