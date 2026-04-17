# ADR-0004: Runtime model output is proposal-only until validator approval

## Status

Proposed (migrated excerpt from MVP docs)

## Decision

The model may suggest narrative text, triggers, and effects. No suggestion is authoritative until output validation and engine legality checks pass.

## Consequences

- the model cannot silently mutate truth
- blocked turns are first-class
- commit logic remains engine authority

## Source

Migrated from `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md`