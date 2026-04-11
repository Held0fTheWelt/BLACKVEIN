# Despaghettification — information input list for implementers

*Path:* `despaghettify/despaghettification_implementation_input.md` — Overview: [README.md](../README.md).

This document is **not** part of the frozen consolidation archive under [`docs/archive/documentation-consolidation-2026/`](../../docs/archive/documentation-consolidation-2026/). That archive holds **completed** findings and migration evidence (ledgers, topic map, validation reports) — **do not overwrite or “continue writing” those files**.

Here you find the **living working basis**: structural and spaghetti topics in **code**, prioritised input rows for task implementers, coordination rules, and an **optional** progress note. Like documentation consolidation 2026: **one canonical truth per topic** — applied here to **code structure** (fewer duplicates, clearer boundaries, smaller coherent modules).

**This file is part of wave discipline:** Whoever implements a **despaghettification wave** in code (new helper modules, noticeable AST/structure change) **updates this Markdown in the same wave** — not only the code. Details: § **“Maintaining this file during structural waves”** under coordination. This does **not** replace pre/post artefacts under `despaghettify/state/artifacts/…` (they remain mandatory per [`EXECUTION_GOVERNANCE.md`](../state/EXECUTION_GOVERNANCE.md)); it complements them as the **functional** entry and priority track.

## Link to `despaghettify/state/` (execution governance, pre/post)

This document is **not** a replacement for [`state/EXECUTION_GOVERNANCE.md`](../state/EXECUTION_GOVERNANCE.md); it is the **functional input side** for structural refactors that should use the **same** evidence and restart rules.

| Governance building block | Role for despaghettification |
|---------------------------|------------------------------|
| [`EXECUTION_GOVERNANCE.md`](../state/EXECUTION_GOVERNANCE.md) | Mandatory: read state document, **pre** and **post** artefacts per wave, compare pre→post, update state from evidence (**completion gate**). |
| [`WORKSTREAM_INDEX.md`](../state/WORKSTREAM_INDEX.md) | Maps **workstream** → `artifacts/workstreams/<slug>/pre|post/`. |
| [`state/README.md`](../state/README.md) | Entry to the state hub. |
| `despaghettify/state/artifacts/repo_governance_rollout/pre|post/` | Optional for **repo-wide** waves (e.g. large diff across packages); useful when a structural wave needs the same repo commands as the rollout. |

**Artefact paths (canonical, relative to `despaghettify/state/`):**

- Per affected workstream: `artifacts/workstreams/<workstream>/pre/` and `…/post/`.
- Slugs as in the index: `backend_runtime_services`, `ai_stack`, `administration_tool`, `world_engine` (documentation only if MkDocs/nav is in scope).

**Naming convention for structural waves (DS-*):**

- Session/wave prefix as today: `session_YYYYMMDD_…`.
- **DS-ID in the filename**, e.g. `session_YYYYMMDD_DS-001_scope_snapshot.txt`, `session_YYYYMMDD_DS-001_pytest_collect.exit.txt`, `session_YYYYMMDD_DS-001_pre_post_comparison.json` (the latter typically under **`post/`**).
- At least **one** human-readable artefact (`.txt`/`.md`) and **preferably** one machine-readable (`.json`) — as governance requires.

**DS-ID → primary workstream (where to place pre/post):**

| ID | Primary workstream (`artifacts/workstreams/…`) | Also involved (own pre/post only for real scope) |
|----|--------------------------------------------------|-----------------------------------------------------|
| DS-001 | `backend_runtime_services` | — |
| DS-002 | `backend_runtime_services` | — |
| DS-003 | `backend_runtime_services` | — |
| DS-004 | `backend_runtime_services` | `ai_stack` (callers / semantics; no separate pre/post unless scope crosses package) |
| DS-005 | `backend_runtime_services` | — |

**Fill in:** For each active **DS-*** one row (or a group sharing the same primary workstream); slugs as in [`WORKSTREAM_INDEX.md`](../state/WORKSTREAM_INDEX.md): `backend_runtime_services`, `ai_stack`, `administration_tool`, `world_engine`, `documentation`. Repo-wide cross-check without product code: optional `artifacts/repo_governance_rollout/pre|post/` (e.g. **DS-REPLAY-G**).

Implementers: tick the **completion gate** from `EXECUTION_GOVERNANCE.md`; record the wave and new artefact paths in the matching `WORKSTREAM_*_STATE.md`. Avoid crossings: one clear wave owner per **DS-ID**; multiple workstreams only with agreed **separate** artefact sets.

## Link to documentation-consolidation-2026

| Archive artefact | Link to code despaghettification |
|------------------|----------------------------------|
| [`TOPIC_CONSOLIDATION_MAP.md`](../../docs/archive/documentation-consolidation-2026/TOPIC_CONSOLIDATION_MAP.md) | Topics map to **one** active doc per topic; code refactors should not reopen the same functional edge across two parallel implementations (e.g. RAG, MCP, runtime). |
| [`DURABLE_TRUTH_MIGRATION_LEDGER.md`](../../docs/archive/documentation-consolidation-2026/DURABLE_TRUTH_MIGRATION_LEDGER.md) | Model for **traceable** moves instead of silent drift; despaghettification: **one source** for shared building blocks (e.g. builtins). |
| [`FINAL_DOCUMENTATION_VALIDATION_REPORT.md`](../../docs/archive/documentation-consolidation-2026/FINAL_DOCUMENTATION_VALIDATION_REPORT.md) | Closure criteria for a **documentation** strand; for code: tests/CI green, behaviour unchanged, interfaces explicit. |

## Coordination — extend work without colliding

1. **Claims:** Before larger refactors, name the **ID(s)** in team/issue/PR (all **`DS-*** you are taking from this information input list). Preferably **one** clear owner per ID.
2. **No double track:** Two implementers do **not** work the same ID in parallel; if split: separate sub-tasks explicitly (e.g. DS-003a backend wiring only, DS-003b world-engine import only).
3. **Leave archive alone:** Do not mirror code findings into `documentation-consolidation-2026/*.md`; use CHANGELOG, PR description, **`despaghettify/state/` artefacts**, **this input list** (§ *Latest structure scan*, filled DS rows, optional § *progress*) and matching **`WORKSTREAM_*_STATE.md`**.
4. **Interfaces first:** For cycles (runtime cluster) small **DTO / protocol modules** before big moves; avoids PRs that touch half of `app.runtime` at once.
5. **Measurement optional:** AST/review-based lengths are **guidance**; success is **understandable** boundaries + green suites, not a percentage score.

### Maintaining this file during structural waves (move with the code)

For every relevant **DS-*** / despaghettification **wave**, update this file in the **same PR/commit logic** (not “code only”):

| What | Content |
|------|---------|
| **Information input list** | Per **DS-***: maintain columns (*hint / measurement idea*, *direction*, *collision hint*); mark completed waves briefly. |
| **§ Latest structure scan** | After measurable change: **main table** (as-of **date and time**, **M7** overall, 7 category scores, and AST telemetry **N / L₅₀ / L₁₀₀ / D₆**); subsection **M7 calculation and thresholds**; optional **extra checks**; **open hotspots** on every [spaghetti-check-task.md](../spaghetti-check-task.md) run (**prune** solved items). For runtime edges `tools/ds005_runtime_import_check.py`. Rankings: script output only. |
| **§ Recommended implementation order** | Update when priority, dependency, or phase changes; optional Mermaid. |
| **§ Progress / work log** | Optional **one** new row: DS-ID(s), short summary, gates/tests, pre/post paths (or “see PR”). |
| **DS-ID → workstream table** | Place new or moved **DS-*** here; note co-involved workstreams. |

**Governance:** `despaghettify/state/artifacts/workstreams/<slug>/pre|post/` and `WORKSTREAM_*_STATE.md` remain **formal** evidence; this file is the **compact** working and review map.

## Latest structure scan (orientation, no warranty)

**Purpose:** A **fillable** overview after measurable runs — after larger refactors update **date and time**, **M7 inputs**, and optional **extra checks** / **open hotspots**. Measurement flow, builtins grep, runtime spot check: [spaghetti-check-task.md](../spaghetti-check-task.md). The spaghetti check maintains the **information input list** and **recommended implementation order** when the **trigger policy** in § *Trigger policy for check task updates* fires (per-category score thresholds **or** composite **`M7 ≥ M7_ref`**); otherwise this scan section (including M7 and category breakdown) is enough. **Rankings** and longest functions: output of `python tools/spaghetti_ast_scan.py` only (repo root). **Open hotspots:** [spaghetti-solve-task.md](../spaghetti-solve-task.md) clears or narrows items when waves resolve them; on every spaghetti-check run, **prune** so solved items are not listed.

| Field | Value (adjust when updating scan) |
|-------|-------------------------------------|
| **As of (date & time)** | **2026-04-12** *(Europe/Berlin; DS-004 report assembly slice)* |
| Spaghetti scan command | `python tools/spaghetti_ast_scan.py` (ROOTS = *measurement scope* column) |
| Measurement scope (ROOTS) | `backend/app`, `world-engine/app`, `ai_stack`, `story_runtime_core`, `tools/mcp_server`, `administration-tool` |
| **M7** — weighted 7-category spaghetti score | **≈ 25.4%** |
| C1: Circular dependencies | **18** |
| C2: Nesting depth | **12** |
| C3: Long functions + complexity | **45** |
| C4: Multi-responsibility modules | **27** |
| C5: Magic numbers + global state | **18** |
| C6: Missing abstractions / duplication | **22** |
| C7: Confusing control flow | **24** |
| **AST telemetry N / L₅₀ / L₁₀₀ / D₆** | **4230** / **263** / **71** / **0** |
| Extra check builtins | **One** `def build_god_of_carnage_solo` in `story_runtime_core/goc_solo_builtin_template.py`; **0** duplicate defs in `**/builtins.py` (backend + world-engine) — **2026-04-11 23:37:21** *(Europe/Berlin)* |
| Extra check runtime | `python tools/ds005_runtime_import_check.py` — exit **0** (unchanged frozen list); grep under `backend/app/runtime` for deferred-import / cycle comments: **4** sites (unchanged heuristic) — **2026-04-12** |
| **Open hotspots** | — *(no items from the prior input-list queue after **DS-004**; run `spaghetti_ast_scan` / governance check for the next hotspot set.)* **D₆ = 0**; telemetry baseline **4230 / 263 / 71 / 0** (not re-run). |

### Score *M7* — inputs, weights, and calculation

| Symbol | Meaning | Value |
|--------|---------|-------|
| **C1** | Circular dependencies | **18** |
| **C2** | Nesting depth | **12** |
| **C3** | Long functions + complexity | **45** |
| **C4** | Multi-responsibility modules | **27** |
| **C5** | Magic numbers + global state | **18** |
| **C6** | Missing abstractions / duplication | **22** |
| **C7** | Confusing control flow | **24** |

**Formula:** `M7 = 0.20*C1 + 0.10*C2 + 0.20*C3 + 0.15*C4 + 0.10*C5 + 0.15*C6 + 0.10*C7`

**Evaluation:** After filling **C1..C7**, compute **M7** and copy into the main table.

**Trigger policy for check task updates:**

Update § *Information input list*, § *Recommended implementation order*, and § *DS-ID → primary workstream* (for new IDs) when **any** of the following holds (scores **C1..C7** are the same 0–100 style values as in the tables above; use strict **>** for per-category lines):

| Condition | Rule |
|-----------|------|
| **C1** — Circular dependencies | **C1 > 5** |
| **C2** — Nesting depth | **C2 > 10** |
| **C3** — Long functions + complexity | **C3 > 35** |
| **C4** — Multi-responsibility modules | **C4 > 25** |
| **C5** — Magic numbers + global state | **C5 > 20** *(default bar; change here by team agreement if needed)* |
| **C6** — Missing abstractions / duplication | **C6 > 15** |
| **C7** — Confusing control flow | **C7 > 20** |
| **Composite** | **`M7 ≥ M7_ref`** with **`M7_ref = 19%`** — the value of **M7** when each **C1..C7** is set to its trigger boundary (**C5** uses **20** in that calculation): `0.20×5 + 0.10×10 + 0.20×35 + 0.15×25 + 0.10×20 + 0.15×15 + 0.10×20 = 19.0%`. |

**Otherwise** (no per-category trigger **and** **`M7 < 19%`**): update **only** § *Latest structure scan*.

*Note:* M7 is heuristic; AST telemetry (`N/L₅₀/L₁₀₀/D₆`) remains mandatory context for trend comparability.

## Information input list (extensible)

Each row: **ID**, **pattern**, **location**, **hint / measurement idea**, **direction**, **collision hint** (what is risky in parallel).

| ID | pattern | location (typical) | hint / measurement idea | direction (solution sketch) | collision hint |
|----|---------|--------------------|-------------------------|----------------------------|----------------|
| ~~DS-001~~ ✓ CLOSED (2026-04-11) | ~~Deferred imports / cycle-avoidance pattern~~ | ~~`backend/app/runtime` (four modules with local-import comments)~~ | ~~`ds005` clean; grep cycle-hint comments~~ | ✓ Seams tightened; 4 deferred imports promoted; type narrowing applied | Completed |
| DS-002 | Very long stage callable | `writers_room_pipeline_packaging_stage.py` — `run_writers_room_packaging_stage` (~**277** AST lines) | AST leaderboard | Further stage extractions; stable Writers Room API | High: `tests/writers_room/` |
| ~~DS-003~~ ✓ CLOSED (2026-04-12 structure) | ~~Long commit-path orchestration~~ | ~~`update_narrative_threads_from_commit_impl` (**63** AST L orchestrator); `NarrativeCommitThreadDrive` + `narrative_threads_update_from_commit_phases` + `narrative_threads_commit_path_utils`~~ | ~~AST + narrative tests~~ | ✓ Explicit drive + phased apply; pure helpers module | Completed (prior DS-007 narrative DTO workstream closure remains authoritative for protocol) |
| ~~DS-004~~ ✓ CLOSED (2026-04-12 assembly) | ~~Multi-section report assembly~~ | ~~`assemble_closure_cockpit_report` (**64** AST L); `assemble_session_evidence_bundle` (**24** AST L); `ai_stack_closure_cockpit_report_sections`, `ai_stack_evidence_session_bundle_sections`~~ | ~~AST; callers~~ | ✓ Section helpers; ✓ payload contracts preserved (M11 pytest) | Completed (distinct from earlier DS-004 magic-number wave in workstream history) |
| ~~DS-005~~ ✓ CLOSED (2026-04-10 optional) | ~~API + pipeline orchestration~~ | ~~`execute_users_update_put` (**70** AST L); `run_validated_turn_pipeline` (**90** AST L); `user_put_collect_service_kwargs`; `turn_executor_validated_pipeline_{apply,narrative_log}`~~ | ~~AST; route + runtime tests~~ | ✓ Thin handler; ✓ pipeline companion modules | Completed (see prior DS-005 guard waves 2026-04-11 + optional thin 2026-04-10) |

**New rows:** consecutive **DS-001**, **DS-002**, … (or your ID scheme); briefly justify why it is a structure/spaghetti topic. Per § *DS-ID → primary workstream* pick `artifacts/workstreams/<slug>/pre|post/` paths.

## Recommended implementation order

Prioritised **phases**, **order**, and **dependencies** — aligned with § **information input list** and [`EXECUTION_GOVERNANCE.md`](../state/EXECUTION_GOVERNANCE.md). After filling: optional subsections per phase, Mermaid `flowchart`, gates per wave, short priority list.

| Priority / phase | DS-ID(s) | short logic | workstream (primary) | note (dependencies, gates) |
|------------------|----------|-------------|----------------------|----------------------------|
| 1 | DS-001 | Stabilise runtime import / cycle-hint seams before wide service churn | `backend_runtime_services` | `python tools/ds005_runtime_import_check.py`; targeted runtime pytest if touched |
| 2 | ~~DS-005~~ ✓ | Thin user PUT + validated turn pipeline surfaces | `backend_runtime_services` | **Done (2026-04-10):** `ds005` + users_update pytest + `test_execute_turn_system_error_path`; artefacts `session_20260410_DS-005_optional_thin_*` |
| 3 | ~~DS-003~~ ✓ | Decompose narrative commit orchestration with explicit contracts | `backend_runtime_services` | **Done (2026-04-12):** narrative thread + narrative bundle pytest; artefacts `session_20260412_DS-003_commit_path_structure_*` |
| 4 | ~~DS-004~~ ✓ | Split closure cockpit + evidence bundle assembly by section | `backend_runtime_services` | **Done (2026-04-12):** `pytest backend/tests/test_m11_ai_stack_observability.py` + `ds005`; artefacts `session_20260412_DS-004_report_assembly_*` |
| 5 | DS-002 | Tackle Writers Room packaging stage last (largest AST body) | `backend_runtime_services` | `cd backend && python -m pytest tests/writers_room/ -q`; `ds005` |

**Fill in:** one phase row per open **DS-*** (or an explicit merge noted in **note**). Order by **risk**: stabilise **runtime / import seams** (`backend_runtime_services` under `app.runtime`, `ds005`-touched paths) before very large **service orchestration** waves; **`ai_stack`**-only (or other packages) typically **later** unless the scan shows a hard blocker. **Workstream (primary)** must match [WORKSTREAM_INDEX.md](../state/WORKSTREAM_INDEX.md) for pre/post paths. **note** column: concrete **gates** (`pytest …`, `ds005`). Full rules: [spaghetti-check-task.md](../spaghetti-check-task.md) § *Maintaining the input list* → **Recommended implementation order** → *How to build a suitable phase table*. Coordination § *Maintaining this file*: when priority changes or new **DS-*** appear, update this section and Mermaid if used.

**Implementation** of phases until documented closure (completion gate, session by session): [spaghetti-solve-task.md](../spaghetti-solve-task.md).

## Progress / work log (optional, in addition to mandatory maintenance above)

Implementers may **briefly** record visible progress (for reviewers and the next iteration). **Mandatory** for structural waves remains **updating the input table, § structure scan, and — if needed — this log** (see coordination § *Maintaining this file*). **Additionally**, new waves add **pre/post files** under `despaghettify/state/artifacts/…` (see `EXECUTION_GOVERNANCE.md`); older session artefacts may be missing if intentionally cleaned — proof then via Git/CI/PR. Not a substitute for issues/PRs.

| date | ID(s) | short description | pre artefacts (rel. to `despaghettify/state/`) | post artefacts (rel. to `despaghettify/state/`) | state doc(s) updated | PR / commit |
|------|-------|-------------------|----------------------------------------|----------------------------------------|----------------------|-------------|
| 2026-04-12 | DS-004 | **Report assembly:** closure cockpit + session evidence bundles split into section modules; entrypoints slimmed; M11 + ds005 green. | `artifacts/workstreams/backend_runtime_services/pre/session_20260412_DS-004_report_assembly_pre.md` | `artifacts/workstreams/backend_runtime_services/post/session_20260412_DS-004_report_assembly_post.md` + `…/post/session_20260412_DS-004_pre_post_comparison.json` | `WORKSTREAM_BACKEND_RUNTIME_AND_SERVICES_STATE.md` | *(pending commit)* |
| 2026-04-12 | DS-003 | **Commit-path structure:** split `update_narrative_threads_from_commit_impl` into drive builder, terminal resolution, non-terminal apply; pure helpers in `narrative_threads_commit_path_utils`. | `artifacts/workstreams/backend_runtime_services/pre/session_20260412_DS-003_commit_path_structure_pre.md` | `artifacts/workstreams/backend_runtime_services/post/session_20260412_DS-003_commit_path_structure_post.md` + `…/post/session_20260412_DS-003_pre_post_comparison.json` | `WORKSTREAM_BACKEND_RUNTIME_AND_SERVICES_STATE.md` | `3753a4b` |
| 2026-04-10 | DS-005 | **Optional thin slice:** `user_put_collect_service_kwargs` + slim `execute_users_update_put`; validated pipeline split into `turn_executor_validated_pipeline_apply` + `turn_executor_validated_pipeline_narrative_log`; test monkeypatch target updated. | `artifacts/workstreams/backend_runtime_services/pre/session_20260410_DS-005_optional_thin_pre.md` | `artifacts/workstreams/backend_runtime_services/post/session_20260410_DS-005_optional_thin_post.md` + `…/post/session_20260410_DS-005_optional_thin_pre_post_comparison.json` | `WORKSTREAM_BACKEND_RUNTIME_AND_SERVICES_STATE.md` | `ba499a7` |
| 2026-04-11 | DS-001 | **Closure (2026-04-11):** Deferred imports / cycle-avoidance pattern resolved. Tasks 1–4: promoted 4 deferred imports to module-level top-level (role_structured_decision.py, ai_decision.py, ai_failure_recovery.py, turn_executor.py). Type narrowing applied: `ParseResult.role_aware_decision` now `ParsedRoleAwareDecision \| None`. Backwards compatible. All tests: 207/207 passing (role_structured_decision, ai_decision, ai_decision_logging, ai_failure_recovery, turn_executor, session_history). | `session_20260411_DS-001_baseline.md` (plan reference) | See `WORKSTREAM_BACKEND_RUNTIME_AND_SERVICES_STATE.md` § *Hotspot / target status* | `WORKSTREAM_BACKEND_RUNTIME_AND_SERVICES_STATE.md` | `3b0e27a` (turn_executor), `d834e4b` (ai_failure_recovery), prior (ai_decision, role_structured_decision) |
| 2026-04-11 | — | **spaghetti-check-task** (standalone): `spaghetti_ast_scan.py` (**N=4230**, **L₅₀=263**, **L₁₀₀=71**, **D₆=0**); builtins grep; runtime grep (**4** cycle-hint sites); `ds005` exit **0**. § *Latest structure scan* refreshed (**As of** + extra-check stamps + **Open hotspots**). **M7** / **C1..C7** and **DS / phase** tables **unchanged** — same telemetry and thesis as prior row (per check task: confirm when only numbers stable). | — | — | — | — |
| 2026-04-11 | — | **spaghetti-reset-task:** Steps 1–2 (temp cleanup where present; input reset from `templates/…EMPTY.md`); Step 3 one **spaghetti-check** — AST **N=4230**, **L₅₀=263**, **L₁₀₀=71**, **D₆=0**; builtins grep; runtime grep; `ds005` exit **0**. Trigger met (**M7 ≈ 25.4% ≥ 19%**); filled scan, **DS-001..005**, workstream map, phase table. | — | — | — | — |

**New rows:** chronologically (**newest first** recommended); **DS-ID(s)**, gates/tests run, pre/post paths as in [`EXECUTION_GOVERNANCE.md`](../state/EXECUTION_GOVERNANCE.md); for scan/docs-only updates note briefly. Longer history: Git, PRs, `WORKSTREAM_*_STATE.md`.

## Canonical technical reading paths (after refactor)

After structural changes to runtime/AI/RAG/MCP, align **active** technical docs (not the 2026 archive):

- Runtime / authority: [`docs/technical/runtime/runtime-authority-and-state-flow.md`](../../docs/technical/runtime/runtime-authority-and-state-flow.md) — supervisor orchestration: `supervisor_orchestrate_execute.py` + `supervisor_orchestrate_execute_sections.py`; subagent invocation: `supervisor_invoke_agent.py` + `supervisor_invoke_agent_sections.py`
- Inspector projection (backend): `inspector_turn_projection_sections.py` orchestrates; pieces in `inspector_turn_projection_sections_{utils,constants,semantic,provenance}.py`
- Admin tool routes: `administration-tool/route_registration.py` + `route_registration_{proxy,pages,manage,security}.py`
- God-of-Carnage solo builtin (core): `story_runtime_core/goc_solo_builtin_template.py` + `goc_solo_builtin_catalog.py` + `goc_solo_builtin_roles_rooms.py`
- AI / RAG / LangGraph: [`docs/technical/ai/RAG.md`](../../docs/technical/ai/RAG.md), [`docs/technical/integration/LangGraph.md`](../../docs/technical/integration/LangGraph.md), [`docs/technical/integration/MCP.md`](../../docs/technical/integration/MCP.md)
- Dev seam overview: [`docs/dev/architecture/ai-stack-rag-langgraph-and-goc-seams.md`](../../docs/dev/architecture/ai-stack-rag-langgraph-and-goc-seams.md)

---

*Created as an operational bridge between structural code work, the state hub under [`despaghettify/state/`](../state/README.md) (pre/post evidence), and the completed documentation archive of 2026.*
