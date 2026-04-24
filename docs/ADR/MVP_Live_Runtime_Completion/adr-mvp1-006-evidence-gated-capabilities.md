# ADR-MVP1-006: Evidence-Gated Architecture Capabilities

**Status**: Accepted
**MVP**: 1 — Experience Identity and Session Start
**Date**: 2026-04-24

## Context

Previous capability reports in the system could claim "implemented" status without concrete source anchors or behavioral tests. This led to false confidence in features that were not actually functioning in the live path.

## Decision

All capability reports produced by this system must:

1. Include `source_anchors` — real file paths and function names for each implemented capability
2. Use `"status": "missing"` for capabilities that are not yet implemented — never static success
3. Be backed by passing tests named in the `tests` field
4. Not claim "implemented" for any capability that lacks at least one source anchor

The capability evidence report for MVP1 is at `tests/reports/MVP_Live_Runtime_Completion/MVP1_CAPABILITY_EVIDENCE.md` and the test `test_ldss_capability_added_to_e0_report_requires_source_anchor` validates this rule.

Error code for violation: `capability_evidence_missing_source_anchor`

## Affected Services/Files

- `tests/reports/MVP_Live_Runtime_Completion/MVP1_CAPABILITY_EVIDENCE.md` (NEW)
- `world-engine/tests/test_mvp1_experience_identity.py:TestCapabilityEvidence`

## Consequences

- LDSS, Narrative Gov, and Langfuse are explicitly marked `missing` in the MVP1 capability report
- Implemented capabilities (profile resolution, role selection, visitor removal) have concrete source anchors
- MVP4 must provide real source anchors when it marks diagnostics capabilities as `implemented`

## Alternatives Considered

- Static capability declaration (always "implemented"): rejected — source of previous trust failures
- Database-driven capability registry: deferred to MVP4 (diagnostics MVP)

## Validation Evidence

- `test_ldss_capability_added_to_e0_report_requires_source_anchor` — PASS

## Operational Gate Impact

No operational tooling changes required.
