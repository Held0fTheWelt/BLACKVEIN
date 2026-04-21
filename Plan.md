---
name: Full MVP Re-Integration
overview: Fully ingest the recreated `MVP/` tree into active repository systems and canonical documentation, using strict file-by-file mapping, conflict reconciliation, domain validation, and deletion-gate enforcement so that `MVP/` can only be retired after verified no-loss integration.
todos:
  - id: intake-lock
    content: Ingest recreated MVP tree and build complete inventory + mapping baseline
    status: completed
  - id: reconcile-conflicts
    content: Record and resolve all conflicts between MVP source content and already active repo implementation before destructive integration
    status: completed
  - id: map-targets
    content: Finalize domain-by-domain destination map for code, config, tests, and docs
    status: completed
  - id: integrate-runtime-assets
    content: Implement MVP code/config/test content into active service paths
    status: in_progress
  - id: populate-canonical-docs
    content: Fully rewrite and fill canonical MVP bundle documentation
    status: in_progress
  - id: normalize-navigation
    content: Update docs entrypoints to one canonical MVP route
    status: completed
  - id: verify-and-retire
    content: Run full verification and retire MVP only if deletion gate passes
    status: pending
isProject: false
---

# Full MVP Re-Integration Plan

## Goal
Implement the source tree under [`MVP/`](MVP/) at the repository root into the active repository structure as real integrated assets (code, configs, tests, docs), not passive references, then retire `MVP/` only after full verification.

## Run state and handoff

`Task.md` must live at the repository root and must be treated as the primary execution-state and handoff file for the entire run.

This file (`Plan.md`) states the normative integration contract. Current progress, decisions, blockers, and handoff for the next executor are maintained only in repository-root `Task.md`, not as a second live source of truth inside chat logs or inside this plan text.

## Execution Contract
- No source file in `MVP/` is allowed to remain unmapped.
- No meaningful requirement, behavior contract, sequencing rule, validation constraint, or test intent may be silently dropped.
- Documentation must be fully rewritten and populated into canonical destinations under `docs/` and `docs/MVPs/`, not left as legacy references.
- Code/test/config artifacts from `MVP/` must be merged into real runtime locations (`backend/`, `world-engine/`, `ai_stack/`, `frontend/`, `administration-tool/`, tests and supporting paths) where they are executable and maintainable.
- Blind overwrite is forbidden: if an `MVP/` artifact maps to an already active runtime/config/test file, execution must perform an explicit reconciliation step first.
- Reconciliation is mandatory and must determine per target file: what already exists, what is missing, what conflicts, what must be merged, and what must remain unchanged.
- Any destructive replacement without explicit reconciliation evidence is prohibited.
- Conflict recording is mandatory: every meaningful conflict between `MVP/` source content and active implementation/test/docs must be captured in `integration_conflict_register.md`.
- Integration must remain evidence-based. If `MVP/` content is incomplete, execution may recompose or normalize content, but must not invent speculative runtime behavior, architecture, or acceptance logic.
- Any introduced behavior/architecture/acceptance statement must be traceable to at least one allowed evidence source: `MVP/` source tree, already active repository truth, or explicit canonical documentation already present in the repository.
- Domain validation matrix is mandatory: for each touched destination domain (`backend`, `world-engine`, `ai_stack`, `frontend`, `administration-tool`, canonical docs), execution must record migrated inputs, affected destination paths, validation commands, expected evidence type, and resulting status.
- Execution is incomplete unless every touched destination domain has a recorded validation outcome.
- Repository-root `Task.md` continuity tracking is mandatory and must be maintained as the primary repository-local execution state throughout the run (no shadow `Task.md` under `docs/`, bundles, or subtrees as the authoritative copy).
- Repository-root `Task.md` must be updated at start, after each completed phase, after each meaningful mapping/integration decision, after each conflict resolution, after each verification run, before any destructive action, and immediately before stop/handoff.
- No phase is complete until repository-root `Task.md` reflects that completion state.
- No deletion/retirement action is allowed unless repository-root `Task.md` explicitly records that deletion-gate conditions are satisfied.

## Governed migration and tooling anchor

This plan distinguishes **three complementary surfaces**; all are normative for how MVP work may land in the repo:

1. **Repository-local rules and migration tooling (`'fy'-suites/`)**  
   The directory **`'fy'-suites/`** (literal name including quotes) at the repository root is the **canonical home** for fy meta-suites (Contractify, Docify, Despaghettify, **mvpify**, Postmanify, etc.) **intended for this repository**. It is not application/game runtime code under `backend/` or `world-engine/`. Very deep paths under that tree may fail to materialise on some hosts (path length); **shallower** files that exist remain authoritative for those paths.

2. **Path-level MVP integration scripts (`scripts/`, `tools/`)**  
   - Intake and inventory/mapping: `tools/mvp_reintegration_intake.py`  
   - Byte reconciliation and conflict register: `scripts/mvp_reconcile.py`  
   - Snapshot copy from active into `MVP/` for compared domains: `scripts/mvp_sync_domain_snapshot_from_register.py`  
   - Heuristic list of MVP paths whose **active** target is still missing (**forward** candidates): `scripts/mvp_forward_integration_candidates.py` → [`docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/forward_integration_candidates.md`](docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/forward_integration_candidates.md)  
   Canonical narrative, execution records, and **mvpify** / CLI quick reference: [`docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/README.md`](docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/README.md).

3. **Governed MVP bundle import (`mvpify`)**  
   For **prepared MVP bundles** — normalised trees under `mvpify/imports/<id>/normalized`, documentation mirrored under `docs/MVPs/imports/<id>`, and orchestration across fy suites — execution **must prefer** the **mvpify** suite (read ``'fy'-suites/mvpify/README.md``) over ad-hoc bulk file copies from the forward-candidate table alone.  
   **CLI:** install once with `pip install -e .` from ``'fy'-suites/`` (package **fy-suites-autark**, console script **`mvpify`** in ``'fy'-suites/pyproject.toml``). Then `mvpify <inspect|plan|ai-pack|full>` with optional `--repo-root`, `--source-root`, `--mvp-zip`, `--quiet`; module equivalent from ``'fy'-suites/``: `python -m mvpify.tools.hub_cli <subcommand> …` (implementation: ``'fy'-suites/mvpify/tools/hub_cli.py``). Verb summary: ``'fy'-suites/docs/platform/SUITE_COMMAND_REFERENCE.md``. Optional **`mvpify-adapter`**: ``'fy'-suites/mvpify/adapter/cli.py``.

**Handoff:** repository-root [`Task.md`](Task.md) carries live state; this section is the **normative anchor** so later phases do not treat `'fy'-suites/` or **mvpify** as optional side notes.

## Phase 1 - Intake and Source Lock
1. Confirm that the full `MVP/` tree exists and is ready for intake.
2. Freeze an intake snapshot (inventory baseline) so implementation works against a stable source set.
3. Build the mandatory source inventory and source-to-destination mapping table for every file under `MVP/`.
4. Tag each file with one disposition: `MIGRATE_DIRECT`, `MERGE_INTO_SECTION`, `PRESERVE_AS_REFERENCE`, `OMIT_WITH_JUSTIFICATION`.
5. Initialize or refresh repository-root `Task.md` with current objective, execution state, and source baseline before moving to Phase 2.

## Phase 2 - Target Design and Mapping Approval
1. Define final destination paths per domain:
   - Runtime/code: [`backend/`](backend/), [`world-engine/`](world-engine/), [`ai_stack/`](ai_stack/), [`frontend/`](frontend/), [`administration-tool/`](administration-tool/)
   - Canonical docs: [`docs/`](docs/) and [`docs/MVPs/`](docs/MVPs/)
   - Tests and validation surfaces: service test trees and repo-level validation docs.
2. Lock section ownership for the canonical MVP bundle:
   - `README.md`
   - `scope_and_goals.md`
   - `architecture_and_system_shape.md`
   - `content_and_experience_contract.md`
   - `implementation_sequence.md`
   - `acceptance_and_validation.md`
   - `open_tasks_and_follow_on_work.md`
3. Confirm no domain remains “reference-only” if it is intended to be active implementation behavior.

## Phase 3 - Code, Config, and Test Integration (Hard Implementation)

**Gate:** Follow **Governed migration and tooling anchor** (above) — use path-level scripts/registers for inventory, reconcile, and forward heuristics; use **mvpify** for governed **prepared MVP bundle** import (normalisation + `docs/MVPs/imports/<id>` mirroring) instead of ad-hoc bulk copies unless explicitly waived with justification in repository-root `Task.md`.

1. Run file-by-file reconciliation for every `MVP/` source that maps into an already active runtime/config/test target path.
2. Produce reconciliation decisions for each target: keep-existing, merge, partial replace, or no-change, with explicit conflict notes.
3. Build and maintain `integration_conflict_register.md` for all meaningful conflicts across behavior, architecture, config, test, documentation, and sequencing.
4. Migrate runtime-relevant code from `MVP/` into active codebases by behavior ownership, using reconciliation outcomes as the only allowed write mode.
5. Merge configuration/bootstrap/governance settings into active config surfaces and startup paths, preserving valid existing behavior unless reconciliation justifies change.
6. Integrate tests from `MVP/` into active test suites, preserving intent and adapting to canonical service layout.
7. Remove duplicated or generated-only artifacts from active path consideration; keep only justified reference evidence.
8. Run incremental verification per domain (unit/integration/smoke as applicable).
9. Update repository-root `Task.md` after each integration decision and conflict resolution.
10. When integrating **bundle-shaped** MVP imports that require normalisation and documentation mirroring, run **mvpify** (see anchor section) and record outcomes under `mvpify/reports/` in the target repo root.

## Phase 4 - Documentation Population and Canonicalization
1. Fully populate the canonical MVP bundle under [`docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/`](docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/).
2. Rewrite source materials into implementation-grade documents in strict English:
   - clear authority model
   - real runtime seams
   - real implementation sequence and dependencies
   - explicit acceptance and test criteria
3. Enforce evidence binding for all canonical documentation claims; each non-trivial runtime/architecture/acceptance claim must be source-traceable.
4. Eliminate process-noise wording from canonical docs.
5. Keep historical evidence as explicitly non-canonical reference only.

## Phase 5 - Navigation Normalization
1. Update primary entrypoints to canonical bundle route:
   - [`docs/README.md`](docs/README.md)
   - [`docs/INDEX.md`](docs/INDEX.md)
   - [`docs/MVPs/README.md`](docs/MVPs/README.md)
2. Remove active navigation pointing into retired `MVP/` source paths.
3. Ensure exactly one canonical MVP entrypoint is discoverable.

## Phase 6 - Verification and Deletion Gate
1. Complete mapping-table verification for every source file.
2. Validate that code/test/config migrations are active and pass required checks.
3. Validate docs completeness, internal consistency, and canonical navigation.
4. Validate that `integration_conflict_register.md` is complete and each conflict has a resolution and validation status.
5. Validate evidence traceability: no speculative runtime/architecture/acceptance claims were introduced without allowed source support.
6. Validate the domain validation matrix is complete for every touched destination domain and each recorded command has an outcome status.
7. Produce verification and retirement records.
8. Delete `MVP/` only if all gate checks pass; otherwise retain minimal explicit legacy remainder and record blockers.
9. Update repository-root `Task.md` immediately before and after any deletion/retirement action.

Deletion hard-stop conditions (any one condition blocks deletion of `MVP/`):
- any unmapped source file remains
- any unresolved conflict remains in `integration_conflict_register.md`
- any migrated destination domain lacks recorded validation outcome in `domain_validation_matrix.md`
- any canonical documentation section remains incomplete
- any active navigation path still points to `MVP/`
- any mapping-table row lacks final verification status

## Deliverables
A. `mvp_source_inventory.md`
B. `source_to_destination_mapping_table.md`
C. `reconciliation_report.md`
D. `integration_conflict_register.md`
E. `domain_validation_matrix.md`
F. `Task.md` at repository root (primary execution-state and handoff file)
G. integrated code/config/test changes in active runtime paths
H. canonical MVP bundle documentation
I. `migration_report.md`
J. `navigation_update_record.md`
K. `verification_record.md`
L. `retirement_record.md`
M. `forward_integration_candidates.md` (generated; forward triage; see **Governed migration and tooling anchor**)

### Task.md continuity record (repository root)
A continuously maintained execution-state file that records:
- current phase
- mapping progress
- domain integration status
- conflicts
- changed files
- validation outcomes
- blockers
- next actions
- handoff notes

## Definition of Done
- The recreated `MVP/` content is implemented into active repo systems (not parked as references).
- Canonical MVP documentation is fully populated and implementation-usable.
- Tests/config/code changes are integrated and validated.
- Source-to-destination mapping is complete and verified for every source file.
- `integration_conflict_register.md` is complete for all meaningful conflicts and each entry has resolution plus validation status.
- Canonical implementation outputs are evidence-traceable to allowed sources and contain no speculative unsupported runtime/architecture/acceptance inventions.
- Every touched destination domain has a recorded validation matrix outcome (commands, evidence type, resulting status).
- Repository-root `Task.md` is up to date, handoff-safe, and accurately reflects final execution state and deletion-gate status.
- `MVP/` is retired only after deletion gate success.
- Any **prepared MVP bundle** ingestion that required normalisation and `docs/MVPs/imports/<id>` mirroring was executed through **mvpify** (see **Governed migration and tooling anchor**), or explicitly waived with a recorded justification in repository-root `Task.md`.

## Mandatory Conflict Register Schema

`integration_conflict_register.md` must include one row per meaningful conflict and, at minimum:
- conflict ID
- affected source files
- affected active destination files
- conflict type (`behavior`, `architecture`, `config`, `test`, `documentation`, `sequencing`)
- chosen resolution
- justification
- validation status

## Mandatory Domain Validation Matrix Schema

`domain_validation_matrix.md` must include one row per touched destination domain and, at minimum:
- destination domain (`backend`, `world-engine`, `ai_stack`, `frontend`, `administration-tool`, `canonical docs`)
- migrated source inputs
- affected destination paths
- required validation commands
- expected evidence type (`unit`, `integration`, `smoke`, `doc consistency`, `navigation`)
- resulting status

## Mandatory Task.md continuity schema

The authoritative file is `<repository-root>/Task.md` only. It must be continuously updated and include at minimum:
```markdown
# Task

## Current Objective
...

## Current Execution State
...

## Source Baseline
...

## Mapping Progress
...

## Domain Integration Status

### backend
...

### world-engine
...

### ai_stack
...

### frontend
...

### administration-tool
...

### canonical docs
...

## Conflict Register Summary
...

## Files Changed
...

## Validation Summary
...

## Open Blockers
...

## Next Required Actions
1. ...
2. ...
3. ...

## Handoff Notes
...
```

Continuity requirements:
- Another executor must be able to resume directly from repository-root `Task.md` without hidden chat context.
- If execution pauses or stops, repository-root `Task.md` must end in handoff-safe state.