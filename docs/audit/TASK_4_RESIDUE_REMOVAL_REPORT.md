# Task 4 — Residue Removal Report

## Scope

- Applies operational residue criteria (2-of-3 rule) to cleanup-relevant tracked surfaces.
- This pass classifies and decides keep/demote/remove intent; no destructive removal is executed here.

## Operational criteria

1. active-value omission test
2. durable-role displacement test
3. transitional/history logic test

A surface is residue/residue-candidate only when at least 2 of 3 are satisfied.

## Decision table

| Surface | Omission | Displacement | Transitional/history | Decision | Priority | Rationale |
|---|---|---|---|---|---|---|
| `docs/audit/gate_summary_matrix.md` | no | no | no | keep | P0 | active audit control surface with current gate baseline role |
| `outgoing/*` and `docs/g9_evaluator_b_external_package/*` mirror pair | no | partial | yes | keep with strict mirror policy | P0 | still active evaluator handoff role; drift risk managed by policy |
| `docs/reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md` (formerly root `PATCH_NOTES_FLASK_PLAY_INTEGRATION.md`) | yes | yes | yes | **executed:** under `docs/reports/` | P1 | historical process note; path corrected to tracked location |
| `backend/fixtures/improvement_experiment_runs/improvement_experiment_*.json` (formerly `backend/world-engine/app/var/runs/`) | partial | yes | yes | **executed:** relocated to fixtures | P1 | placement ambiguity resolved; samples are explicit fixtures |
| `docs/reports/*` (subset) | partial | partial | yes | mixed; case-by-case demote | P1 | some reports remain active evidence, others historical |
| `docs/research_mvp_gate_closure.md` | yes | yes | yes | residue-candidate demote/archive | P1 | superseded by newer audit/control surfaces |
| `docs/research_mvp_implementation_summary.md` | yes | yes | yes | residue-candidate demote/archive | P1 | superseded process narrative |
| `docs/ROADMAP_MVP_REPOSITORY_SURFACE_TRUTH_AND_STRUCTURE_CLEANUP.md` | partial | yes | yes | residue-candidate demote after extraction | P1 | planning history with partial durable-truth overlap |
| `docs/ROADMAP_MVP_RESEARCH_AND_CANON_IMPROVEMENT_SYSTEM.md` | partial | yes | yes | residue-candidate demote after extraction | P1 | process-heavy roadmap history |
| `docs/ROADMAP_MVP_SEMANTIC_DRAMATIC_PLANNER.md` | partial | yes | yes | residue-candidate demote after extraction | P1 | process-heavy roadmap history |
| `docs/testing/README.md` | no | partial | partial | keep, targeted cleanup | P1 | still active mixed-audience entrypoint pending split completion |
| `tests/reports/*` tracked subset | no | partial | yes | keep with explicit local-vs-tracked policy | P1 | still referenced by gate/audit surfaces; policy controls needed |

## Ambiguity handling log

- `docs/reports/*`: not globally removable because active-value differs per file.
- `tests/reports/*`: tracked subset has active evidence role; untracked local evidence remains non-authoritative.

## Outcome

- Residue criteria are applied operationally (not rhetorical).
- P0 surfaces are retained with policy controls.
- P1 candidates are explicitly marked for downstream demotion/relocation where criteria pass.

