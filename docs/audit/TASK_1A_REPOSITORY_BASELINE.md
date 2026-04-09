# Task 1A — Repository Access Verification, Inventory, and Classification Baseline

**Reader orientation (downstream):** Start with **§5** for actionable inventories, **§7** for governing rules, **§9** for failure conditions that reject an incomplete baseline, **§10** for self-verification against this file only, then **§4** for classification semantics, **§2** for access/scope grounding, **§1** / **§6** for judgment and surface-level truth candidates. **Appendices A–D** close P0 follow-ups from the controlling plan (evidence paths, mirror policy, world-engine taxonomy, Task 1B handoff).

## 1. Executive judgment

The cleanup initiative is **controllable as a bounded implementation sequence** because the repository already separates concerns by top-level service packages (`backend/`, `world-engine/`, `ai_stack/`, `frontend/`, `administration-tool/`, `writers-room/`, `story_runtime_core/`, `content/`, `docs/`, `tests/`, `tools/`, `outgoing/`). Downstream work can proceed **workstream-by-workstream** (docs taxonomy, test suite normalization, path hygiene) once every change is preceded by the classification rules in §4 and §7.

**Primary control risks (not solved here):** (a) **documentation that references evidence paths under `tests/reports/`** while [`.gitignore`](../../.gitignore) contains `/tests/reports`—only two Markdown files are tracked under `tests/reports/` per `git ls-files`, so **fresh clones may not contain** paths cited as authoritative in active docs; (b) **parallel “distribution” documentation** in [`outgoing/`](../../outgoing/) and [`docs/g9_evaluator_b_external_package/`](../g9_evaluator_b_external_package/); (c) **nested `backend/world-engine/`** alongside root [`world-engine/`](../../world-engine/), which invites wrong assumptions about runtime layout.

### Critical note (scope boundary)

Task 1A is **not** the place for **deep cross-stack cohesion analysis** or **deep GoC dependency mapping**; those belong to **Task 1B** (Appendix A). Task 1A may **register** such hotspots as scoped follow-ups when needed to explain an inventory blocker.

### Protected in-progress exception (narrow — do not generalize)

The **still-unfinished canonical turn-contract surface** is a **protected exception** for generic cleanup framing in Task 1A:

- [`docs/CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md)
- Its **associated ten gates (G1–G10)** where they are part of the **unfinished canonical-turn-contract completion chain**—concretely, the tracked baseline pairings under `docs/audit/` for **`gate_G1` … `gate_G10`** (e.g. `gate_G1_semantic_contract_baseline.md` through `gate_G10_end_to_end_closure_baseline.md`) **when** they are exercised as that chain (not as unrelated audit scrap).

**Task 1A must still inventory and classify** this surface (claims, paths, shorthand, readability diagnosis). It **must not** treat remaining shorthand, gate structure, or **temporary readability deficits** on this surface as **normal cleanup residue** for **generic** de-abstraction, generic audience-taxonomy enforcement, or “default Task 2 readability” backlog items.

**Tagging requirement:**

- **Protected in-progress canonical surface** (`R5_protected_in_progress_exception` + `X1_protected_canonical_in_progress_surface`)
- **Readability exception by active completion status** (document *why* it is in-flight, not “bad housekeeping”)
- **Follow-up governed by its own completion program** (record owning workstream/plan ID when executing the full 1A pass—e.g. controlling doc under `docs/plans/` or roadmap slice)

**Non-generalization rule:** This exception is **narrow**. It **must not** justify leaving shorthand-heavy or process-heavy documentation **elsewhere** in the repo untouched; other docs follow normal `A*` / `R*` / Task 2 rules.

---

## 2. Repository access verification

**Confirmed:** Workspace path `WorldOfShadows` is a git repository; inspection used directory listing, `git ls-files`, and targeted file reads (baseline refresh: 2026-04-09).

**Observed top-level entries (names only):** `.claude`, `.cursor`, `.devcontainer`, `.dockerignore`, `.env`, `.env.example`, `.git`, `.github`, `.gitignore`, `.idea`, `.mcp.json`, `.venv`, `.worktrees`, `.wos`, `CHANGELOG.md`, `DEVELOPMENT_SETUP.md`, `PYTHONANYWHERE_SETUP.md`, `README.md`, `Task.md`, `WorldOfShadows.code-workspace`, `docker-compose.yml`, `docker-up.py`, `favicon.svg`, `run-smoke-tests.bat`, `run-smoke-tests.sh`, `setup-test-environment.bat`, `setup-test-environment.sh`, `start-world-engine.ps1`, `_tmp_goc_dbg`, `administration-tool`, `ai_stack`, `audits`, `backend`, `content`, `data-tool`, `database`, `docker`, `docs`, `frontend`, `outgoing`, `postman`, `promo`, `resources`, `schemas`, `scripts`, `story_runtime_core`, `tests`, `tools`, `world-engine`, `writers-room`. *(Refresh: root `PATCH_NOTES_FLASK_PLAY_INTEGRATION.md` relocated to [`docs/reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md`](../reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md).)*

**Primary directories/files inspected for this baseline:** [`.gitignore`](../../.gitignore); [`README.md`](../../README.md); [`docs/CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md); [`docs/audit/gate_summary_matrix.md`](gate_summary_matrix.md); [`docs/rag_task3_source_governance.md`](../rag_task3_source_governance.md); [`docs/architecture/runtime_authority_decision.md`](../architecture/runtime_authority_decision.md); [`tests/goc_gates/test_g9_threshold_validator.py`](../../tests/goc_gates/test_g9_threshold_validator.py); [`backend/tests/test_authorization_boundaries.py`](../../backend/tests/test_authorization_boundaries.py) (split from former `test_coverage_expansion.py`); `git ls-files` scopes for `docs/`, `tests/`, `outgoing/`, `audits/`, `docs/plans/`, `docs/architecture/`; samples for `docs/**/*.md`, `**/test*.py`, `schemas/`.

**Measured tracked counts (refresh):** `git ls-files docs/` → **215** paths; `git ls-files tests/` → **18** paths (repo-root `tests/` tree only—package suites live under `backend/tests/`, `world-engine/tests/`, etc.).

**Gitignored vs tracked (scope rule):** [`.gitignore`](../../.gitignore) ignores e.g. `_tmp_goc_dbg/`, `/tests/reports`, `Task.md`, `.venv`, `world-engine/app/var/runs` (path as written in file). **`_tmp_goc_dbg` and most of `tests/reports/` are out of scope** for classification unless a **tracked** file references them (then flag dependency/misleading reference). **`backend/fixtures/improvement_experiment_runs/*.json`** are **tracked** sample improvement-loop payloads (relocated from the misleading `backend/world-engine/app/var/runs/` tree); they **are in scope** as fixtures.

### 2.1 In scope (Task 1A — inventory and classification only)

Baseline work includes, for **tracked** files only (unless a tracked asset depends on gitignored material): (1) repository access verification; (2) active technical documentation surface inventory; (3) candidate obsolete process/history docs in active-visible areas; (4) technical-claim candidates for later truth-check; (5) abstract/shorthand documentation patterns; (6) audience-placement issues; (7) opaque or historically named test modules and mixed-purpose suites; (8) suite sidecars and adjunct files; (9) path/category ambiguity; (10) misplaced tracked files; (11) classification framework and source-of-truth *candidate* map (surface-level); (12) tracked-surface hygiene indicators; **(13) documentation readability hotspots in active tracked documents**—including documents that are **difficult to understand for reasons other than gate/phase/task shorthand** (e.g. nested terminology, unclear ownership, missing orienting prose, tables without introduction, normative density without reader guidance, “insider timeline” assumptions); **(14) explicit identification of protected exceptions** intentionally **excluded from generic readability enforcement**—with [`docs/CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md) and its **associated unfinished G1–G10 completion chain** (see §1 *Protected in-progress exception*) as the **primary** protected exception, each recorded per §5.11.

**Explicit non-scope for Task 1A:** rewriting, reordering, de-abstracting, or “fixing” readability in prose (that is **Task 2+**). Task 1A only records **that** a document is hard to read and **why**, with `R*`, `X*`, and dimension tags—not prescriptive edit plans.

---

## 3. Current-state audit summary

| Area | Observation |
|------|-------------|
| **Documentation surface** | Large tracked corpus under [`docs/`](../) (~215 tracked files): `architecture/` (51), `audit/` (20), `plans/` (3), plus `api/`, `testing/`, `mcp/`, `reports/`, ~~`superpowers/`~~ (archived 2026-04-10 to [`docs/archive/superpowers-legacy-execution-2026/`](../archive/superpowers-legacy-execution-2026/README.md)), `goc_evidence_templates/`, RAG task docs, evaluator package mirror, etc. Root [`README.md`](../../README.md) is the primary onboarding index. [`CHANGELOG.md`](../../CHANGELOG.md) is very large (history density). |
| **Claim density** | High in freeze/roadmap/contract docs (`CANONICAL_TURN_CONTRACT_GOC`, `VERTICAL_SLICE_CONTRACT_GOC`, gate baselines, RAG task docs). [`README.md`](../../README.md) asserts service roles and runtime authority. |
| **Abstract / shorthand patterns** | Widespread **G1–G10, G9B, Area2, Task N, MCP M1/M2, W0/W1** naming in filenames and headings (`docs/audit/gate_*.md`, `backend/tests/runtime/test_area2_*`, `docs/architecture/area2_*.md`, `docs/archive/superpowers-legacy-execution-2026/plans/*w*-*`). |
| **Documentation readability (beyond shorthand)** | Normative contracts and gate docs combine **dense tables**, **cross-references**, and **program vocabulary**; some docs assume **prior program context**; risk of **unclear responsibility boundaries** and **tables without orienting narrative**—see §5.10 and `R*` classes (inventory only in 1A). **Exception:** canonical turn contract + **G1–G10 in-completion chain** tagged `R5`/`X1`—not generic cleanup residue (§1, §5.11). |
| **Audience placement** | Mixed: operator/testing material under `docs/testing/`, security under `docs/security/` and root [`audits/`](../../audits/), MCP under `docs/mcp/`, **superpowers** plans/specs **archived** under `docs/archive/superpowers-legacy-execution-2026/` (process/tooling-adjacent), **outgoing** handoffs at repo root. No single `dev/` vs `admin/` vs `user/` root convention. |
| **Test readability** | Many modules encode **program or gate IDs** in names (`test_area2_task4_closure_gates.py`, `test_mcp_m2_gates.py`, `test_g9_threshold_validator.py`). Former omnibus coverage file was **split** into focused modules under `backend/tests/test_*` (authorization, constraints, state transitions, activity logging, error contracts, bulk ops, service edge cases). |
| **Historically named suites** | `backend/tests/runtime/` aggregates orchestration/gate/closure tests; `tests/smoke/` for cross-service smoke; `tests/goc_gates/` for G9 validator CLI; per-package suites under `*/tests/`. |
| **Sidecar fragmentation** | JSON fixtures next to `tests/goc_gates/`; templates under [`docs/goc_evidence_templates/`](../goc_evidence_templates/) consumed by tests; [`backend/.coveragerc`](../../backend/.coveragerc); optional local pytest/XML/evidence trees under `tests/reports/` (mostly ignored). |
| **Path / category ambiguity** | **Two world-engine paths:** root [`world-engine/`](../../world-engine/) vs [`backend/world-engine/`](../../backend/world-engine/). **`content/modules/`** vs **`writers-room/app/models/`** narrative assets. **`schemas/`** (JSON schemas) vs inline models in services. **`docs/reports/`** vs **`tests/reports/`** for closure artifacts. |
| **Misplaced / hygiene** | Tracked **improvement experiment JSON** now under [`backend/fixtures/improvement_experiment_runs/`](../../backend/fixtures/improvement_experiment_runs/) (relocated from nested `backend/world-engine/`). **Duplicate evaluator packaging** narratives: [`outgoing/`](../../outgoing/) and [`docs/g9_evaluator_b_external_package/`](../g9_evaluator_b_external_package/). [`docs/reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md`](../reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md) — historical integration note (relocated from repo root). |
| **Process / report artifacts** | Tracked: `docs/reports/*.md`, `docs/reports/ai_stack_gates/*`, two `tests/reports/*CLOSURE*.md`, [`outgoing/*`](../../outgoing/) handoff trees. Local-only: most `tests/reports/evidence/*` per ignore rule. |
| **Tracked-surface hygiene** | Strong reliance on **docs that cite gitignored evidence paths** creates **clone-to-clone drift risk**. Parallel mirrors increase **staleness** risk if one copy updates without the other. |

---

## 4. Classification framework (rules for later tasks)

**Documentation classes:** `D0_onboarding_index`, `D1_architecture_decision`, `D2_contract_normative`, `D3_roadmap_freeze`, `D4_testing_ops_runbook`, `D5_audit_gate_baseline`, `D6_security_compliance`, `D7_api_reference`, `D8_process_plan_wip`, `D9_external_handoff_mirror`, `D10_changelog_release`, `D11_report_closure_evidence`.

**Primary and secondary `D*` (mandatory shape):** Each document receives **exactly one primary `D*`** when classified. **Secondary `D*` tags** are optional (e.g. `D2` primary + `D5` secondary) when they add downstream signal; they **do not** replace the primary.

**`D*` conflict resolution (executable):** If more than one `D*` is plausible, assign primary using this **priority ladder** (highest wins):

1. **`D2_contract_normative`**, **`D3_roadmap_freeze`**, **`D5_audit_gate_baseline`**, **`D6_security_compliance`**, **`D7_api_reference`** — when the document contains **current** assertions that **constrain implementation, review, or operational behavior** (normative “must / shall / may not,” binding interfaces, or audit baselines presented as authoritative for today’s stack).
2. **`D1_architecture_decision`**, **`D0_onboarding_index`**, **`D4_testing_ops_runbook`**, **`D9_external_handoff_mirror`**, **`D10_changelog_release`**, **`D11_report_closure_evidence`** — orientation, runbooks, handoffs, history, or closure reports **without** overriding (1).
3. **`D8_process_plan_wip`** — plans, dated WIP, or process narratives that **do not** currently bind code when (1) applies.

**Concrete precedence example:** **`D2_contract_normative` > `D8_process_plan_wip`** when the same file mixes plan language **and** normative assertions that **currently** constrain implementation or review (e.g. scoring rules, seam contracts, freeze clauses treated as binding).

**Conflict log:** When the runner-up class is plausible, record **one short justification** (in the inventory row or a footnote): *why the primary won* and *which secondary was rejected* (e.g. “Primary `D2`: normative gate/scoring rules bind tests; secondary `D8` rejected: draft plan sections are subordinate to binding policy in the same file.”).

**Technical-claim truth classes:** `T0_implementation_binding` (must match code), `T1_process_historical` (time-bound), `T2_aspirational_target`, `T3_external_package_constraint`, `T4_evidence_pointer` (must resolve in tracked surface or be explicitly local-only).

**Documentation-abstraction classes:** `A0_descriptive_prose`, `A1_identifier_shorthand` (gate/phase/task codes without gloss), `A2_matrix_summary` (tables assuming prior context), `A3_internal_codename` (Area2, superpowers week IDs).

**Documentation-readability classes** (orthogonal to `A*`—a doc can be `A0` but `R3`; Task 1A assigns `R*`, Task 2+ addresses prose structure):

- `R0_readable_for_intended_audience` — structure and terminology match the inferred audience without requiring hidden program context.
- `R1_context_dependent_but_salvageable` — understandable once the reader knows slice/program context; needs framing gloss, not necessarily a full rewrite.
- `R2_structurally_hard_to_read` — e.g. long unbroken normative sections, important tables without lead-in, weak heading hierarchy, buried definitions.
- `R3_terminology_heavy_without_grounding` — many stacked terms/roles/seams without links to concrete components, paths, or a glossary.
- `R4_opaque_even_without_shorthand` — difficult despite little or no G*/Area2/MCP shorthand (e.g. unclear ownership, missing “who does what,” dense assertion lists without reader guidance).
- `R5_protected_in_progress_exception` — readability/shorthand/structure may look like backlog fodder, but the document set is **actively governed by a dedicated completion program**; **do not** queue for **generic** Task 2 readability/de-abstraction merely on that basis. Use **with** `X1` for the canonical turn-contract surface.

**Protected-exception classes** (orthogonal to `R*`; default `X0`):

- `X0_no_exception` — normal rules apply; generic readability and de-abstraction enforcement may target this doc when classified.
- `X1_protected_canonical_in_progress_surface` — **narrow** exception: [`docs/CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md) plus the **G1–G10** audit baselines under `docs/audit/` that are part of the **unfinished canonical-turn-contract completion chain**. **Must not** be cited as precedent to exempt unrelated shorthand-heavy docs.

**Documentation-audience classes:** `U_dev_contributor`, `U_ops_deploy`, `U_security_auditor`, `U_product_roadmap`, `U_external_evaluator`, `U_mixed_untagged` (default until split).

**Test-suite classes:** `S_unit_package_local`, `S_integration_service`, `S_runtime_orchestration`, `S_contract_gate_closure`, `S_cli_tool_smoke`, `S_cross_repo_smoke`, `S_improvement_loop`, `S_retrieval_rag`.

**Suite-sidecar classes:** `C_fixture_json`, `C_template_shared_doc`, `C_coverage_config`, `C_evidence_archive`, `C_conftest_shared`, `C_makefile_runner`.

**Path/category classes:** `P_service_root`, `P_shared_library`, `P_authoritative_content`, `P_authoring_ui_asset`, `P_schema_contract`, `P_script_tooling`, `P_generated_or_runtime_var`, `P_distribution_outgoing`, `P_nested_duplicate_name` (flag only).

**Misplaced-file classes:** `M_wrong_service_root`, `M_evidence_under_test_tree`, `M_operational_var_in_repo`, `M_duplicate_mirror`, `M_root_stray_process_note`, `M_content_vs_prompt_asset_split`.

**Tracked-surface hygiene classes:** `H_tracked_gitignored_pointer`, `H_stale_mirror_pair`, `H_oversized_changelog`, `H_duplicate_path_casing` (if any).

**Module-content classes:** `M0_yaml_canonical_module`, `M1_runtime_prompt_markdown`, `M2_demo_fallback`, `M3_published_projection` (as referenced in docs—verify in follow-up).

---

## 5. Prioritized inventory tables

### 5.1 Active technical docs (representative + P0)

| Path | Current class | Reason | Pri | Downstream |
|------|---------------|--------|-----|------------|
| [`README.md`](../../README.md) | D0 + T0 mix | Onboarding + service role claims | P0 | Doc de-abstraction, audience split |
| [`docs/CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md) | D2 | Normative seam model | P0 | Claim audit vs `ai_stack` seams |
| [`docs/VERTICAL_SLICE_CONTRACT_GOC.md`](../VERTICAL_SLICE_CONTRACT_GOC.md) | D2 | Slice boundaries referenced by contract | P0 | Same |
| [`docs/FREEZE_OPERATIONALIZATION_MVP_VSL.md`](../FREEZE_OPERATIONALIZATION_MVP_VSL.md) | D3 | Freeze rules | P0 | Governance cleanup |
| [`docs/ROADMAP_MVP_VSL.md`](../ROADMAP_MVP_VSL.md) | D3 | Target state | P0 | Roadmap vs changelog alignment |
| [`docs/architecture/runtime_authority_decision.md`](../architecture/runtime_authority_decision.md) | D1 | Authority split | P0 | Path taxonomy education |
| [`docs/audit/gate_summary_matrix.md`](gate_summary_matrix.md) | D5 + T4 | Aggregates gate status + **evidence paths** | P0 | **Tracked vs ignored evidence** resolution |
| [`docs/GATE_SCORING_POLICY_GOC.md`](../GATE_SCORING_POLICY_GOC.md) | D2/D5 | Scoring/diagnostics policy | P1 | Test/doc alignment |
| [`docs/rag_task3_source_governance.md`](../rag_task3_source_governance.md) | D2 + T0 refs | Retrieval governance + pointer to `ai_stack/rag.py` | P1 | RAG doc set normalization |
| [`docs/rag_task4_readiness_and_trace.md`](../rag_task4_readiness_and_trace.md) | D4/D8 | RAG harness readiness | P1 | Testing docs |
| [`docs/mcp/00_M0_scope.md`](../mcp/00_M0_scope.md) etc. | D1/D4 | MCP program | P1 | MCP doc tree |
| [`docs/testing/QUALITY_BASELINE.md`](../testing/QUALITY_BASELINE.md) | D4 | Quality baseline | P1 | Test readability |
| [`CHANGELOG.md`](../../CHANGELOG.md) | D10 | Release history | P1 | De-abstraction / indexing |

**Primary `D*` for mixed cells:** Where “Current class” shows two codes (e.g. `D2/D5`), downstream must record **one primary `D*`** using §4 conflict rule; the table preserves **observed overlap** only.

*Summary of remainder:* ~200 additional tracked `docs/**` files (architecture deep dives, per-gate `docs/audit/gate_*.md`, `docs/plans/*.md`, `docs/archive/superpowers-legacy-execution-2026/**` (formerly `docs/superpowers/**`), `docs/reports/**`)—classify in bulk using §4 before moves/edits.

**Tie-break record (reproducibility for §5.1):** Per Task 1A concreteness, **all P0** rows in this class are listed (**7** rows). Among **remaining** candidates, ordering uses **TB1** downstream-task risk → **TB2** ownership/role/category ambiguity → **TB3** active-surface visibility → **TB4** breadth of affected paths → **TB5** alphabetical path. **Applied to the P1 block (table order top-to-bottom):** `docs/rag_task3_source_governance.md` (**TB1**); `docs/GATE_SCORING_POLICY_GOC.md` (**TB1**); `docs/rag_task4_readiness_and_trace.md` (**TB1**); `docs/mcp/00_M0_scope.md` (stands in for `docs/mcp/*`, **TB3**); `docs/testing/QUALITY_BASELINE.md` (**TB3**); [`CHANGELOG.md`](../../CHANGELOG.md) (**TB1** lower than RAG/gate/MCP/testing entrypoints; **TB5** among peers). **Reviewer check:** extend the P1 set only with **per-row TB note** (which criterion broke ties).

### 5.2 Candidate obsolete / process-heavy docs (active-visible)

| Path | Class | Reason | Pri | Downstream |
|------|-------|--------|-----|------------|
| [`docs/archive/superpowers-legacy-execution-2026/plans/*.md`](../archive/superpowers-legacy-execution-2026/plans/) | D8 | Dated implementation plans (`2026-03-28-...`) | P2 | **Archived** 2026-04-10 (see `SUPERPOWERS_*` ledgers) |
| [`docs/archive/superpowers-legacy-execution-2026/specs/*.md`](../archive/superpowers-legacy-execution-2026/specs/) | D8 | Spec snapshots | P2 | **Archived** 2026-04-10 |
| [`docs/reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md`](../reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md) | D8 | Historical integration patch note | P2 | Archive vs active dev docs decision |
| [`docs/plans/*.md`](../plans/) (3 tracked) | D8 | Formal plans | P1 | Plan vs implementation drift check |

**Enumeration posture:** **4** representative rows; **not** claimed exhaustive for all process-heavy tracked docs—full 1A extends the table or adds a *Summary of remainder* with approximate class size.

### 5.3 Shorthand-heavy / opaque docs

**Governance (read before the table — Task 2 agents must not skip):** The `docs/audit/gate_G*.md` family **splits**: files that are part of the **`X1` G1–G10 canonical-turn-contract completion chain** are **not** generic shorthand-cleanup targets (they follow the **owning completion program**; see §1 and §5.11). **All other** gate-baseline or gate-shorthand docs in that glob remain normal **`A1`/`A2`** backlog unless separately classified.

| Path | Abstraction | Reason | Pri | Downstream |
|------|-------------|--------|-----|------------|
| [`docs/audit/gate_G*.md`](.) | A1/A2 | Gate IDs assume program context | P0 | Default: gloss or “audit program” index — **unless** row is in **`X1`** scope (see callout above) |
| [`docs/architecture/area2_*.md`](../architecture/) | A3 | Area2 workstream shorthand | P1 | Rename or add stable titles |
| [`docs/archive/superpowers-legacy-execution-2026/plans/*`](../archive/superpowers-legacy-execution-2026/plans/) | A3 | Week/workstream IDs | P2 | Audience tagging |
| [`docs/GATE_SCORING_POLICY_GOC.md`](../GATE_SCORING_POLICY_GOC.md) | A1 | Gate/scoring vocabulary | P1 | De-abstraction |

*Additional long tail:* filenames containing `g9`, `g10`, `mcp_m`, `w3-` across `docs/`—batch-tag as `A1`/`A3` during inventory sweep.

### 5.4 Audience-placement issues

| Path | Current | Issue | Pri | Downstream |
|------|---------|-------|-----|------------|
| [`outgoing/*`](../../outgoing/) | D9 | External handoff at root | P1 | Explicit “distribution” audience root vs `docs/` |
| [`docs/g9_evaluator_b_external_package/`](../g9_evaluator_b_external_package/) | D9 mirror | Overlaps `outgoing/` | P0 | Single owner + mirror policy |
| [`audits/*.md`](../../audits/) | D6 | Parallel to `docs/security/` / `docs/audit/` | P1 | Consolidate taxonomy |
| [`docs/testing/*.md`](../testing/) | D4 | Mixed developer + CI operator | P1 | Split `dev` vs `ci` subtrees if desired |
| [`postman/*.md`](../../postman/) | D4 | API manual adjacent to collection | P2 | User vs dev labeling |

**Completeness (concreteness rule):** This class has **≤5** distinct rows in the baseline pass—**all are listed above**. A **full-repo** audience sweep may add entries (e.g. `docs/development/`, per-package `README.md`, `DEVELOPMENT_SETUP.md`); the Self-verification (§10) requires stating whether §5.4 was **exhaustive for baseline** or **explicitly extended** after sweep.

### 5.5 Claim-audit candidates (minimum depth)

| Doc | Location | Claim summary | Material because | Pri | Downstream |
|-----|----------|---------------|------------------|-----|------------|
| [`README.md`](../../README.md) | “Services and packages” table | Each listed directory has stated role (e.g. `world-engine` authoritative play runtime) | Defines mental model for all cleanup | P0 | Verify against code entrypoints |
| [`README.md`](../../README.md) | “Architecture and request flow” | Runtime authority for live play in **`world-engine`** | Conflicts cause wrong edits | P0 | Align with deployment docs |
| [`README.md`](../../README.md) | “Repository structure” | `tests/` described as smoke + `run_tests.py` | Test layout expectations | P1 | Runner docs vs reality |
| [`CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md) | §2.1 table | **Commit** seam may alter truth; **Validation** may not emit player copy | Contract for narrative stack | P0 | Code seam audit (later task) |
| [`CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md) | §2.2 bullets | **Commit** is sole source for “what holds in the world” for dramatic facts | Authority claim | P0 | Same |
| [`CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md) | §2.3 | **Single writer per seam**; skipping seams is governance issue | Test/gate expectations | P1 | Gate test mapping |
| [`CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md) | §2.1 + §2.2 | Non-GoC modules use **waived** validation and preview-class visibility | Module behavior scope | P1 | Module matrix |
| [`gate_summary_matrix.md`](gate_summary_matrix.md) | Notes § | G1–G8 promotion evidence in `tests/reports/evidence/all_gates_closure_20260409/` | **Evidence path** | P0 | **Reconcile with `/tests/reports` ignore** |
| [`gate_summary_matrix.md`](gate_summary_matrix.md) | Table | All listed gates `structural_status` green / `level_a_capable` | Audit baseline | P1 | Truth-check vs current CI |
| [`rag_task3_source_governance.md`](../rag_task3_source_governance.md) | “Observability” | `retrieval_policy_version` = `task3_source_governance_v1` from `RETRIEVAL_POLICY_VERSION` in **`ai_stack/rag.py`** | Version identity | P0 | Code-doc sync (path cited) |
| [`rag_task3_source_governance.md`](../rag_task3_source_governance.md) | Path note | Lane detection uses substrings like `content/published/` | Path semantics | P1 | Ingest layout docs |
| [`rag_task3_source_governance.md`](../rag_task3_source_governance.md) | Profile table | Profile `runtime_turn_support` hard-drops same-module draft when published canonical present | Runtime retrieval policy | P1 | Test expectations |
| [`runtime_authority_decision.md`](../architecture/runtime_authority_decision.md) | Summary | **World-Engine** authoritative runtime host; **backend** policy/publishing | Architectural boundary | P0 | world-engine vs backend folder messaging |
| [`runtime_authority_decision.md`](../architecture/runtime_authority_decision.md) | Contract implications | **AI output non-authoritative**; commit authority outside model layer | Safety/governance | P0 | AI stack doc alignment |

**Enumeration posture:** **14** claim rows (minimum-depth sample across **4** docs); not exhaustive for all tracked docs—extend in full 1A or add rows under the same columns.

### 5.6 Opaque / mixed test modules

| Path | Class | Reason | Pri | Downstream |
|------|-------|--------|-----|------------|
| [`backend/tests/runtime/test_area2_*_closure_gates.py`](../../backend/tests/runtime/) | S_contract_gate_closure | Area2/task naming | P0 | Rename only after suite classification |
| [`backend/tests/runtime/test_area2_convergence_gates.py`](../../backend/tests/runtime/test_area2_convergence_gates.py) | S_contract_gate_closure | Shared helpers imported by siblings | P0 | Owning-suite consolidation |
| [`tests/goc_gates/test_g9_threshold_validator.py`](../../tests/goc_gates/test_g9_threshold_validator.py) | S_cli_tool_smoke | Spawns `scripts/g9_threshold_validator.py` | P0 | Sidecar ownership |
| [`tools/mcp_server/tests/test_mcp_m1_gates.py`](../../tools/mcp_server/tests/test_mcp_m1_gates.py) | S_contract_gate_closure | MCP milestone gates | P1 | Naming/readability |
| [`tools/mcp_server/tests/test_mcp_m2_gates.py`](../../tools/mcp_server/tests/test_mcp_m2_gates.py) | S_contract_gate_closure | Same | P1 | Same |
| `backend/tests/test_authorization_boundaries.py` (+ related split modules) | S_integration_service | API permission and constraint tests | P1 | Keep suite names behavior-readable |
| [`backend/tests/test_goc_semantic_parity.py`](../../backend/tests/test_goc_semantic_parity.py) | S_contract_gate_closure | GoC parity | P1 | Doc cross-links |
| [`ai_stack/tests/test_goc_phase2_scenarios.py`](../../ai_stack/tests/test_goc_phase2_scenarios.py) | S_retrieval_rag | Phase vocabulary | P2 | Phase glossary |

*Summary:* ~200 backend tests, 60 world-engine tests, 39 ai_stack tests, plus admin/frontend/database/writers-room—apply `S_*` tags before renames.

### 5.7 Sidecar / adjunct files

| Path | Class | Owning suite / consumer | Pri | Downstream |
|------|-------|-------------------------|-----|------------|
| [`tests/goc_gates/fixtures/*.json`](../../tests/goc_gates/fixtures/) | C_fixture_json | `test_g9_threshold_validator.py` | P0 | Co-locate or document |
| [`docs/goc_evidence_templates/*`](../goc_evidence_templates/) | C_template_shared_doc | Validator tests + scripts | P0 | Template governance |
| [`backend/.coveragerc`](../../backend/.coveragerc) | C_coverage_config | Backend pytest/coverage | P1 | Suite consolidation |
| [`tests/Makefile`](../../tests/Makefile), [`tests/run_tests.py`](../../tests/run_tests.py), [`tests/run_tests.sh`](../../tests/run_tests.sh) | C_makefile_runner | Multi-suite orchestration | P1 | Doc cross-link |
| [`tests/requirements_hygiene/test_requirements_test_files_resolve.py`](../../tests/requirements_hygiene/) | S_unit_package_local | Requirements resolution | P2 | Sidecar of hygiene suite |

*Note:* Massive `tests/reports/**` on disk is **gitignored** except [`tests/reports/MCP_M1_*.md`](../../tests/reports/)—do not treat local XML/evidence as shared baseline.

### 5.8 Ambiguous paths

**Completeness and ordering:** This subsection lists **5** path-ambiguity patterns—the **full explicit set** enumerated here for this baseline document (**not** a statistical sample of the whole repository). An extended sweep may **append** rows; if it does, revise the count in this sentence and mark **baseline vs added**. **Row order:** by **priority** (P0, then P1, then P2); **within the same priority**, alphabetical by **path pattern** text.

| Path pattern | Issue | Pri | Downstream |
|--------------|-------|-----|------------|
| `world-engine/` vs `backend/world-engine/` | Duplicate naming; different roles unclear from path alone | P0 | Taxonomy doc + README diagram (see **Appendix D**) |
| `docs/reports/` vs `tests/reports/` | Both host “closure” narratives | P1 | Single evidence taxonomy |
| `content/modules/` vs `writers-room/app/models/` | Both hold GoC narrative assets | P1 | Authoritative vs authoring |
| [`schemas/*.schema.json`](../../schemas/) vs service-local models | Cross-service JSON contracts vs code | P1 | Schema ownership map |
| `docs/audit/` vs root `audits/` | “Audit” word in two trees | P2 | Merge or rename |

### 5.9 Misplaced tracked files (candidates)

| Path | Suggested issue class | Reason | Pri | Downstream |
|------|----------------------|--------|-----|------------|
| `backend/fixtures/improvement_experiment_runs/improvement_experiment_*.json` (6 tracked) | M_operational_var_in_repo (mitigated) | Sample improvement-loop JSON | P1 | Fixture README + stable owner path |
| Duplicate narratives under [`outgoing/`](../../outgoing/) and [`docs/g9_evaluator_b_external_package/`](../g9_evaluator_b_external_package/) | M_duplicate_mirror | Same program, two locations | P0 | Pick canonical tracked location (see **Appendix C**) |
| [`docs/reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md`](../reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md) | M_root_stray_process_note (resolved) | Process note | P2 | Relocated under `docs/reports/` |

**Enumeration posture:** **3** candidate rows; **not** claimed exhaustive for all misplaced tracked files.

### 5.10 Readability hotspots in active tracked docs (diagnosis only — not rewrite)

**Task boundary:** Task 1A states *“this document is hard to read because …”* (with `R*` + dimensions). Task 2+ defines *how* it will be rewritten, reordered, and de-abstracted. Do not collapse 1A into editorial work.

**Dimension tags** (use all that apply per row): `shorthand` (A1/A3-style IDs), `structure` (layout/sections/tables), `terminology` (undefined or stacked terms), `density` (many claims without guidance), `missing_context` (assumes insider program timeline).

| Path | Why it is hard to read | Intended audience (inferable) | Dimensions | `R*` | Pri | Downstream |
|------|------------------------|-------------------------------|------------|------|-----|------------|
| [`docs/CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md) | Dense normative structure/terminology; **`R5`/`X1`** — not generic Task 2 queue | Core implementers / narrative runtime owners | structure, terminology, density, shorthand, missing_context | **R5** + **`X1`** | P0 | Claim audit §5.5; editorial closure via **completion program** (§1, §5.11) |
| [`docs/GATE_SCORING_POLICY_GOC.md`](../GATE_SCORING_POLICY_GOC.md) | Gate/diagnostic vocabulary tied to scoring; easy to misread severity without full audit context | Gate owners / AI runtime auditors | shorthand, terminology, missing_context | R1/R3 | P0 | Task 2: bridge from policy to examples; align with tests |
| [`docs/FREEZE_OPERATIONALIZATION_MVP_VSL.md`](../FREEZE_OPERATIONALIZATION_MVP_VSL.md) | Operational rules cross-link heavily; hard to skim without roadmap freeze mental model | Contributors enforcing MVP VSL | structure, density, missing_context | R1/R2 | P0 | Task 2: reader paths (“if you are X, read Y first”) |
| [`docs/audit/gate_summary_matrix.md`](gate_summary_matrix.md) | Matrix assumes gate program; notes reference evidence paths that may not exist on clone | Audit readers / release owners | shorthand, structure, missing_context | R1 | P0 | Task 2: evidence-path hygiene; optional gloss row |
| [`docs/rag_task3_source_governance.md`](../rag_task3_source_governance.md) | Correct but packs lanes/profiles/observability in few pages; table-first | RAG / retrieval implementers | terminology, density | R1 | P1 | Task 2: expand one worked example; keep normative brevity |
| [`CHANGELOG.md`](../../CHANGELOG.md) | Very long; high entry cost for “what matters now” | Maintainers / release readers | structure, density | R2 | P1 | Task 2: index/top summary policy (separate from 1A) |
| [`README.md`](../../README.md) | Broad; many links—skimmers may miss authority ordering (README vs contracts) | New contributors | density, missing_context | R1 | P1 | Task 2: explicit “start here” precedence box |

**Long tail:** Extend §5.10 using TB1–TB5 (same order as §5.1); omit generic Task 2 queueing for **`R5`/`X1`** rows.

### 5.11 Protected exceptions (registry — no duplicate prose)

**Authority:** Normative definition and non-generalization rule live in **§1** *Protected in-progress exception* and **§4** `R5` / `X1`. **§7** rules 11–12 enforce behavior.

**Registry (minimal — fill owner pointer at full 1A execution):**

| Protected surface | Owner program (doc pointer) |
|-------------------|----------------------------|
| [`docs/CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md) | Roadmap / gate program: e.g. `docs/ROADMAP_MVP_VSL.md`, `docs/ROADMAP_MVP_GoC.md`, `docs/plans/*` as applicable |
| `docs/audit/gate_G1` … `gate_G10` baselines (in-chain only; not G9B unless new `X*`) | Same completion program as canonical turn contract |

---

## 6. Surface-level source-of-truth candidate map (≤2 sentences per surface)

- **Active technical docs:** Truth is distributed across [`README.md`](../../README.md), [`docs/architecture/`](../architecture/), and GoC slice contracts, with contributors and operators as the primary consumers, and the dominant risk is missing precedence between the README and deeper freeze/roadmap material.
- **Technical claims in docs:** Authority is strongest where a doc binds a concrete path (e.g. [`rag_task3_source_governance.md`](../rag_task3_source_governance.md) → `ai_stack/rag.py`). Claims without such anchors stay unverifiable until mapped to code in a later task.
- **Descriptive audience docs:** [`docs/testing/`](../testing/) and [`docs/operations/`](../operations/) are candidate runbooks; consumers are dev/CI. Risk: **mixed skill levels** in one folder without labels.
- **Shorthand gate/phase docs:** [`docs/audit/`](.) and [`docs/architecture/area2_*.md`](../architecture/) encode program shorthand; consumers are gate owners. Risk: **opaque IDs** without a maintained glossary.
- **Templates:** [`docs/goc_evidence_templates/`](../goc_evidence_templates/) plus handoff templates under [`outgoing/`](../../outgoing/); consumers are scripts/tests/evaluators. Risk: **template drift** between mirrors.
- **Generic schemas:** [`schemas/*.schema.json`](../../schemas/); consumers are tooling and cross-service validation. Risk: unclear which service **owns** evolution vs duplicates in code.
- **Concrete module content:** [`content/modules/god_of_carnage/`](../../content/modules/god_of_carnage/); consumers are compiler/runtime/retrieval. Risk: confusion with **writers-room prompts** under `writers-room/app/models/`.
- **Fixtures:** e.g. [`tests/goc_gates/fixtures/`](../../tests/goc_gates/fixtures/); consumers are pytest. Risk: fixtures treated as **production config**.
- **Published/canonical content:** Referenced in RAG docs as `content/published/` substrings; verify tracked tree in follow-up (not enumerated here). Risk: path rules in docs may not match actual tree.
- **Builtin/fallback/demo:** [`backend/docs/DEMO_FALLBACK_GUIDE.md`](../../backend/docs/DEMO_FALLBACK_GUIDE.md) (exists in repo index); consumers are operators/dev. Risk: demo paths mistaken for production defaults.
- **Reports/evidence:** [`docs/reports/`](../reports/) plus sparse [`tests/reports/*.md`](../../tests/reports/); consumers are audit readers. Risk: **references to gitignored `tests/reports/evidence/`** break reproducibility on clean clones.
- **Tests:** Package-local `*/tests/` plus repo [`tests/smoke`](../../tests/smoke) and [`tests/goc_gates`](../../tests/goc_gates); consumers are CI. Risk: **unclear which suite is “source”** for gate closure without a matrix doc update.

---

## 7. Baseline decision rules for later tasks

1. **Classify before changing anything** using §4 tags—including **exactly one primary `D*`** per document (§4 conflict rule), optional secondary `D*`, plus **`R*`** / **`X*`** where applicable.
2. **Tracked files are the cleanup surface**; gitignored trees are out of scope unless a tracked asset references them—then record `H_tracked_gitignored_pointer` and fix pointer or promote tracked evidence.
3. **No document removal** without `D*` + `T*` classification and archival policy.
4. **No shorthand-heavy doc stays in high-traffic index** without gloss or explicit “program internal” banner (`A1`/`A3` mitigation)—**except** paths under **`X1_protected_canonical_in_progress_surface`**, which are governed by §1 / §5.11, not generic index rules.
5. **No test rename** without `S_*` suite classification and import/collection impact check.
6. **No suite consolidation** without identifying **owning suite** and sidecars (`C_*`).
7. **No path normalization** without `P_*` category and service-boundary check (especially `world-engine` vs `backend/world-engine`).
8. **No misplaced-file move** without `M_*` destination-role classification.
9. **No claim correction** without repository evidence (code path, test, or tracked artifact) or explicit narrowing rationale recorded in the change log for the doc workstream.
10. **Task 1A vs Task 2:** Task 1A **does not** rewrite documents. It **only** inventories readability (`R*`, `X*`, dimensions in §5.10) and classifies. Task 2 (or later doc workstreams) consumes that inventory to produce **concrete** restructuring, de-abstraction, and editorial changes.
11. **No generic readability-enforcement or de-abstraction cleanup** may be applied to [`docs/CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md) or its **associated unfinished G1–G10 chain** **merely because** they contain shorthand, gate structure, or in-progress canonical framing—those paths use **`R5`/`X1`** and the **owning completion program**.
12. **Anti-generalization:** The **`X1`** exception is **narrow** and **must be recorded** in §5.11; it **must not** justify retaining unrelated shorthand-heavy or process-heavy documentation without normal `A*`/`R*` classification and cleanup queueing.

---

### Task 1A vs Task 2 (readability)

| Task 1A (this baseline) | Task 2+ (follow-on) |
|-------------------------|---------------------|
| Identify hotspot: “hard to read because …” | Prescribe and apply: reorder, split, gloss, de-abstract |
| Assign `R*`, `A*`, `D*`, dimensions | Implement narrative structure and audience-specific paths |
| No mandatory “how to fix” beyond classification | Editorialize and verify claims against repo evidence |

---

## 8. Deliverables downstream tasks must consume

- This document’s **§4 classification tags** (including **one primary `D*`** per doc, **`R*`**, **`X*`**) and **§7 rules** as non-optional gates.
- **§5 inventories** as starting backlogs (prioritized P0→P2).
- **§5.5 claim-audit table** as first truth-check queue (expand per doc in doc-cleanup tasks).
- **§5.10 readability hotspot table** as the **input queue for Task 2** doc readability work (expand long tail in 1A completion pass)—**minus** rows tagged **`R5`/`X1`**, which are owned by §5.11 / completion program.
- **§5.11 registry** (owner pointers) plus **§1** / **§4** / **§7** as the **non-generalizable** `X1` record.
- **§6 map** as **non-authoritative** orientation only until superseded by Task 1B (deep mapping).
- Explicit follow-up registration: **Task 1B** — deep GoC dependency and cross-stack cohesion mapping (Appendix A).

---

## 9. Quality bar (Task 1A insufficient if…)

Task 1A is **insufficient** if it:

**Access and evidence**

- **Skips or fabricates repository access verification** (no actual top-level listing and named inspection scope as in §2, or inventories appear **without** §2 grounding).
- **Uses placeholder paths** where concrete repo paths are required in inventory tables (rows must be verifiable strings, not “TBD” or generic labels).
- **Omits summary posture** for any long-tail inventory: each summarized class must have an explicit *Summary* / *Summary of remainder* / *Long tail* / *Note* line stating **what** is summarized and **why** full enumeration is deferred.

**Classification control plane**

- **Lacks a usable classification framework** (§4 incomplete: missing `D*` list, `R*`/`X*`, or **D-class conflict rule**).
- **Fails to enforce exactly one primary `D*`** per classified document or **fails to document conflict resolution** when multiple `D*` are plausible (no justification per §4).
- **Omits decision rules for downstream work** (§7) or **contradicts** §4/§7 internally.

**Inventories and prioritization**

- **Fails to prioritize inventories** in an actionable way (no P0/P1/P2 or equivalent where required; no tie-break record for §5.1-style tables).
- **Fails to distinguish baseline vs extended sweep** where a subsection claims completeness for a pass (e.g. §5.4, §5.8) without stating which applies.
- **Misstates protected exceptions:** missing §1 definition, missing §5.11 registry row, or **`X1` scope dishonest** (claiming protection for paths outside the defined canonical-in-progress surface).
- **Generalizes `X1`** to unrelated shorthand-heavy docs.

**Readability and protected surface (retained)**

- **Fails to inventory general readability hotspots** beyond shorthand (§2.1 item 13 / §5.10 dimensions: structure, terminology, density, missing context).
- **Fails to record** the protected in-progress exception for [`docs/CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md) and the **G1–G10 in-chain** surface in **§1** + **§5.11** + **§4** `R5`/`X1` such that reason, scope, owner pointer, and non-generalization are recoverable by a reader.

---

## 10. Self-verification (revision checklist)

Each item is **pass/fail from this document alone** (no new repo inspection required).

1. **§2 access:** The file names an observed **top-level** list and a **non-empty** set of inspected paths/tools (§2 body)—confirm both appear.
2. **§4 conflict rule:** §4 contains **primary `D*`**, **secondary optional**, **priority ladder**, **example `D2` > `D8`**, and **conflict justification** requirement—confirm all five strings of intent appear.
3. **§5.1 counts:** **13** table rows are fully listed; the remainder is covered by *Summary of remainder*; **7** are P0 and **6** are P1; the tie-break paragraph names **TB1–TB5** and states they order the P1 block—confirm counts and TB list match the table + paragraph.
4. **§5.2–§5.4:** §5.2 has **4** fully listed rows + **Enumeration posture** line; §5.3 has **4** table rows + *Additional long tail* summary line; §5.4 has **5** rows and states **≤5 exhaustive for baseline**—confirm numbers.
5. **§5.5–§5.7:** Claim-audit table has **≥14** claim rows across **≥4** docs + **Enumeration posture** line; §5.6 has **8** test-module rows + *Summary* line for the rest; §5.7 has **5** sidecar rows + *Note*—confirm.
6. **§5.8:** States **5** ambiguous patterns, claims they are the **full explicit set** for this doc, and defines **ordering** (P0→P2, then alphabetical within Pri)—confirm.
7. **§5.9–§5.11:** §5.9 has **3** misplaced rows; §5.10 has **7** readability rows + *Long tail* line; §5.11 registry has **2** protected rows—confirm.
8. **Long-tail rule:** Every §5 subsection that does not fully enumerate its class contains **either** a *Summary* / *Summary of remainder* / *Additional long tail* / *Long tail* / *Note* line **or** an explicit **completeness** / **Enumeration posture** paragraph (§5.2, §5.4, §5.8, §5.9)—confirm none are missing.
9. **§5.3 governance:** `X1` / G1–G10 split appears **above** the shorthand table (callout), not only inside a cell—confirm.
10. **§6:** Count **≤2 sentences** per list item in §6 (**12** surfaces)—confirm by sentence count.
11. **§7 vs §4:** Rule 1 requires **one primary `D*`** and points to §4 conflict rule—confirm.
12. **§9:** Quality bar lists **≥10** distinct failure bullets spanning access, framework, inventories, protected surface—confirm.
13. **No false completion:** Nowhere does the document claim cleanup, rewrites, or Task 2 execution were performed—confirm.

---

## Appendix A — Task 1B scope registration (GoC / cross-stack cohesion)

**Status:** Explicitly **out of scope** for Task 1A; this appendix **registers** the follow-up so cleanup workstreams do not silently absorb it.

**Published Task 1B baseline (standalone):** [`TASK_1B_CROSS_STACK_COHESION_BASELINE.md`](TASK_1B_CROSS_STACK_COHESION_BASELINE.md) — authoritative for cross-stack cohesion, GoC dependency depth, workflow seams, staleness (§9), and baseline decision rules (§8).

**Operational checklists (plan todos):** [`TASK_1B_DOWNSTREAM_CHECKLISTS.md`](TASK_1B_DOWNSTREAM_CHECKLISTS.md) — section **A** (GoC relocate/renamespace gate = §6 sufficiency), section **B** (P0 seam producer/consumer audit).

**P0 relocation rule:** Do **not** rename `content/modules/god_of_carnage/`, change `module_id` / template IDs, or renamespace writers-room `implementation.god_of_carnage.*` entries until Task 1B §6 dependency sufficiency is **completed and recorded** (see checklist A). Green tests alone do **not** satisfy §6 or seam closure.

**Task 1B shall deliver (minimum):**

1. **Deep GoC dependency map** across `content/modules/god_of_carnage/`, `ai_stack/`, `story_runtime_core/`, `world-engine/`, `backend/`, and retrieval surfaces, with named entrypoints and test anchors.
2. **Authoritative code↔doc seam map** for the canonical turn contract (which functions/modules implement each seam vs which docs assert them), including drift detection hooks for CI or periodic audit.
3. **Cross-stack cohesion notes** where runtime authority, compiler projection, and RAG lanes intersect (supersedes §6 “non-authoritative” map for those seams).

**Controlling baseline for handoff:** this file (`docs/audit/TASK_1A_REPOSITORY_BASELINE.md`) §4–§8 remain the **documentation classification** gate. **Cross-stack seam truth, GoC dependency sufficiency, and cohesion decision rules** are governed by [`TASK_1B_CROSS_STACK_COHESION_BASELINE.md`](TASK_1B_CROSS_STACK_COHESION_BASELINE.md) §4–§9 (refresh per Task 1B §9 if stale).

---

## Appendix B — Evidence path reconciliation (`tests/reports` vs `.gitignore`)

**Facts (verified):**

- [`.gitignore`](../../.gitignore) contains `/tests/reports`, so **new** files under `tests/reports/` are not picked up by default.
- **Tracked exceptions** today: `tests/reports/MCP_M1_CANONICAL_PARITY_CLOSURE_REPORT.md`, `tests/reports/MCP_M1_CLOSURE_REPORT.md` (still in the index).
- Many audit baselines and CI notes cite **`tests/reports/evidence/...`** trees (e.g. `all_gates_closure_20260409/`, G10 trio logs). Those paths are **local reproduction artifacts** for typical clones.

**Resolved policy (for downstream doc/test hygiene tasks):**

1. **Tag** any tracked doc that cites `tests/reports/evidence/` without a tracked replica as **`H_tracked_gitignored_pointer`** until remediated.
2. **Clone-safe narrative:** Prefer summaries under **`docs/reports/`** (or another tracked subtree) for “what happened” stories; use `tests/reports/` for **machine-captured** logs that operators regenerate.
3. **Gate matrix and baselines:** When citing evidence dirs, **always** state that the path is **optional local output** unless a file is explicitly listed in `git ls-files`.
4. **Remediation options (pick per row in Task 2+):** promote a **minimal** tracked index or hash manifest; or **repoint** links to `docs/reports/` equivalents; or add a **one-line reproduction command** instead of a path-only pointer.

**Implementation note:** [`gate_summary_matrix.md`](gate_summary_matrix.md) includes an explicit clone-reproducibility bullet (edited alongside this baseline) pointing here.

---

## Appendix C — Single owner: `outgoing/` vs `docs/g9_evaluator_b_external_package/`

**Canonical owner (distribution / frozen handoff):** **`outgoing/`** — versioned evaluator bundles, zips, frozen JSON scenarios, and assembly notes for external parties. Classify as **`P_distribution_outgoing`**, primary audience **`U_external_evaluator`**.

**In-repo documentation mirror:** **`docs/g9_evaluator_b_external_package/`** — same instructional markdown and JSON templates for **hyperlinking from internal docs** and for contributors who never open `outgoing/`. Classify as **`D9_external_handoff_mirror`** (secondary to `D4` where runbook-like).

**Stale-mirror rule (mandatory on any content change):**

1. **One logical change set** updates **both** trees in the **same commit** when altering shared documents (`01_EVALUATOR_B_HANDOUT.md`, checklists, templates), **or** the author records an explicit exception (e.g. outgoing-only hotfix) in the commit message with a follow-up issue to resync the docs mirror.
2. **Prefer `outgoing/`** when assembling **frozen** zip artifacts; **`docs/g9_evaluator_b_external_package/`** must never drift to become the *only* updated copy for a frozen audit ID.
3. **README cross-links:** The docs mirror README points readers at the canonical outgoing bundle path for the same `audit_run_id`.

---

## Appendix D — Path taxonomy: `world-engine/` vs `backend/world-engine/`

| Path | `P_*` / flags | Role (baseline classification) |
|------|----------------|----------------------------------|
| [`world-engine/`](../../world-engine/) | **`P_service_root`** | **Authoritative FastAPI play runtime** — application code, Dockerfile, tests, session/WebSocket runtime. Aligns with [`README.md`](../../README.md) and [`docs/architecture/runtime_authority_decision.md`](../architecture/runtime_authority_decision.md). |
| [`backend/world-engine/`](../../backend/world-engine/) | **`P_nested_duplicate_name`** (residue) | **Not** a second copy of the play service. Tracked experiment JSON **relocated** to [`backend/fixtures/improvement_experiment_runs/`](../../backend/fixtures/improvement_experiment_runs/). Empty or stub `backend/world-engine/` trees should not be treated as a runtime service root. |

**Normalization guidance (for later tasks; no move in Task 1A):**

- Treat **`world-engine/`** at repo root as the **only** runtime service path in diagrams, onboarding, and new code.
- For JSON artifacts under `backend/world-engine/`, either **relocate** to an explicit `backend/var/...` store (with `.gitignore` policy) or **document as intentional fixtures** linked from improvement-loop docs—after `M_*` / `S_*` classification per §7.

---

*End of Task 1A baseline document.*
