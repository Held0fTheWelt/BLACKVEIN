# ADR-0006: Revision review uses a state machine, not loose status strings

## Status
Proposed (migrated excerpt from MVP docs)

## Date
2026-04-17

## Intellectual property rights
Repository authorship and licensing: see project LICENSE; contact maintainers for clarification.

## Privacy and confidentiality
This ADR contains no personal data. Implementers must follow the repository privacy and confidentiality policies, avoid committing secrets, and document any sensitive data handling in implementation steps.

## Related ADRs

- [README.md](README.md) — ADR index *(no tightly coupled ADR beyond references below)*.

## Context


## Decision
Revision lifecycle must be enforced through a formal workflow state machine with role permissions and side effects.

## Consequences
- multi-operator work is safer
- approval paths become auditable
- system side effects like draft apply and evaluation launch can be attached to transitions

## Diagrams

Revision lifecycle is a **typed state machine**: transitions carry **roles** and may attach **side effects** (draft apply, evaluation).

```mermaid
flowchart LR
  S1[Workflow state] -->|transition + RBAC| S2[Next state]
  S2 --> FX[Side effects: apply draft / launch eval]
```

## Testing

Contract / unit coverage as cited in **References**; extend this section when a dedicated gate exists. Revisit this ADR if enforcement drifts or the decision is bypassed in code review.

## References
docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md
