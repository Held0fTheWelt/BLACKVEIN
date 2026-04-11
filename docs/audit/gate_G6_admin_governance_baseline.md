# Gate G6 Baseline: Admin Governance

## Gate

- Gate name: G6 Admin Governance
- Gate class: structural
- Audit subject: admin authority boundaries (control plane yes, semantic authorship no)

## Repository Inspection Targets

- `administration-tool/app.py`
- `backend/app/api/v1/ai_stack_governance_routes.py`
- `backend/app/api/v1/improvement_routes.py`
- `backend/tests/test_game_admin_routes.py`
- `backend/tests/test_admin_security.py`
- `tests/smoke/test_admin_startup.py`

## Required Evidence

- admin-manageable policy/operations surfaces
- prevention of direct semantic-authoring operations
- versioned/review-visible admin change traces
- route-level authorization/security checks

## Audit Methods Used In This Baseline

- static admin route and governance-surface inspection
- static security test review
- static startup smoke-surface review (no runtime execution in this block)

## Command Strategy

| command | status | basis | promotion requirement |
| --- | --- | --- | --- |
| `cd backend && python -m pytest tests/test_game_admin_routes.py tests/test_admin_security.py tests/test_goc_admin_semantic_boundary.py -q --tb=short --no-cov` | `repo-verified` | Canonical admin route/security/semantic-boundary path. | Archived: `tests/reports/evidence/all_gates_closure_20260409/g6_admin_backend.txt` |
| `python -m pytest tests/smoke/test_admin_startup.py -v --tb=short` | `repo-verified` | Canonical startup smoke path for admin service readiness. | Archived: `tests/reports/evidence/all_gates_closure_20260409/g6_admin_smoke.txt` |

## Baseline Findings

1. Admin control-plane UI routes and governance views are explicitly present in `administration-tool/app.py`.
2. Governance APIs in `backend/app/api/v1/ai_stack_governance_routes.py` are moderator/admin protected and primarily evidence-oriented (`session-evidence`, `improvement-packages`, `release-readiness`).
3. Improvement governance state in `improvement_service.py` includes explicit review states (`pending_governance_review`, `governance_accepted`, `governance_rejected`) and decision history.
4. Security test coverage exists (`test_admin_security.py`), and admin game-route governance flows are tested (`test_game_admin_routes.py`).
5. Combined route/security/semantic-boundary runtime evidence now exists in this closure run; no canonical admin drift contradiction was observed.

## Status Baseline

- structural_status: `green`
- closure_level_status: `level_a_capable`

Rationale: governance/security scaffolding plus canonical route/security/semantic-boundary/smoke paths are executed and archived.

## Evidence Quality

- evidence_quality: `high`
- justification: direct implementation evidence and executed canonical command transcripts in `all_gates_closure_20260409`.

## Execution Risks Carried Forward

- Keep backend admin-governance and smoke command pair as mandatory regression evidence paths.
