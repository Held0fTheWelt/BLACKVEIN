# ADR-0008: Validation strategy must be explicit and configurable

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
Output validation must expose a strategy: `schema_only`, `schema_plus_semantic`, or `strict_rule_engine`.

## Consequences
- runtime behavior becomes transparent
- environments can trade latency for scrutiny
- test suites can target strategy-specific expectations

## Testing

Contract / unit coverage as cited in **References**; extend this section when a dedicated gate exists. Revisit this ADR if enforcement drifts or the decision is bypassed in code review.

## References
docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md
