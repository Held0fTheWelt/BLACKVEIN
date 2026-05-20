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

- [x] Repair stale flat `world-engine/app/story_runtime/manager.py` gate assumptions for the package-based `world-engine/app/story_runtime/manager/` runtime.
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

### Phase 6 — Legacy localization decommission (planned)

- Once all consumers read W5 projections, remove legacy localization / actor-location helpers that bypass W5.
- `environment_state` remains, but only as substrate input to the extractor.

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
`world-engine/app/story_runtime/manager.py` in `StoryRuntimeManager._finalize_committed_turn`,
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
