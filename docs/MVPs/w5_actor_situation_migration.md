# W5 Actor Situation Tracker — Migration Plan

**Authoritative ADR:** [ADR-0063](../ADR/adr-0063-w5-actor-situation-tracker.md) — W5 Actor Situation Tracker.

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

- W5 is the actor-situation authority for higher-level consumers.
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

- [x] `ai_stack/w5_actor_situation/` package created with:
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

### Phase 2 — Bounded read-only projections for narrator / NPC consumers (planned)

- Define narrator and NPC `W5Projection` builders.
- Wire dual-read in narrator/NPC code paths behind a feature flag.
- Add equivalence tests comparing legacy actor-location reads against W5 projections.
- No write-side changes.

### Phase 3 — Director / gathering / validation consumers (planned)

- Switch Director gathering composition and validation to read W5 projections.
- Migrate `validation_outcome` evidence to cite W5 facts where it currently cites raw environment fields.
- Maintain dual-read until equivalence is proven.

### Phase 4 — Frontend / admin / observability projections (planned)

- Build `player_shell`, `admin`, and `diagnostics` projections with source/truth attribution metadata (no huge raw ledgers in player/admin views).
- Remove direct reads of `environment_state.actor_locations` from frontend / admin surfaces.

### Phase 5 — Legacy localization decommission (planned)

- Once all consumers read W5 projections, remove legacy localization / actor-location helpers that bypass W5.
- `environment_state` remains, but only as substrate input to the extractor.

### Phase 6 — Retention / compaction (planned)

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
