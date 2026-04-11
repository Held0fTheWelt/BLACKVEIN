# Despaghettification — information input list for implementers

*Path:* `despaghettify/despaghettification_implementation_input.md` — Overview: [README.md](../README.md).

This document is **not** part of the frozen consolidation archive under `[docs/archive/documentation-consolidation-2026/](../../docs/archive/documentation-consolidation-2026/)`. That archive holds **completed** findings and migration evidence (ledgers, topic map, validation reports) — **do not overwrite or “continue writing” those files**.

Here you find the **living working basis**: structural and spaghetti topics in **code**, prioritised input rows for task implementers, coordination rules, and an **optional** progress note. Like documentation consolidation 2026: **one canonical truth per topic** — applied here to **code structure** (fewer duplicates, clearer boundaries, smaller coherent modules).

**This file is part of wave discipline:** Whoever implements a **despaghettification wave** in code (new helper modules, noticeable AST/structure change) **updates this Markdown in the same wave** — not only the code. Details: § **“Maintaining this file during structural waves”** under coordination. This does **not** replace pre/post artefacts under `despaghettify/state/artifacts/…` (they remain mandatory per `[EXECUTION_GOVERNANCE.md](../state/EXECUTION_GOVERNANCE.md)`); it complements them as the **functional** entry and priority track.

## Link to `despaghettify/state/` (execution governance, pre/post)

This document is **not** a replacement for `[state/EXECUTION_GOVERNANCE.md](../state/EXECUTION_GOVERNANCE.md)`; it is the **functional input side** for structural refactors that should use the **same** evidence and restart rules.


| Governance building block                                     | Role for despaghettification                                                                                                                 |
| ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `[EXECUTION_GOVERNANCE.md](../state/EXECUTION_GOVERNANCE.md)` | Mandatory: read state document, **pre** and **post** artefacts per wave, compare pre→post, update state from evidence (**completion gate**). |
| `[WORKSTREAM_INDEX.md](../state/WORKSTREAM_INDEX.md)`         | Maps **workstream** → `artifacts/workstreams//pre                                                                                            |
| `[state/README.md](../state/README.md)`                       | Entry to the state hub.                                                                                                                      |
| `despaghettify/state/artifacts/repo_governance_rollout/pre    | post/`                                                                                                                                       |


**Artefact paths (canonical, relative to `despaghettify/state/`):**

- Per affected workstream: `artifacts/workstreams/<workstream>/pre/` and `…/post/`.
- Slugs as in the index: `backend_runtime_services`, `ai_stack`, `administration_tool`, `world_engine` (documentation only if MkDocs/nav is in scope).

**Naming convention for structural waves (DS-*):**

- Session/wave prefix as today: `session_YYYYMMDD_…`.
- **DS-ID in the filename**, e.g. `session_YYYYMMDD_DS-001_scope_snapshot.txt`, `session_YYYYMMDD_DS-001_pytest_collect.exit.txt`, `session_YYYYMMDD_DS-001_pre_post_comparison.json` (the latter typically under `**post/**`).
- At least **one** human-readable artefact (`.txt`/`.md`) and **preferably** one machine-readable (`.json`) — as governance requires.

**DS-ID → primary workstream (where to place pre/post):**


| ID     | Primary workstream (`artifacts/workstreams/…`) | Also involved (own pre/post only for real scope)        |
| ------ | ---------------------------------------------- | ------------------------------------------------------- |
| DS-006 | `backend_runtime_services`                     | `ai_stack` (if report/RAG helpers move across packages) |
| DS-007 | `backend_runtime_services`                     | —                                                       |
| DS-008 | `backend_runtime_services`                     | —                                                       |
| DS-009 | `ai_stack`                                     | `backend_runtime_services` (call sites)                 |


**Fill in:** For each active **DS-*** one row (or a group sharing the same primary workstream); slugs as in `[WORKSTREAM_INDEX.md](../state/WORKSTREAM_INDEX.md)`: `backend_runtime_services`, `ai_stack`, `administration_tool`, `world_engine`, `documentation`. Repo-wide cross-check without product code: optional `artifacts/repo_governance_rollout/pre|post/` (e.g. **DS-REPLAY-G**).

Implementers: tick the **completion gate** from `EXECUTION_GOVERNANCE.md`; record the wave and new artefact paths in the matching `WORKSTREAM_*_STATE.md`. Avoid crossings: one clear wave owner per **DS-ID**; multiple workstreams only with agreed **separate** artefact sets.

## Link to documentation-consolidation-2026


| Archive artefact                                                                                                                           | Link to code despaghettification                                                                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `[TOPIC_CONSOLIDATION_MAP.md](../../docs/archive/documentation-consolidation-2026/TOPIC_CONSOLIDATION_MAP.md)`                             | Topics map to **one** active doc per topic; code refactors should not reopen the same functional edge across two parallel implementations (e.g. RAG, MCP, runtime). |
| `[DURABLE_TRUTH_MIGRATION_LEDGER.md](../../docs/archive/documentation-consolidation-2026/DURABLE_TRUTH_MIGRATION_LEDGER.md)`               | Model for **traceable** moves instead of silent drift; despaghettification: **one source** for shared building blocks (e.g. builtins).                              |
| `[FINAL_DOCUMENTATION_VALIDATION_REPORT.md](../../docs/archive/documentation-consolidation-2026/FINAL_DOCUMENTATION_VALIDATION_REPORT.md)` | Closure criteria for a **documentation** strand; for code: tests/CI green, behaviour unchanged, interfaces explicit.                                                |


## Coordination — extend work without colliding

1. **Claims:** Before larger refactors, name the **ID(s)** in team/issue/PR (all *`*DS-*** you are taking from this information input list). Preferably **one** clear owner per ID.
2. **No double track:** Two implementers do **not** work the same ID in parallel; if split: separate sub-tasks explicitly (e.g. DS-003a backend wiring only, DS-003b world-engine import only).
3. **Leave archive alone:** Do not mirror code findings into `documentation-consolidation-2026/*.md`; use CHANGELOG, PR description, `**despaghettify/state/` artefacts**, **this input list** (§ *Latest structure scan*, filled DS rows, optional § *progress*) and matching `**WORKSTREAM_*_STATE.md`**.
4. **Interfaces first:** For cycles (runtime cluster) small **DTO / protocol modules** before big moves; avoids PRs that touch half of `app.runtime` at once.
5. **Measurement optional:** AST/review-based lengths are **guidance**; success is **understandable** boundaries + green suites, not a percentage score.

### Maintaining this file during structural waves (move with the code)

For every relevant **DS-*** / despaghettification **wave**, update this file in the **same PR/commit logic** (not “code only”):


| What                                   | Content                                                                                                                                                                                                                                                                                                                                                                                                            |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Information input list**             | Per **DS-***: maintain columns (*hint / measurement idea*, *direction*, *collision hint*); mark completed waves briefly.                                                                                                                                                                                                                                                                                           |
| **§ Latest structure scan**            | After measurable change: **main table** (as-of date, **M7** overall, 7 category scores, and AST telemetry **N / L₅₀ / L₁₀₀ / D₆**); subsection **M7 calculation and thresholds**; optional **extra checks**; **open hotspots** on every [spaghetti-check-task.md](../spaghetti-check-task.md) run (**prune** solved items). For runtime edges `tools/ds005_runtime_import_check.py`. Rankings: script output only. |
| **§ Recommended implementation order** | Update when priority, dependency, or phase changes; optional Mermaid.                                                                                                                                                                                                                                                                                                                                              |
| **§ Progress / work log**              | Optional **one** new row: DS-ID(s), short summary, gates/tests, pre/post paths (or “see PR”).                                                                                                                                                                                                                                                                                                                      |
| **DS-ID → workstream table**           | Place new or moved **DS-*** here; note co-involved workstreams.                                                                                                                                                                                                                                                                                                                                                    |


**Governance:** `despaghettify/state/artifacts/workstreams/<slug>/pre|post/` and `WORKSTREAM_*_STATE.md` remain **formal** evidence; this file is the **compact** working and review map.

## Latest structure scan (orientation, no warranty)

**Purpose:** A **fillable** overview after measurable runs — after larger refactors update **date**, **M7 inputs**, and optional **extra checks** / **open hotspots**. Measurement flow, builtins grep, runtime spot check: [spaghetti-check-task.md](../spaghetti-check-task.md). The spaghetti check maintains the **information input list** and **recommended implementation order** when **M7 is elevated** (`M7 >= 25%`) **or** at least one category score is **critical** (`>= 45%`); otherwise this scan section (including M7 and category breakdown) is enough. **Rankings** and longest functions: output of `python tools/spaghetti_ast_scan.py` only (repo root). **Open hotspots:** [spaghetti-solve-task.md](../spaghetti-solve-task.md) clears or narrows items when waves resolve them; on every spaghetti-check run, **prune** so solved items are not listed.


| Field                                        | Value (adjust when updating scan)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **As of (date)**                             | **2026-04-12**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Spaghetti scan command                       | `python tools/spaghetti_ast_scan.py` (ROOTS = *measurement scope* column)                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Measurement scope (ROOTS)                    | `backend/app`, `world-engine/app`, `ai_stack`, `story_runtime_core`, `tools/mcp_server`, `administration-tool`                                                                                                                                                                                                                                                                                                                                                                                                                        |
| **M7** — weighted 7-category spaghetti score | **33%** (heuristic; trigger **met** — § *Information input list* and § *Recommended implementation order* updated this pass per policy **M7 ≥ 25%** / **any C ≥ 45%**)                                                                                                                                                                                                                                                                                                                                                                |
| C1: Circular dependencies                    | **20%**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| C2: Nesting depth                            | **12%**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| C3: Long functions + complexity              | **52%**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| C4: Multi-responsibility modules             | **44%**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| C5: Magic numbers + global state             | **24%**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| C6: Missing abstractions / duplication       | **32%**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| C7: Confusing control flow                   | **38%**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| **AST telemetry N / L₅₀ / L₁₀₀ / D₆**        | **4189** / **261** / **73** / **0**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Extra check builtins                         | `def build_god_of_carnage_solo`: **1** hit (`story_runtime_core/goc_solo_builtin_template.py`); **0** duplicate defs in `**/builtins.py` (backend + world-engine) — **2026-04-12**                                                                                                                                                                                                                                                                                                                                                    |
| Extra check runtime                          | `python tools/ds005_runtime_import_check.py` — **exit 0** (all `import_ok`). Spot grep: a few “avoid circular” local-import comments under `backend/app/runtime`; **no** `TYPE_CHECKING` matches there                                                                                                                                                                                                                                                                                                                                |
| **Open hotspots**                            | Top AST offenders: closure cockpit / evidence bundles (155–160L, deferred to DS-009). Treated (DS-006 closed 2026-04-12): Writers Room `run_writers_room_packaging_stage` extracted issue_extraction + recommendation_bundling sub-stages (319→317L); inspector `assemble_filled_inspector_sections` extracted 16 helpers (248→157L). Treated (DS-007 closed 2026-04-12): `run_validated_turn_pipeline` extracted `_log_narrative_outcomes` helper (staged pipeline), `narrative_threads_update_from_commit_impl` refactored with protocol documentation. In progress (DS-008): `apply_improvement_recommendation_decision` extracted guards + builders (176→136L). Context-pack assembly: `rag_context_pack_`* modules + `assemble_context_pack` (DS-009 deferred). `ds005` clean; GoC solo builtin single template definition. |


### Score *M7* — inputs, weights, and calculation


| Symbol | Meaning                            | Value  |
| ------ | ---------------------------------- | ------ |
| **C1** | Circular dependencies              | **20** |
| **C2** | Nesting depth                      | **12** |
| **C3** | Long functions + complexity        | **52** |
| **C4** | Multi-responsibility modules       | **44** |
| **C5** | Magic numbers + global state       | **24** |
| **C6** | Missing abstractions / duplication | **32** |
| **C7** | Confusing control flow             | **38** |


**Formula:** `M7 = 0.20*C1 + 0.10*C2 + 0.20*C3 + 0.15*C4 + 0.10*C5 + 0.15*C6 + 0.10*C7`

**Evaluation:** After filling **C1..C7**, compute **M7** and copy into the main table.

**Trigger policy for check task updates:**

- If **M7 >= 25%** or **any category >= 45%**: update § *Information input list* and § *Recommended implementation order*.
- If **M7 < 25%** and **no category >= 45%**: update only § *Latest structure scan*.

*Note:* M7 is heuristic; AST telemetry (`N/L₅₀/L₁₀₀/D₆`) remains mandatory context for trend comparability.

## Information input list (extensible)

Each row: **ID**, **pattern**, **location**, **hint / measurement idea**, **direction**, **collision hint** (what is risky in parallel).


| ID     | pattern                                               | location (typical)                                                                                                                                                                                                                                                              | hint / measurement idea                        | direction (solution sketch)                                                 | collision hint                                               |
| ------ | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------ |
| DS-006 | **(CLOSED 2026-04-12)** Long multi-step service orchestration in one callable | ~~`writers_room_pipeline_packaging_stage.py` (319→317L)~~ extracted 2 sub-stages + helpers; ~~`inspector_turn_projection_sections_assembly_filled.py` (248→157L)~~ extracted 16 helpers; `ai_stack_closure_cockpit_report_assembly.py` / `ai_stack_evidence_session_bundle.py` (155–160L) for DS-009 | AST leaderboard; stage cohesion vs. file churn | Further stage-sized extractions or helper modules ✓ DONE; closure bundles deferred to DS-009 | High: many tests import service surfaces; one owner per wave |
| DS-007 | **(CLOSED 2026-04-12)** Runtime narrative + validated pipeline blocks         | ~~`narrative_threads_update_from_commit.py` (~164L)~~ refactored with protocol docs; ~~`turn_executor_validated_pipeline.py` (~155L)~~ → staged + helper; `pipeline_decision_guards.py` extracted; 1 circular import documented (ai_decision.py)                                                            | LOC + import ergonomics; `ds005` green         | Smaller units + DTO/protocol edges before large reflows ✓ DONE                    | High: turn path; coordinate with executor tests ✓ RESOLVED           |
| DS-008 | Improvement / recommendation single-function weight   | ~~`improvement_service_recommendation_decision.py` (176→136L)~~ extracted 3 guards + 3 builders to `improvement_service_policy_evaluators.py`; related improvement routes (all 60 tests passing)                                                                                                                                                                                            | Branch count inside decision application       | Extract policy/guard or step functions; preserve API contracts ✓ IN PROGRESS                | Medium: business rules drift if split carelessly             |
| DS-009 | RAG context-pack assembly + closure bundles           | `rag_context_pack_section_titles` / `result_tail` / `compact_body` / `trace_footer` + `rag_context_pack_build` + assembler; closure cockpit report (~182L) G9/G9B/G10 extraction; evidence session bundle (~167L) world engine bridge extraction                                                                                                                                                      | Wave 1 + closure bundle analysis done (DS-006 Task 4)         | Optional sub-stage extraction from DS-006 candidates; defer to DS-009 wave                                                                          | —                                                            |


**New rows:** consecutive **DS-001**, **DS-002**, … (or your ID scheme); briefly justify why it is a structure/spaghetti topic. Per § *DS-ID → primary workstream* pick `artifacts/workstreams/<slug>/pre|post/` paths.

## Recommended implementation order

Prioritised **phases**, **order**, and **dependencies** — aligned with § **information input list** and `[EXECUTION_GOVERNANCE.md](../state/EXECUTION_GOVERNANCE.md)`. After filling: optional subsections per phase, Mermaid `flowchart`, gates per wave, short priority list.


| Priority / phase | DS-ID(s) | short logic                                                                                               | workstream (primary)       | note (dependencies, gates)                                         |
| ---------------- | -------- | --------------------------------------------------------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------ |
| Phase 1          | DS-007   | **(CLOSED 2026-04-12)** Stabilise runtime narrative + validated-pipeline seams (DTOs / smaller units) ✓ DONE | `backend_runtime_services` | `ds005` ✓ + targeted `pytest` under `backend/tests` for runtime/turn ✓ |
| Phase 2          | DS-006   | Shrink largest backend orchestration functions (Writers Room / inspector / closure bundles)               | `backend_runtime_services` | Prefer incremental stage extractions; Writers Room tests as gate   |
| Phase 3          | DS-008   | Flatten improvement recommendation decision path                                                          | `backend_runtime_services` | Route + service tests; avoid behaviour drift                       |
| Phase 4          | DS-009   | **Done (2026-04-12):** context-pack logic → `rag_context_pack_build`; optional follow-up trims only       | `ai_stack`                 | RAG trio + `ds005` as in post artefact `session_20260412_DS-009_`* |


**Fill in:** take rows from the input table; make hard chains explicit (e.g. interfaces before large moves). Coordination § *Maintaining this file*: when priority changes or new **DS-*** appear, update this section and Mermaid if used.

**Implementation** of phases until documented closure (completion gate, session by session): [spaghetti-solve-task.md](../spaghetti-solve-task.md).

## Progress / work log (optional, in addition to mandatory maintenance above)

Implementers may **briefly** record visible progress (for reviewers and the next iteration). **Mandatory** for structural waves remains **updating the input table, § structure scan, and — if needed — this log** (see coordination § *Maintaining this file*). **Additionally**, new waves add **pre/post files** under `despaghettify/state/artifacts/…` (see `EXECUTION_GOVERNANCE.md`); older session artefacts may be missing if intentionally cleaned — proof then via Git/CI/PR. Not a substitute for issues/PRs.


| date       | ID(s)  | short description                                                                                                                                                                                                                                                                                                                                                                                                                                          | pre artefacts (rel. to `despaghettify/state/`)                               | post artefacts (rel. to `despaghettify/state/`)                                                               | state doc(s) updated                                                                                                  | PR / commit                    |
| ---------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| 2026-04-12 | DS-007 | **DS-007 closure (Tasks 3–5):** Pipeline decision guards extracted (`pipeline_decision_guards.py` 227 LOC); `run_validated_turn_pipeline` refactored (155 LOC main + 70 LOC helper, staged); `narrative_threads_update_from_commit.py` protocol documented (input/output/semantics); circular import (ai_decision.py) documented + mitigated. 1 module created, 3 modified, 0 behaviour changes. Pre/post: `artifacts/workstreams/backend_runtime_services/post/session_20260412_DS-007_post.md` + `session_20260412_DS-007_pre_post_comparison.json` | — (refactoring; no pre snapshot required) | `artifacts/workstreams/backend_runtime_services/post/session_20260412_DS-007_post.md` + `session_20260412_DS-007_pre_post_comparison.json` | `WORKSTREAM_BACKEND_RUNTIME_AND_SERVICES_STATE.md` | — |
| 2026-04-12 | DS-009 | **DS-009 optional:** submodules `section_titles`, `result_tail`, `compact_body`, `trace_footer`; thin `rag_context_pack_build`; RAG trio 73; `ds005` 0.                                                                                                                                                                                                                                                                                                    | `artifacts/workstreams/ai_stack/pre/session_20260412_DS-009_optional_pre.md` | `artifacts/workstreams/ai_stack/post/session_20260412_DS-009_optional_post.md` (+ optional verification json) | `WORKSTREAM_AI_STACK_STATE.md`                                                                                        | —                              |
| 2026-04-12 | DS-009 | **DS-009:** `rag_context_pack_build.py` + delegating assembler; RAG pytest trio 73; `ds005` 0. Pre/post: `artifacts/workstreams/ai_stack/pre                                                                                                                                                                                                                                                                                                               | post/session_20260412_DS-009_`*.                                             | `artifacts/workstreams/ai_stack/pre/session_20260412_DS-009_scope.md`                                         | `artifacts/workstreams/ai_stack/post/session_20260412_DS-009_post.md` (+ `session_20260412_DS-009_verification.json`) | `WORKSTREAM_AI_STACK_STATE.md` |
| 2026-04-12 | —      | **Spaghetti-check-task:** `python tools/spaghetti_ast_scan.py` (N=4189, L₅₀=261, L₁₀₀=73, D₆=0); builtins grep (no `builtins.py` duplicate for `build_god_of_carnage_solo`); runtime grep + `ds005_runtime_import_check.py` exit 0. Trigger **M7 ≥ 25%** / **C ≥ 45%** → filled § *Latest structure scan*, **DS-006..009**, § *Recommended implementation order*, **DS-ID → workstream** table.                                                            | —                                                                            | —                                                                                                             | —                                                                                                                     | —                              |
| 2026-04-11 | —      | **Spaghetti-reset-task:** removed ephemeral dirs where present (`.pytest_cache`, `htmlcov`, `_tmp_goc_dbg`, `site`); reset `despaghettification_implementation_input.md` from `templates/…EMPTY.md`; one **spaghetti-check** pass (AST scan, builtins grep, runtime grep, `ds005` exit 0). § *Latest structure scan* filled; **M7 ≈ 33%** (≥ **25%** threshold). DS/phase tables left as `—` from reset; **fill** on next pass per updated trigger policy. | —                                                                            | —                                                                                                             | —                                                                                                                     | —                              |
| —          | —      | —                                                                                                                                                                                                                                                                                                                                                                                                                                                          | —                                                                            | —                                                                                                             | —                                                                                                                     | —                              |


**New rows:** chronologically (**newest first** recommended); **DS-ID(s)**, gates/tests run, pre/post paths as in `[EXECUTION_GOVERNANCE.md](../state/EXECUTION_GOVERNANCE.md)`; for scan/docs-only updates note briefly. Longer history: Git, PRs, `WORKSTREAM_*_STATE.md`.

## Canonical technical reading paths (after refactor)

After structural changes to runtime/AI/RAG/MCP, align **active** technical docs (not the 2026 archive):

- Runtime / authority: `[docs/technical/runtime/runtime-authority-and-state-flow.md](../../docs/technical/runtime/runtime-authority-and-state-flow.md)` — supervisor orchestration: `supervisor_orchestrate_execute.py` + `supervisor_orchestrate_execute_sections.py`; subagent invocation: `supervisor_invoke_agent.py` + `supervisor_invoke_agent_sections.py`
- Inspector projection (backend): `inspector_turn_projection_sections.py` orchestrates; pieces in `inspector_turn_projection_sections_{utils,constants,semantic,provenance}.py`
- Admin tool routes: `administration-tool/route_registration.py` + `route_registration_{proxy,pages,manage,security}.py`
- God-of-Carnage solo builtin (core): `story_runtime_core/goc_solo_builtin_template.py` + `goc_solo_builtin_catalog.py` + `goc_solo_builtin_roles_rooms.py`
- AI / RAG / LangGraph: `[docs/technical/ai/RAG.md](../../docs/technical/ai/RAG.md)`, `[docs/technical/integration/LangGraph.md](../../docs/technical/integration/LangGraph.md)`, `[docs/technical/integration/MCP.md](../../docs/technical/integration/MCP.md)`
- Dev seam overview: `[docs/dev/architecture/ai-stack-rag-langgraph-and-goc-seams.md](../../docs/dev/architecture/ai-stack-rag-langgraph-and-goc-seams.md)`

---

*Created as an operational bridge between structural code work, the state hub under `[despaghettify/state/](../state/README.md)` (pre/post evidence), and the completed documentation archive of 2026.*