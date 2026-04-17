# ADR-0006: Revision review uses a state machine, not loose status strings

## Status

Proposed (migrated excerpt from MVP docs)

## Decision

Revision lifecycle must be enforced through a formal workflow state machine with role permissions and side effects.

## Consequences

- multi-operator work is safer
- approval paths become auditable
- system side effects like draft apply and evaluation launch can be attached to transitions

## Source

Migrated from `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md`