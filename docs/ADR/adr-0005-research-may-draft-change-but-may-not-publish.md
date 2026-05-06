# ADR-0005: Research may draft change, but may not publish change

## Status
Accepted

## Implementation Status

**Implemented at the process level; enforcement is structural (path separation), not code-gated.**

- Writers-room (`writers-room/`) produces recommendation artifacts only; publishing authority stays in backend/admin processes.
- `backend/app/content/compiler/` is the sole publish path; writers-room content does not reach runtime until approved through backend publish routes.
- `docs/technical/content/writers-room-and-publishing-flow.md` documents the production/publish separation.
- No automated CI test enforces this boundary; it is maintained by structural path separation and code review convention.
- Status promoted from "Proposed" because the structural decision is in force and the pattern is stable.

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
Research outputs may create findings, revision candidates, and draft patch bundles. Research may never directly modify canonical runtime packages.

## Consequences
- no AI-to-AI uncontrolled publish loop
- review and evaluation remain mandatory
- writers-room and admin stay meaningful in the content chain

## Diagrams

Research may produce **drafts and findings**; only governed promotion paths may touch **canonical runtime packages**.

```mermaid
flowchart LR
  R[Research outputs] --> REV[Review + evaluation]
  REV --> PUB[Publish / promote]
  R -.->|never direct write| PKG[Canonical runtime packages]
  PUB --> PKG
```

## Testing

Contract / unit coverage as cited in **References**; extend this section when a dedicated gate exists. Revisit this ADR if enforcement drifts or the decision is bypassed in code review.

## References
docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md
