# ADR-0001: Runtime authority in world-engine

## Status

Accepted - aligns with `docs/technical/runtime/runtime-authority-and-state-flow.md` and the archived `docs/archive/architecture-legacy/runtime_authority_decision.md` (Milestones 0-5).

## Date

2026-04-10 (ADR authored with documentation program; decision content predates this file.)

## Context

World of Shadows split **platform API / governance** from **live narrative execution**. Without a single authoritative runtime host, duplicate business logic and conflicting session state would emerge across Flask backends and experimental paths.

## Decision

1. **`world-engine` (play service)** is the **authoritative runtime host** for story sessions: lifecycle, turn execution, and runtime-side session persistence model.
2. **`backend`** remains responsible for content curation, publishing controls, review/moderation workflows, policy validation, and admin/operator diagnostics integration - **not** for hosting canonical player HTML or re-implementing committed turn logic.
3. **`story_runtime_core`** holds shared interpretation, registry/adapters, and reusable models consumed by the play service.
4. **AI output** remains **non-authoritative proposal data** until validated and committed by runtime seams (see `docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md` for GoC specifics).

## Consequences

**Positive**

- Clear seam for engineering ownership and on-call triage.
- Enables MCP and admin tooling without conflating them with committed play state.

**Negative / risks**

- Requires careful **proxy and secret** configuration between backend and play service.
- Transitional backend paths must be **explicitly labeled** deprecated until removed.

**Follow-ups**

- Track removal of transitional in-process runtime shims as documented in `runtime_authority_decision.md`.
- Keep ADR synchronized if authority shifts (supersede rather than silently edit).

## References

- `docs/technical/runtime/runtime-authority-and-state-flow.md`
- `docs/archive/architecture-legacy/runtime_authority_decision.md` (archived original)
- `world-engine/app/story_runtime/manager.py` (`StoryRuntimeManager`)
- `docs/dev/architecture/runtime-authority-and-session-lifecycle.md`

## Migrated excerpt from MVPs

Source: `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md`

**Migrated Decision (ADR-001 — Compiled Narrative Package is the only runtime content authority)**

Runtime must consume only approved compiled packages. Raw authored source, research outputs, and draft patches are never read directly by live runtime execution.

**Migrated Consequences**

- promotion becomes a formal act
- preview builds are first-class
- rollback becomes feasible
- authored source and runtime stability are cleanly separated
