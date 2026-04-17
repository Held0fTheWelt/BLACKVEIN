# Runtime Authority Decision
**Migrated Decision:** See canonical ADR: [ADR-0001: Runtime authority in world-engine](../../ADR/adr-0001-runtime-authority-in-world-engine.md)



Status: Canonical decision for Milestones 0-5.

Ownership boundaries

### Backend remains responsible for

- content curation and publishing controls,
- review and moderation workflows,
- policy validation interfaces and governance endpoints,
- operational diagnostics and admin-facing session tooling.

### World-Engine becomes responsible for

- story session lifecycle (create, execute turn, state, diagnostics),
- authoritative turn execution and state progression,
- runtime-side persistence for hosted story sessions.

### Shared core becomes responsible for

- model and adapter contracts,
- model registry and routing policy,
- reusable runtime models for interpreted input and diagnostics,
- reusable input interpretation behavior.

## Migration and compatibility policy

- Existing backend in-process runtime paths are transitional and deprecated.
- Compatibility shims are allowed only when explicitly labeled transitional.
- Command-style input remains supported, but only as one interpretation mode.
- No new duplicate business logic is introduced intentionally.

## Contract-level implications

- AI output remains non-authoritative proposal data.
- Runtime commit authority remains outside the model layer.
- Canonical authored content compiles into runtime/retrieval/review projections.
- Backend session APIs shift to World-Engine-hosted execution paths.
