# Task 3 — Non-GoC Path Taxonomy and Placement Cleanup Map

## Boundary statement

This map is limited to non-GoC placement/path-category cleanup.

It does not plan or execute:
- GoC namespace relocation,
- GoC dependency closure,
- documentation rewrite.

## Target category taxonomy (non-GoC)

| Category | Definition | Typical location guidance |
|---|---|---|
| `tests` | Executable test suites and test modules | Package-local `*/tests` and selected root orchestrator/smoke trees |
| `fixtures` | Deterministic test input artifacts consumed by tests/scripts | Co-located with owning suite, or explicit shared fixture surface |
| `reports_evidence` | Human-readable closure/evidence reports | Canonical tracked report surfaces with clear ownership |
| `generated_artifacts` | Runtime/generated outputs not intended as source-of-truth | Untracked or isolated generated-artifact areas |
| `templates` | Reusable data templates consumed by tests/workflows | Dedicated template package surfaces |
| `schemas_models` | Structural contracts/schemas for validation | Dedicated schema surfaces with clear owner role |
| `runtime_consumed_content` | Tracked runtime inputs/configs consumed by runtime | Service-owned runtime content roots |
| `misplaced_tracked_non_goc` | Tracked files in misleading paths/roles | Relocate to path matching actual ownership/role |

## Non-GoC misplaced-file relocation list (planned)

| Path | Current classification | Planned category | Planned relocation action | Reason |
|---|---|---|---|---|
| `backend/world-engine/app/var/runs/improvement_experiment_*.json` | (pre-state) Misleading nested service path | `fixtures` | **Executed:** `git mv` → `backend/fixtures/improvement_experiment_runs/` + `README.md` | Relocated tracked JSON off false `backend/world-engine` service root. |
| `PATCH_NOTES_FLASK_PLAY_INTEGRATION.md` | Root-level process/report artifact | `reports_evidence` | **Executed:** `git mv` → `docs/reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md` | Removes misleading root placement. |

## Non-GoC path cleanup map (planned)

| Surface | Current issue | Category decision | Cleanup directive |
|---|---|---|---|
| `tests/reports/*` vs `docs/reports/*` | Mixed evidence narrative surfaces with different implied authority | `reports_evidence` + `generated_artifacts` split | Keep canonical tracked reports in one declared authority surface; treat generated/local evidence separately. |
| `outgoing/g9b_*` vs `docs/g9_evaluator_b_external_package/*` | Duplicate handoff/mirror ownership ambiguity | `reports_evidence` + `templates` with canonical/mirror policy | Declare one canonical owner and one mirror policy with sync requirements. |
| `docs/goc_evidence_templates/schemas/*` vs `schemas/*.schema.json` | Evidence-template schemas and system-level schemas can be conflated | `schemas_models` (subclassed by owner role) | Distinguish evidence-template schemas from system contract schemas in taxonomy metadata and references. |
| `tests/goc_gates/fixtures/*` | Sidecar clarity depends on owning suite linkage | `fixtures` | Keep fixture colocation with owner suite; maintain sidecar map linkage. |
| `backend/.coveragerc` | Coverage sidecar sometimes mistaken as runtime config | `fixtures`/execution-sidecar metadata | Keep as execution sidecar with explicit owner annotation in cleanup outputs. |

## Non-GoC path/category normalization controls

- Every relocation candidate must record:
  - current path,
  - target category,
  - destination rule,
  - ownership rationale.
- No file movement is executed by this Task 3 artifact; this is the execution control map.
- Any category conflict must be resolved with ownership first, then readability.

## Priority

- P0:
  - ~~`backend/world-engine/app/var/runs/improvement_experiment_*.json`~~ **done** → `backend/fixtures/improvement_experiment_runs/`
  - `outgoing/*` vs `docs/g9_evaluator_b_external_package/*`
- P1:
  - `tests/reports/*` vs `docs/reports/*`
  - `docs/goc_evidence_templates/schemas/*` vs `schemas/*.schema.json`
  - ~~`PATCH_NOTES_FLASK_PLAY_INTEGRATION.md`~~ **done** → `docs/reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md`
