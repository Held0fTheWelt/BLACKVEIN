# W5 Actor Tracking — Migration Plan

**Authoritative ADR:** [ADR-0063](../ADR/adr-0063-w5-actor-tracking.md) — W5 Actor Tracking.

**Status:** Proposed (Phase 0/1 in progress).

**Scope abbreviation:** `W5-AST` only when disambiguation is needed. The concept name remains **W5**.

---

## Cross-reference note (does not change ADR-0033 semantics)

[ADR-0033](../ADR/adr-0033-live-runtime-commit-semantics.md) is the live-runtime commit-semantics authority. W5 is **downstream of** ADR-0033, not parallel to it:

- W5 OBSERVED facts are only produced after a turn has reached the ADR-0033 committed/persisted lifecycle state.
- The W5 extractor never participates in the live-commit decision and cannot promote uncommitted LLM output to OBSERVED.
- ADR-0033's `live_success`, `adapter_kind`, `visible_output_present`, `quality_class`, and `degradation_signals` semantics are unchanged. W5 does not weaken or replace any of these.
- The Actor Lane / Commit / Readiness contract, `validation_outcome`, and Canonical Path semantics remain authoritative. W5 reads them; it does not gate them.

This note records the relationship without changing ADR-0033.

---

## Target architecture (post-migration)

- W5 is the actor-tracking authority for higher-level consumers.
- Narrator composition, NPC planning, Director gathering, validation, frontend, admin, and observability read **W5 projections**, not legacy `environment_state.actor_locations` / `current_room` / `current_area` / `previous_room_id` directly.
- `environment_state` remains the **low-level committed substrate** only.

---

## Phases

### Phase 0 — ADR + migration scaffolding (this commit)

**Goal:** establish the contract before any code consumers move.

- [x] Add ADR-0063 as **Proposed**.
- [x] Add this migration document with Phase 0/1 entries.
- [x] Add minimal cross-reference note relating W5 to ADR-0033 (above) without modifying ADR-0033.

No code behavior changes.

### Phase 1 — Shadow-only extraction (this commit)

**Goal:** produce W5 snapshots after every committed runtime event, persist them append-only, change no consumer behavior.

- [x] `ai_stack/actor_tracking/` package created with:
  - `models.py` — closed enums (`W5Dimension`, `W5TruthLevel`, `W5Source`, `W5VisibilityScope`, `W5FactStatus`, `W5FreshnessStatus`, `W5ActorType`, `W5ProjectionConsumer`, `W5ActionState`, `W5ConflictResolutionStatus`, `W5ValidationFailureCode`) and records (`W5Fact`, `W5ActorSituation`, `W5Snapshot`, `W5Conflict`, `W5Projection`).
  - `extractor.py` — `extract_w5_snapshot_from_committed_event(...)` pure function.
- [x] `StorySession` extended with append-only `w5_history: list[W5Snapshot]` and `w5_latest_snapshot: W5Snapshot | None`.
- [x] `story_session_to_payload` / `story_session_from_payload` round-trip W5 history; legacy payloads default to `[]` / `None`.
- [x] Shadow extraction wired in `StoryRuntimeManager._finalize_committed_turn` after `lifecycle_state="observed"` and before `_persist_session`. Extraction failures are caught and recorded as a diagnostic — they do **not** fail the turn.
- [x] Tests:
  - Closed-enum coverage.
  - Extractor purity (no I/O, no mutation, deterministic).
  - OBSERVED only from committed substrate.
  - How as first-class dimension.
  - INFERRED Why soft-truth.
  - StorySession W5 round-trip.
  - Legacy payload defaults safely.
- [x] Existing localization-related tests remain green (regression check).

**Constraints in Phase 1:**
- No LLM proposal may produce OBSERVED W5 facts.
- INFERRED Why may exist only as `truth_level="inferred"`.
- How is a first-class dimension and must not be collapsed into What.
- Extraction is pure, deterministic, source-tagged, truth-leveled, and append-only.
- Narrator, NPC, Director, frontend, admin, and validation are **not** migrated.
- Legacy localization helpers are **not** removed.
- `environment_state` remains the low-level committed substrate.

### Phase 2 — Bounded read-only projections for narrator (complete)

- [x] Define `build_w5_projection_for_narrator(...)`.
- [x] Wire narrator `source_facts.w5_projection` behind `W5_AST_NARRATOR_PROJECTION_ENABLED`.
- [x] Preserve legacy narrator transition/location fields as fallback.
- [x] Keep How first-class and inferred Why soft-truth.
- [x] Coerce persisted `w5_latest_snapshot` dicts through `W5Snapshot.from_dict()` inside the projection builder.

No write-side changes.

### Phase 2.5 — Director/Gathering baseline stabilization (complete)

- [x] Reconfirmed ADR-0061 behavior before migrating Director/Gathering:
  - actor-location absence can pause;
  - actor return clears pause;
  - same-room `participation_relevance="broken"` can pause;
  - same-room `visibility_audibility="not_audible"` can pause;
  - topology-confirmed presence does not suppress explicit resolver break evidence.
- [x] Confirmed W5 does not feed Director/Gathering in the Phase 2.5 baseline.

### Phase 3A — Director/Gathering W5 projection input (complete)

- [x] Add `build_w5_projection_for_director(...)`.
- [x] Director projection exposes compact per-actor `where.scene_location`, optional `where.visibility_audibility`, freshness/status, source/truth attribution, and a compatibility `derived_actor_locations` map.
- [x] Director projection preserves all five W5 dimensions internally (`who_summary`, `where_summary`, `what_summary`, `how_summary`, `why_summary`) while Director/Gathering only depends on the location/visibility fields needed for ADR-0061 pause semantics.
- [x] Wire Director/Gathering actor-location input behind `W5_AST_DIRECTOR_PROJECTION_ENABLED`.
- [x] Keep `compute_gathering_state` semantics and signature unchanged.
- [x] Keep `complete_actor_locations_for_gathering` and `gathering_scene_id`.
- [x] Add compact diagnostics:
  - `w5_director_projection_used`
  - `w5_director_projection_failed`
  - `w5_snapshot_id`
  - `derived_actor_locations_source`
  - `gathering_pause_source`

ADR-0061 cross-reference: Phase 3A changes only the actor-location input source when the flag is enabled. The pause predicate remains the ADR-0061 composition over topology plus resolver participation / visibility / audibility evidence.

### Phase 3B — NPC projection consumers (complete)

- [x] Add `build_w5_projection_for_npc(snapshot, actor_id=...)`.
- [x] NPC projections are actor-specific (`target_consumer="npc"`, `actor_id=<target NPC>`) and preserve all five W5 dimensions (`who_summary`, `where_summary`, `what_summary`, `how_summary`, `why_summary`).
- [x] Keep How first-class; inferred Why remains soft truth.
- [x] Preserve `source_attribution` and `truth_attribution` without exposing raw W5 fact ledgers to NPC planning prompts.
- [x] Respect actor knowledge / privacy boundaries:
  - the target NPC may receive its own private/inferred Why;
  - another actor's private/inferred Why is exposed only when `actor_knowledge_scope` allows the target NPC;
  - player-private facts do not leak to NPC projections.
- [x] Wire NPC planning inputs behind `W5_AST_NPC_PROJECTION_ENABLED`.
- [x] Disabled/unset flag behavior remains legacy-only.
- [x] Projection failures are diagnostic-only and fall back to legacy NPC context.
- [x] Legacy NPC context fields remain present as fallback.
- [x] No validation, frontend/player shell, or admin migration in this phase.

Phase 3B keeps W5 read-only for NPC planning. Actor Lane authority, commit/readiness semantics, `validation_outcome`, Canonical Path semantics, and ADR-0061 Director/Gathering pause behavior are unchanged.

### Phase 4A — W5 validation checks (complete)

- [x] Add `ai_stack/actor_tracking/validation.py`.
- [x] Register W5 validation in the canonical `run_validation_seam(...)` behind `W5_AST_VALIDATION_ENABLED`.
- [x] Actor Lane and existing hard safety checks remain more authoritative: W5 validation is reached only after those checks have not rejected the turn, and Actor Lane rejection reasons are not converted or masked.
- [x] W5 validation is detection / commit-gating only; it does not rewrite proposed blocks, mutate committed output, or mutate committed events.
- [x] Legacy validation remains fallback. Missing or malformed W5 snapshots record a compact fallback diagnostic and do not fail a turn in Phase 4A.
- [x] INFERRED Why conflicts do not hard-block; they remain warnings / pending Director evidence unless a future ADR configures otherwise.
- [x] Diagnostics include compact failure codes, warnings, snapshot id, source, fallback reason, and source/truth fact references without exposing raw W5 ledgers.

### Phase 4B — Admin / diagnostics visibility (complete)

- [x] Add compact typed diagnostic builders in `ai_stack/actor_tracking/diagnostics.py`.
- [x] Add read-only world-engine internal W5 surfaces for snapshot, per-actor drill-in, conflicts, narrator projection preview, NPC projection preview, and latest validation diagnostics.
- [x] Add backend admin proxy routes under `/api/v1/admin/w5/...` using existing moderator/admin and World-Engine `observe` capability checks.
- [x] Extend the Narrative Runtime governance UI with W5 Actor Tracking, per-actor, source/truth, visibility/perception, stale/contradicted, projection preview, and validation panels.
- [x] Add compact runtime diagnostics and Langfuse metadata (`w5.snapshot_id`, actor/conflict counts, How/Why presence, validation flags/failure codes) without emitting raw W5 ledgers or inferred Why prose.
- [x] Admin panels are read-only and do not mutate runtime truth, committed events, validation state, or any projection feature flag.
- [x] `admin_override`, where present in future repair flows, remains audited and cannot produce OBSERVED truth in this phase.
- [x] W5 visibility in admin/governance remains diagnostic; no operator repair authority exists until a separate ADR defines it.

### Phase 4C — Package-runtime gate repair (complete)

- [x] Repair stale flat `world-engine/app/story_runtime/manager/` gate assumptions for the package-based `world-engine/app/story_runtime/manager/` runtime.
- [x] Preserve LDSS, ADR-0033, observability, and no-fallback false-green assertions while updating symbol/file lookups.

### Phase 5A — Player-shell W5 projection (complete)

- [x] Add `build_w5_projection_for_player_shell(...)` in `ai_stack/actor_tracking/projection.py`.
- [x] Player-shell projection exposes compact Who / Where / What / How / Why summaries with How first-class and inferred Why marked through `truth_attribution`.
- [x] Player-shell projection is player-visible only: private NPC inferred Why requires explicit actor knowledge scope, and other player-private facts do not leak.
- [x] Story-runtime state exposes `w5_player_view` behind `W5_AST_FRONTEND_PLAYER_VIEW_ENABLED`; disabled/unset leaves the payload on the legacy path.
- [x] Missing or malformed W5 snapshots fall back to legacy `current_room` / `current_room_id` behavior with compact diagnostics.
- [x] Frontend room helpers prefer `w5_player_view.where_summary.scene_location.value` / current visible location when the flag is enabled, then fall back to legacy `current_room`.
- [x] `snapshot.current_room` and legacy localization fields remain compatibility aliases/fallbacks. No legacy localization removal occurs in this phase.

### Phase 5B — Legacy frontend/current-room fallback hardening (complete)

- [x] Keep `W5_AST_FRONTEND_PLAYER_VIEW_ENABLED` fail-closed: disabled/unset leaves player-facing room selection on legacy `current_room` / `current_room_id`.
- [x] When the flag is enabled and `w5_player_view` has a valid player-visible location, W5 is the preferred player-facing location source.
- [x] When W5 is missing, malformed, or lacks an active player-visible location, runtime payloads fall back to legacy `current_room` without failing the turn.
- [x] W5/legacy location disagreement is explicit in diagnostics via `current_room_legacy_value`, `current_room_w5_value`, and `current_room_mismatch`.
- [x] Frontend room helpers and WebSocket live snapshot rendering tolerate missing nested W5 fields and do not render Why/private inferred text.
- [x] World-Engine W5 manager helpers live under `world-engine/app/story_runtime/manager/actor_tracking/`; core W5 files live under `ai_stack/actor_tracking/`.
- [x] No legacy localization fields, `current_room`, `actor_locations`, `complete_actor_locations_for_gathering`, `gathering_scene_id`, or projection fallbacks are removed in this phase.

### Phase 6A — Legacy consumer-removal inventory (complete)

**Goal:** Produce a complete, classified inventory of every remaining direct consumer, writer, compatibility alias, test dependency, doc reference, and runtime fallback related to the legacy localization / current-room system so Phase 6B can remove or convert them safely. **No code is removed in Phase 6A.**

- [x] Confirmed forbidden packages absent: `ai_stack/actor_situation/` and `ai_stack/w5_actor_situation/` do not exist on disk and have **zero** active `import` references in the working tree.
- [x] Confirmed active W5 packages are the only W5 surfaces:
  - `ai_stack/actor_tracking/` (models, extractor, projection, validation, diagnostics).
  - `world-engine/app/story_runtime/manager/actor_tracking/` (session_state_w5_view, w5_projection helpers).
- [x] Enumerated every legacy surface in scope: `current_room`, `current_room_id`, `current_area`, `previous_room_id`, `actor_locations`, `participant.current_room_id`, `snapshot.current_room`, `visible_room_ids`, `RuntimeVisibilityPolicy.visible_occupants`, `complete_actor_locations_for_gathering`, `gathering_scene_id`, `derived_gathering_room_id`, `transition_from_previous.location_changed`, and direct `environment_state.*` location reads outside substrate/extractor/compatibility layers.
- [x] Classified every finding using the Phase 6A taxonomy (`substrate_keep`, `w5_authority_consumer_should_migrate`, `compatibility_alias_keep_temporarily`, `remove_in_phase_6b`, `rename_in_phase_6b`, `test_only_update`, `doc_only_update`, `unrelated_keep`).
- [x] Identified five `rename_in_phase_6b` items where the function name `validate_w5_actor_situation`, the diagnostic string `"w5_actor_situation_validation"`, and four docstring/ADR references still use the deprecated `w5_actor_situation` term.
- [x] Identified the highest-risk legacy consumers and recommended a safe Phase 6B removal order, gated on each W5 flag becoming the default before its legacy fallback is removed.
- [x] Wrote the full inventory to `docs/MVPs/w5_legacy_consumer_removal_inventory.md`.

**Constraints in Phase 6A:**

- No legacy localization helpers or fields are removed.
- No W5 feature flag is enabled implicitly or by default.
- No tests are weakened or converted from semantic to field-presence assertions.
- Substrate writers (`apply_action_to_environment_state`, the backend/world-engine `engine.py` MOVE_ACTOR effects, the `Participant.current_room_id` dataclass field) are preserved exactly as-is.
- No new imports of `ai_stack/actor_situation` or `ai_stack/w5_actor_situation` are introduced (and none existed prior).

**Outcome:** Phase 6B is safe to begin once the four W5 consumer flags (Director, Narrator, NPC, Player Shell) are queued to default-on in a coordinated commit and the rename items (R1–R5 in the inventory) are sequenced as the first 6B commit. Substrate consolidation remains out of scope for 6B.

### Phase 6B-0 — Rename pass for R1–R5 (complete)

**Goal:** Apply the low-risk terminology cleanup items R1–R5 from the Phase 6A inventory before flipping any W5 flag to default-on or removing any legacy consumer. No runtime behavior is changed in Phase 6B-0.

- [x] R1 — Function renamed: `validate_w5_actor_situation` → `validate_w5_actor_tracking`. Definition in `ai_stack/actor_tracking/validation.py`, re-export from `ai_stack/actor_tracking/__init__.py`, production callsite in `ai_stack/story_runtime/turn/god_of_carnage_turn_seams_validation.py`, and all twelve test callsites in `ai_stack/tests/test_w5_actor_tracking_validation.py` updated atomically. No backward alias retained; the call graph is enumerated and small.
- [x] R2 — Diagnostic string renamed: `failure_class = "w5_actor_situation_validation"` → `"w5_actor_tracking_validation"` in `ai_stack/story_runtime/turn/god_of_carnage_turn_seams_validation.py`. No downstream consumer/filter in production code asserts the old value.
- [x] R3 — Docstring path updated in `ai_stack/actor_tracking/models.py` from `docs/ADR/adr-0063-w5-actor-situation-tracker.md` to `docs/ADR/adr-0063-w5-actor-tracking.md`.
- [x] R4 — Docstring paths updated in `ai_stack/actor_tracking/__init__.py` and `ai_stack/actor_tracking/extractor.py` from `docs/MVPs/w5_actor_situation_migration.md` to `docs/MVPs/w5_actor_tracking_migration.md`. `__init__.py` retains a single historical sentence noting the prior package names — historical context only, not a current-state claim.
- [x] R5 — Docstring path updated in `ai_stack/actor_tracking/projection.py` from `docs/MVPs/w5_actor_situation_migration.md` to `docs/MVPs/w5_actor_tracking_migration.md`.
- [x] Forbidden package scan still reports zero active imports of `ai_stack/actor_situation` or `ai_stack/w5_actor_situation`.
- [x] No W5 feature flag was flipped; no legacy fallback or substrate writer was modified; no committed-event mutation introduced.
- [x] Substrate fields `current_room`, `actor_locations`, `gathering_scene_id`, `transition_from_previous`, and `complete_actor_locations_for_gathering` are untouched.

**Note on `player_actor_situation`:** The W5 player-shell projection payload retains the key `where_summary.player_actor_situation` (`ai_stack/actor_tracking/projection.py`). This is a runtime payload field, semantically *the situation an actor is in*, not a reference to the deprecated package name. It is **not** in the R1–R5 scope and was deliberately left untouched.

### Phase 6B-1 — Default-on W5 consumer flags (complete)

**Goal:** Flip the five W5 consumer flags to default-on in one coordinated commit so W5 Actor Tracking becomes the default higher-level actor-situation authority for Director, Narrator, NPC planning, validation, and player shell/frontend. Legacy fallbacks remain in place for this phase; no legacy code is removed.

- [x] `W5_AST_DIRECTOR_PROJECTION_ENABLED` default flipped to **enabled** in `ai_stack/langgraph/runtime_executor/director_location_completion.py` (SOURCE_LINES). Explicit env override `0/false/no/off` continues to disable.
- [x] `W5_AST_NARRATOR_PROJECTION_ENABLED` default flipped to **enabled** in `world-engine/app/story_runtime/manager/opening_fallback_observability.py::_w5_ast_narrator_projection_enabled`. Explicit opt-out preserved.
- [x] `W5_AST_NPC_PROJECTION_ENABLED` default flipped to **enabled** in `ai_stack/langgraph/runtime_executor/reaction_order_governance.py` (SOURCE_LINES). Explicit opt-out preserved.
- [x] `W5_AST_VALIDATION_ENABLED` default flipped to **enabled** in `ai_stack/actor_tracking/validation.py::w5_ast_validation_enabled`. Explicit opt-out preserved.
- [x] `W5_AST_FRONTEND_PLAYER_VIEW_ENABLED` default flipped to **enabled** in `world-engine/app/story_runtime/manager/actor_tracking/session_state_w5_view.py::_w5_ast_frontend_player_view_enabled`. Explicit opt-out preserved.
- [x] Reporter helper `ai_stack/actor_tracking/diagnostics.py::_flag_enabled` mirrors the new default-on semantics so `w5_projection_flag_states()` reflects runtime gate behavior.
- [x] Fallback behavior preserved end-to-end:
  - Narrator: legacy `transition_from_previous` block stays in `source_facts`; W5 projection is added when the snapshot is well-formed.
  - Director/Gathering: `complete_actor_locations_for_gathering` baseline still runs; W5 projection only replaces the actor-location substrate when the snapshot is well-formed. ADR-0061 pause predicate unchanged.
  - NPC: legacy NPC context fields remain; W5 projection augments per-actor when the snapshot is well-formed; projection failures are diagnostic-only.
  - Validation: legacy validation seam remains canonical; W5 validation runs after Actor Lane has accepted; missing/malformed snapshot records a fallback diagnostic and does not fail the turn.
  - Player shell: legacy `current_room` / `current_room_id` remains the compatibility fallback; W5 player view is preferred when valid.
- [x] Safety semantics unchanged:
  - Actor Lane remains authoritative — W5 validation cannot mask Actor Lane rejection.
  - Inferred Why remains soft truth; How remains first-class.
  - LLM output cannot create OBSERVED W5 facts.
  - No mutation of committed events or committed output (the only new entries are the W5 diagnostics/metadata that already existed under explicit opt-in).
- [x] Diagnostics still emitted for each default-on path: narrator `w5_narrator_projection_failed` (on fallback), Director `w5_director_projection_used` / `w5_director_projection_failed` / `derived_actor_locations_source` / `gathering_pause_source`, NPC `w5_npc_projection_used` / `w5_npc_projection_failed` / `npc_projection_source`, validation `w5_validation_enabled` / `w5_validation_ran` / `w5_validation_failure_codes`, player shell `w5_player_view_used` / `current_room_source` / `current_room_mismatch`.
- [x] Tests:
  - `ai_stack/tests/test_w5_actor_tracking_phase_6b1_default_on_flags.py` pins the resolver matrix (5 flags × default-on + explicit opt-out + explicit opt-in) with semantic assertions, and verifies the SOURCE_LINES-assembled Director and NPC resolvers via `ai_stack.langgraph.runtime_executor.public`.
  - `world-engine/tests/test_story_runtime_w5_narrator_projection.py` covers default-on adds W5 projection + legacy fallback present; explicit `0` opt-out reverts to legacy.
  - `world-engine/tests/test_story_runtime_w5_player_view.py` covers default-on adds W5 player view and `feature_flags`; explicit `0` opt-out reverts.
  - `ai_stack/tests/test_w5_actor_tracking_validation.py` covers default-on W5 validation runs after Actor Lane, does not mask Actor Lane rejection, and explicit `0` opt-out leaves the seam unchanged.
  - `ai_stack/tests/test_npc_agency_planner.py` covers default-on actor-specific NPC projection (privacy preserved) and explicit `0` opt-out reverts to legacy NPC context.
- [x] Migration & inventory doc updated to mark this phase complete and to note that the next phase should inspect which fallback branches are now dead under default config.

**Phase 6B-1 explicitly does not remove any legacy code path.** Legacy fallbacks remain temporarily so any operator who opts a flag out gets the pre-Phase-6B-1 behavior exactly. The next phase (Phase 6B-2, planned) is a fallback / dead-branch inventory that catalogs which legacy branches are now unreachable under the default config and which still serve as explicit-opt-out paths.

### Phase 6B-2 — Fallback / dead-branch inventory under default-on W5 (complete)

**Goal:** With all five W5 consumer flags now default-on, catalog every remaining legacy fallback branch and classify each one so Phase 6B-3 can remove or migrate only branches that are demonstrably safe to touch. **No legacy code is removed in Phase 6B-2.**

- [x] Inventoried every fallback branch in: Director gathering (`director_w5_location_projection.py`, `director_location_completion.py`), narrator (`world-engine/.../actor_tracking/w5_projection.py`, `god_of_carnage_narrator_path.py`, `narrator_output_prompts.py`, `opening_fallback_observability.py`), NPC (`reaction_order_governance.py`, `npc_agency_projection.py`), validation (`validation.py`, `god_of_carnage_turn_seams_validation.py`), player-shell (`session_state_w5_view.py`, backend `game_routes.py::_player_shell_state_view`), admin diagnostics bridge (`diagnostics_api.py`), and the inline action-resolution substrate reads (`executor_action_resolution_start.py`, `executor_action_resolution_commit.py`).
- [x] Classified all 25 catalogued branches against the 6B-2 taxonomy (`keep_explicit_opt_out_fallback`, `keep_malformed_w5_safety_fallback`, `remove_dead_default_path_in_6b3`, `migrate_to_w5_first_before_removal`, `substrate_keep`, `doc_only_update`, `unknown_needs_runtime_trace`). Result by classification: 5 opt-out, 5 malformed-W5 safety, 5 substrate, 8 migrate-to-W5-first, 2 doc-only, **0 dead-default-path**, 0 unknown.
- [x] Recorded the result in [w5_legacy_consumer_removal_inventory.md](./w5_legacy_consumer_removal_inventory.md) with the per-branch fallback-condition matrix (D = default-on happy path, O = explicit opt-out, M = malformed/missing W5, L = legacy client / old session) plus the per-branch pre-removal test list.
- [x] Documented why **no branch can be removed unconditionally in 6B-3**: every fallback that fires under default-on is either the opt-out short-circuit, the malformed-W5 safety net, substrate or substrate-derived, or still feeds a downstream consumer that has not been migrated to a W5-first contract.
- [x] Recommended Phase 6B-3 ordering as four sequenced *consumer migrations* (not branch deletions): (1) F1 lazy re-order in `director_w5_location_projection.py`, (2) F21/F22 W5-first reads in the executor action-resolution split, (3) F8/F18/F19 sequenced removal of the narrator `transition_from_previous` fallback once the narrator prompt is W5-only and parity tests are rewritten, (4) F11 NPC planner W5-first migration once the planner test suites are pinned. F17/F23/F24 remain deferred to later ADRs.
- [x] Added Phase 6B-2 classification-proof tests in `ai_stack/tests/test_w5_actor_tracking_phase_6b2_fallback_inventory.py` covering:
  - default-on Director happy path uses `w5_projection` source (legacy-only fallback is not primary);
  - explicit-opt-out Director path returns baseline (`environment_state_with_actor_lane_fallback`);
  - malformed-W5 Director path returns baseline and emits `w5_director_projection_failed`;
  - default-on narrator happy path does not emit `w5_narrator_projection_failed`;
  - default-on validation happy path does not emit `w5_validation_fallback_reason`;
  - default-on player-view happy path emits `current_room_source == "w5_player_view"` (not `"fallback"`);
  - default-on NPC happy path emits `npc_projection_source == "w5_projection"` (not `"actor_lane_context"`);
  - reporter `w5_projection_flag_states()` matches the live resolver state under default-on.
- [x] Extended `scripts/inventory_w5_legacy_consumers.py` with a Phase 6B-2 informational header that labels each surface with its 6B-2 classification (substrate vs opt-out vs malformed vs alias). The script remains non-failing.

**Phase 6B-2 explicitly does not change runtime behavior.** No flag default was changed. No legacy function was renamed or deleted. No committed-event output was modified. The only code additions are (a) the classification-proof tests, (b) the inventory script's informational labels, and (c) the documentation updates here and in the inventory doc.

### Phase 6B-3A — Director eager-baseline lazy reorder + Executor W5-first reads (complete)

**Goal:** Land the first two sequenced consumer migrations of Phase 6B-3 — the **F1** lazy re-order of the Director eager baseline and the **F21 / F22** W5-first reads in the executor action-resolution split — without removing any opt-out short-circuit, malformed-W5 safety net, substrate read, or public compatibility alias. No committed-event output is mutated.

**F1 — Director eager-baseline lazy re-order**

- [x] `complete_actor_locations_for_gathering_with_optional_w5_projection` (`ai_stack/langgraph/runtime_executor/director_w5_location_projection.py` SOURCE_LINES) no longer pre-computes the eager `baseline_completion = complete_actor_locations_for_gathering(...)` at function entry. The legacy completion is now invoked **only** inside the two return paths that need it:
  - the explicit-opt-out short-circuit (`if not enabled:`),
  - the malformed-W5 `except Exception as exc:` branch.
- [x] The default-on happy path no longer performs the wasted baseline computation under `D`. The W5-success branch still runs its own completion call (F4 in the Phase 6B-2 inventory) over W5-derived actor locations; ADR-0061 pause semantics, `gathering_scene_id` derivation, and NPC fallback voting are unchanged.
- [x] Output is bit-for-bit identical on `D`, `O`, and `M` paths. The function still returns the same `{"location_completion": …, "diagnostics": …, "w5_projection": …}` envelope on every path.
- [x] `complete_actor_locations_for_gathering` (the legacy completion algorithm) is **not** removed; it remains the single source of truth for NPC fallback voting and gathering_scene_id derivation (substrate_keep / F5 in the Phase 6B-2 inventory).

**F21 / F22 — Executor action-resolution W5-first reads**

- [x] New helper `resolve_w5_first_actor_locations(...)` (also under `director_w5_location_projection.py` SOURCE_LINES, re-exported from `ai_stack.langgraph.runtime_executor.public`) classifies the actor-location read into one of four sources:
  - `w5_projection` — default-on happy path; W5 `where_summary.derived_actor_locations` won.
  - `explicit_opt_out_legacy` — `W5_AST_DIRECTOR_PROJECTION_ENABLED=0/false/no/off`.
  - `malformed_w5_fallback` — default-on but `build_w5_projection_for_director(...)` raised or returned no usable derived_actor_locations.
  - `old_payload_legacy` — default-on but no `w5_latest_snapshot` in graph state (pre-Phase-1 session or missing wire-in).
- [x] `executor_action_resolution_start.py` SOURCE_LINES now calls `resolve_w5_first_actor_locations(...)` to compute `_pr_c_actor_locations_raw`, replacing the inline `state.get("actor_locations")` → `environment_state.actor_locations` chain. Legacy substrate reads remain as the helper's fallback inputs.
- [x] `executor_action_resolution_commit.py` SOURCE_LINES emits the resulting `actor_locations_source` diagnostic on `graph_diagnostics`:
  - `graph_diagnostics["actor_locations_source"]["source"]` is one of the four classification strings above.
  - `graph_diagnostics["actor_locations_source"]["w5_snapshot_id"]` is set when `source == "w5_projection"`.
  - `graph_diagnostics["actor_locations_source"]["failure_reason"]` is set when `source == "malformed_w5_fallback"`.
- [x] No committed event is mutated. The `director_gathering_state` payload, the actor lane, the canonical path, `validation_outcome`, and ADR-0061 pause semantics are unchanged. The new diagnostic lives entirely on `graph_diagnostics` (read-side observability surface).
- [x] `complete_actor_locations_for_gathering_with_optional_w5_projection` is unchanged on the wire — the executor still passes it the same `actor_locations=...` keyword (now W5-derived under `D`, legacy under `O` / `M` / `L`). F1 then runs its own W5 attempt against the same snapshot for the `w5_director_projection` diagnostic the admin surfaces already read.

**Fallback behavior preserved**

- [x] Explicit opt-out (`W5_AST_DIRECTOR_PROJECTION_ENABLED=0/false/no/off`) continues to revert the Director and the F21/F22 reads to the legacy substrate verbatim. The F1 opt-out short-circuit (F2 in the inventory) is preserved.
- [x] Malformed/missing W5 snapshots continue to fall back to the legacy baseline completion (F3 in the inventory) and the malformed-W5 source classification at F21/F22.
- [x] Old sessions without a `w5_latest_snapshot` in graph state continue to use the legacy substrate at F21/F22 with `source == "old_payload_legacy"` and at F1 with the malformed-W5 safety branch (`missing_w5_latest_snapshot`).
- [x] Public compatibility aliases remain in place: `current_room`, `current_room_id`, `gathering_scene_id`, and `complete_actor_locations_for_gathering` are all preserved.

**Diagnostics added / updated**

- [x] `graph_diagnostics["actor_locations_source"]` — typed source classifier as above. New in Phase 6B-3A.
- [x] `graph_diagnostics["w5_director_projection"]` — existing F22 diagnostic preserved verbatim under default-on; opt-out continues to suppress it.
- [x] `graph_diagnostics["actor_location_completion"]` — emitted unchanged on the diagnostic_blocker path.
- [x] F1 internal diagnostics (`w5_director_projection_used`, `w5_director_projection_failed`, `w5_snapshot_id`, `derived_actor_locations_source`, `gathering_pause_source`) are unchanged.

**Tests**

- [x] New `ai_stack/tests/test_w5_actor_tracking_phase_6b3a_consumer_migration.py` pins:
  - F1 lazy reorder happy path (`D`), opt-out (`O`) bit-for-bit envelope, malformed-W5 (`M`) baseline + `w5_director_projection_failed`, and the W5-success → legacy completion-call parity (F1 ↔ F4 contract).
  - F21/F22 helper `resolve_w5_first_actor_locations(...)` four-way classification: `w5_projection`, `explicit_opt_out_legacy`, `malformed_w5_fallback`, `old_payload_legacy`. Each case asserts the resolved `actor_locations`, the `source` tag, the `w5_snapshot_id`, the `failure_reason`, defensive-copy semantics, and that the explicit `w5_director_projection_enabled=...` argument overrides the environment variable.
- [x] Existing `ai_stack/tests/test_phase1_live_wiring.py`, `ai_stack/tests/test_pr_c_director_pause_mode.py`, `ai_stack/tests/test_w5_actor_tracking_phase_6b1_default_on_flags.py`, and `ai_stack/tests/test_w5_actor_tracking_phase_6b2_fallback_inventory.py` continue to pass against the lazy reorder — they pin the F1 envelope on every path.
- [x] `tests/test_inventory_w5_legacy_consumers.py` continues to pass; the inventory script reports the same forbidden-package state and the same R1–R5 rename guarantees.

**Phase 6B-3A explicitly does not start narrator transition migration (F8/F18/F19) and does not start NPC legacy-context removal (F11).** Those are sequenced as Phase 6B-3B / 6B-3C and require their own pre-removal parity-test rewrites (see [w5_legacy_consumer_removal_inventory.md](./w5_legacy_consumer_removal_inventory.md) Phase 6B-3 ordering).

### Phase 6B-3B — Narrator `transition_from_previous` migration behind strict flag (complete)

**Goal:** Migrate the F8 / F18 / F19 / F20 narrator-transition surfaces toward W5-only narrator situation input behind a new opt-in strict flag `W5_AST_NARRATOR_STRICT_ENABLED`. No legacy code is removed; no committed event is mutated; explicit opt-out and malformed-W5 safety fallbacks are preserved.

**New strict flag — `W5_AST_NARRATOR_STRICT_ENABLED` (opt-in, default-off)**

- [x] Resolver `w5_ast_narrator_strict_enabled()` added at `ai_stack/actor_tracking/diagnostics.py` SOURCE_LINES and re-exported from `ai_stack.actor_tracking` (`__init__.py`).
- [x] Default-off semantics (opt-in, opposite of the default-on `W5_AST_NARRATOR_PROJECTION_ENABLED`):
  - unset / empty / explicit `0/false/no/off` → strict mode disabled (Phase 6B-3A behavior preserved bit-for-bit).
  - explicit `1/true/yes/on` (case-insensitive) → strict mode enabled.
- [x] Independent of `W5_AST_NARRATOR_PROJECTION_ENABLED` — toggling projection does not change strict state and vice versa.
- [x] Reporter `w5_projection_flag_states()` exposes the strict flag under the `"narrator_strict"` key alongside the five Phase 6B-1 consumer flags.

**F8 — narrator path `source_facts.transition_from_previous` migration**

- [x] `ai_stack/story_runtime/narrator/god_of_carnage_narrator_path.py::_block` SOURCE_LINES now consults the strict resolver.
- [x] Under strict-OFF (default): `source_facts["transition_from_previous"] = _transition_facts(...)` is emitted exactly as in Phase 6B-3A — first-class narrator situation input, fully wired to the legacy fallback paragraph.
- [x] Under strict-ON: `source_facts["transition_from_previous"]` is **omitted** from the top-level contract and the same payload is demoted into `source_facts["_legacy_compat"]["transition_from_previous"]`, accompanied by `authority="w5_projection"` and a `notice` string declaring the W5 narrator projection as authoritative. Authored `directed_transition.kind == "hard_cut"` remains inspectable for operator parity under `_legacy_compat`.
- [x] No other narrator path output changes: canonical step IDs, block ids, mandatory beat coverage, `mandatory_beat.coverage_cues`, location resolution, and visual emphasis are unchanged under both postures.

**F18 — narrator prompt fallback paragraph migration**

- [x] `world-engine/app/story_runtime/manager/narrator_output_prompts.py::_narrator_path_output_prompt` SOURCE_LINES now branches on the strict resolver.
- [x] Under strict-OFF: the prompt continues to instruct the narrator that `source_facts.w5_projection` is primary and `source_facts.transition_from_previous` is the fallback, including the hard-cut directed-transition guidance.
- [x] Under strict-ON: the fallback paragraph is replaced with a W5-only paragraph that:
  - names `who_summary` / `where_summary` / `what_summary` / `how_summary` / `why_summary` explicitly;
  - keeps `how_summary` first-class and forbids folding it into `what_summary`;
  - marks `why_summary` as inferred / soft truth and forbids narrating it as observed fact;
  - explicitly instructs the narrator **not** to consult `source_facts.transition_from_previous` and treats `source_facts._legacy_compat` as non-authoritative debug breadcrumbs only.
- [x] Both postures preserve the Who / Where / What / How / Why guidance contract. Inferred Why remains soft truth. How is first-class.

**F19 — opening fallback observability wording**

- [x] `world-engine/app/story_runtime/manager/opening_fallback_observability.py::_w5_ast_narrator_projection_enabled` docstring SOURCE_LINES rewritten to W5-first / `transition_from_previous`-legacy-compatibility language. The docstring now explicitly notes that under Phase 6B-3B strict mode the legacy block is demoted into `source_facts._legacy_compat` and the prompt fallback paragraph is removed. The resolver itself is unchanged; the Phase 6B-1 default-on / explicit-opt-out semantics for `W5_AST_NARRATOR_PROJECTION_ENABLED` are preserved.

**F20 — admin parity bridge under strict flag**

- [x] `world-engine/app/story_runtime/manager/diagnostics_api.py::get_w5_langfuse_metadata` SOURCE_LINES now consults the strict resolver and annotates the returned payload accordingly:
  - `w5.location_changed_this_turn` continues to be computed primarily from the typed W5 history projection (per-actor `where.value` comparison across `w5_history[-2]` and `w5_history[-1]`). `transition_from_previous.location_changed` is **not** read by the admin bridge under either posture.
  - `w5.location_changed_source` is `"w5_history_projection"` when the bridge succeeds and `"w5_history_insufficient"` when fewer than two snapshots are available; `w5.location_changed_compute_failed=True` is set on per-actor extraction errors.
  - `w5.narrator_strict_enabled` mirrors the resolver under both postures.
  - `w5.legacy_transition_parity` is `"legacy_compat_visible"` under strict-OFF (operators may correlate against `source_facts.transition_from_previous` from committed narrator blocks) and `"demoted_to_legacy_compat"` under strict-ON (parity surface is non-authoritative debug breadcrumb).
- [x] Existing payload keys (`w5.snapshot_id`, `w5.actor_count`, `w5.unresolved_conflict_count`, `w5.has_how`, `w5.has_inferred_why`, `w5.validation_enabled`, `w5.validation_failed`, `w5.validation_failure_codes`) are unchanged. The admin parity bridge does not produce committed-event output.

**Fallback behavior preserved**

- [x] Explicit opt-out for narrator projection (`W5_AST_NARRATOR_PROJECTION_ENABLED=0/false/no/off`) still suppresses `source_facts.w5_projection` and the malformed-W5 safety branch still records `w5_narrator_projection_failed` — independent of the strict flag.
- [x] Public compatibility aliases (`current_room`, `current_room_id`, `actor_locations`, `gathering_scene_id`, `complete_actor_locations_for_gathering`) are unchanged.
- [x] No legacy function or fallback branch is removed. `_transition_facts(...)` is still computed under both strict postures — strict mode only changes where the payload lands in `source_facts`.
- [x] How remains first-class. Inferred Why remains soft truth. Actor Lane, Commit/Readiness, `validation_outcome`, ADR-0033, ADR-0061, ADR-0063, the Canonical Path, and W5 validation semantics are all unchanged.

**Tests added / updated**

- [x] New `ai_stack/tests/test_w5_actor_tracking_phase_6b3b_narrator_strict_migration.py` pins:
  - `W5_AST_NARRATOR_STRICT_ENABLED` resolver default-off / explicit-on / explicit-off / independence-from-projection contract.
  - F8 strict-OFF default and explicit-`false` keep `source_facts["transition_from_previous"]` first-class and `_legacy_compat` absent.
  - F8 strict-ON removes `transition_from_previous` from the top-level `source_facts` and demotes it under `_legacy_compat` with `authority="w5_projection"` and a non-authoritative `notice`.
  - F8 strict-ON preserves canonical step IDs, block ids, mandatory-beat coverage, and the authored `hard_cut` directed-transition breadcrumb.
  - Strict flag does not regress Phase 6B-1 default-on Narrator / Director / NPC / Player-shell / Validation flags.
- [x] New `world-engine/tests/test_story_runtime_w5_narrator_strict_migration.py` pins:
  - F18 strict-OFF keeps the legacy fallback paragraph and hard-cut guidance; F18 strict-ON removes them and forbids consulting `source_facts.transition_from_previous`.
  - F18 both postures preserve Who / Where / What / How / Why guidance and keep `how_summary` first-class and inferred `why_summary` soft.
  - F20 strict-OFF reads W5 history first and labels parity surface `legacy_compat_visible`; F20 strict-ON labels it `demoted_to_legacy_compat`; F20 strict-ON ignores stray legacy `transition_from_previous.location_changed=True` claims in session diagnostics.
- [x] Updated `ai_stack/tests/test_w5_actor_tracking_phase_6b1_default_on_flags.py` and `ai_stack/tests/test_w5_actor_tracking_phase_6b2_fallback_inventory.py` reporter-shape assertions to include the new `narrator_strict` key under default-off. The Phase 6B-1 default-on contract for the five consumer flags is unchanged.
- [x] Existing `world-engine/tests/test_story_runtime_w5_narrator_projection.py` Phase 2 / Phase 6B-1 parity tests remain green under strict-OFF (the legacy `transition_from_previous` block in narrator `source_facts` is still present alongside `w5_projection`).
- [x] Existing `ai_stack/tests/test_god_of_carnage_narrator_path.py` and `world-engine/tests/test_goc_narrator_path_opening.py` opening-start contract tests remain green under strict-OFF.

**Phase 6B-3B explicitly does not** delete the `transition_from_previous` block, the prompt fallback paragraph, or the admin parity bridge. The legacy block is gated behind an opt-in strict flag; the F11 NPC legacy-context-bundle removal is left untouched and sequenced as Phase 6B-3C.

### Phase 6B-3C — NPC planner W5-first migration (planned)

- F11 NPC planner W5-first migration: pass `npc_w5_situations` first into the planner contract; treat `npc_context_bundle` as a malformed-W5 fallback. Pin `test_npc_agency_planner.py`, `test_npc_agency_contracts.py`, `test_npc_agency_long_horizon_claim_readiness.py`, and `test_wave3_multi_actor_vitality.py` before removing the bundle from the non-fallback call path.

### Phase 6B — Legacy localization decommission (planned)

- Once all consumers read W5 projections, remove legacy localization / actor-location helpers that bypass W5.
- `environment_state` remains, but only as substrate input to the extractor.
- The full removal order, risk ranking, and required pre-removal tests are documented in [w5_legacy_consumer_removal_inventory.md](./w5_legacy_consumer_removal_inventory.md).

### Phase 7 — Retention / compaction (planned)

- Define retention policy for `w5_history` (e.g., compact prior snapshots into `superseded` status with bounded scrollback).
- Until then, `w5_history` is unbounded per session.

---

## Schema reference (Phase 1)

All enum **values** are `lower_snake_case` strings (Python member names may be `UPPER_CASE`).

### Dimensions

`W5Dimension` ∈ `{ who, where, what, how, why }`.

### Truth levels

`W5TruthLevel` ∈ `{ canonical, observed, declared, director_assigned, inferred, projected }`.

Rules:
- INFERRED `why.*` must never become OBSERVED unless a future explicit engine-owned commit path / ADR defines the promotion.
- PROJECTED is not a committed fact truth level.
- LLM structured output must never create OBSERVED facts directly.

### Sources

`W5Source` ∈ `{ canonical_content, committed_action, participant_state_move, free_player_action_resolution, director_gathering_state, director_composition, npc_agency_simulation, character_mind_record, sensory_context_engine, souffleuse, narrator_composition, admin_override }`.

Source rules:
- `committed_action` / `participant_state_move` may produce OBSERVED `where`/`what` only after substrate commit.
- `free_player_action_resolution` usually produces DECLARED until committed.
- `character_mind_record` / `npc_agency_simulation` may produce INFERRED `how`/`why`.
- `souffleuse` / `narrator_composition` are projection-lane only.
- `admin_override` is audited and must never produce OBSERVED.

### Visibility, status, freshness, action state, conflict resolution

- `W5VisibilityScope` ∈ `{ public, private_to_actor, gm_only, director_only }`.
- `W5FactStatus` ∈ `{ active, stale, superseded, contradicted, resolved, pending_validation }`.
- `W5FreshnessStatus` ∈ `{ fresh, aging, stale }`.
- `W5ActorType` ∈ `{ human, npc, narrator }`.
- `W5ProjectionConsumer` ∈ `{ narrator, npc, director, player_shell, admin, diagnostics }`.
- `W5ActionState` ∈ `{ starting, ongoing, completed, interrupted, stale }`.
- `W5ConflictResolutionStatus` ∈ `{ unresolved, resolved, pending_director }`.
- `W5ValidationFailureCode` ∈ `{ w5_actor_not_present, w5_location_continuity_break, w5_perception_break, w5_action_continuity_break, w5_unresolved_conflict }`.

### Recommended fact key set

- `who.*` — `actor_type`, `actor_role_in_scene`, `involvement_type`.
- `where.*` — `scene_location`, `local_position`, `relative_position`, `proximity`, `movement_state`, `visibility_audibility`.
- `what.*` — `current_action`, `current_state`, `target_actor_id`, `target_object_id`, `target_location_id`, `interaction_type`, `action_state`.
- `how.*` — `tone`, `manner`, `intensity`, `pace`, `physicality`, `method`, `style`.
- `why.*` — `motive`, `trigger`, `goal`, `pressure`, `dramatic_function`, `reaction_to`.

### Recommended confidence defaults

- `canonical`: `1.0`
- `observed`: `1.0`
- `director_assigned`: `0.9`
- `declared`: `0.6`
- `inferred`: `0.4`
- `projected`: never written as fact truth; projection metadata preserves the source fact confidence.

---

## Wire-in point (Phase 1)

Shadow extraction is invoked from
`world-engine/app/story_runtime/manager/` in `StoryRuntimeManager._finalize_committed_turn`,
between `committed_record["lifecycle_state"] = "observed"` /
`session.diagnostics.append(event)` and `self._persist_session(session)`.

Extraction is **best-effort**: any exception is caught, recorded as a `w5_shadow_extraction_failed` diagnostic, and **does not fail the turn**. Phase 1 is shadow-only and must not change live runtime behavior.

---

## Non-goals (explicit, until later phases)

- No consumer migration in Phase 1.
- No removal of legacy localization helpers.
- No changes to narrator / NPC / Director / frontend / admin / validation behavior.
- No bounded retention / compaction of `w5_history`.
- No promotion of INFERRED facts to OBSERVED.
- No projection-side LLM calls in the extractor itself.
