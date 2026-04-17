# ADR-0018: Role-aware `AIDecisionLog` and `ParsedRoleAwareDecision`

## Status
Proposed

## Date
2026-04-17

## Intellectual property rights
Repository authorship and licensing: see project LICENSE; contact maintainers for clarification.

## Privacy and confidentiality
This ADR contains no personal data. Implementers must follow the repository privacy and confidentiality policies, avoid committing secrets, and document any sensitive data handling in implementation steps.

## Related ADRs

- [README.md](README.md) — ADR index *(no tightly coupled ADR beyond references below)*.

## Context
Workstream W2/W3 introduced role-structured decision artifacts (interpreter, director, responder) and a need to record role-aware decision diagnostics in a canonical, machine-readable form for auditing and debugging.

## Decision
- Extend the `AIDecisionLog` to include: `parsed_decision` (the canonical `ParsedAIDecision`), role fields (interpreter, director, responder summaries), and `parsed_output` as a serialisable representation of the canonical decision.
- Introduce `ParsedRoleAwareDecision` as a schema that normalizes role-aware fields into `parsed_decision` when present.
- Implement helper `construct_ai_decision_log()` to populate these fields deterministically from the parsing layer.

## Consequences
- Logging schema changes; consumers must read `parsed_decision` from `AIDecisionLog` rather than inferring decisions from raw outputs.
- Tests and evidence builders should assert canonicalization invariants (parsed_decision identity).
- Backward compatibility: when role-aware fields are absent, systems fall back to legacy raw outputs.

## Testing

Contract / unit coverage as cited in **References**; extend this section when a dedicated gate exists. Revisit this ADR if enforcement drifts or the decision is bypassed in code review.

## References
(Automated migration entry created 2026-04-17)
