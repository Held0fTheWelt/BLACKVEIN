# ADR-0002: Backend session / transitional runtime surface - quarantine and retirement

## Status

Accepted

## Context

The platform historically exposed backend-local session and runtime-shaped APIs. The world-engine is the **authoritative** live and story runtime for committed play state. A large transitional surface on the backend increases the risk that tools, tests, or new features attach to the wrong authority layer (audit finding class "backend transitional session drift").

## Decision

1. **Inventory** all backend routes and services under `backend/app/runtime/`, `session_service.py`, `session_start.py`, and session-related API modules (normative list: **Appendix A**).
2. **Classify** each entry point as: **retire** (remove when no caller), **quarantine** (explicit non-authoritative labeling, narrow compatibility window), or **compat** (documented operator-only surface with no player truth claims).
3. **Quarantine** non-authoritative surfaces in naming and documentation so they cannot be mistaken for production authority (prefixes, deprecation notices, ADR links).

## Decision gate (mandatory)

**No retirement or breaking URL removal** for any row in Appendix A without a separate **decision record** in this ADR (amendment) or in [audit_resolution_state_world_of_shadows.md](../governance/audit_resolution/audit_resolution_state_world_of_shadows.md) **decision log** (author, date, audience impact). Inventory and classification may proceed without that gate; **execute retire** only after the gate.

## Consequences

- Positive: Reduced drift; clearer onboarding for engineers.
- Negative: Migration work for any remaining callers of retired surfaces; coordination with product for compat timelines.

## Appendix A - Session / runtime surface inventory (normative)

Canonical replacement = authoritative World Engine HTTP surface where applicable. **MCP** = MCP service token on `/api/v1/sessions/*`. **WE** = world-engine internal/public story session API.

| Surface id | Class | Canonical replacement / path | Allowed callers | Forbidden callers | Sunset / removal | Proof artifact | Row status |
|------------|-------|-------------------------------|-----------------|-------------------|------------------|----------------|------------|
| `POST /api/v1/sessions` | Quarantine | WE `POST /api/story/sessions` after first turn bridge; in-process `SessionState` only for bootstrap | CI, operators, optional JWT create | Player product treating response as durable truth | none until decision log | `session_routes.py` warnings + docstring; ADR-0002 | Closed |
| `GET /api/v1/sessions/<id>` | Quarantine | WE `GET /api/story/sessions/<we_id>/state` when `world_engine_story_session_id` in metadata | MCP token | Anonymous | none until decision log | MCP route + metadata bridge in `session_routes.py` | Closed |
| `GET /api/v1/sessions/<id>/diagnostics` | Quarantine | WE `GET .../diagnostics` | MCP token | Player | none until decision log | `session_routes.py` | Closed |
| `GET /api/v1/sessions/<id>/capability-audit` | Quarantine | WE diagnostics + local bundle | MCP token | Player | none until decision log | `session_routes.py` | Closed |
| `GET /api/v1/sessions/<id>/play-operator-bundle` | Quarantine | WE state + diagnostics | MCP token | Player | none until decision log | `session_routes.py` | Closed |
| `POST /api/v1/sessions/<id>/turns` | Quarantine | WE `POST .../turns` (authoritative execution) | MCP, CI, operators | Player-only shell without engine | none until decision log | `game_service.execute_story_turn` + audit log | Closed |
| `GET /api/v1/sessions/<id>/logs` | Quarantine | WE session event stream (when bridged); else in-process only | MCP, CI | Player | none until decision log | `session_routes.py` | Closed |
| `GET /api/v1/sessions/<id>/state` | Quarantine | WE `GET .../state` when bridged | MCP, CI | Player | none until decision log | `session_routes.py` | Closed |
| `GET /api/v1/sessions/<id>/export` | Quarantine | WE export or operator snapshot (documented per route) | MCP | Player | none until decision log | `session_routes.py` | Closed |
| `GET /api/v1/admin/world-engine/story/sessions` | Compat | WE `GET /api/story/sessions` | Admin JWT, operators | Public internet | none | `world_engine_console_routes.py` | Closed |
| `POST /api/v1/admin/world-engine/story/sessions` | Compat | WE `POST /api/story/sessions` | Admin JWT | Public | none | `world_engine_console_routes.py` | Closed |
| `GET .../admin/.../story/sessions/<id>/state` | Compat | WE state | Admin JWT | Public | none | `world_engine_console_routes.py` | Closed |
| `GET .../admin/.../story/sessions/<id>/diagnostics` | Compat | WE diagnostics | Admin JWT | Public | none | `world_engine_console_routes.py` | Closed |
| `POST .../admin/.../story/sessions/<id>/turns` | Compat | WE turns | Admin JWT | Public | none | `world_engine_console_routes.py` | Closed |
| `session_service.create_session` | Quarantine | Same as `POST /api/v1/sessions` | Backend API layer, tests | External services | none | `session_service.py` docstring | Closed |
| `session_service.get_session` | Quarantine | WE state / future W3.2 | none (raises NotImplemented) | Production reliance | TBD with W3.2 | Code inspection | Closed |
| `session_service.execute_turn` | Quarantine | WE turns | none (NotImplemented) | Production | TBD with W3.2 | Code inspection | Closed |
| `session_service.get_session_logs` | Quarantine | WE / future persistence | none (NotImplemented) | Production | TBD | Code inspection | Closed |
| `session_service.get_session_state` | Quarantine | WE state | none (NotImplemented) | Production | TBD | Code inspection | Closed |
| `session_start.start_session` | Quarantine | Engine-backed session after bridge | `session_service`, tests | Standalone product | none | `session_start.py` | Closed |
| `session_store` (volatile dict) | Quarantine | WE durable store | In-process Flask, tests | Multi-instance prod truth | none | `backend-runtime-classification.md` | Closed |
| MCP `wos.session.*` path map | Quarantine | Same as `/api/v1/sessions/*` rows | MCP client | - | none | `mcp_client/client.py` | Closed |

## Links

- State: [audit_resolution_state_world_of_shadows.md](../governance/audit_resolution/audit_resolution_state_world_of_shadows.md) (finding F-H2)
- Architecture: [backend-runtime-classification.md](../technical/architecture/backend-runtime-classification.md)

## Migrated excerpt from MVPs

Source: `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md`

**Migrated Decision (ADR-002 — Package versions are immutable and append-only)**

A package version, once built and stored under `versions/<package_version>/`, is immutable. `active/` is a pointer to a version, never the storage location of mutable content.

**Migrated Consequences**

- package promotion is pointer movement plus event log
- rollback is pointer movement to an earlier version
- audit history is lossless
- preview vs active comparisons are reliable
