# Gate G8 Baseline: Improvement Path Operating

## Gate

- Gate name: G8 Improvement Path Operating
- Gate class: operational
- Audit subject: typed, bounded improvement loop with approval/rejection and post-change verification behavior

## Repository Inspection Targets

- `backend/app/services/improvement_service.py`
- `backend/app/services/improvement_task2a_routing.py`
- `backend/app/api/v1/improvement_routes.py`
- `backend/app/contracts/improvement_entry_class.py`
- `backend/app/contracts/improvement_operating_loop.py`
- `backend/app/contracts/writers_room_artifact_class.py` (shared `WritersRoomArtifactClass` for improvement output artifact class)
- `backend/tests/improvement/test_improvement_routes.py`
- `backend/tests/improvement/test_improvement_unit.py`
- `backend/tests/improvement/test_improvement_task2a_routing_positive.py`
- `backend/tests/improvement/test_improvement_task2a_routing_negative.py`
- `tests/reports/pytest_improvement_*.xml`

## Required Evidence

- typed improvement entry classes
- bounded proposal and approval/rejection handling
- publication and post-change verification traces
- route/service/test evidence for full loop stages
- operational evidence that improvements are progressed through the loop, not only accepted by handlers

## Audit Methods Used In This Baseline

- static service/route contract inspection
- loop-stage artifact progression inspection
- executed operational tests for route, unit, and routing-task2a behavior

## Command Strategy

| command | status | basis | execution evidence |
| --- | --- | --- | --- |
| `cd backend && python -m pytest tests/improvement/ -q --tb=short --no-cov` | `repo-verified` | Canonical G8 directory; matches CI job `improvement-g8-contract-tests` in `.github/workflows/backend-tests.yml`. | CI job and archived rerun: `tests/reports/evidence/all_gates_closure_20260409/g8_improvement.txt` (60 passed) |

## Baseline Findings

1. Improvement loop stages are concretely represented and exercised: variant creation, sandbox experiment execution, evaluation and recommendation drafting, retrieval enrichment, transcript evidence readback, governance review bundle creation, semantic compliance validation, and decision handling.
2. Typed roadmap entry classes (`runtime_issue_improvement`, `module_completeness_improvement`, `semantic_quality_improvement`) are enforced via `ImprovementEntryClass` and strict parsing; API and service reject unknown values and metadata/top-level conflicts.
3. `workflow_stages` entries carry explicit `loop_stage` values aligned to roadmap §6.8 (`ImprovementLoopStage`).
4. Recommendation packages carry `semantic_compliance_validation` with fixed mandatory checks; `pass` requires all mandatory checks to succeed.
5. `improvement_output_artifact_class` uses the canonical `WritersRoomArtifactClass` values (`proposal_artifact` until terminal decision, then `approved_authored_artifact` or `rejected_artifact`).
6. `publication_verification_trace` includes `publication_surface`, `published_record_id`, and `post_change_verification` (including `verified_against_stored_evaluation` on accept and `not_applicable` on reject); `declared_runtime_promotion` remains false — HITL registry record only, not live module promotion.
7. `improvement_loop_progress` records terminal loop stages (`approval_rejection`, `publication`, `post_change_verification`) after governance decisions.

## Status Baseline

**Operational gate note on `structural_status`:** For operational gate G8, `structural_status` records whether the **bounded Improvement operating loop** is **sufficiently evidenced and structurally governable** in implementation and executed tests.

- structural_status: `green`
- closure_level_status: `level_a_capable`

**Rationale:** Typed entry classes, mandatory semantic compliance, explicit `loop_stage` traces, publication/post-change verification artifacts, and executed tests under `tests/improvement/` (plus CI job `improvement-g8-contract-tests` gating `backend-coverage-tests`) close the prior roadmap-contract gaps for this gate.

## Immediate Remediation Targets

None for the prior G8 contract gaps (typed classes, publication/verification formalization). Ongoing: any future drift should be caught by `tests/improvement/` and mandatory compliance checks.

## Evidence Quality

- evidence_quality: `high`
- justification: implementation evidence plus executed route/unit/routing tests and CI-explicit `tests/improvement/` path.

## Execution Risks Carried Forward

- Canonical authored truth promotion remains a separate governed action; traces state this explicitly.
- Stored variants with missing `improvement_entry_class` are coalesced to the documented default on read; invalid stored values raise when loaded for experiment execution.
