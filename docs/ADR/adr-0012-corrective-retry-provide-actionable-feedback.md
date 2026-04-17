# ADR-0012: Corrective retry must provide actionable validation feedback

## Status

Proposed (migrated excerpt from MVP docs)

## Decision

Retry is not blind regeneration. When validation fails, the runtime must produce actionable feedback describing the violation, the violated rule, and legal alternatives where available.

## Consequences

- retry quality is materially better than blind re-roll
- validation feedback becomes a first-class contract
- semantic and rule-based validators must expose machine-usable violation details
- prompt assembly must support corrective context

## Source

Migrated from `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md`