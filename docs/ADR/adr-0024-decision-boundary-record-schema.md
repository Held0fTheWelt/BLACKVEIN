# ADR-0024: Decision Boundary Record — minimum schema for decision boundary recording

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
The `ROADMAP_MVP_GoC.md` documents a set of minimum fields for runtime records including a Decision Boundary Record. Capturing decision boundary metadata consistently supports auditability and governance.

## Decision
- Standardize a `Decision Boundary Record` with the following minimum fields:
  - `decision_name`
  - `decision_class`
  - `owner_layer`
  - `input_seam_ref`
  - `chosen_path`
  - `validation_result`
  - `failure_seam_used`
  - `notes_code`

- Ensure runtime and governance layers emit this record when a decision boundary is crossed.

## Consequences
- Instrumentation work required in runtime components to populate the record.
- Downstream storage, retrieval, and reporting should include these fields for governance views.

## Testing

Contract / unit coverage as cited in **References**; extend this section when a dedicated gate exists. Revisit this ADR if enforcement drifts or the decision is bypassed in code review.

## References
(Automated migration entry created 2026-04-17)
