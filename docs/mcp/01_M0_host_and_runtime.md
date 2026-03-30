# M0 Host & Runtime · Decision

## Decision (Default for Phase A)

**Host/Runtime for MCP Phase A:**
- MCP server runs **locally** on operator/dev machine (stdio transport).
- MCP tools speak to backend **remotely** via HTTPS (PythonAnywhere remains default).
- MCP is used in Phase A as **operator console** (debug/inspect), not as in-game mechanic.

## Rationale

- Fits current remote-first setup (backend on PythonAnywhere).
- Minimizes risk: no changes to God of Carnage turn loop.
- Fastest path to real value (transparency, debuggability, QA).

## Concrete Implications

- Operator requires:
  - Access to repo (for local content reads, optional)
  - Backend URL (e.g., PythonAnywhere)
  - Auth token (see Security Baseline)

## Future Extensions

- B: AI host in backend can use MCP client (in-loop).
- C: Supervisor/subagents build on tool contracts + policies.

