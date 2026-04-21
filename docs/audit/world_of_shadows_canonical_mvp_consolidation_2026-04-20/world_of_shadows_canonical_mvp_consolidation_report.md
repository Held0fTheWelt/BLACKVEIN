# World of Shadows canonical MVP consolidation report

## Executive summary

I audited the two supplied archives directly, compared them structurally and textually, inspected the contained documentation, contracts, governance ledgers, validation reports, authored content, and key code/test surfaces, then rebuilt one canonical MVP reading layer on top of the richer archive.

The most important finding is this:

- the **FULL** archive is the real evidence-rich source base,
- the **LEAN** archive is useful as a curation/comparison artifact,
- the broad historical `mvp/` tree still carries material World of Shadows truth,
- and the newer repo-adjacent docs plus validation corpus carry the active slice reality and proof burden.

No single existing document carried all of that faithfully enough.
The new canonical MVP set now does.

## What was audited

At minimum, this pass audited and cross-reconciled:

- both supplied archives,
- the historical MVP tree under `mvp/`,
- current repository docs under `docs/`,
- governance ledgers under `governance/`,
- proof reports under `validation/`,
- GoC authored content under `content/modules/god_of_carnage/`,
- and owner-component repository surfaces under `world-engine/`, `backend/`, `frontend/`, `ai_stack/`, `writers-room/`, `administration-tool/`, and `tests/`.

A grouped source inventory is included separately in:
`docs/audit/world_of_shadows_canonical_mvp_consolidation_2026-04-20/world_of_shadows_canonical_mvp_source_inventory.md`

## Reconstruction method

The consolidation followed this order:

1. inventory the supplied archives and their document families,
2. compare FULL vs LEAN to determine which archive actually carried the stronger truth base,
3. extract product, architecture, proof, and experience requirements from the broad MVP, the current docs, and the proof corpus,
4. reconcile them against repository reality,
5. build an anti-loss preservation matrix,
6. explicitly review justified improvements,
7. write one subject-based canonical MVP document family,
8. keep residues and proof tasks visible instead of hiding them.

## Major findings

### 1. The source set contained two different but compatible MVP layers

The historical `mvp/` tree still carries the **broad WoS system target**:
constitutional laws, memory architecture, emotional/consciousness layers, Writers’ Room intelligence, authoring analytics, and a reference scaffold.

The newer repository docs and validation corpus carry the **active proof-bearing slice**:
GoC, world-engine authority, publish/runtime continuity, player shell behavior, and closure gating.

The right move was not to delete one layer in favor of the other.
The right move was to make the relationship explicit.

### 2. Important content had become underrepresented rather than truly removed

The consolidation found that the following were still materially present in the source set but not well represented in one canonical place:

- player-facing UI/UX expectations,
- GoC room/object/social-performance experience depth,
- GoC B/C/D/E/F conversational behavior,
- authoring → compiler → publish → runtime continuity,
- explicit runtime-proof posture and Level A vs Level B distinction,
- backend transitional retirement residue,
- and the enduring broader WoS target that still survives in `mvp/`.

### 3. The active GoC slice is much stronger than a shallow reading would suggest

The proof corpus shows that the active slice already supports far more than a generic “scene-grounded reply”:

- addressed reply identity,
- side/pair geometry,
- exchange-type differentiation,
- carryover pressure,
- room/object anchoring,
- surface-priority compression,
- core character voice differentiation,
- immediate and delayed continuity reuse,
- interruption/deflection/re-entry pressure,
- rhythm overlap and hesitation,
- micro-weave exchange choreography,
- and multi-speaker pressure relay.

Before this pass, too much of that truth lived only in wave-labeled reports.

### 4. The archive is strong enough for a slice-centered runtime-proof judgment, but not for full-program closure claims

The source set supports a **strong Level A, active-slice-centered runtime-proof posture**.

It does **not** honestly support claims that:

- the entire WoS target platform is fully closure-complete,
- backend transitional retirement is fully closed,
- evaluator-independent Level B closure has been achieved,
- or the broad historical target layers are all equally repo-proven now.

## Previously lost or underrepresented content restored by this pass

This pass directly restored and/or normalized:

- the relationship between the broad WoS target and the active GoC slice,
- the constitutional runtime law set,
- explicit UI/UX expectations for the player shell,
- the canonical GoC experience behavior across the A-F line,
- explicit authoring/publish/runtime continuity,
- runtime-proof evidence burden and closure classification,
- and an explicit residue/task layer so nothing important has to disappear to look “clean.”

## Contradictions and tensions found

The most important remaining tensions are:

- broad target-state WoS ambition vs narrower currently proven active slice,
- backend transitional POST-local bootstrap residue,
- Level B evaluator independence still blocked,
- builtin GoC fallback coexisting with published canonical path,
- Writers’ Room / RAG overlap being governed but intentionally not erased,
- and direct backend/frontend replay in this audit container being blocked by missing Flask even though stronger package-contained proof exists.

These tensions are recorded explicitly in:
`world_of_shadows_canonical_mvp_residue_and_contradictions.md`

## Preservation decisions

The anti-loss matrix distinguishes between:

- preserved directly,
- preserved after normalization,
- merged into a stronger canonical section,
- strengthened and integrated now,
- preserved as bounded residue,
- or explicitly rejected as speculative/out of scope.

That matrix is included in:
`world_of_shadows_canonical_mvp_preservation_matrix.md`

## Improvements integrated directly

The pass integrated these justified improvements now:

- one canonical subject-based MVP document family,
- restored UI/UX expectations,
- restored GoC experience behavior from the wave corpus,
- restored authoring/publish/runtime continuity as one canonical seam,
- explicit Level A vs Level B proof posture,
- and an explicit distinction between enduring target-state truth and active slice reality.

## Improvements deferred into runtime-proof tasks

The following remained justified but not honestly closeable inside this consolidation pass:

- final backend transitional retirement closure,
- Level B evaluator independence,
- present-container reproducibility for direct backend/frontend replay,
- continuing Writers’ Room / RAG overlap re-audits,
- and broader conversion of historical target layers into repo-proven implementation.

Those tasks are listed in:
`world_of_shadows_canonical_mvp_runtime_proof_tasks.md`

## Final canonical MVP structure

The new canonical MVP document family now lives under:

`docs/MVPs/world_of_shadows_canonical_mvp/`

It contains:

- `README.md`
- `01_system_identity_and_player_experience.md`
- `02_authority_architecture_and_runtime_laws.md`
- `03_content_authoring_publish_and_runtime_continuity.md`
- `04_god_of_carnage_canonical_experience.md`
- `05_player_ui_ux_and_operator_surfaces.md`
- `06_implementation_reality_and_proof_status.md`

## Implementation / proof reality check

### Direct execution performed in this consolidation

| Command | Result | Summary |
|---|---|---|
| python -m pytest -q mvp/reference_scaffold/tests --tb=short | PASS | 37 passed, 1 warning |
| python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py -q | PASS | 18 tests collected; all passed |
| python -m pytest -q world-engine/tests/test_story_runtime_narrative_commit.py --tb=short | PASS | 18 passed, 1 warning |
| python -m pytest -q ai_stack/tests/test_goc_scene_identity.py --tb=short | PASS | 5 passed |
| python -m pytest -q ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py --tb=short | PASS | 5 passed |
| python -m pytest -q backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine' --tb=short | BLOCKED IN THIS CONTAINER | ModuleNotFoundError: No module named 'flask' |
| PYTHONPATH=frontend python -m pytest -q frontend/tests/test_routes_extended.py -k 'play_shell_frames_latest_transcript_with_runtime_response_prefix' --tb=short | BLOCKED IN THIS CONTAINER | ModuleNotFoundError: No module named 'flask' |

### Interpretation of that evidence

The direct reruns confirm that:

- the historical MVP scaffold still works,
- core world-engine GoC runtime seams still work,
- GoC AI-stack support seams still work,
- and the present audit container is insufficiently provisioned for direct backend/frontend replay without Flask.

That local replay limit does not invalidate the stronger package-contained proof reports already present in `validation/`.
It does mean the final judgment must stay honest about what I reran directly here versus what I accepted from the supplied proof corpus.

## Runtime-proof readiness judgment

### Honest positive judgment

The final consolidated archive is strong enough to serve as the **canonical MVP package going forward**.

It also honestly supports a **slice-centered runtime-proof posture** for the current GoC-driven MVP, especially around:

- world-engine runtime authority,
- turn truth discipline,
- publish/runtime activation,
- shell-loop behavior,
- and the active GoC experience.

### Honest negative judgment

The archive should **not** yet be labeled as:

- full-program runtime-proof complete,
- fully backend-retirement-closed,
- or Level B evaluator-independent.

## Final closure judgment for this consolidation pass

This consolidation pass is **materially closed**.

It achieved the right goal:

- not shallow summary,
- not latest-file-wins collapse,
- not sentimental preservation of wave clutter,
- and not speculative redesign.

Instead it produced:

- one correct consolidated MVP reading layer,
- one audit/consolidation report,
- one source inventory,
- one preservation matrix,
- one improvement review,
- one runtime-proof task list,
- one residue record,
- one changed-files record,
- and one final archive whose additional documentation now makes the real source set usable as a canonical MVP package.
