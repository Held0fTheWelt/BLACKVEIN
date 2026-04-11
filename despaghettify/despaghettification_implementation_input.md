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
| DS-004 | `backend_runtime_services` | — |
| DS-005 | `backend_runtime_services` | — |
| DS-006 | `backend_runtime_services` | — |
| DS-007 | `backend_runtime_services` | — |
| DS-008 | `backend_runtime_services` | — |
| DS-009 | `ai_stack` | `backend_runtime_services` |

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
| **§ Latest structure scan** | After measurable change: **main table** (as-of date, **M7** overall, 7 category scores, and AST telemetry **N / L₅₀ / L₁₀₀ / D₆**); subsection **M7 calculation and thresholds**; optional **extra checks**; **open hotspots** on every [spaghetti-check-task.md](../spaghetti-check-task.md) run (**prune** solved items). For runtime edges `tools/ds005_runtime_import_check.py`. Rankings: script output only. |
| **§ Recommended implementation order** | Update when priority, dependency, or phase changes; optional Mermaid. |
| **§ Progress / work log** | Optional **one** new row: DS-ID(s), short summary, gates/tests, pre/post paths (or “see PR”). |
| **DS-ID → workstream table** | Place new or moved **DS-*** here; note co-involved workstreams. |

**Governance:** `despaghettify/state/artifacts/workstreams/<slug>/pre|post/` and `WORKSTREAM_*_STATE.md` remain **formal** evidence; this file is the **compact** working and review map.

## Latest structure scan (orientation, no warranty)

**Purpose:** A **fillable** overview after measurable runs — after larger refactors update **date**, **M7 inputs**, and optional **extra checks** / **open hotspots**. Measurement flow, builtins grep, runtime spot check: [spaghetti-check-task.md](../spaghetti-check-task.md). The spaghetti check maintains the **information input list** and **recommended implementation order** when the **trigger policy** in § *Trigger policy for check task updates* fires (per-category thresholds **or** **`M7 ≥ M7_ref`**); otherwise this scan section (including M7 and category breakdown) is enough. **Rankings** and longest functions: output of `python tools/spaghetti_ast_scan.py` only (repo root). **Open hotspots:** [spaghetti-solve-task.md](../spaghetti-solve-task.md) clears or narrows items when waves resolve them; on every spaghetti-check run, **prune** so solved items are not listed.

| Field | Value (adjust when updating scan) |
|-------|-------------------------------------|
| **As of (date)** | **2026-04-12** (DS-006/007/008 closed) |
| Spaghetti scan command | `python tools/spaghetti_ast_scan.py` (ROOTS = *measurement scope* column) |
| Measurement scope (ROOTS) | `backend/app`, `world-engine/app`, `ai_stack`, `story_runtime_core`, `tools/mcp_server`, `administration-tool` |
| **M7** — weighted 7-category spaghetti score | **33%** (heuristic; trigger **met** — several **C** above per-category bars **and** **`M7 ≥ M7_ref` (19%)**; see § *Trigger policy*) |
| C1: Circular dependencies | **20%** |
| C2: Nesting depth | **12%** |
| C3: Long functions + complexity | **52%** |
| C4: Multi-responsibility modules | **44%** |
| C5: Magic numbers + global state | **24%** |
| C6: Missing abstractions / duplication | **32%** |
| C7: Confusing control flow | **38%** |
| **AST telemetry N / L₅₀ / L₁₀₀ / D₆** | **4230** / **263** / **71** / **0** |
| Extra check builtins | `def build_god_of_carnage_solo`: **1** hit (`story_runtime_core/goc_solo_builtin_template.py`); **0** in `**/builtins.py` — **2026-04-13** |
| Extra check runtime | `python tools/ds005_runtime_import_check.py` — **exit 0** (all `import_ok`). Spot grep: a few “avoid circular” local-import comments under `backend/app/runtime`; **no** `TYPE_CHECKING` matches there |
| **Open hotspots** | Remaining targets after DS-006/007/008 closure: Writers Room generation stage (~160L), closure cockpit report assembly (~182L), evidence session bundle (~167L) — deferred to DS-009. `execute_users_update_put` candidate for future optimization. AI stack: `evaluate_dramatic_effect_gate` (~146L) for DS-009. `ds005` clean; GoC solo builtin single canonical definition. |

### Score *M7* — inputs, weights, and calculation

| Symbol | Meaning | Value |
|--------|---------|-------|
| **C1** | Circular dependencies | **20** |
| **C2** | Nesting depth | **12** |
| **C3** | Long functions + complexity | **52** |
| **C4** | Multi-responsibility modules | **44** |
| **C5** | Magic numbers + global state | **24** |
| **C6** | Missing abstractions / duplication | **32** |
| **C7** | Confusing control flow | **38** |

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
| DS-001 | **(CLOSED 2026-04-11)** Turn executor import decoupling | `turn_executor_validated_pipeline.py`; circular imports in turn executor test patches | Import coupling + testing isolation | Remove `turn_executor` import from `turn_executor_validated_pipeline`; tests patch instead ✓ DONE | High: turn path coupling |
| DS-002 | **(CLOSED 2026-04-11)** Writers Room pipeline monolith | Writers Room stages 1–5 refactoring (~585→82 AST LOC main workflow) | Multi-stage orchestration density | Stage-by-stage extraction + helper deduplication ✓ DONE | High: 64 writers room tests |
| DS-003 | **(CLOSED 2026-04-10)** AI stack RAG despaghettification | RAG module (1973→175 LOC) | Extraction + modularization | Helper consolidation + context pack assembly ✓ DONE | Medium: AI stack test bundles |
| DS-004 | **(CLOSED 2026-04-11)** Magic numbers + mutable state | 500–800 literals across routes + extensions.py mutable globals | Constants extraction + state hardening | Config modules (route_constants.py, limiter_config.py) + 24 route files refactored ✓ DONE | High: route handler tests |
| DS-005 | **(CLOSED 2026-04-11)** User/news control-flow guards | `user_service`, `news_service`, routes (6 stages) | Guard extraction + policy validation | Service guard modules + route guards ✓ DONE | High: 321 integration tests |
| DS-006 | **(CLOSED 2026-04-12)** Writers Room packaging + inspector | `writers_room_pipeline_packaging_stage.py` (354→317L), `inspector_turn_projection_sections_assembly_filled.py` (248→157L) | Sub-stage + helper extraction | 2 packaging sub-stages + 16 inspector helpers ✓ DONE | High: 79 tests (64+15) |
| DS-007 | **(CLOSED 2026-04-12)** Runtime narrative DTO integration | `narrative_threads_update_from_commit.py`, `turn_executor_validated_pipeline.py` | DTO extraction + pipeline refactoring | Narrative state transfer DTOs + pipeline guards ✓ DONE | High: runtime narrative layer |
| DS-008 | **(CLOSED 2026-04-12)** Improvement recommendation decision | `improvement_service_recommendation_decision.py` (176→136L) | Policy guard + builder extraction | 3 guards + 3 builders in policy_evaluators module ✓ DONE | Medium: 60 improvement tests |
| DS-009 | **(PLANNED)** RAG context-pack + closure bundles | `rag_context_pack_*`, closure cockpit (~182L), evidence bundle (~167L) | Sub-stage extraction + helper consolidation | World engine bridge + G9/G9B/G10 extraction | Medium: ai_stack + backend tests |

**New rows:** consecutive **DS-001**, **DS-002**, … (or your ID scheme); briefly justify why it is a structure/spaghetti topic. Per § *DS-ID → primary workstream* pick `artifacts/workstreams/<slug>/pre|post/` paths.

## Recommended implementation order

Prioritised **phases**, **order**, and **dependencies** — aligned with § **information input list** and [`EXECUTION_GOVERNANCE.md`](../state/EXECUTION_GOVERNANCE.md). After filling: optional subsections per phase, Mermaid `flowchart`, gates per wave, short priority list.

| Priority / phase | DS-ID(s) | short logic | workstream (primary) | note (dependencies, gates) |
|------------------|----------|-------------|----------------------|----------------------------|
| Phase 1 | DS-002 | Stabilise runtime narrative + validated-pipeline seams before deeper service moves | `backend_runtime_services` | `ds005` + targeted `pytest` under `backend/tests` for runtime/turn |
| Phase 2 | DS-001 | Shrink largest backend orchestration (Writers Room, closure bundles, inspector projections) | `backend_runtime_services` | Incremental stage extractions; Writers Room tests as gate |
| Phase 3 | DS-003 | Flatten user-update PUT handler branches | `backend_runtime_services` | Route + handler tests |
| Phase 4 | DS-004 | Trim long ai_stack evaluation/integration callables | `ai_stack` | Run `ai_stack` pytest slices after each change |

**Fill in:** take rows from the input table; make hard chains explicit (e.g. interfaces before large moves). Coordination § *Maintaining this file*: when priority changes or new **DS-*** appear, update this section and Mermaid if used.

**Implementation** of phases until documented closure (completion gate, session by session): [spaghetti-solve-task.md](../spaghetti-solve-task.md).

## Progress / work log (optional, in addition to mandatory maintenance above)

Implementers may **briefly** record visible progress (for reviewers and the next iteration). **Mandatory** for structural waves remains **updating the input table, § structure scan, and — if needed — this log** (see coordination § *Maintaining this file*). **Additionally**, new waves add **pre/post files** under `despaghettify/state/artifacts/…` (see `EXECUTION_GOVERNANCE.md`); older session artefacts may be missing if intentionally cleaned — proof then via Git/CI/PR. Not a substitute for issues/PRs.

| date | ID(s) | short description | pre artefacts (rel. to `despaghettify/state/`) | post artefacts (rel. to `despaghettify/state/`) | state doc(s) updated | PR / commit |
|------|-------|-------------------|----------------------------------------|----------------------------------------|----------------------|-------------|
| 2026-04-13 | — | **Spaghetti-reset-task:** ephemeral dirs cleaned per reset doc; `despaghettification_implementation_input.md` reset from `templates/…EMPTY.md`; **spaghetti-check** once — AST (N=4230, L₅₀=263, L₁₀₀=71, D₆=0), builtins grep, runtime grep, `ds005` exit 0. Trigger (per policy then in § *Trigger policy*) → § *Latest structure scan*, **DS-001..004**, § *Recommended implementation order*, **DS-ID → workstream** table. | — | — | — | — |
| — | — | — | — | — | — | — |

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
