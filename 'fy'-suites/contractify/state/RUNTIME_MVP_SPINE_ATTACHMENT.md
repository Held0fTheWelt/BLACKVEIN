# Runtime/MVP spine attachment state

## Status

- State: active
- Scope: runtime/MVP contract spine
- Tracking mode: stable ongoing state file
- Canonical tracked audit snapshot: `../reports/CANONICAL_REPO_ROOT_AUDIT.md`
- Local machine audit export: `../reports/_local_contract_audit.json`
- Canonical local audit command: `python -m contractify.tools audit --json --out "'fy'-suites/contractify/reports/_local_contract_audit.json"`
- Canonical profile source: repo-root `fy-manifest.yaml` (`suites.contractify.max_contracts = 60`)
- Attachment report: `../reports/runtime_mvp_attachment_report.md`

## Purpose

Track the bounded Contractify wave that promotes the runtime/MVP normative-index spine into first-class Contractify records with repository-grounded relations, implementation links, validation links, precedence handling, and explicit unresolved overlap notes.

This file exists so the pass is **state-tracked and restartable** in the repository, not only visible through local JSON.

## Why this pass exists

Before this wave, the repository already contained many of the right runtime and MVP contracts, but Contractify still governed too little of that reality directly.

The gap was not absence of contracts.
The gap was insufficient first-class attachment, relation richness, and evidence visibility inside Contractify.

## Scope used in this pass

### Mandatory documented anchors promoted

- `docs/technical/runtime/runtime-authority-and-state-flow.md`
- `docs/technical/runtime/player_input_interpretation_contract.md`
- `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md`
- `docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md`
- `docs/MVPs/MVP_VSL_And_GoC_Contracts/GATE_SCORING_POLICY_GOC.md`
- `docs/technical/architecture/backend-runtime-classification.md`
- `docs/technical/architecture/canonical_runtime_contract.md`
- `docs/technical/content/writers-room-and-publishing-flow.md`
- `docs/technical/ai/RAG.md`
- `docs/ADR/adr-0001-runtime-authority-in-world-engine.md`
- `docs/ADR/adr-0002-backend-session-surface-quarantine.md`
- `docs/ADR/adr-0003-scene-identity-canonical-surface.md`

### Mandatory code/test surfaces inspected for evidence attachment

- `world-engine/app/story_runtime/manager.py`
- `world-engine/app/api/http.py`
- `backend/app/api/v1/session_routes.py`
- `backend/app/runtime/session_store.py`
- `backend/app/services/session_service.py`
- `backend/app/api/v1/world_engine_console_routes.py`
- `backend/app/api/v1/writers_room_routes.py`
- `story_runtime_core/input_interpreter.py`
- `ai_stack/goc_scene_identity.py`
- `ai_stack/goc_yaml_authority.py`
- `ai_stack/rag.py`
- `backend/app/services/game_service.py`
- `tests/run_tests.py`
- `ai_stack/tests/test_goc_scene_identity.py`
- `story_runtime_core/tests/test_input_interpreter.py`
- `tests/experience_scoring_cli/test_experience_score_matrix_cli.py`
- `tests/smoke/test_repository_documented_paths_resolve.py`

## Tracking model used for this pass

### Human-tracked visibility

- This file records the pass state.
- `ATTACHMENT_PASS_INDEX.md` points readers here.
- `contract_governance_input.md` carries backlog/follow-up items.
- `reports/runtime_mvp_attachment_report.md` provides a concise generated summary.

### Canonical tracked visibility + local machine exports

- `reports/CANONICAL_REPO_ROOT_AUDIT.md` is the tracked human-readable canonical snapshot for repo review.
- local `reports/_local_contract_audit.json` carries the machine payload for the current run when needed.
- `precedence_rules`, `runtime_mvp_families`, and `manual_unresolved_areas` are emitted into the local audit payload and summarized in tracked markdown.
- Curated runtime/MVP records and relations are injected into Contractify discovery/audit output via `tools/runtime_mvp_spine.py` and discovery/audit integration.

## Continuation update (2026-04-17)

- The repo now has a root `fy-manifest.yaml`, so Contractify no longer needs legacy fallback when run canonically from repo root.
- The canonical audit profile is now manifest-backed through `suites.contractify.max_contracts = 60`, eliminating the hidden expanded-run requirement for the runtime/MVP spine.
- The canonical tracked snapshot at `../reports/CANONICAL_REPO_ROOT_AUDIT.md` must be regenerated from the canonical manifest-backed run whenever audit totals change.
- The generated runtime/MVP markdown report is regenerated from the same canonical run and must stay count-synchronized with the tracked snapshot.
- Writers' Room governance still carries direct validation evidence from `backend/tests/writers_room/test_writers_room_routes.py`.
- RAG governance still carries direct validation evidence from `ai_stack/tests/test_retrieval_governance_summary.py`.

## Evidence produced by this pass

- Updated tracked audit snapshot: `../reports/CANONICAL_REPO_ROOT_AUDIT.md`
- Concise generated summary: `../reports/runtime_mvp_attachment_report.md`
- Curated attachment logic: `../tools/runtime_mvp_spine.py`
- Discovery integration: `../tools/discovery.py`
- Audit integration: `../tools/audit_pipeline.py`
- Conflict alignment for curated overlap boundaries: `../tools/conflicts.py`
- Tests for the curated runtime/MVP spine: `../tools/tests/test_runtime_mvp_spine.py`

## What became materially visible

1. Major runtime and MVP anchors now exist as first-class Contractify records, not only as index-linked references.
2. Runtime/MVP relations now include bounded uses of `depends_on`, `refines`, `derives_from`, `overlaps_with`, `implements`, `implemented_by`, `validates`, `validated_by`, and `operationalizes` where repo evidence supports them.
3. Precedence tiers distinguish runtime authority, slice-level normative contracts, implementation evidence, verification evidence, and low-weight projections.
4. Explicit unresolved overlap areas remain visible instead of being silently flattened.

## Intentional non-claims

- This pass does **not** claim full semantic contradiction mining across the whole repository.
- This pass does **not** retire backend transitional surfaces by decree.
- This pass does **not** turn every related file into a first-class contract.

## Explicit unresolved areas preserved

1. **Runtime transitional retirement**
   - Backend transitional session surfaces are attached and weighted.
   - The actual retirement timeline remains unresolved on purpose.

2. **Writers' Room / RAG overlap boundary**
   - Retrieval/context-pack overlap exists.
   - Publishing authority and runtime truth remain distinct and should continue to be reviewed explicitly.

## Restart guidance

When resuming work on this attachment family:

1. Read this file.
2. Read `ATTACHMENT_PASS_INDEX.md`.
3. Read `../reports/runtime_mvp_attachment_report.md`.
4. Run `python .scripts/regenerate_contract_audit.py` from repo root to refresh the tracked canonical markdown snapshot and the bounded runtime/MVP report.
5. Inspect local `../reports/_local_contract_audit.json` only when machine-level detail is needed.
6. Update `contract_governance_input.md` if new unresolved issues or follow-up tasks appear.

## Edit history

- Initial runtime/MVP spine attachment pass established as a tracked Contractify state file.
- State tracking aligned with backlog and report visibility.
- Stable file naming adopted so the current attachment state keeps one durable entry point.
