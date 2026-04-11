# Task 1B — Cross-Stack Cohesion, Ownership, and GoC Dependency Baseline

**Standalone control document.** Downstream tasks **must** treat **this file** as the authoritative Task 1B baseline. **No** chat transcript, plan UI, or external message may substitute for the sections below.

**Template note:** The original Task 1B specification used eleven top-level sections. This document **adds §9 (Staleness and re-validation trigger)** so the baseline cannot silently rot; former §9–§11 are **§10–§12**.

**Scope:** Planning and baseline only. This document does **not** assert that structural risks are resolved, does **not** perform cleanup, and does **not** replace implementation or test work.

**Baseline input:** [TASK_1A_REPOSITORY_BASELINE.md](TASK_1A_REPOSITORY_BASELINE.md) (Task 1A v4 inventory, path taxonomy, mirror policy, `X1` canonical surface exception).

---

## 1. Executive judgment

Higher-risk structural cleanup remains **controllable as a bounded sequence** **if** GoC relocation and cross-stack closure are **gated** on dependency sufficiency (§6), explicit producer/consumer seam inspection (§5.6), and the decision rules in §8—including the rule that **passing tests do not prove cross-stack cohesion** (§8, standalone item).

Without those gates, **silent breakage** is likely because the same logical artifact (module identity, narrative truth, templates, retrieval lanes) is touched from **backend**, **world-engine**, **ai_stack** (LangChain/LangGraph/RAG), **writers-room**, **MCP tools**, **schemas**, **fixtures**, and **normative docs**. The work is bounded by stack boundaries listed in §2 and §5, not by test greenness.

---

## 2. Repository access verification

**Confirmed:** Inspection used workspace listing, targeted reads, `rg` counts for `god_of_carnage`, and directory listing of `content/modules/god_of_carnage/`. Refresh aligned with Task 1A snapshot (2026-04-09 era).

**Observed top-level names (representative; live tree may include local-only entries such as `.venv`):** `.github`, `.gitignore`, `administration-tool`, `ai_stack`, `audits`, `backend`, `content`, `database`, `data-tool`, `docker`, `docs`, `frontend`, `outgoing`, `postman`, `promo`, `resources`, `schemas`, `scripts`, `story_runtime_core`, `tests`, `tools`, `world-engine`, `writers-room`, plus root metadata (`README.md`, `docker-compose.yml`, `CHANGELOG.md`, etc.).

**Primary directories/files inspected for Task 1B:**

| Area | Paths |
|------|--------|
| Task 1A baseline | `docs/audit/TASK_1A_REPOSITORY_BASELINE.md` |
| Authority / contracts | `docs/architecture/runtime_authority_decision.md`, `docs/CANONICAL_TURN_CONTRACT_GOC.md`, `docs/VERTICAL_SLICE_CONTRACT_GOC.md` |
| Canonical GoC module (tracked) | `content/modules/god_of_carnage/*` (11 files: `module.yaml`, `characters.yaml`, `scenes.yaml`, `triggers.yaml`, `transitions.yaml`, `endings.yaml`, `relationships.yaml`, `escalation_axes.yaml`, `direction/*`) |
| Backend module pipeline | `backend/app/content/module_service.py`, `backend/app/content/module_loader.py` |
| AI / RAG / GoC coupling | `ai_stack/goc_yaml_authority.py`, `ai_stack/goc_frozen_vocab.py`, `ai_stack/goc_gate_evaluation.py`, `ai_stack/rag.py`, `ai_stack/tests/test_goc_*.py`, `ai_stack/tests/test_langgraph_runtime.py`, `ai_stack/tests/test_langchain_integration.py`, `ai_stack/tests/test_rag.py` |
| World-engine runtime | `world-engine/app/story_runtime/manager.py`, `world-engine/app/content/builtins.py`, `world-engine/tests/test_http_api_extended.py`, `world-engine/tests/test_canonical_runtime_contract.py` |
| Writers-room | `writers-room/app/models/implementations/god_of_carnage/`, `writers-room/app/models/markdown/_registry/prompt_registry.yaml`, `writers-room/app/models/markdown/_presets/god_of_carnage_*.md` |
| MCP | `tools/mcp_server/fs_tools.py`, `tools/mcp_server/config.py`, `tools/mcp_server/tests/test_fs_tools.py`, `tools/mcp_server/tests/test_tools_handlers.py`, `tools/mcp_server/tests/test_backend_client.py` |
| Schemas | `schemas/content_module.schema.json`, `schemas/session_state.schema.json`, `schemas/ai_story_output.schema.json` |
| Shared core | `story_runtime_core/` (spot-check: no literal `god_of_carnage` in `.py`—integration is via world-engine imports) |
| Admin / frontend / compose | `docker-compose.yml`, `administration-tool/` (routing surface only—no deep GoC code pass), `frontend/tests/test_routes*.py` (template id references) |
| Cross-stack tests (sample) | `backend/tests/content/test_god_of_carnage.py`, `backend/tests/runtime/conftest.py`, `backend/tests/runtime/test_*` (GoC fixtures), `tests/smoke/test_goc_module_structure_smoke.py`, `tests/goc_gates/` |

**Gitignored material:** Per Task 1A, paths such as `_tmp_goc_dbg/`, most of `tests/reports/`, local venvs, etc. are **out of scope** unless a **tracked** file depends on them (Task 1A flags `H_tracked_gitignored_pointer` for evidence paths).

---

## 3. Current-state deep-baseline summary

- **GoC structural risk:** Module identity `god_of_carnage` and the directory `content/modules/god_of_carnage/` are **hard-coupled** in code (`ai_stack/goc_frozen_vocab.py` `GOC_MODULE_ID`, `ai_stack/goc_yaml_authority.py` path builder) and **soft-coupled** across tests, MCP handlers, RAG path heuristics, world-engine builtins (`god_of_carnage_solo`), and writers-room registry IDs. Relocation without a completed dependency map is a **P0** failure mode.

- **Cross-stack cohesion hotspots:** World-engine imports `story_runtime_core` **and** `ai_stack` for turn execution and retrieval (`world-engine/app/story_runtime/manager.py`). Backend owns module load/validate from `content/modules` (`backend/app/content/module_service.py`). RAG distinguishes `content/modules/` vs `content/published/` substring semantics (`ai_stack/rag.py`). These stacks **compose** but **authority** (who may commit truth, who serves runtime) must be checked per seam, not inferred from CI.

- **Ownership ambiguity:** Parallel narrative surfaces—**canonical YAML module** under `content/modules/god_of_carnage/` vs **writers-room** markdown/yaml under `writers-room/app/models/implementations/god_of_carnage/` and registry entries—create **duplicate-truth** risk for prompts, scene copy, and operator mental models.

- **Duplicate-truth hotspots:** `outgoing/` vs `docs/g9_evaluator_b_external_package/` (Task 1A Appendix C policy); `docs/reports/` vs sparse `tests/reports/*.md` vs gitignored evidence trees; root `world-engine/` vs `backend/world-engine/` naming collision (Task 1A Appendix D).

- **Declared-vs-actual workflow seams:** Docs declare world-engine as authoritative runtime host and backend as publishing/governance (`docs/architecture/runtime_authority_decision.md`); backend still hosts transitional paths and admin/session APIs that must align with compose wiring (`docker-compose.yml` `PLAY_SERVICE_*` variables). Publishing flow (draft vs published retrieval lanes) is normative in RAG docs and **path-based** in `ai_stack/rag.py`.

- **Contract-alignment hotspots:** `docs/CANONICAL_TURN_CONTRACT_GOC.md` and `docs/VERTICAL_SLICE_CONTRACT_GOC.md` bind semantics for seams, validation, and slice YAML; `ai_stack/goc_yaml_authority.py` explicitly cites `VERTICAL_SLICE_CONTRACT_GOC.md` §6.1. Alignment must be verified **per seam** against producer and consumer code, not assumed from document tone.

- **Authority-boundary ambiguity:** AI output non-authoritative vs runtime commit authority is stated in `runtime_authority_decision.md`; the **exact** handoff points (commit models, supervisor, preview vs commit) require code-level mapping in later tasks—this baseline **does not** complete that mapping.

- **Integration ambiguity:** MCP discovers repo root via `content/` (`tools/mcp_server/config.py`) and lists modules from `content/modules/` (`tools/mcp_server/fs_tools.py`); runtime sessions may be created via backend client tests with `module_id="god_of_carnage"`. **Tool**, **API**, and **filesystem** views can diverge if mounts or roots differ (e.g. container vs host).

**Summary posture:** P2 and long-tail file references across `docs/archive/superpowers-legacy-execution-2026/plans/*` (formerly `docs/superpowers/plans/*`), `promo/`, `postman/`, and per-feature admin templates are **not** exhaustively inventoried here; they are summarized to preserve depth for P0/P1.

---

## 4. Deep classification framework

### 4.1 Drift classes (required definitions)

| Class | Definition |
|-------|------------|
| **Responsibility drift** | Docs, code, or ops assume different owning roles for the same concern (e.g. who validates a module, who commits narrative state). |
| **Contract drift** | Producer and consumer disagree on fields, lifecycles, or invariants (schemas, API payloads, seam outputs). |
| **Flow drift** | Documented workflow order or handoff differs from what runtime, jobs, or UIs actually execute. |
| **Ownership drift** | Same artifact class has two maintainable locations without a single declared winner (authoring vs canonical tree). |
| **Abstraction drift** | Shared concepts (module_id, template_id, scene_id) map inconsistently across layers. |
| **Integration drift** | Boundaries between services (HTTP, internal keys, env URLs) disagree across compose, tests, and docs. |
| **Documentation drift** | Normative docs cite paths, gates, or evidence that tracked code or clone layout does not guarantee. |
| **Placement drift** | Files live under misleading roots (`backend/world-engine/` vs `world-engine/`), causing wrong edits or imports. |

### 4.2 GoC dependency risk classes

| Class | Meaning |
|-------|--------|
| **ID_literal** | Hard-coded `god_of_carnage` / `god_of_carnage_solo` strings in code, tests, or config. |
| **Path_filesystem** | Repo-relative paths assuming `content/modules/<id>/` or `content/published/<id>/`. |
| **Registry_prompt** | Writers-room `prompt_registry.yaml` and preset markdown paths. |
| **Schema_contract** | JSON schema examples and validators keyed to module shape. |
| **RAG_lane** | Retrieval ranking, suppression, and observability keyed on path substrings and `module_id`. |
| **Runtime_graph** | LangGraph / executor / capability registry wiring in `ai_stack` consumed by world-engine. |
| **MCP_tool** | Filesystem tools and handlers exposing module paths to agents. |
| **Normative_doc** | Contracts and gate baselines that constrain behavior without automatic code linkage. |
| **Fixture_frozen** | Tests, outgoing JSON, evaluator bundles pinning scenarios or vocab. |

### 4.3 Authority-boundary ambiguity classes

| Class | Meaning |
|-------|--------|
| **Commit_vs_preview** | Unclear which layer may surface text to players vs durable state. |
| **Authoring_vs_canonical** | Writers-room content vs `content/modules` as source for runtime. |
| **Service_host** | Which process owns session lifecycle vs which proxies it (`docker-compose.yml` vs local dev). |
| **Tool_vs_API** | MCP or scripts bypassing backend/world-engine invariants. |
| **Transitional_shim** | Deprecated path still reachable; authority unclear until removal. |

---

## 5. Prioritized deep-baseline inventories

**Tie-break after P0:** (1) downstream-task risk → (2) authority/ownership ambiguity → (3) silent producer/consumer breakage likelihood → (4) active-surface visibility → (5) breadth → (6) alphabetical path.

### 5.1 GoC-related paths and dependencies

**P0 dependency classes (all listed) — concrete inspected surfaces**

| P0 class | Inspected paths / surfaces |
|----------|----------------------------|
| ID_literal | `ai_stack/goc_frozen_vocab.py` (`GOC_MODULE_ID`); widespread `god_of_carnage` in `backend/tests/`, `world-engine/tests/`, `ai_stack/tests/`, `tools/mcp_server/tests/` |
| Path_filesystem | `ai_stack/goc_yaml_authority.py` → `content/modules/god_of_carnage/`; `backend/app/content/module_service.py` / `module_loader.py` (`content_modules_root()`); `ai_stack/rag.py` `_MODULE_PATH` / `_PUBLISHED_MODULE_PATH` |
| Registry_prompt | `writers-room/app/models/markdown/_registry/prompt_registry.yaml` (`implementation.god_of_carnage.*`); `writers-room/app/models/markdown/_presets/god_of_carnage_*.md` |
| Schema_contract | `schemas/content_module.schema.json` (documents `god_of_carnage` example) |
| RAG_lane | `ai_stack/rag.py` published vs modules lane logic and `module_id` filters |
| Runtime_graph | `world-engine/app/story_runtime/manager.py` (`RuntimeTurnGraphExecutor`, `build_runtime_retriever`); `ai_stack` LangGraph/runtime tests |
| MCP_tool | `tools/mcp_server/fs_tools.py`, `tools/mcp_server/config.py` |
| Normative_doc | `docs/CANONICAL_TURN_CONTRACT_GOC.md`, `docs/VERTICAL_SLICE_CONTRACT_GOC.md`, `docs/GATE_SCORING_POLICY_GOC.md` |
| Fixture_frozen | `tests/goc_gates/*`, `docs/goc_evidence_templates/*`, `outgoing/**/frozen_scenarios/*goc*.json` (sample inspected) |

**Representative P0 rows (detail)**

| GoC surface | Dependency class | Consumer / assumption | Break under rename | Pri | Downstream |
|-------------|------------------|---------------------|-------------------|-----|------------|
| `content/modules/god_of_carnage/` | Path_filesystem | `goc_yaml_authority`, `ModuleService`, RAG path regex | Loaders and RAG lanes miss module | P0 | GoC normalization |
| `GOC_MODULE_ID` | ID_literal | Gates, YAML authority, tests | String mismatch across stacks | P0 | Same |
| `god_of_carnage_solo` template | ID_literal + abstraction drift | `world-engine/app/content/builtins.py`, HTTP tests | Session start selects wrong template | P0 | Template/module alignment |
| `prompt_registry.yaml` entries | Registry_prompt | Writers-room assembly | Broken prompt paths | P0 | Ownership consolidation |
| `ai_stack/rag.py` path heuristics | RAG_lane | Retrieval suppression / observability | Wrong lane, silent retrieval change | P0 | RAG governance closure |

**P1 dependencies (≤10 listed in full — set is larger; remainder summarized)**

| Surface | Class | Consumer | Risk | Pri |
|---------|-------|----------|------|-----|
| `frontend/tests/test_routes*.py` | ID_literal | UI routing assumptions | Wrong default experience | P1 |
| `backend/app/models/game_experience_template.py` | abstraction drift | DB/API templates vs builtins | Template parity drift | P1 |
| `postman/*.md` + collections | documentation drift | Operators | Wrong endpoints | P1 |
| `scripts/g9_level_a_evidence_capture.py` | Fixture_frozen | Evidence automation | Path assumptions | P1 |
| `database/tests/test_database_game_and_misc_models.py` | ID_literal | Persistence models | Data test breakage | P1 |

**Summary posture:** Remaining `god_of_carnage` occurrences in `docs/archive/superpowers-legacy-execution-2026/plans/*`, `docs/audit/gate_*.md`, and long-tail tests are **P1/P2** by file; full enumeration deferred to dependency-matrix tooling—not required for P0 sufficiency **if** every **P0 class** above is mapped before moves.

### 5.2 Cross-stack cohesion hotspots

| Surface | Drift | Reason | Pri | Downstream |
|---------|-------|--------|-----|------------|
| `world-engine/app/story_runtime/manager.py` ↔ `ai_stack` | integration + contract | Single runtime session pulls retriever, graph executor, adapters | Silent AI/runtime mismatch | P0 | Seam audit |
| `backend/app/content/*` ↔ `content/modules` | flow + responsibility | Publishing/validation vs runtime consumption | Wrong module version served | P0 | Publishing closure |
| `ai_stack/rag.py` ↔ `content/published` tree | flow + contract | Path substring semantics | Retrieval governance violations | P0 | RAG vs content layout |
| `story_runtime_core` ↔ consumers | abstraction | Shared interpreter/registry without GoC literals | Behavior drift on change | P1 | Core API stability |

### 5.3 Ownership ambiguity hotspots

| Surface | Drift | Reason | Pri | Downstream |
|---------|-------|--------|-----|------------|
| `content/modules/god_of_carnage/` vs `writers-room/.../god_of_carnage/` | ownership | Two authoring-shaped trees | Contradictory edits | P0 | Single owner definition |
| `outgoing/` vs `docs/g9_evaluator_b_external_package/` | documentation + ownership | Mirror policy (Task 1A C) | Stale handoff | P1 | Mirror discipline |

### 5.4 Duplicate-truth hotspots

| Surface | Drift | Reason | Pri | Downstream |
|---------|-------|--------|-----|------------|
| World-engine builtins title vs `module.yaml` | contract | `builtins.py` comments cite canonical YAML (`world-engine/app/content/builtins.py`) | Template vs module divergence | P0 | Parity checks |
| Gate evidence paths vs `.gitignore` | documentation | Task 1A Appendix B | Clone lacks evidence | P0 | Evidence policy |
| `README.md` vs deep contracts | documentation | Onboarding vs normative slice docs | Wrong precedence | P1 | Doc precedence box |

### 5.5 Declared-vs-actual workflow seams

*Material seam definition:* boundary affecting authority handoff, payload agreement, publishing/runtime consumption, module ownership, orchestration, tool invocation, admin/writer/runtime handoff, AI/runtime decision boundary, or lifecycle expectations for later cleanup.

| Workflow | Declared surface | Actual / apparent surface | Seam summary | Why material | Pri | Downstream |
|----------|------------------|---------------------------|--------------|--------------|-----|------------|
| Live play session | `docs/architecture/runtime_authority_decision.md` (world-engine host) | `docker-compose.yml` backend↔play-service wiring + `world-engine/app/story_runtime/manager.py` | Runtime lives in play-service container; backend depends on it | Wrong URL/key breaks authority assumption | P0 | Deploy + integration audit |
| Module load for governance | Backend content services | `backend/app/content/module_loader.py` filesystem read | Filesystem is source for validation APIs | Bypass breaks review guarantees | P0 | Admin/publish flows |
| Retrieval for turns | RAG governance docs | `ai_stack/rag.py` + `build_runtime_retriever` in world-engine | Retrieval assembled inside runtime graph | Lane bugs change AI context silently | P0 | RAG closure |
| Authoring assistance | Writers-room prompts | `prompt_registry.yaml` paths | Prompts not automatically canonical YAML | Drift between author UI and module | P1 | Ownership |
| MCP-assisted editing | MCP docs / tool inventory | `tools/mcp_server/fs_tools.py` lists `content/modules` | Agents see FS module list | May skip backend validation | P1 | MCP governance |
| External evaluator handoff | `outgoing/` canonical | `docs/g9_evaluator_b_external_package/` mirror | Two trees must move together | Stale instructions | P1 | Mirror commits |

**Summary posture:** Additional seams (e.g. LangSmith/trace, improvement loop JSON under `backend/fixtures/improvement_experiment_runs/`) exist; listed rows cover the densest cross-stack GoC/runtime surfaces for this pass.

### 5.6 Contract-alignment hotspots

| Surface | Drift | Reason | Pri | Downstream |
|---------|-------|--------|-----|------------|
| `docs/CANONICAL_TURN_CONTRACT_GOC.md` seams vs `ai_stack`/`world-engine` producers | contract | Normative table vs code entrypoints | False closure claims | P0 | Producer/consumer matrix |
| `docs/VERTICAL_SLICE_CONTRACT_GOC.md` §6 vs `goc_yaml_authority.py` | contract | Explicit doc reference in code | Doc/code skew breaks gates | P0 | Slice verification |
| `schemas/*.schema.json` vs `backend`/`content` validators | contract | Multiple validation layers | Inconsistent module shape acceptance | P1 | Schema ownership |

### 5.7 Authority-boundary ambiguity hotspots

| Surface | Drift | Reason | Pri | Downstream |
|---------|-------|--------|-----|------------|
| Commit vs preview (GoC) | commit_vs_preview | Contract doc claims vs runtime modules (`app/story_runtime/commit_models.py` referenced in audits—not re-proven here) | Player-visible vs durable mismatch | P0 | Turn contract completion |
| AI proposal vs runtime authority | authority | `runtime_authority_decision.md` | Model output treated as canon by mistake | P0 | Safety/governance |
| Transitional backend runtime paths | transitional_shim | Same decision doc | Duplicate execution paths | P1 | Deprecation closure |

---

## 6. GoC dependency sufficiency requirements

**Why relocation is high risk:** Consumers span **filesystem paths**, **string IDs**, **regex-based RAG routing**, **template IDs**, **registry YAML**, **frozen JSON**, **MCP listings**, and **normative contracts**. A partial rename updates one layer and leaves stale references in another—often **green tests** if suites mock paths or skip integration.

**Classes that must be mapped before any move:** Every **P0 class** in §5.1 (ID_literal, Path_filesystem, Registry_prompt, Schema_contract, RAG_lane, Runtime_graph, MCP_tool, Normative_doc, Fixture_frozen).

**What must be checked:** Codepaths (`ai_stack`, `backend/app/content`, `world-engine/app`, `writers-room`, `tools/mcp_server`), **configs** (`docker-compose.yml`, MCP config), **tests** (all packages + `tests/smoke` + `tests/goc_gates`), **docs** (contracts, gate baselines, RAG task docs), **scripts** (`scripts/`), **loaders/registries** (`module_loader`, `prompt_registry.yaml`, `builtins.py`), **tooling** (MCP repo root discovery, CI workflows under `.github/workflows`).

**Sufficient mapping means:** For each P0 class, a **closed list** of tracked references (or an automated inventory with human sign-off), **consumer named**, and **failure mode** if path/ID changes—plus explicit handling for **published** vs **modules** trees.

**Later GoC work must refuse to:** rename directories, change `module_id`, or renamespace registry IDs **until** sufficiency is recorded and reviewed; must refuse **cohesion-closure** claims based solely on test passes (§8).

---

## 7. Critical source-of-truth and authority-boundary map

*Max three sentences per surface. File paths cite **tracked** evidence where behavior is asserted.*

- **GoC canonical YAML module (`content/modules/god_of_carnage/`):** Apparent runtime/governance truth for structured module data; primary consumers include `backend/app/content/module_service.py`, `ai_stack/goc_yaml_authority.py`, and RAG ingestion paths in `ai_stack/rag.py`. Authority boundary: authoring must converge here for machine-readable canon; ambiguity risk is parallel writers-room markdown drifting from YAML.

- **Writers-room implementations (`writers-room/app/models/implementations/god_of_carnage/` + registry):** Apparent authoring-side prompt and narrative asset store; consumers are writers-room services and operators. Boundary vs `content/modules` is **unclear** without an explicit promotion rule in tracked docs tied to automation.

- **World-engine builtins (`world-engine/app/content/builtins.py`):** Declares `god_of_carnage_solo` template with comment that canonical title comes from `module.yaml`; consumers are world-engine session/template selection and tests. Ambiguity: builtins remain a **secondary** surface—risk of title/beat drift from YAML if not synced by process.

- **Runtime turn execution (`world-engine/app/story_runtime/manager.py`):** Imports `story_runtime_core` and `ai_stack` to run turns; consumers are play service HTTP/WebSocket APIs. Authority boundary: runtime host executes; ambiguity is whether all admin/backend entrypoints route here consistently.

- **Backend publishing/governance (`backend/` content + admin routes):** `runtime_authority_decision.md` assigns curation/review; consumers include administration-tool via backend APIs. Ambiguity: extent of transitional in-process runtime paths is **unclear** from this baseline alone—needs code-path audit.

- **RAG / retrieval (`ai_stack/rag.py`):** Path-based lane detection for `content/modules/` vs `content/published/`; consumers are runtime retrieval in world-engine. Ambiguity: if published tree layout differs from doc examples, **silent** lane misclassification is possible.

- **Normative contracts (`docs/CANONICAL_TURN_CONTRACT_GOC.md`, `docs/VERTICAL_SLICE_CONTRACT_GOC.md`):** Primary consumers are implementers and gate programs; authority is **documentary** until each seam is mapped to code. Drift risk: high—contracts can run ahead of or behind code.

- **JSON schemas (`schemas/`):** Consumers are validators and tooling; evolution ownership across services is **unclear** without a single declared owner file.

- **MCP filesystem tools (`tools/mcp_server/fs_tools.py`):** Expose `content/modules` to tools; consumers are agent workflows. Boundary: tools may **bypass** backend validation—risk if edits are treated as canonical without publish steps.

- **Workflow definitions (compose + CI):** `docker-compose.yml` wires backend to play-service; consumers are local and CI-like environments. Ambiguity: hostnames/ports in `frontend` env vs `backend` internal URLs must match actual deployment—integration drift if not checked per environment.

---

## 8. Baseline decision rules for later tasks

1. **No GoC relocation** before dependency sufficiency (§6) is established and recorded.
2. **No cohesion-closure claim** without explicit inspection of **authority**, **contract**, **ownership**, and **workflow fit** across producer and consumer surfaces.
3. **No ownership assumption** without repository evidence (tracked paths, contracts, or code).
4. **No contract-alignment claim** without checking **both** producer and consumer surfaces.
5. **No workflow-alignment claim** without checking **declared** (docs) and **actual** (code/config/runtime) surfaces.

**Passing automated tests—including green CI—does not count as sufficient evidence of cross-stack cohesion.** Tests may omit environments, mock filesystems, or skip lanes; cohesion requires explicit seam evidence per §5 and §6.

---

## 9. Staleness and re-validation trigger

This baseline becomes **stale** and **must be revalidated or replaced** before downstream tasks treat it as control input if **any** of the following occurs:

- A **top-level service boundary** or primary responsibility shifts (e.g. runtime host, publishing owner).
- **GoC-related** paths, loaders, registries, template IDs, or runtime-consumption surfaces change.
- **Backend, world-engine, ai_stack, MCP, LangChain, LangGraph, RAG, writers-room, or administration-tool** ownership or integration assumptions change materially.
- **Publishing or runtime-consumption** workflows change (including `content/published` layout or RAG rules).
- New **duplicate-truth** surfaces appear or mirror policy changes.
- **Documented authority boundaries** or controlling contracts change in a way that affects P0/P1 hotspots.
- **Tracked repository structure** changes affecting any P0 or P1 hotspot in §5 (e.g. new `world-engine` nesting, module root moves).

**Rule:** A stale Task 1B baseline is **not** valid control input. Downstream work must **pause** or **re-run** baseline discovery until an updated Task 1B-class document is published.

---

## 10. Deliverables for downstream tasks

Downstream tasks **must consume** from **this file**:

- §5 **inventories** (GoC dependencies, cohesion, ownership, duplicate-truth, seams, contracts, authority hotspots).
- §4 **classification** vocabulary for drift, GoC dependency classes, and authority ambiguity classes.
- §6 **sufficiency criteria** and refusal rules for GoC moves.
- §7 **critical SoT map** (non-exhaustive; bounded) for orientation—supersede only with deeper seam matrices that cite code.
- §8 **decision rules**, including the **standalone** test/cohesion rule.
- §9 **staleness policy** for baseline lifecycle.
- Task 1A **tags and mirror rules** from [TASK_1A_REPOSITORY_BASELINE.md](TASK_1A_REPOSITORY_BASELINE.md) remain in force for doc/test classification workstreams.
- **Execution checklists** (optional fill-in, plan-todo anchors): [TASK_1B_DOWNSTREAM_CHECKLISTS.md](TASK_1B_DOWNSTREAM_CHECKLISTS.md) — GoC relocate gate (§6) and P0 seam audit table (§5.5).

---

## 11. Quality bar (failure conditions)

Task 1B baseline work is **insufficient** if it:

- Skips **repository access verification** or lacks concrete paths (§2).
- Collapses into **Task 1A-style shallow inventory** without P0/P1 depth for GoC and seams.
- Treats **GoC risk as a side note** rather than a **relocation blocker**.
- Fails to **prioritize** P0/P1 hotspots with explicit downstream relevance.
- Omits **concrete** repository paths or component surfaces in hotspot rows.
- Omits **GoC dependency sufficiency** definition or refusal rules.
- Omits **workflow seam** inventory meeting minimum depth (§5.5).
- Omits a **usable** critical SoT map or exceeds three sentences per surface in §7.
- Produces a **speculative** map entry with **no** path anchor where a path is knowable from the repo.
- Treats **passing tests** as sufficient evidence of **cross-stack cohesion** (must be explicit in §8—this document satisfies that).
- Exceeds **5,000 words** without retaining P0/P1 necessity in long sections (this document targets <4,500 words).

---

## 12. Self-verification checklist

Each item is **pass/fail from this document alone** (no repo re-open required).

| # | Criterion | Pass condition |
|---|-----------|----------------|
| 1 | Repository access | §2 lists top-level observation and a non-empty inspected-path set. |
| 2 | Task 1A overlap controlled | §2 names Task 1A file as baseline input; §3/§5 deepen without duplicating 1A as sole content. |
| 3 | GoC blocker logic | §1 and §6 state relocation/high-risk dependency gating explicitly. |
| 4 | Deep classification framework | §4 defines all required drift classes plus GoC dependency and authority ambiguity classes. |
| 5 | Concrete inventories | §5 tables use **tracked** paths or named components (not placeholders). |
| 6 | Summary posture | §3 end and §5.1/§5.5 state what is summarized and why. |
| 7 | GoC sufficiency | §6 lists classes, checks, sufficiency definition, refusal rules. |
| 8 | Critical map discipline | §7 entries ≤3 sentences; paths cited where claims attach to files. |
| 9 | Workflow seams depth | §5.5 lists multiple named seams with declared/actual columns and materiality. |
| 10 | Contract hotspots | §5.6 lists contract-alignment hotspots explicitly. |
| 11 | Tests vs cohesion | §8 contains **standalone** normative sentence that passing tests ≠ cross-stack cohesion. |
| 12 | No false execution | Nowhere claims cleanup, moves, or fixes were performed. |
| 13 | Size rule | If document >5,000 words, each non-tabular section >700 words must be P0/P1-only (monitor on future edits). |
| 14 | Staleness governance | §9 defines stale baseline as invalid control input and lists triggers. |
| 15 | Downstream deliverables | §10 enumerates consumable sections from **this file** only—no external chat reference. |

---

## Revision verification (authoring checklist)

- Repository access grounded in **actual** top-level observation and named inspections (§2).
- Does **not** replace Task 1A; **extends** with cross-stack and GoC depth.
- GoC dependency risk treated as **P0 gate**, not a footnote.
- Hotspots tied to **concrete** surfaces.
- Authority, ownership, contract, and workflow fit **called out** in §3, §5, §7, §8.
- **Passing tests** are **not** treated as cohesion proof (§8).
- Critical map **bounded** and **path-anchored** where applicable (§7).
- GoC dependency inventory lists **all P0 classes** with inspected surfaces (§5.1).
- Workflow seam table meets **material seam** depth (§5.5).
- **No** reliance on chat messages as authoritative baseline (this file is self-contained).

---

*End of Task 1B standalone baseline document.*
