# Despaghettification — completed work log (archive)

*Path:* `despaghettify/despaghettification_completed_log.md` — Overview: [README.md](README.md). Empty bootstrap: [templates/despaghettification_completed_log.EMPTY.md](templates/despaghettification_completed_log.EMPTY.md).

**Purpose:** Long-running record of **finished** despaghettification waves (closed **DS-***, completed check/reset passes, merged PRs). Keeps [despaghettification_implementation_input.md](despaghettification_implementation_input.md) small — that file holds only **open** DS rows and in-flight progress.

**Language:** [Repository language](../../docs/dev/contributing.md#repository-language) — English for all rows.

**Do not** mirror completed rows back into the input § *Open* tables. Formal evidence remains under `despaghettify/state/artifacts/…` and `WORKSTREAM_*_STATE.md` per [EXECUTION_GOVERNANCE.md](state/EXECUTION_GOVERNANCE.md).

## When to append here (mandatory)

| Event | Action |
|-------|--------|
| **DS-ID closed** ([spaghetti-solve-task.md](spaghetti-solve-task.md) finalization) | Append **one** summary row to § *Completed waves* (**newest first**); remove from input § *Open*. |
| **Partial wave** (`k < N`) | Input § *Active progress* only — not here until **CLOSED**. |
| **`spaghetti-check`** / **`spaghetti-reset`** | Append if logged; clear input § *Active progress*. |
| **Bulk archive** | If § *Active progress* has **>5** rows, move oldest closed rows here (keep ≤3 active in input). |

---

## Closed DS detail (batch 2026-05-20)

Full row text formerly in the input list — kept here so the input file stays lean.

| ID | pattern | location (typical) | outcome (done) | gates / evidence |
|----|---------|--------------------|----------------|------------------|
| **DS-008** | **C4 · C7 ·** LangGraph runtime executor decomposition | `ai_stack/langgraph/langgraph_runtime_executor.py` | Runtime aspect validation orchestration moved to `ai_stack/langgraph/langgraph_runtime_validation.py`; `_validate_seam` delegates validation execution, retry feedback, attempt record assembly, and validation update copying. `_build_runtime_aspect_validation` and `_validate_seam` no longer appear in top longest/nesting rankings. | `compileall` pass; focused pytest **51 passed**; `tests/run_tests.py --suite ai_stack_graph ai_stack_narrative ai_stack_quality --quick` pass; `check --with-metrics` pass; post evidence `artifacts/workstreams/ai_stack/post/session_20260520_DS-008_w01_runtime_validation_comparison.*`, `artifacts/workstreams/ai_stack/post/session_20260520_DS-008_w02_validation_seam_comparison.*` |
| **DS-007** | **C1 ·** Backend app import-cycle cluster | `backend/app` import graph | C1 reduced from **22/393** files (**5.598%**) to **6/395** files (**1.519%**), below the **2%** bar. | `ds005` pass; `check --with-metrics` pass; focused pytest bundle **73 passed**; post evidence `artifacts/workstreams/backend_runtime_services/post/session_20260520_DS-007_w01_cycle_comparison.*` |
| **DS-006** | **C5 · C6 · C7 ·** Scan-scope hygiene before product refactors | `fy-manifest.yaml`, `despaghettify/tools/spaghetti_ast_scan.py`, `world-engine/source/Lib/site-packages` | `fy-manifest.yaml` scan roots now match the fixed product-code scope from `spaghetti-check-task.md`; vendored `site-packages` is no longer measured. | `wave-plan-validate` pass; `check --with-metrics` pass; `spaghetti_ast_scan.py` pass; post evidence `artifacts/workstreams/repo_governance_rollout/post/session_20260520_DS-006_w01_scope_comparison.*` |
| **DS-001** | **C1 ·** Runtime import / cycle pressure | `backend/app/runtime` (turn executor, supervisor, validators) | Pipeline/executor seams split; no `TYPE_CHECKING` cycle hints under runtime | `ds005_runtime_import_check.py` exit **0**; `tests/run_tests.py --suite backend_runtime --quick` |
| **DS-002** | **C4 ·** Multi-responsibility hotspots | `backend/app/runtime`, `backend/app/services` | Writers Room pipeline stages, narrative commit phases, evidence/inspector section modules | `tests/run_tests.py --suite backend_services --quick` |
| **DS-004** | **C5 ·** Magic numbers + global-ish state | `backend/app/services`, configuration edges | `backend/app/config/route_constants.py` | `pytest backend/tests/api/v1/tests/test_ds004_route_constants_integration.py` — **16** passed |
| **DS-003** | **C6 ·** Duplication / missing abstractions | `ai_stack/tests`, `ai_stack/research/research_*` | `ai_stack/rag/*` package split; `goc_yaml_cache_fixtures` autouse; research pipeline phases | `tests/run_tests.py --suite ai_stack_goc ai_stack_retrieval_research --quick` |
| **DS-005** | **C7 ·** Confusing control flow | `ai_stack/story_runtime/turn/goc_turn_seams_validation.py`, `backend/app/runtime/relationship_context_derive.py` | Validation seam extracted from `goc_turn_seams.py`; relationship derive already phased | `ds005` exit **0**; seam pytest bundle — **27** passed |

**Recommended order used:** phase **1** DS-001 → **2** DS-002 → **3** DS-004 → **4** DS-003 → **5** DS-005 (runtime/import risk before large `ai_stack` dedupe, constants before cross-package C7).

---

## Completed waves

| date | ID(s) | short description | pre artefacts (rel. to `despaghettify/state/`) | post artefacts (rel. to `despaghettify/state/`) | state doc(s) updated | PR / commit |
|------|-------|-------------------|----------------------------------------|----------------------------------------|----------------------|-------------|
| 2026-05-20 | **DS-008** | C4/C7: LangGraph validation orchestration split; runtime aspect validation and validation-seam retry helpers moved behind stable executor wrappers. | `artifacts/workstreams/ai_stack/pre/session_20260520_DS-008_*` | `artifacts/workstreams/ai_stack/post/session_20260520_DS-008_w01_runtime_validation_comparison.*`; `artifacts/workstreams/ai_stack/post/session_20260520_DS-008_w02_validation_seam_comparison.*` | `WORKSTREAM_AI_STACK_STATE.md` | working tree |
| 2026-05-20 | **DS-007** | C1: backend/app static cycle share reduced below bar; avoidable auth/API/runtime back-edges removed. | `artifacts/workstreams/backend_runtime_services/pre/session_20260520_DS-007_*` | `artifacts/workstreams/backend_runtime_services/post/session_20260520_DS-007_w01_cycle_comparison.*` | `WORKSTREAM_BACKEND_RUNTIME_SERVICES_STATE.md` | working tree |
| 2026-05-20 | **DS-006** | C5/C6/C7 scan-scope hygiene: Despaghettify now scans fixed product roots and excludes vendored environment noise from `world-engine/source`. | `artifacts/workstreams/repo_governance_rollout/pre/session_20260520_DS-006_*` | `artifacts/workstreams/repo_governance_rollout/post/session_20260520_DS-006_w01_scope_comparison.*` | `WORKSTREAM_REPO_GOVERNANCE_ROLLOUT_STATE.md` | working tree |
| 2026-05-20 | **DS-005** | C7: `goc_turn_seams_validation.py` extracted; `goc_turn_seams.py` re-exports; `validation_authority_bridge` points at new seam. | — | (in batch) `artifacts/workstreams/ai_stack/post/session_20260520_DS-003-005_pre_post_comparison.json` | `WORKSTREAM_AI_STACK_STATE.md` | working tree |
| 2026-05-20 | **DS-003** | C6: RAG package split, shared GoC YAML cache fixture, research pipeline phase modules. | — | (in batch) `artifacts/workstreams/ai_stack/post/session_20260520_DS-003-005_pre_post_comparison.json` | `WORKSTREAM_AI_STACK_STATE.md` | working tree |
| 2026-05-20 | **DS-004** | C5: `route_constants.py`; fewer magic route literals in services. | — | (in batch) `artifacts/workstreams/backend_runtime_services/post/session_20260520_DS-001-005_pre_post_comparison.json` | `WORKSTREAM_BACKEND_RUNTIME_SERVICES_STATE.md` | working tree |
| 2026-05-20 | **DS-002** | C4: runtime/service orchestration split into section modules (inspector, narrative commit, evidence). | — | (in batch) `artifacts/workstreams/backend_runtime_services/post/session_20260520_DS-001-005_pre_post_comparison.json` | `WORKSTREAM_BACKEND_RUNTIME_SERVICES_STATE.md` | working tree |
| 2026-05-20 | **DS-001** | C1: runtime import seams stabilised before downstream service edits. | — | (in batch) `artifacts/workstreams/backend_runtime_services/post/session_20260520_DS-001-005_pre_post_comparison.json` | `WORKSTREAM_BACKEND_RUNTIME_SERVICES_STATE.md` | working tree |
| 2026-04-12 | — | `spaghetti-reset-task` + one **`spaghetti-check`**: workstreams wiped, EMPTY → live input, metrics from `check --with-metrics`. | — | — | — | `despaghettify/reports/reset_check_with_metrics.json`, `despaghettify/reports/reset_ast_scan_capture.txt` |

**New rows:** append at the **top** of § *Completed waves* (newest first). For a multi-DS session, add one row per **DS-ID** plus optional one-line batch note in § *Closed DS detail*.
