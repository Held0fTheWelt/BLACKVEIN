# ADR-0027: MCP Transport & Connectivity — Phase A defaults

## Status
Accepted

## Implementation Status

**Implemented — stdio transport, HTTPS connectivity, and trace headers in place.**

- MCP server uses stdio transport locally (confirmed by `tools/mcp_server/` structure and `docs/mcp/02_M0_transport_connectivity.md`).
- Backend HTTP timeout 5s, single retry on network errors — documented in `docs/mcp/02_M0_transport_connectivity.md`.
- Trace headers `X-WoS-Trace-Id`, `X-WoS-Client`, and optional `Authorization` included on MCP→backend calls.
- `docs/mcp/02_M0_transport_connectivity.md` has "Migrated Decision: See ADR-0027" pointer.
- Status promoted from "Proposed" because the transport and header conventions are implemented.

## Date
2026-04-17

## Intellectual property rights
Repository authorship and licensing: see project LICENSE; contact maintainers for clarification.

## Privacy and confidentiality
This ADR contains no personal data. Implementers must follow the repository privacy and confidentiality policies, avoid committing secrets, and document any sensitive data handling in implementation steps.

## Related ADRs

- [README.md](README.md) — ADR index *(no tightly coupled ADR beyond references below)*.

## Context
MCP transport and connectivity need stable defaults for Phase A operator/QA usage.

## Decision
- Use `stdio` as the MCP transport for Phase A (local runs).
- Use HTTPS for backend connectivity.
- Baseline timeouts and retries: backend HTTP timeout 5s, retry once on network errors.
- Include trace headers on MCP→backend calls: `X-WoS-Trace-Id`, `X-WoS-Client`, and optional `Authorization`.

## Consequences
- Implementers should ensure tooling honours timeouts and header conventions.

## Diagrams

**stdio** MCP transport locally; **HTTPS** to backend with timeouts, single retry, and **WoS trace headers**.

```mermaid
flowchart LR
  MCP[MCP client] -->|stdio| SRV[Local MCP server]
  SRV -->|HTTPS 5s timeout, 1 retry| BE[Backend]
  SRV -->|X-WoS-Trace-Id, X-WoS-Client| BE
```

## Testing

Contract / unit coverage as cited in **References**; extend this section when a dedicated gate exists. Revisit this ADR if enforcement drifts or the decision is bypassed in code review.

## References
(Automated migration entry created 2026-04-17)
