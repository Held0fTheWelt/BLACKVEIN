# ADR-0007: Revision conflicts are explicit governance objects

## Status

Proposed (migrated excerpt from MVP docs)

## Decision

Competing revision candidates targeting overlapping content units must create conflict records before draft apply.

## Consequences

- no silent last-write-wins behavior
- operators can resolve conflicts deliberately
- revision batches remain inspectable

## Source

Migrated from `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md`