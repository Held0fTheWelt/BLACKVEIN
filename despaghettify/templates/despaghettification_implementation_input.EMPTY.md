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
| — | — | — |

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
| **As of (date & time)** | **—** *(required on every scan: `YYYY-MM-DD HH:mm:ss`; optional `(IANA or UTC)`)* |
| Spaghetti scan command | `python tools/spaghetti_ast_scan.py` (ROOTS = *measurement scope* column) |
| Measurement scope (ROOTS) | `backend/app`, `world-engine/app`, `ai_stack`, `story_runtime_core`, `tools/mcp_server`, `administration-tool` |
| **M7** — weighted 7-category spaghetti score | **—** |
| C1: Circular dependencies | **—** |
| C2: Nesting depth | **—** |
| C3: Long functions + complexity | **—** |
| C4: Multi-responsibility modules | **—** |
| C5: Magic numbers + global state | **—** |
| C6: Missing abstractions / duplication | **—** |
| C7: Confusing control flow | **—** |
| **AST telemetry N / L₅₀ / L₁₀₀ / D₆** | **—** / **—** / **—** / **—** |
| Extra check builtins | *optional:* grep as in task doc — **hit count** and **date**, else **—** |
| Extra check runtime | *optional:* `python tools/ds005_runtime_import_check.py` — **exit code**; if odd, **short** note (e.g. `TYPE_CHECKING`, lazy imports), else **—** |
| **Open hotspots** | **—** (after reset: fill on first [spaghetti-check-task.md](../spaghetti-check-task.md) pass; never list solved items) |

### Score *M7* — inputs, weights, and calculation

| Symbol | Meaning | Value |
|--------|---------|-------|
| **C1** | Circular dependencies | **—** |
| **C2** | Nesting depth | **—** |
| **C3** | Long functions + complexity | **—** |
| **C4** | Multi-responsibility modules | **—** |
| **C5** | Magic numbers + global state | **—** |
| **C6** | Missing abstractions / duplication | **—** |
| **C7** | Confusing control flow | **—** |

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
| — | — | — | — | — | — |

**New rows:** consecutive **DS-001**, **DS-002**, … (or your ID scheme); briefly justify why it is a structure/spaghetti topic. Per § *DS-ID → primary workstream* pick `artifacts/workstreams/<slug>/pre|post/` paths.

## Recommended implementation order

Prioritised **phases**, **order**, and **dependencies** — aligned with § **information input list** and [`EXECUTION_GOVERNANCE.md`](../state/EXECUTION_GOVERNANCE.md). After filling: optional subsections per phase, Mermaid `flowchart`, gates per wave, short priority list.

| Priority / phase | DS-ID(s) | short logic | workstream (primary) | note (dependencies, gates) |
|------------------|----------|-------------|----------------------|----------------------------|
| — | — | — | — | — |

**Fill in:** one phase row per open **DS-*** (or an explicit merge noted in **note**). Order by **risk**: stabilise **runtime / import seams** (`backend_runtime_services` under `app.runtime`, `ds005`-touched paths) before very large **service orchestration** waves; **`ai_stack`**-only (or other packages) typically **later** unless the scan shows a hard blocker. **Workstream (primary)** must match [WORKSTREAM_INDEX.md](../state/WORKSTREAM_INDEX.md) for pre/post paths. **note** column: concrete **gates** (`pytest …`, `ds005`). Full rules: [spaghetti-check-task.md](../spaghetti-check-task.md) § *Maintaining the input list* → **Recommended implementation order** → *How to build a suitable phase table*. Coordination § *Maintaining this file*: when priority changes or new **DS-*** appear, update this section and Mermaid if used.

**Implementation** of phases until documented closure (completion gate, session by session): [spaghetti-solve-task.md](../spaghetti-solve-task.md).

## Progress / work log (optional, in addition to mandatory maintenance above)

Implementers may **briefly** record visible progress (for reviewers and the next iteration). **Mandatory** for structural waves remains **updating the input table, § structure scan, and — if needed — this log** (see coordination § *Maintaining this file*). **Additionally**, new waves add **pre/post files** under `despaghettify/state/artifacts/…` (see `EXECUTION_GOVERNANCE.md`); older session artefacts may be missing if intentionally cleaned — proof then via Git/CI/PR. Not a substitute for issues/PRs.

| date | ID(s) | short description | pre artefacts (rel. to `despaghettify/state/`) | post artefacts (rel. to `despaghettify/state/`) | state doc(s) updated | PR / commit |
|------|-------|-------------------|----------------------------------------|----------------------------------------|----------------------|-------------|
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
