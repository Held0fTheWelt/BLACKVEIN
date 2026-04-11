# Gate G7 Baseline: Writers' Room Operating Contract

## Gate

- Gate name: G7 Writers' Room Operating Contract
- Gate class: operational
- Audit subject: bounded Writers' Room usefulness, artifact flow, and approval boundaries without second-runtime truth behavior

## Repository Inspection Targets

- `writers-room/app.py`
- `writers-room/app/models/`
- `writers-room/app/models/implementations/god_of_carnage/`
- `backend/app/contracts/writers_room_artifact_class.py`
- `backend/app/services/writers_room_service.py`
- `backend/app/services/writers_room_model_routing.py`
- `backend/app/api/v1/writers_room_routes.py`
- `backend/tests/writers_room/test_writers_room_routes.py`
- `backend/tests/writers_room/test_writers_room_model_routing.py`
- `backend/tests/writers_room/test_writers_room_unit.py`
- `backend/tests/writers_room/test_writers_room_g7_operating_contract.py`

## Required Evidence

- analysis/proposal/authoring-support functional paths
- bounded output classing and recommendation-only behavior
- approval boundaries preventing direct runtime truth mutation
- semantic alignment checks with shared vocabulary/routing contracts
- operational traces showing bounded workflow consumption (not endpoint existence only)

## Audit Methods Used In This Baseline

- static route/service and workflow-contract inspection
- artifact-flow and approval-state inspection
- executed operational tests for route, routing, unit behavior, and G7 contract tests

## Command Strategy

| command | status | basis | execution evidence |
| --- | --- | --- | --- |
| `cd backend && python -m pytest tests/writers_room/ -q --tb=short --no-cov` | `repo-verified` | Gate G7 Writers' Room tree; includes routes, routing, unit, and `test_writers_room_g7_operating_contract.py`. | CI job `writers-room-g7-contract-tests` and archived rerun: `tests/reports/evidence/all_gates_closure_20260409/g7_writers_room.txt` |

## Baseline Findings

1. Writers' Room exposes bounded operational functions through a concrete flow: request intake, retrieval analysis, proposal generation, artifact packaging, governance envelope, and human review pending (`workflow_manifest` and `workflow_stages` in `writers_room_service.py`).
2. Analysis/proposal/authoring-support behavior is materially present as workflow outputs (`issues`, `recommendation_artifacts`, `proposal_package`, `patch_candidates`, `variant_candidates`) and is consumed by governance-oriented workflow states rather than direct runtime mutation.
3. Approval/rejection boundaries are explicit and enforced through `pending_human_review` -> `pending_revision` -> terminal `accepted`/`rejected` transitions in `apply_writers_room_decision()` and `submit_writers_room_revision()`. The `governance_outcome_artifact` key is **absent** until a terminal accept/reject; tests assert that absence and post-terminal exclusivity.
4. The service enforces recommendation-only posture (`outputs_are_recommendations_only` and governance checklist) and prevents implicit publish/canonicalization within Writers' Room paths.
5. Executed route and G7 contract tests verify bounded operational consumption and HITL behavior (create/fetch/decision/revision-submit loops, invalid decision rejection, no double-finalize, retrieval materiality effects, §7.3 metadata on governed artifacts).
6. Roadmap artifact classes (`analysis_artifact`, `proposal_artifact`, `candidate_authored_artifact`, `approved_authored_artifact`, `rejected_artifact`) are first-class via `artifact_class` on governed outputs; `artifact_provenance` no longer carries a parallel `kind` discriminator. A derived `writers_room_artifact_manifest` indexes `{artifact_id, artifact_class}` for audit.

## Status Baseline

**Operational gate note on `structural_status`:** The roadmap and baseline audit plan use one dual-status model for all gates: `structural_status` and `closure_level_status` share the same field names everywhere. For **operational** gates such as G7, `structural_status` is still that shared baseline field; here it records whether the **bounded Writers' Room operating contract** (artifact flow, approval boundaries, recommendation-only posture, and absence of second-runtime truth behavior) is **sufficiently evidenced and structurally governable** in implementation and executed tests.

- structural_status: `green`
- closure_level_status: `level_a_capable`

**Rationale:** Implementation carries explicit roadmap §7.3 metadata (`artifact_id`, `artifact_class`, `source_module_id`, `shared_semantic_contract_version`, `evidence_refs`, `proposal_scope`, `approval_state`) on governed artifact records, a single live taxonomy (no `artifact_provenance.kind`), terminal HITL exclusivity enforced in code and tests, and CI runs an explicit `tests/writers_room/` job plus the broader backend fast suite. **This is not program-level MVP closure** (G9/G9B/G10 and other gates remain per master report).

## Remediation (prior targets — addressed in-repo)

1. **Artifact-class taxonomy:** Addressed — `WritersRoomArtifactClass`, `build_writers_room_artifact_record`, stamped outputs, `test_writers_room_g7_operating_contract.py`, and manifest index.
2. **Recommendation-only posture:** Preserved and test-asserted; adjacent publication surfaces remain out of scope for automatic canonicalization (HITL note on terminal outcome artifact).

## Evidence Quality

- evidence_quality: `high`
- justification: direct implementation evidence, executed route and G7 contract tests, workflow traces, and explicit CI path for `tests/writers_room/`.

## Execution Risks Carried Forward

- boundedness still depends on continued governance discipline across adjacent publication surfaces outside this gate's pytest scope
- future regressions could weaken workflow-stage/approval-state assertions if tests are diluted
