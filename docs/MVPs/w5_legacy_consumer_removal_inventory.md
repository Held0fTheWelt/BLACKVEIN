# W5 — Phase 6A Legacy Localization Consumer-Removal Inventory

**Phase:** 6A — Inventory and planning only. **No code is removed in this phase.**

**Phase 6B-0 status:** R1–R5 (the rename items) are **complete**. The function `validate_w5_actor_situation` is now `validate_w5_actor_tracking`, the `failure_class` string is now `"w5_actor_tracking_validation"`, and the four docstring/ADR/migration-doc references now point at the renamed-current files. No runtime behavior, fallback, substrate writer, or W5 flag was touched. The rest of this inventory (S, C, A, T, D, U entries) remains as written: Phase 6B-1 may now proceed to default-on flag rollout.

**Authoritative ADR:** [ADR-0063 — W5 Actor Tracking](../ADR/adr-0063-w5-actor-tracking.md).

**Migration plan:** [w5_actor_tracking_migration.md](./w5_actor_tracking_migration.md).

**Active packages (the only places W5 lives):**

- `ai_stack/actor_tracking/` — core W5 models, extractor, projections, validation, diagnostics.
- `world-engine/app/story_runtime/manager/actor_tracking/` — runtime manager helpers and the player-shell W5 view fallback layer.

**Forbidden packages (must never appear):**

- `ai_stack/actor_situation/` — not present in working tree; not referenced by any active import.
- `ai_stack/w5_actor_situation/` — not present in working tree; not referenced by any active import.

As of Phase 6A, the residual mentions of `actor_situation` / `w5_actor_situation` in active code were (a) a function name `validate_w5_actor_situation()`, (b) a `failure_class` string, and (c) docstring references to renamed-away doc files. All were inventoried below and have since been resolved by Phase 6B-0 (see the "Phase 6B-0 status" note above). The only remaining mention is one historical sentence in `ai_stack/actor_tracking/__init__.py` that documents the prior package names for readers tracing the migration; it is not a current-state claim.

---

## Inventory method

1. Grep across the entire repository for every legacy surface enumerated by the Phase 6A scope:
   - `current_room`, `current_room_id`, `current_area`, `previous_room_id`
   - `actor_locations`, `participant.current_room_id`, `snapshot.current_room`
   - `visible_room_ids`, `RuntimeVisibilityPolicy.visible_occupants`
   - `complete_actor_locations_for_gathering`, `gathering_scene_id`, `derived_gathering_room_id`
   - `transition_from_previous.location_changed`
   - direct `environment_state.*` localization reads outside substrate/extractor/compatibility layers
   - forbidden package names (`ai_stack/actor_situation`, `ai_stack/w5_actor_situation`)
2. Cross-reference each match against the current architecture:
   - Is the file the substrate writer (kept)?
   - Is it the W5 extractor (kept)?
   - Is it the compatibility fallback (kept until removal)?
   - Or is it a higher-level consumer still bypassing W5?
3. Confirm the absence of forbidden package directories on disk.
4. Confirm there is **no `import` of either forbidden package** anywhere in active code.
5. Classify and group findings by recommended action.

This inventory was assembled without changing runtime behavior, without enabling any W5 flag, and without removing any legacy code or test.

The `'fy'-suites/delagecy/` reports and `audit_*.json` snapshots are also excluded from the consumer-removal scope; they are read-only audit artifacts that mirror legacy strings as data — they do not consume the legacy surfaces at runtime.

---

## Classification taxonomy

| Tag | Meaning |
|-----|---------|
| `substrate_keep` | Low-level committed substrate writer/reader. Stays in Phase 6B/6C. |
| `w5_authority_consumer_should_migrate` | Higher-level consumer still reading legacy localization directly. Must migrate to a W5 projection before its legacy read can be removed. |
| `compatibility_alias_keep_temporarily` | Explicit Phase 5A/5B compatibility fallback or alias. Keep while the corresponding W5 flag stays optional. |
| `remove_in_phase_6b` | Code/comment/log line that can be deleted once Phase 6B is approved. |
| `rename_in_phase_6b` | Code that survives 6B but should be renamed for naming consistency (e.g., `w5_actor_situation` → `w5_actor_tracking`). |
| `test_only_update` | Test fixture or assertion. Migrate to W5-aware assertions before removing the producer; the test itself is not the consumer. |
| `doc_only_update` | Docstring, ADR text, design log. Update or remove text without behavioral impact. |
| `unrelated_keep` | Mention happens to overlap a legacy keyword but is not the legacy surface (e.g., a CHANGELOG entry, an unrelated dataclass). |

---

## Summary by classification

| Classification | Count |
|----------------|-------|
| `substrate_keep` | 8 |
| `w5_authority_consumer_should_migrate` | 11 |
| `compatibility_alias_keep_temporarily` | 9 |
| `remove_in_phase_6b` | 0 (Phase 6B will introduce the first deletion candidates; nothing is approved for deletion in 6A) |
| `rename_in_phase_6b` | 5 |
| `test_only_update` | 13 |
| `doc_only_update` | 12 |
| `unrelated_keep` | 4 |

**Forbidden package imports found:** 0.

**Phase 6B-1 safe to begin:** Yes, conditionally — see *Recommended Phase 6B removal order* below. Conditions (2) and (3) below are now satisfied by Phase 6B-0; only condition (1) remains as an operational decision: (1) Director gathering, NPC planning, narrator composition, validation, and player shell must each have their W5 flag enabled by default before their legacy fallback can be removed; ~~(2)~~ ✅ the `validate_w5_actor_situation` function and `failure_class = "w5_actor_situation_validation"` string have been renamed to their `*_actor_tracking` analogues; ~~(3)~~ ✅ the four docstring/ADR references to renamed-away files have been repaired. Substrate writers (`apply_action_to_environment_state`, backend/world-engine `engine.py` MOVE_ACTOR effects, the Participant dataclass `current_room_id` field) are explicitly out of scope for 6B per the migration plan.

---

## Substrate writers / readers — `substrate_keep`

These are the low-level committed-substrate writers and the W5 extractor's substrate input. They remain in place until a later, separately-scoped ADR consolidates them.

| # | File | Symbol / scope | Legacy field used | Role | W5 replacement exists? | Recommended action | Risk if removed too early | Required tests before removal |
|---|------|----------------|-------------------|------|------------------------|--------------------|---------------------------|-------------------------------|
| S1 | `ai_stack/contracts/environment_state_contracts.py` | `apply_action_to_environment_state` (`L375+`), `normalize_environment_state` (`L260+`), `_visible_room_ids` (`L155`), `project_environment_state_view` (`L515+`) | `current_room_id`, `previous_room_id`, `current_area`, `actor_locations`, `visible_room_ids` | Substrate writer/reader. Single source of truth for the committed environment-state dict. The W5 extractor reads its output. | N/A — this is the substrate that W5 reads from. | **Keep.** Migration plan §"Target architecture" makes `environment_state` the low-level substrate. | Breaks every higher-level consumer including W5 extraction. | All `ai_stack/tests/test_environment_state_contracts.py` plus W5 extractor regression. |
| S2 | `backend/app/runtime/engine.py` `L46-L347` and `world-engine/app/runtime/engine.py` `L46-L358` | `RuntimeEngine`, MOVE_ACTOR effect handlers, build of `RuntimeSnapshot.current_room` | `actor.current_room_id`, `Participant.current_room_id`, `RuntimeSnapshot.current_room` | Substrate writer for participant location and snapshot composer for the legacy participant lane. | N/A — W5 reads downstream of this commit. | **Keep.** Migration plan defers consolidation of the runtime-engine substrate writers. | Breaks every Backend/World-Engine runtime turn end-to-end. | `world-engine/tests/test_runtime_engine.py`, `test_runtime_commands.py`, `test_runtime_visibility.py`. |
| S3 | `backend/app/runtime/models.py:32` and `world-engine/app/runtime/models.py:25` | `Participant.current_room_id: str` | Participant dataclass field | Persisted runtime participant identity. | N/A. | **Keep.** | Breaks persistence + store recovery (json/sqlalchemy/recovery tests). | `test_store_json.py`, `test_store_sqlalchemy.py`, `test_store_recovery.py`. |
| S4 | `backend/app/runtime/manager.py:144,234` and `world-engine/app/runtime/manager.py:192,239,301,535` | `RuntimeManager` initial-room assignment + move resolution | `current_room_id` | Substrate writer at instance creation; engine-side reader. | N/A. | **Keep.** | Breaks instance bootstrap. | `world-engine/tests/test_runtime_manager.py`. |
| S5 | `backend/app/runtime/visibility.py`, `world-engine/app/runtime/visibility.py` | `RuntimeVisibilityPolicy.visible_occupants`, `RuntimeVisibilityPolicy.is_target_visible`, `build_current_room_payload` | `viewer.current_room_id`, `actor.current_room_id`, `visible_occupants` list | Engine-level visibility policy for the legacy runtime substrate. Lives parallel to W5 perception/audibility facts. | Partial — W5 carries `where.visibility_audibility` per-actor, but Phase 5B has not migrated this engine policy. | **Keep.** Document as substrate-tied. | Breaks legacy visibility test suite and snapshot construction. | `world-engine/tests/test_runtime_visibility.py`, `test_ws_runtime_commands_and_isolation.py`. |
| S6 | `ai_stack/actor_tracking/extractor.py:161-167` | `extract_w5_snapshot_from_committed_event` actor-location read | `environment_state_after.actor_locations` | The pure W5 extractor reads the substrate `actor_locations` map to build OBSERVED `where.scene_location` facts. | This IS the W5 producer. | **Keep.** | Breaks every W5 snapshot. | `ai_stack/tests/test_w5_actor_tracking_extractor.py`. |
| S7 | `ai_stack/actor_tracking/validation.py:170-208` | `_allowed_location_ids`, `_block_location` | reads `current_room_id`, `current_room` from frames/blocks | Validation entry point — reads frame substrate to compare against W5 facts. Must accept legacy frame schema until producers also migrate. | Hybrid. | **Keep** as substrate read. Remove the legacy keys from the *allowed set* only after every block producer emits `where.scene_location`. | False rejections / continuity break errors. | `ai_stack/tests/test_w5_actor_tracking_validation.py`. |
| S8 | `ai_stack/story_runtime/narrator/god_of_carnage_narrator_path.py` `L319-L376` | `_transition_facts` (`location_changed`, `scene_changed`, `transition_from_previous`) | builds `source_facts.transition_from_previous.location_changed` from `previous_*` ↔ `current_*` substrate | Substrate-derived transition block used by the GoC narrator path as the legacy transition input. Phase 2 keeps it as fallback alongside `w5_projection.where_summary.location_changed`. | Yes — `where_summary.location_changed` mirrors it (see `ai_stack/actor_tracking/projection.py:214-221`). | **Keep** until narrator flag flips to W5-only default. | Narrator path loses the legacy transition fallback and silently degrades on missing W5. | `ai_stack/tests/test_god_of_carnage_narrator_path.py`, `world-engine/tests/test_goc_narrator_path_opening.py`, `world-engine/tests/test_story_runtime_w5_narrator_projection.py`. |

---

## Higher-level consumers still reading legacy directly — `w5_authority_consumer_should_migrate`

These consumers should ultimately read a W5 projection (or accept one as an injected substrate) instead of reaching for the legacy substrate. They are **not** removed in Phase 6B; Phase 6B retires their *legacy-only fallback* once a W5 flag is on by default.

| # | File | Symbol | Legacy field used | Role | W5 replacement exists? | Recommended action | Risk if removed too early | Required tests before removal |
|---|------|--------|-------------------|------|------------------------|--------------------|---------------------------|-------------------------------|
| C1 | `ai_stack/langgraph/runtime_executor/director_location_completion.py` | `complete_actor_locations_for_gathering`, `complete_actor_locations_for_gathering_with_optional_w5_projection`, `_w5_director_projection_failure_reason` | reads `actor_locations`, writes `gathering_scene_id` | Director-Pause input completion. Phase 3A wires the optional W5 projection here; legacy completion still runs as baseline. | Yes — Phase 3A `build_w5_projection_for_director` exposes `derived_actor_locations`. | **Keep both code paths.** Phase 6B may drop the *legacy-only* code path *only* after `W5_AST_DIRECTOR_PROJECTION_ENABLED` is the default. | Director-Pause regresses to "missing_actor_locations" for any session predating the W5 default. | `ai_stack/tests/test_phase1_live_wiring.py` (full file), `ai_stack/tests/test_pr_c_director_pause_mode.py`. |
| C2 | `ai_stack/langgraph/runtime_executor/director_w5_location_projection.py` | `_pr_c_director_w5_projection_fragment` | reads `where_summary.derived_actor_locations` from W5 projection; writes `derived_actor_locations`, `derived_actor_locations_source` diagnostics | W5 → Director adapter. Already migrated but still wraps legacy completion. | Yes (this *is* the W5 adapter). | **Keep.** No change in 6B. | None — this is the W5-aware path. | Same as C1. |
| C3 | `ai_stack/langgraph/runtime_executor/executor_action_resolution_start.py:L150-L182` | inline `actor_locations` source resolution + `current_room_id` extraction (`_pr_c_env_state`) | reads `environment_state.actor_locations`, `environment_state.current_room_id` | Live-fix Phase-1 wiring that feeds Director-Pause inputs at action-resolution start. | Partially — same data is in W5 snapshot's `where_summary.facts.scene_location`, but the adapter is in `director_location_completion.py`, not here. | **Migrate** to consume the W5 projection directly when `W5_AST_DIRECTOR_PROJECTION_ENABLED` is on; retain the legacy read as fallback for one phase. | Director-Pause input goes blank for legacy turns mid-flight. | `ai_stack/tests/test_phase1_live_wiring.py`, `tests/smoke/test_thin_path_pr_c_director_pause_live_smoke.py`. |
| C4 | `ai_stack/langgraph/runtime_executor/executor_action_resolution_commit.py:L11-L96` | `_pr_c_actor_locations_raw`, `_pr_c_actor_locations`, `_pr_c_gathering_scene_id`, `_pr_c_w5_director_projection` | mirror of C3 at commit-side | Same flow at commit-side, including the optional `w5_director_projection` diagnostic payload. | Same as C3. | **Migrate** in lockstep with C3. | Same as C3. | Same as C3. |
| C5 | `ai_stack/story_runtime/player_action_resolution.py:142,350,366,390-455` | `_current_area_from_affordance_model`, `_local_context_player_change_safe`, `_resolve_target_id` | reads `current_room_id`, `current_location_id`, `current_area` | Player-action interpretation reads the legacy localization keys from the affordance model / surface. | Not directly. W5 player-shell projection exists but is consumer-side, not producer-side. | **Migrate** to read `w5_player_view.where_summary.scene_location` when present; keep legacy fallback. | Player movement target resolution silently fails for affordances that lack the legacy keys. | `ai_stack/tests/test_player_action_resolution.py`, `ai_stack/tests/test_free_player_action_resolution_contract.py`. |
| C6 | `ai_stack/story_runtime/semantic_planner/semantic_scene_planner.py:679-680` | `_anchor_room_id_from_env` | `env.get("current_room_id") or env.get("current_area")` | Semantic planner fallback chain. | Indirect via W5 `where_summary.scene_location`. | **Migrate** to consume W5 if a planner-scoped projection is added; otherwise keep as benign fallback. | Semantic planner returns `None` for anchor room when both legacy keys absent. | `ai_stack/tests/test_semantic_scene_planner.py`. |
| C7 | `ai_stack/contracts/narrator_consequence_contracts.py:26-280` | `narrator_consequence` payload builder | reads/writes `current_area`, `from_area`, `to_area` on the `current_player_local_context` substrate | Narrator-consequence contract still composes movement metadata from legacy localization fields. | Partial — W5 `where_summary.location_changed` exists; transition `kind` does not yet have a W5 equivalent. | **Migrate** to read W5 first, fall back to legacy. Coordinate with narrator path (S8). | Narrator loses movement framing. | `ai_stack/tests/test_narrator_consequence_contract.py`. |
| C8 | `ai_stack/story_runtime/narrative/sensory_context_engine.py:154,167` | `_current_area_from_affordance` chain | `to_area`, `current_area`, `from_area` | Sensory context engine fallback for stage-level area. | Partial. | **Migrate** to read W5 `where_summary.scene_location`; keep legacy fallback. | Sensory engine produces blank stage on partial substrate. | `ai_stack/tests/test_information_disclosure_contracts.py`, ambient sensory tests. |
| C9 | `ai_stack/language_io/language_adapter.py:338-346`, `ai_stack/module_runtime_policy.py:247` | adapter payload field `current_area` | reads `interaction_surface.current_area` and builds outgoing payload | Language adapter passes the legacy area along; user-facing surface for input interpretation. | Not directly. | **Migrate** in a future phase together with adapter contract refresh (out of scope for Phase 6B). | Language adapter loses scene-anchor in payload. | `ai_stack/tests/test_langgraph_runtime.py`. |
| C10 | `world-engine/app/story_runtime/runtime_world.py:239-401` | `build_runtime_world_from_environment` | builds `runtime_world.current_room_id` from `environment_state`, fills props/actors per-room | Mid-level projector that pre-dates W5. Higher-level consumers read `runtime_world.current_room_id`. | Partially — W5 player-shell view supersedes this for player-facing consumers, but `runtime_world` is still the projection seed. | **Migrate** higher-level callers to W5 (already largely done in Phase 5A/5B); keep `runtime_world` as the substrate projection seed. | Player shell, opening rendering, scene presenter all read from this. | `world-engine/tests/test_story_runtime_runtime_world.py`. |
| C11 | `world-engine/app/story_runtime/manager/dramatic_context_authority.py:210` | reads `session.environment_state.current_room_id` for authority context | direct substrate read | Authority/context composer for dramatic generation. | Not yet — Director-style W5 projection exposes scene_location but not the wider authority context. | **Migrate** to W5 director projection input. | Authority context loses anchor room. | `world-engine/tests/test_story_runtime_w5_narrator_projection.py`, dramatic-authority-specific tests. |

---

## Compatibility aliases — `compatibility_alias_keep_temporarily`

These are the explicit Phase 5A/5B fallbacks that the migration plan keeps until W5 is the default for the corresponding consumer.

| # | File | Symbol | Legacy field used | Role | W5 replacement exists? | Recommended action | Risk if removed too early | Required tests before removal |
|---|------|--------|-------------------|------|------------------------|--------------------|---------------------------|-------------------------------|
| A1 | `world-engine/app/story_runtime/manager/actor_tracking/session_state_w5_view.py:50-59` | `_fallback_current_room_id` | reads `runtime_world.current_room_id`, `environment_state.current_room_id`, `environment_state.current_area` | Player-view fallback when `W5_AST_FRONTEND_PLAYER_VIEW_ENABLED` is off or W5 snapshot missing. Documented Phase 5B compatibility. | Yes — `build_w5_projection_for_player_shell`. | **Keep** until Phase 5C makes W5 the player-shell default. | Player UI shows blank room when flag disabled or W5 missing on the very next deploy. | `backend/tests/test_w5_player_shell_payload.py`, `world-engine/tests/test_story_runtime_w5_player_view.py`. |
| A2 | `backend/app/api/v1/game_routes.py:486-549` | `_attach_w5_player_view_to_view` (effective) | reads `runtime_world.current_room_id`, then prefers `w5_player_view.where_summary.scene_location.value` | Backend route that prefers W5 over legacy when present. | Yes. | **Keep** the fallback. Remove the legacy fallback only when frontend supports W5-only payloads. | Frontend loses `current_room_id`. | `backend/tests/test_play_service_client.py`, `test_player_session_live_opening_contract.py`, `test_game_service_play_http.py`. |
| A3 | `world-engine/app/story_runtime/manager/session/session_lifecycle.py:21` and `manager/runtime_config.py:221` | snapshot composers | `current_room_id` field on emitted snapshot | Snapshot serializers keep `current_room_id` for legacy WS subscribers. | Yes. | **Keep** until WebSocket subscribers consume W5. | WS clients lose `viewer_room_id`. | `world-engine/tests/test_ws_state_transitions.py`, `test_ws_runtime_commands_and_isolation.py`. |
| A4 | `world-engine/app/story_runtime_shell_readout.py:147-180` | `_environment_state_readout`, `_environment_state_brief_readout` | `current_room_id`, `current_area`, `previous_room_id`, `visible_room_ids` | Operator/debug shell readout. | Indirect — admin W5 view exists, but shell readout is a separate diagnostic channel. | **Keep** but consider routing through W5 admin diagnostics in Phase 6C. | Operator readout loses room context. | Manual shell-readout regression. |
| A5 | `world-engine/diagnostics/story_runtime/create_session_runtime_template.py:87-148,344` | template builder | `current_room_id`, `current_area` from world/state | Diagnostic creation template. | None — diagnostic substrate only. | **Keep.** | Diagnostic template build fails. | `world-engine/tests/test_story_runtime_runtime_world.py`. |
| A6 | `world-engine/app/story_runtime/manager/diagnostics_api.py:70-94` | `_w5_runtime_metadata_for_session` | reads `transition_from_previous.location_changed` from any narrator block when computing W5 admin metadata | Phase 4B admin diagnostic bridge. | Yes (W5 itself), but the bridge keeps the legacy parity check. | **Keep**. The bridge intentionally inspects both. | Admin diagnostics loses parity check. | `world-engine/tests/test_story_runtime_w5_admin_diagnostics.py`. |
| A7 | `world-engine/app/story_runtime/manager/narrator_output_prompts.py:48-56` | narrator system-prompt text | mentions `transition_from_previous.location_changed`, `transition_from_previous.directed_transition.kind` | Phase 2 prompt explicitly tells the narrator W5 is primary and `transition_from_previous` is fallback. This is the contractual fallback signal. | Yes. | **Keep** prompt as-is until W5 narrator flag is permanently on; then prune the fallback paragraph. | Narrator loses fallback instruction. | `world-engine/tests/test_story_runtime_w5_narrator_projection.py`. |
| A8 | `world-engine/app/story_runtime/manager/opening_fallback_observability.py:233` | docstring + diagnostic | mentions `transition_from_previous` as fallback | Opening-path observability comment. | Yes. | **Keep**; prune comment in 6B. | None (comment-only). | `world-engine/tests/test_goc_narrator_path_opening.py`. |
| A9 | `ai_stack/actor_tracking/projection.py:588-826,628-660` | `build_w5_projection_for_director` + player-shell projection internals | populates `where_summary.derived_actor_locations`, `where_summary.location_changed` | The W5 projection itself exposes a compatibility map keyed by actor ID so Director can keep its existing pause semantics. | This IS the W5 producer. | **Keep.** Plan-of-record per Phase 3A. | Director-Pause loses its bridge. | `ai_stack/tests/test_w5_actor_tracking_projection.py`. |

---

## Rename targets — `rename_in_phase_6b`

Naming-only items. They survive 6B but must be renamed for consistency with the new `actor_tracking` package name.

| # | Status | File | Symbol | Old name | New name | Note |
|---|--------|------|--------|----------|----------|------|
| R1 | ✅ done (Phase 6B-0) | `ai_stack/actor_tracking/validation.py` (definition) and `__init__.py` (re-export) | function `validate_w5_actor_situation` | `validate_w5_actor_situation` | `validate_w5_actor_tracking` | Function and re-export renamed. Production callsite in `ai_stack/story_runtime/turn/god_of_carnage_turn_seams_validation.py` and all 12 test callsites in `ai_stack/tests/test_w5_actor_tracking_validation.py` updated atomically. No backward alias retained. |
| R2 | ✅ done (Phase 6B-0) | `ai_stack/story_runtime/turn/god_of_carnage_turn_seams_validation.py` | string literal `failure_class = "w5_actor_situation_validation"` | `"w5_actor_situation_validation"` | `"w5_actor_tracking_validation"` | Diagnostic string surfaces through Langfuse metadata. No production consumer/filter asserts the old value. |
| R3 | ✅ done (Phase 6B-0) | `ai_stack/actor_tracking/models.py` | docstring | `docs/ADR/adr-0063-w5-actor-situation-tracker.md` | `docs/ADR/adr-0063-w5-actor-tracking.md` | Pure doc fix. |
| R4 | ✅ done (Phase 6B-0) | `ai_stack/actor_tracking/__init__.py` and `ai_stack/actor_tracking/extractor.py` | docstring | `docs/MVPs/w5_actor_situation_migration.md` | `docs/MVPs/w5_actor_tracking_migration.md` | Pure doc fix. `__init__.py` retains one historical sentence noting prior package names. |
| R5 | ✅ done (Phase 6B-0) | `ai_stack/actor_tracking/projection.py` | docstring | `docs/MVPs/w5_actor_situation_migration.md` | `docs/MVPs/w5_actor_tracking_migration.md` | Same as R4. |

---

## Tests — `test_only_update`

Tests that assert legacy localization fields directly. They are valid as-is; they need to evolve in lockstep with their producer. **None of these tests are weakened in Phase 6A.**

| # | File | Test / assertion | Legacy field used | Role | Recommended action |
|---|------|-------------------|-------------------|------|--------------------|
| T1 | `ai_stack/tests/test_environment_state_contracts.py:56,87-88,127` | substrate roundtrip on `current_room_id`/`previous_room_id`/`actor_locations`/`visible_room_ids` | full set | Substrate contract test. | **Keep.** Substrate stays. |
| T2 | `ai_stack/tests/test_w5_actor_tracking_extractor.py:44-46` | builds `environment_state` with `current_room_id`, `previous_room_id`, `actor_locations` as W5 extractor input | full set | Extractor regression. | **Keep.** |
| T3 | `ai_stack/tests/test_phase1_live_wiring.py` (1,000+ lines using `actor_locations`/`current_room_id`/`gathering_scene_id`) | full Director-Pause + Phase-1 wiring | full set | Director-Pause contract. | **Keep** as semantic tests; do not field-presence-collapse. |
| T4 | `ai_stack/tests/test_pr_c_director_pause_mode.py` (24 calls) | `compute_gathering_state(actor_locations=…)` | `actor_locations` | Director-Pause semantics. | **Keep.** |
| T5 | `ai_stack/tests/test_w5_actor_tracking_projection.py` (5 location_changed tests, derived_actor_locations parity) | `where_summary.location_changed`, `derived_actor_locations` | full set | W5 projection regression. | **Keep.** Includes legacy-parity test that is critical for migration safety. |
| T6 | `ai_stack/tests/test_w5_actor_tracking_validation.py` (12 calls to `validate_w5_actor_situation`) | validation entry point | rename target R1 | Validation regression. | **Update callsites** alongside R1 rename. Do not weaken assertions. |
| T7 | `ai_stack/tests/test_god_of_carnage_narrator_path.py:30-44` | `source_facts.transition_from_previous.location_changed` and `kind=="opening_start"` | transition block | Narrator-path semantics. | **Keep.** Mirrors A7 fallback. |
| T8 | `backend/tests/test_w5_player_shell_payload.py:30-136` | fallback-vs-W5 mismatch parity, includes string-source check for `app.js` | `current_room_id`, `snapshot.current_room` | Player shell payload regression. | **Keep**, but loosen the JS source-string check only when frontend is upgraded. |
| T9 | `backend/tests/runtime/test_runtime_manager_engine.py`, `test_runtime_core.py` | `Participant.current_room_id` constructor + comparisons | `current_room_id` (dataclass field) | Substrate engine tests. | **Keep.** |
| T10 | `world-engine/tests/test_runtime_visibility.py` (8 tests), `test_runtime_commands.py` (10 tests), `test_runtime_engine.py` (4 tests), `test_runtime_manager.py` (2 tests) | participant location + room moves | `current_room_id` | Substrate engine + visibility regression. | **Keep.** |
| T11 | `world-engine/tests/test_ws_state_transitions.py`, `test_ws_runtime_commands_and_isolation.py` (6 hits) | `viewer_room_id`, `current_room`, `visible_occupants` | snapshot fields | WebSocket transport regression. | **Keep.** |
| T12 | `world-engine/tests/test_story_runtime_w5_player_view.py:150-183` | flag-off fallback parity | `current_room_id` | Phase 5B fallback test. | **Keep.** |
| T13 | `world-engine/tests/test_story_runtime_w5_narrator_projection.py` (legacy parity tests at `L137-L290`) | `transition_from_previous.location_changed` ↔ `where_summary.location_changed` parity | both | Phase 2 parity regression. | **Keep.** Critical migration-safety net. |

---

## Documentation — `doc_only_update`

| # | File | Section | Action |
|---|------|---------|--------|
| D1 | `docs/ADR/adr-0063-w5-actor-tracking.md:84` | "Target architecture (later phases)" — already lists legacy fields. | **Keep** as historical reference. |
| D2 | `docs/ADR/adr-0061-director-pause-mode-for-gathering-interruption.md:52,72-74,169,176` | Director-Pause input contract — references `actor_locations`. | **Keep** until Phase 6B re-publishes the Director input as the W5 projection map. |
| D3 | `docs/ADR/adr-0057-canon-safe-player-freedom-and-affordance-inference.md:131` | Resolver/director input. | **Keep**, footnote-link to W5 in Phase 6B. |
| D4 | `docs/MVPs/w5_actor_tracking_migration.md` | Add Phase 6A entry (this Phase). | **Update** with Phase 6A status (handled below). |
| D5 | `docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/runtime_state_and_session_contracts.md:27-30,703-706` | Lists legacy substrate fields as canonical. | **Annotate** in 6B that these are substrate-only; higher-level consumers must read W5. |
| D6 | `docs/implementation_logs/w5_actor_tracking_piv.md:8,13,18` | PIV log mentions legacy `actor_locations`. | **Keep** as history. |
| D7 | `docs/implementation_logs/pr_c_director_pause_mode_piv.md:132` | mentions legacy fallback line and a path that has since been refactored (`langgraph_runtime_executor.py:6340-6343` — that file no longer exists at those lines). | **Refresh path** in 6B to point at the new split files in `ai_stack/langgraph/runtime_executor/`. |
| D8 | `docs/MVPs/npc_interactivity_piv_log.md:33` | references W5 `actor_locations` enrichment. | **Keep** as history; mark phase complete in 6B. |
| D9 | `NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md:232,257,426,499` | Plan doc references `runtime_world.actor_locations`. | **Keep** as plan doc. |
| D10 | `ai_stack/actor_tracking/models.py:3`, `__init__.py:5`, `extractor.py:5`, `projection.py:8` | docstrings reference renamed-away files. | **Update in Phase 6B** (these are rename targets R3/R4/R5). |
| D11 | `ai_stack/langgraph/runtime_executor/director_location_completion.py:27-58,101-108,114-147` and `director_w5_location_projection.py:11-70`, `executor_action_resolution_start.py:150-180`, `executor_action_resolution_commit.py:11-78` | Docstring blocks of refactored runtime executor modules. They describe legacy + W5 behavior. | **Keep** until C1–C4 migrate. |
| D12 | `CHANGELOG.md:2606,2782` | historical entries mentioning `current_room` / `visible_occupants`. | **Keep** as history. |

---

## Unrelated / overlapping mentions — `unrelated_keep`

| # | File | Note |
|---|------|------|
| U1 | `'fy'-suites/delagecy/**` reports, `'fy'-suites/docify/**` baselines | These are audit/legacy-tracker artifacts mirroring the strings as data. They do not consume the surfaces at runtime. Out of Phase 6B scope. |
| U2 | `audit_turn1.json`, `audit_turn2.json`, …, `audit_state_*.json` | Frozen audit snapshots. Out of scope. |
| U3 | `writers-room/app/models/runtime_load_orders.md:283` | Documentation example uses `{{current_room_id}}` as a Jinja-style placeholder for an authoring template — not a runtime consumer. |
| U4 | `engine_run_last.txt`, `failing-tests.txt`, `tests/reports/_stage*.log` | Run logs. Out of scope. |

---

## Highest-risk legacy consumers

Ranked by blast radius if their legacy read is removed before W5 takes over.

1. **`ai_stack/contracts/environment_state_contracts.py`** (`substrate_keep`, S1) — every higher-level consumer and the W5 extractor depend on this.
2. **`backend/app/runtime/engine.py` + `world-engine/app/runtime/engine.py`** (S2) — every committed turn writes through these.
3. **`ai_stack/langgraph/runtime_executor/director_location_completion.py` + `executor_action_resolution_*.py`** (C1, C3, C4) — Director-Pause is composed here per turn; their legacy fallback is the only path when `W5_AST_DIRECTOR_PROJECTION_ENABLED=0`.
4. **`world-engine/app/story_runtime/manager/actor_tracking/session_state_w5_view.py`** (A1) — the player-shell fallback. Removing prematurely breaks every UI session in deploys without W5 default-on.
5. **`world-engine/app/story_runtime/runtime_world.py`** (C10) — mid-level projector that seeds the legacy `runtime_world.current_room_id`. Many downstream consumers still read it.
6. **`ai_stack/contracts/narrator_consequence_contracts.py`** (C7) — narrator movement framing depends on legacy `current_area`/`from_area`/`to_area`.
7. **`ai_stack/story_runtime/narrator/god_of_carnage_narrator_path.py`** (S8) — produces the `transition_from_previous` block consumed by narrator prompts and W5 parity tests.

---

## Recommended Phase 6B removal order

Phase 6B is the **first** phase that may remove code. It must proceed in this order; each step is independently testable.

1. **Rename phase (low-risk, doc + naming only).** Apply R1–R5: rename `validate_w5_actor_situation` → `validate_w5_actor_tracking`, the `failure_class` string, and the four docstring/ADR references. Update the 12 test callsites in `test_w5_actor_tracking_validation.py` and the two callsites in `god_of_carnage_turn_seams_validation.py`. **Test:** `python tests/run_tests.py --suite mvp1` (or equivalent) plus targeted ai_stack tests.

2. **Default-on Director projection.** Make `W5_AST_DIRECTOR_PROJECTION_ENABLED=1` the default. Keep the legacy completion as fallback. Run all gating gates (MVP1–MVP4). **Test:** `pytest ai_stack/tests/test_phase1_live_wiring.py ai_stack/tests/test_pr_c_director_pause_mode.py` plus smoke `tests/smoke/test_thin_path_pr_c_director_pause_live_smoke.py`.

3. **Default-on Narrator projection.** Make `W5_AST_NARRATOR_PROJECTION_ENABLED=1` the default. **Test:** `pytest world-engine/tests/test_story_runtime_w5_narrator_projection.py world-engine/tests/test_goc_narrator_path_opening.py ai_stack/tests/test_god_of_carnage_narrator_path.py`.

4. **Default-on NPC projection.** Make `W5_AST_NPC_PROJECTION_ENABLED=1` the default. **Test:** scoped W5 + NPC planner suites.

5. **Default-on Validation.** Make `W5_AST_VALIDATION_ENABLED=1` the default. **Test:** `pytest ai_stack/tests/test_w5_actor_tracking_validation.py`.

6. **Default-on Player Shell.** Make `W5_AST_FRONTEND_PLAYER_VIEW_ENABLED=1` the default. **Test:** `pytest backend/tests/test_w5_player_shell_payload.py world-engine/tests/test_story_runtime_w5_player_view.py`.

7. **Migrate higher-level consumers** (C5–C11): make each of them prefer the W5 projection unconditionally, with the legacy substrate read only as last-chance fallback.

8. **Remove single-purpose legacy-only fallbacks** in the rename + flag-on consumers (C1–C4 legacy-only path, A7/A8 prompt paragraphs that mention `transition_from_previous` as fallback).

9. **Update docs** (D7, D10) to remove the renamed-away references and stale path pointers.

Phase 6B **does not** touch S1–S8 (substrate) or A1–A9 in a way that breaks the compatibility contract. Substrate consolidation is a separate, later ADR.

---

## Conditions on Phase 6B start

Phase 6B may begin once:

- [x] This inventory has been written and reviewed.
- [x] Forbidden packages (`ai_stack/actor_situation`, `ai_stack/w5_actor_situation`) are confirmed absent. ✅
- [x] No active code imports either forbidden package. ✅
- [x] Active W5 packages (`ai_stack/actor_tracking`, `world-engine/app/story_runtime/manager/actor_tracking`) are the only W5 surfaces. ✅
- [ ] The four W5 flags (Director, Narrator, NPC, Player Shell) are ready to flip to default-on in a single coordinated commit. The codepath supports it today; the operational decision is the open prerequisite.
- [x] The rename items (R1–R5) are landed as Phase 6B-0 (this commit). The rest of 6B (default-on flag rollout, then consumer migration) can now use the new names.

When the one unchecked item above is decided, Phase 6B-1 (default-on Director/Narrator/NPC/Validation/Player-Shell flag rollout) is safe to start. Substrate writers (S1–S8) remain out of scope for 6B and will be addressed by a separate, dedicated ADR.
