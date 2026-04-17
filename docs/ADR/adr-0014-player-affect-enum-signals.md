# ADR-0014: Player affect uses enum-based signals, not one-off frustration booleans

## Status

Proposed (migrated excerpt from MVP docs)

## Decision

Any player-state interpretation seam should use a general affect model with enums and confidence values. Frustration is one possible affect, not the architecture itself.

## Consequences

- future adaptive assistance remains extensible
- operators and evaluators can inspect broader player-state signals
- player adaptation can stay bounded by policy instead of ad hoc heuristics

## Source

Migrated from `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md`