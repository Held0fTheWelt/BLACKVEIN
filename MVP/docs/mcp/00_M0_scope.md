# M0 Scope · MCP Integration (World of Shadows)

## Goal

M0 defines the binding framework in which MCP is introduced to World of Shadows without destabilizing the current God of Carnage flow.

**Core Principle:** Guard/Validation remains the authoritative instance. MCP/AI must not write state “directly.”

## In-Scope (M0)

- Host/operating model definition (for Phase A)
- Transport/connectivity definition (Phase A)
- Security baseline (read-only/preview only)
- Naming/versioning and error envelope (Contract v0)
- Tool inventory v0 (Phase A: Operator/Dev tooling)
- Backend readiness check + gap list
- Observability conventions (trace IDs, logs)
- Gate checklist (M0 completion verification)

## Out-of-Scope (M0)

- MCP server implementation
- Implementation of new backend endpoints (only as gap list)
- AI tool loop (B2), guarded preview loop (B3)
- Supervisor/subagents as true orchestration (C)

## Definitions

- **Option A:** MCP as operator/dev tooling (out-of-band). No turn-loop changes.
- **Option B:** MCP in AI path (in-loop), initially read-only.
- **Option C:** Supervisor + subagents (true multi-agent orchestration).

## Explicit Non-Goals in Phase A

- No MCP tool may write persistent story state.
- No tool may directly replace “execute_turn” or bypass guard.
- No multi-agent routing logic; tools only.

