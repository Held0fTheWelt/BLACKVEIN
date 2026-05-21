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
- [x] The five W5 flags (Director, Narrator, NPC, Validation, Player Shell) have been flipped to default-on in a single coordinated commit (Phase 6B-1). The legacy fallbacks remain in place; explicit env opt-out (`0/false/no/off`) restores pre-6B-1 behavior.
- [x] The rename items (R1–R5) are landed as Phase 6B-0. The rest of 6B (consumer migration) can now use the new names.

---

## Phase 6B-1 — default-on consumer flags (complete)

Phase 6B-1 flips the five W5 consumer flags to default-on as a single coordinated change. The change is intentionally narrow: only the *default value* of each resolver is flipped, and every legacy fallback branch is preserved.

**Files changed (defaults flipped):**

| Flag | Resolver location | Behavior under default-on |
|------|-------------------|---------------------------|
| `W5_AST_DIRECTOR_PROJECTION_ENABLED` | `ai_stack/langgraph/runtime_executor/director_location_completion.py` (SOURCE_LINES `w5_ast_director_projection_enabled`) | Director/Gathering reads typed W5 projection as actor-location substrate; legacy `complete_actor_locations_for_gathering` remains as fallback. ADR-0061 pause semantics unchanged. |
| `W5_AST_NARRATOR_PROJECTION_ENABLED` | `world-engine/app/story_runtime/manager/opening_fallback_observability.py::_w5_ast_narrator_projection_enabled` | Narrator `source_facts` gets typed `w5_projection`; legacy `transition_from_previous` block remains as fallback. |
| `W5_AST_NPC_PROJECTION_ENABLED` | `ai_stack/langgraph/runtime_executor/reaction_order_governance.py` (SOURCE_LINES `w5_ast_npc_projection_enabled`) | NPC planning gets actor-specific typed W5 projection; legacy NPC context remains as fallback. |
| `W5_AST_VALIDATION_ENABLED` | `ai_stack/actor_tracking/validation.py::w5_ast_validation_enabled` | W5 validation runs after Actor Lane has accepted; Actor Lane remains authoritative; legacy seam stays canonical. |
| `W5_AST_FRONTEND_PLAYER_VIEW_ENABLED` | `world-engine/app/story_runtime/manager/actor_tracking/session_state_w5_view.py::_w5_ast_frontend_player_view_enabled` | Player-shell state exposes typed `w5_player_view` and `feature_flags`; legacy `current_room` / `current_room_id` remains as fallback. |

Reporter helper `ai_stack/actor_tracking/diagnostics.py::_flag_enabled` was updated in lockstep so `w5_projection_flag_states()` and `build_w5_runtime_metadata()` accurately reflect runtime gate state.

**Explicit opt-out preserved.** Every resolver still honors `0/false/no/off` (case-insensitive) as an explicit disable. This is regression-pinned in `ai_stack/tests/test_w5_actor_tracking_phase_6b1_default_on_flags.py`.

**No legacy code removed yet.** Phase 6B-1 deliberately keeps every legacy fallback branch — narrator transition block, Director baseline completion, NPC legacy context, validation seam fallback, `current_room` / `current_room_id` — so opting any single flag out reverts the corresponding consumer to its exact pre-6B-1 path.

**No committed-output mutation.** Default-on does not change committed events. The only new fields visible under default-on are the W5 diagnostics/metadata that were already produced under explicit opt-in (e.g., `w5_director_projection_used`, `w5_player_view_diagnostics`, `feature_flags.W5_AST_FRONTEND_PLAYER_VIEW_ENABLED`, `w5_runtime_metadata.w5_projection_flags_used`).

**Next phase — Phase 6B-2 (planned).** Inspect which fallback branches are now dead under default config. Candidates to investigate (informational, not removed in 6B-1):

- C1 / C4 legacy-only Director completion paths under `complete_actor_locations_for_gathering_with_optional_w5_projection` when the flag is enabled.
- Narrator-only `transition_from_previous` enrichment branches that are never selected when the W5 projection succeeds.
- NPC legacy context fields that are still attached even when W5 projection succeeded.
- Player-shell legacy `current_room` extraction when `w5_player_view` has a valid location.
- Reporter `w5_validation_fallback_reason` emissions that only fire when an operator explicitly opts out.

Substrate writers (S1–S8) and the `Participant.current_room_id` dataclass field remain out of scope for 6B.

---

## Phase 6B-2 — Fallback / dead-branch inventory under default-on W5 (complete)

**Goal:** With all five W5 consumer flags default-on (Phase 6B-1), produce a precise inventory of every remaining legacy fallback branch and classify each one so Phase 6B-3 can remove or migrate only the branches that are demonstrably safe to touch. **No legacy code is removed in Phase 6B-2.**

### Phase 6B-2 classification taxonomy

| Tag | Meaning |
|-----|---------|
| `keep_explicit_opt_out_fallback` | Branch is the path taken when an operator explicitly sets `W5_AST_*=0/false/no/off`. Must remain. |
| `keep_malformed_w5_safety_fallback` | Branch fires when the W5 snapshot is missing, malformed, or cannot project the consumer-specific information. Must remain — this is the safety net the migration plan promises. |
| `remove_dead_default_path_in_6b3` | Default-on never executes the branch; explicit opt-out and malformed-W5 safety are covered by *different* branches; deletion is safe and a small targeted test can pin it. |
| `migrate_to_w5_first_before_removal` | Legacy branch still produces a *parallel* value that is wired into a downstream consumer (prompt text, planner input, frontend payload). The branch cannot be removed until the downstream consumer is migrated to a W5-first contract. Marked for sequenced removal in a later 6B-3.x step. |
| `substrate_keep` | Substrate writer / reader / extractor input. Out of scope for 6B; deferred to a later substrate-consolidation ADR. |
| `test_only_update` | Test asserts a legacy-only field. The producer of the field stays, so the assertion stays; tracked for evolution in lockstep with its producer. |
| `doc_only_update` | Docstring, prompt paragraph, comment, or design-log entry that references the legacy fallback. Update or prune; no runtime impact. |
| `unknown_needs_runtime_trace` | Coverage of the branch under default-on cannot be proven from static reading and requires a live trace before classification. |

### Phase 6B-2 inventory method

1. Read every fallback site enumerated by Phase 6B-1's Phase-6B-2 backlog plus the wider 6A consumer set (C1–C11, A1–A9, S8).
2. For each site, decide which of four conditions actually fires the branch under the live Phase-6B-1 default-on configuration:
   - **D** — default-on happy path (W5 snapshot present and well-formed for that consumer);
   - **O** — explicit opt-out (`0/false/no/off`);
   - **M** — malformed/missing W5 snapshot (default-on but extraction failed or projection raised);
   - **L** — legacy/old-payload compatibility (sessions persisted before Phase 1 wire-in, or external clients that still expect the legacy field).
3. Cross-check static reading against the existing Phase 6B-1 regression suites (`test_w5_actor_tracking_phase_6b1_default_on_flags.py`, `test_story_runtime_w5_narrator_projection.py`, `test_story_runtime_w5_player_view.py`, `test_w5_actor_tracking_validation.py`, `test_npc_agency_planner.py`, `test_w5_actor_tracking_projection.py`) to confirm the conditions are pinned by tests.
4. Tag each branch with the 6B-2 taxonomy. A branch is only ever `remove_dead_default_path_in_6b3` when D ≠ taken AND O is covered by a *different* branch AND M is covered by a *different* branch AND L is either not applicable or covered separately.
5. Order the safe removals.

### Phase 6B-2 fallback branch table (default-on W5)

Conditions: D = default-on happy path; O = explicit opt-out; M = missing/malformed W5; L = legacy client / old session. ✓ = branch fires for that condition. ✗ = branch does not fire.

| # | File:Symbol | Branch | D | O | M | L | Classification | Required test before removal |
|---|-------------|--------|---|---|---|---|----------------|------------------------------|
| F1 | `ai_stack/langgraph/runtime_executor/director_w5_location_projection.py::complete_actor_locations_for_gathering_with_optional_w5_projection` — *eager* `baseline_completion = complete_actor_locations_for_gathering(...)` before the W5 attempt | Always-on baseline pre-compute | ✓ (wasted but its *output* is the safety net only when W5 fails) | ✓ (becomes the return value) | ✓ (becomes the return value) | n/a | `migrate_to_w5_first_before_removal` — the *function* is load-bearing for O+M; only the *eager* placement is wasted under D. Re-arrange to lazy (compute inside the `except` branch and inside the disabled-flag branch) is a 6B-3 optimization, not a 6B legacy removal. Output stays identical. | `test_phase1_live_wiring.py` happy-path assertion that `derived_actor_locations_source=="w5_projection"`; explicit-opt-out test in `test_w5_actor_tracking_phase_6b1_default_on_flags.py`; malformed-snapshot test that returns baseline. |
| F2 | same file — `if not enabled: return {"location_completion": baseline_completion, ...}` | Explicit-opt-out short-circuit | ✗ | ✓ | n/a | n/a | `keep_explicit_opt_out_fallback` | (already pinned by Phase 6B-1 default-on flag test). |
| F3 | same file — `except Exception as exc: diagnostics["w5_director_projection_failed"]=...; return baseline_completion` | Malformed-W5 safety return | ✗ | ✗ | ✓ | n/a | `keep_malformed_w5_safety_fallback` | (already pinned by `test_w5_actor_tracking_projection.py` Director failure cases). |
| F4 | second `complete_actor_locations_for_gathering(...)` *inside* the W5-success branch (lines 56–63) | Substrate re-use of fallback-actor-id + target-location + gathering_scene_id logic with W5-derived actor_locations as input | ✓ | ✗ | ✗ | n/a | `substrate_keep` — not a fallback; it is the consolidation of W5 + actor-lane completion. ADR-0061 pause semantics depend on it. | n/a. |
| F5 | `ai_stack/langgraph/runtime_executor/director_location_completion.py::complete_actor_locations_for_gathering` (legacy completion function itself, NPC fallback voting, gathering_scene_id derivation) | Legacy completion algorithm | ✓ (called from F1 and F4) | ✓ | ✓ | n/a | `substrate_keep` — single source of truth for actor-lane NPC fallback + gathering_scene_id derivation. F1/F4 both invoke it. Cannot be removed in 6B. | n/a. |
| F6 | `world-engine/app/story_runtime/manager/actor_tracking/w5_projection.py::_maybe_enrich_blocks_with_w5_narrator_projection` — `if not self._w5_ast_narrator_projection_enabled(): return source_blocks` | Opt-out short-circuit (no `w5_projection` key added) | ✗ | ✓ | n/a | n/a | `keep_explicit_opt_out_fallback` | (already pinned by `test_story_runtime_w5_narrator_projection.py` opt-out test). |
| F7 | same file — `except Exception as exc: session.diagnostics.append(...w5_narrator_projection_failed...); return source_blocks` | Malformed-W5 safety return | ✗ | ✗ | ✓ | n/a | `keep_malformed_w5_safety_fallback` | New Phase 6B-2 test: default-on happy path emits no `w5_narrator_projection_failed` diagnostic. |
| F8 | `ai_stack/story_runtime/narrator/god_of_carnage_narrator_path.py::_block` line 376 — `source_facts["transition_from_previous"] = _transition_facts(...)` | Always-write legacy transition block | ✓ (written alongside `w5_projection`) | ✓ | ✓ | ✓ | `migrate_to_w5_first_before_removal` — the narrator system prompt still names `transition_from_previous` as the canonical fallback (see A7), and the Phase 2 parity tests assert legacy parity. Removal requires (a) narrator prompt becomes W5-only, (b) parity tests are rewritten to drop legacy parity, (c) opening-fallback observability comment is pruned. Sequenced as 6B-3 step 3. | `test_story_runtime_w5_narrator_projection.py` Phase 2 parity tests; new W5-only narrator prompt test; `test_god_of_carnage_narrator_path.py` `opening_start` kind test. |
| F9 | `ai_stack/langgraph/runtime_executor/reaction_order_governance.py::_build_w5_npc_projection_inputs` — `if not w5_ast_npc_projection_enabled(): return {}, []` | Opt-out short-circuit | ✗ | ✓ | n/a | n/a | `keep_explicit_opt_out_fallback` | (already pinned by Phase 6B-1 flag test). |
| F10 | same file — `except Exception as exc: diagnostic["w5_npc_projection_failed"]=...` per-actor | Per-actor malformed-W5 safety | ✗ | ✗ | ✓ | n/a | `keep_malformed_w5_safety_fallback` | Existing `test_npc_agency_planner.py` failure-case coverage. |
| F11 | `ai_stack/langgraph/runtime_executor/npc_agency_projection.py` — `effective_npc_context_bundle` resolved by `resolve_w5_first_npc_context(...)` then passed into `build_npc_agency_simulation(...)` and the fallback `build_npc_agency_plan(...)` | Phase 6B-3C: W5-first selector. Under D the bundle is demoted to `_legacy_compat` and `effective_npc_context_bundle=None` is forwarded (the `npc_context_bundle` evidence row is absent). Under O / M / L the legacy bundle is forwarded verbatim. | ✗ (D forwards `None`) | ✓ | ✓ | ✓ | `keep_explicit_opt_out_fallback` / `keep_malformed_w5_safety_fallback` / `old_payload_legacy_fallback` — the bundle remains the planner substrate on the three non-`w5_projection` paths. Phase 6B-3C migrated the attachment site without deleting any branch. | ✅ Phase 6B-3C complete. Pinned by `ai_stack/tests/test_w5_actor_tracking_phase_6b3c_npc_planner_migration.py` plus the existing `test_npc_agency_planner.py`, `test_npc_agency_contracts.py`, `test_npc_agency_long_horizon_claim_readiness.py`, and `test_wave3_multi_actor_vitality.py` regressions. |
| F12 | `ai_stack/story_runtime/turn/god_of_carnage_turn_seams_validation.py::_apply_w5_validation_to_outcome` — `if not w5_ast_validation_enabled(): return outcome` | Opt-out short-circuit | ✗ | ✓ | n/a | n/a | `keep_explicit_opt_out_fallback` | (already pinned by Phase 6B-1 validation flag test). |
| F13 | same file — `except Exception as exc: diagnostic = w5_validation_fallback(text)` | Malformed-W5 safety with `w5_validation_fallback_reason` | ✗ | ✗ | ✓ | n/a | `keep_malformed_w5_safety_fallback` | New Phase 6B-2 test: default-on happy path never sets `w5_validation_fallback_reason`. |
| F14 | `world-engine/app/story_runtime/manager/actor_tracking/session_state_w5_view.py::_maybe_build_w5_player_view_for_session` — `if not _w5_ast_frontend_player_view_enabled(): return None, None` | Opt-out short-circuit | ✗ | ✓ | n/a | n/a | `keep_explicit_opt_out_fallback` | (already pinned by Phase 6B-1 player-view flag test). |
| F15 | same file — `except Exception as exc: return None, _player_view_diagnostics(used=False, failed=reason, ...)` | Malformed-W5 safety with `current_room_source="fallback"` | ✗ | ✗ | ✓ | n/a | `keep_malformed_w5_safety_fallback` | New Phase 6B-2 test: default-on happy path emits `current_room_source=="w5_player_view"` (not `"fallback"`). |
| F16 | same file — `_fallback_current_room_id(session)` reads `runtime_world.current_room_id` → `environment_state.current_room_id` → `environment_state.current_area` | Substrate fallback location resolver | ✓ (always computed for the `current_room_fallback_value` diagnostic and mismatch check) | ✓ | ✓ | ✓ | `substrate_keep` — reads committed substrate to surface the mismatch diagnostic. Tied to substrate S1/S2; deferred to later substrate-consolidation ADR. | n/a. |
| F17 | `backend/app/api/v1/game_routes.py::_player_shell_state_view` — `current_room_id` derivation chain (fallback first, then W5 override) | Compatibility alias on the player-shell payload | ✓ (frontend reads it) | ✓ | ✓ | ✓ | `migrate_to_w5_first_before_removal` — the field itself is a legacy *alias*; the frontend `app.js` reads it. Removal requires frontend upgrade and a follow-up ADR (currently A2 in the Phase 6A inventory). Sequenced beyond 6B-3. | `backend/tests/test_w5_player_shell_payload.py` (parity + mismatch), `test_play_service_client.py`, `test_player_session_live_opening_contract.py`. |
| F18 | `world-engine/app/story_runtime/manager/narrator_output_prompts.py` — narrator system-prompt paragraph instructing the LLM to use `transition_from_previous` as fallback | Prompt-text fallback instruction | ✓ (always sent in the prompt) | ✓ | ✓ | ✓ | `doc_only_update` — once F8 is removed, the paragraph is pruned alongside; no runtime branch. Sequenced as 6B-3 step 3 (paired with F8). | `test_story_runtime_w5_narrator_projection.py` prompt-string regression (must update assertion when the paragraph is pruned). |
| F19 | `world-engine/app/story_runtime/manager/opening_fallback_observability.py` — comment-only mention of `transition_from_previous` | Comment-only legacy mention | n/a (comment) | n/a | n/a | n/a | `doc_only_update` — prune in 6B-3 step 3. | n/a. |
| F20 | `world-engine/app/story_runtime/manager/diagnostics_api.py::_w5_runtime_metadata_for_session` — inspects `transition_from_previous.location_changed` from any narrator block when computing W5 admin metadata | Admin-side parity bridge | ✓ (intentional parity inspection) | ✓ | ✓ | ✓ | `substrate_keep` — diagnostic-only parity check; ADR-pinned as A6 in Phase 6A. Stays until F8 is removed *and* admin parity assertion is rewritten. | `world-engine/tests/test_story_runtime_w5_admin_diagnostics.py`. |
| F21 | `ai_stack/langgraph/runtime_executor/executor_action_resolution_start.py` `L150-L182` — inline `environment_state.actor_locations` + `current_room_id` read that feeds Director-Pause inputs | C3 from Phase 6A: inline substrate read at action-resolution start | ✓ | ✓ | ✓ | ✓ | `migrate_to_w5_first_before_removal` — same call seeds F1's `actor_locations` and `environment_current_room_id`. Migration requires reading `where_summary.derived_actor_locations` first. Sequenced as 6B-3 step 2. | `test_phase1_live_wiring.py`, `tests/smoke/test_thin_path_pr_c_director_pause_live_smoke.py`. |
| F22 | `ai_stack/langgraph/runtime_executor/executor_action_resolution_commit.py` `L11-L96` — commit-side mirror of F21 | C4 from Phase 6A | ✓ | ✓ | ✓ | ✓ | `migrate_to_w5_first_before_removal` — must move in lockstep with F21. Sequenced as 6B-3 step 2. | Same as F21. |
| F23 | `ai_stack/contracts/narrator_consequence_contracts.py` (C7) — narrator-consequence payload composes `current_area` / `from_area` / `to_area` | Higher-level consumer still reading legacy area metadata | ✓ | ✓ | ✓ | ✓ | `migrate_to_w5_first_before_removal` — narrator-consequence and sensory engine (C8) read W5 only if a new builder is added. Sequenced beyond 6B-3 (deferred to a later phase ADR). | `ai_stack/tests/test_narrator_consequence_contract.py`. |
| F24 | `world-engine/app/story_runtime/manager/session/session_lifecycle.py` and `manager/runtime_config.py` — snapshot composers emit `current_room_id` field on the live snapshot | A3 from Phase 6A: WebSocket transport compatibility | ✓ | ✓ | ✓ | ✓ | `compatibility_alias_keep_temporarily` (mapped to `migrate_to_w5_first_before_removal` for 6B-2 vocabulary) — old WS subscribers read `viewer_room_id`. Removal requires WS client upgrade. Sequenced beyond 6B-3. | `world-engine/tests/test_ws_state_transitions.py`. |
| F25 | `world-engine/app/story_runtime/manager/actor_tracking/session_state_w5_view.py::_fallback_current_room_id` → `runtime_world.current_room_id` (legacy field) | Substrate read for diagnostics | ✓ | ✓ | ✓ | ✓ | `substrate_keep` — see F16. Reads the substrate emitted by C10 (`runtime_world.py`). | n/a. |

### Phase 6B-2 summary by classification

| Classification | Count | Branches |
|----------------|------:|----------|
| `keep_explicit_opt_out_fallback` | 5 | F2, F6, F9, F12, F14 |
| `keep_malformed_w5_safety_fallback` | 5 | F3, F7, F10, F13, F15 |
| `substrate_keep` | 5 | F4, F5, F16, F20, F25 |
| `migrate_to_w5_first_before_removal` | 8 | F1, F8, F11, F17, F21, F22, F23, F24 |
| `remove_dead_default_path_in_6b3` | **0** | — |
| `doc_only_update` | 2 | F18, F19 |
| `unknown_needs_runtime_trace` | 0 | — |

### Phase 6B-2 result

**No branch is safe for an unconditional default-path deletion in Phase 6B-3.** Every fallback path that fires under default-on either (a) is the explicit opt-out path, (b) is the malformed-W5 safety net, (c) is substrate or substrate-derived, or (d) still feeds a downstream consumer that is not yet W5-first.

This is the **expected** result of Phase 6B-2: it confirms that Phase 6B-1's flag flips did not accidentally orphan any code, and that legacy fallback removal must proceed by *consumer migration*, not by branch deletion.

### Phase 6B-3 — recommended order (no deletions, only consumer migrations + lazy re-ordering)

Each step is independently testable. No step removes any legacy *function* — each step migrates a *call site* to read W5 first, with the legacy function still available as the malformed-W5 safety net.

1. **F1 lazy re-order (low-risk optimization, no contract change).** Move the eager `baseline_completion = complete_actor_locations_for_gathering(...)` call inside the two paths that actually return it (disabled-flag branch and `except` branch). The W5-success path becomes the only baseline call (which is the second one, F4). Output dict is identical bit-for-bit on D, O, and M paths.
   - **Test before:** add a Phase 6B-2 test asserting that on D, `derived_actor_locations_source == "w5_projection"` and `gathering_pause_source == "w5_projection"`; on M, `w5_director_projection_failed` is set and `source == "environment_state_with_actor_lane_fallback"`.
2. **F21 / F22 migration (C3 / C4 of Phase 6A).** Make `executor_action_resolution_start` and `executor_action_resolution_commit` read `w5_latest_snapshot.where_summary.derived_actor_locations` first; fall back to `environment_state.actor_locations` only when no snapshot is present.
   - **Test before:** assert in `test_phase1_live_wiring.py` that the Director-Pause input under D uses the W5-derived locations; under M reverts to legacy substrate.
3. **F8 + F18 + F19 sequenced removal (narrator transition fallback).**
   - First update `narrator_output_prompts.py` (F18) to drop the fallback paragraph behind a W5-narrator-strict flag, default-off.
   - Then turn the flag on after `test_story_runtime_w5_narrator_projection.py` is rewritten to assert W5-only narrator prompts.
   - Finally remove the `source_facts["transition_from_previous"] = …` line in `god_of_carnage_narrator_path.py` (F8) and prune the comment in `opening_fallback_observability.py` (F19).
   - **Test before each sub-step:** the parity tests `test_story_runtime_w5_narrator_projection.py:test_w5_narrator_projection_legacy_parity_*` must be rewritten in lockstep with each sub-step. Admin diagnostics F20 must be updated when F8 is removed.
4. **F11 migration (NPC planner W5-first).** Pass `npc_w5_situations` *first* into the planner contract; treat `npc_context_bundle` as a malformed-W5 fallback. Once `test_npc_agency_planner.py`, `test_npc_agency_contracts.py`, `test_npc_agency_long_horizon_claim_readiness.py`, and `test_wave3_multi_actor_vitality.py` all remain green with W5-first inputs, remove the bundle from the *non-fallback* call path (the bundle is still passed in malformed-W5 cases).
5. **F17 + F24 (player-shell `current_room_id` and WS `viewer_room_id`).** Out of 6B-3 scope. Requires frontend / WS client upgrade. Track as a separate ADR.
6. **F23 (`narrator_consequence_contracts.py` and C8 sensory engine).** Out of 6B-3 scope. Requires a new W5-first builder. Track as a separate ADR.

### Phase 6B-2 branches that must remain until a later ADR

- All five **opt-out short-circuits** (F2, F6, F9, F12, F14). They are the only paths that honor `W5_AST_*=0/false/no/off`. Removing them violates the Phase 6B-1 explicit-opt-out contract.
- All five **malformed-W5 safety returns** (F3, F7, F10, F13, F15). They are the safety net the migration plan commits to (Phase 5B: *"missing or malformed W5 snapshots fall back to legacy current_room without failing the turn"*).
- All **substrate reads** (F4, F5, F16, F20, F25) and the substrate writers S1–S8 from the Phase 6A inventory. Substrate consolidation is a separate, later ADR.
- The **compatibility aliases** (F17, F24) until the frontend and WebSocket clients are upgraded.
- The **narrator-consequence and sensory-engine legacy reads** (F23) until W5-first builders exist for those payloads.

### Phase 6B-2 — is targeted fallback removal safe to begin in Phase 6B-3?

**Yes, conditionally — and the conditions are scoped to consumer migration, not branch deletion.** Phase 6B-3 may begin with:

- The F1 lazy re-order (optimization, no contract change, no legacy removal).
- The F21 / F22 W5-first migration of the executor action-resolution inline reads.
- Sequenced removal of F8 / F18 / F19 only after their parity tests are rewritten and the admin parity bridge F20 is updated in lockstep.
- The F11 NPC planner W5-first migration once the planner test suites are confirmed green.

Phase 6B-3 may **not** delete any opt-out short-circuit, any malformed-W5 safety return, any substrate read, or any compatibility alias on the public payload contract. Each such removal requires its own ADR with the gates listed above.

---

## Phase 6B-3A — Director eager-baseline lazy reorder + Executor W5-first reads (complete)

**Phase:** 6B-3A is the first commit of Phase 6B-3. It lands the two consumer migrations that are demonstrably safe to execute without removing any opt-out short-circuit, malformed-W5 safety net, substrate read, or public compatibility alias. **No legacy code is removed in Phase 6B-3A.**

### Phase 6B-3A — what changed

| # | Change | File(s) | Effect |
|---|--------|---------|--------|
| F1 | Lazy re-order of the Director eager baseline | `ai_stack/langgraph/runtime_executor/director_w5_location_projection.py` (SOURCE_LINES of `complete_actor_locations_for_gathering_with_optional_w5_projection`) | The eager `baseline_completion = complete_actor_locations_for_gathering(...)` call at function entry is removed. The legacy completion now runs only inside the explicit-opt-out `if not enabled:` return path and the malformed-W5 `except Exception as exc:` return path. Output is bit-for-bit identical on D / O / M. F4 (the W5-success branch's `complete_actor_locations_for_gathering(...)` call) is preserved. |
| F21 | Inline `_pr_c_actor_locations_raw` substrate read becomes W5-first | `ai_stack/langgraph/runtime_executor/executor_action_resolution_start.py` (SOURCE_LINES of `_resolve_player_action`) | The inline `state.get("actor_locations")` → `environment_state.actor_locations` chain is wrapped in `resolve_w5_first_actor_locations(...)`. Under default-on the resolver prefers `where_summary.derived_actor_locations`. Under opt-out / malformed-W5 / old-payload it returns the legacy substrate verbatim. |
| F22 | `actor_locations_source` diagnostic emitted on `graph_diagnostics` | `ai_stack/langgraph/runtime_executor/executor_action_resolution_commit.py` (SOURCE_LINES of `_resolve_player_action`) | After F1 is called, the commit side now emits `graph_diagnostics["actor_locations_source"] = {"source": …, "w5_snapshot_id"?: …, "failure_reason"?: …}` so admin diagnostics, Langfuse metadata, and downstream consumers can audit which read path the turn actually used. |

### Phase 6B-3A — what is preserved

- **Explicit opt-out fallback** (F2, F6, F9, F12, F14 in the Phase 6B-2 inventory) is unchanged. `W5_AST_DIRECTOR_PROJECTION_ENABLED=0/false/no/off` continues to revert F1, F21, F22 to the pre-Phase-6B-3A legacy substrate path.
- **Malformed/missing-W5 safety fallback** (F3, F7, F10, F13, F15) is unchanged. Missing or malformed snapshots continue to fall back to the legacy baseline at F1 with `w5_director_projection_failed` set, and to the legacy substrate at F21/F22 with `source == "malformed_w5_fallback"`.
- **Substrate writers and readers** (F4, F5, F16, F20, F25; S1–S8 in Phase 6A) are unchanged. `complete_actor_locations_for_gathering`, the W5 extractor, the environment-state substrate, and the `Participant.current_room_id` dataclass field are all preserved.
- **Public compatibility aliases** (`current_room`, `current_room_id`, `gathering_scene_id`, `complete_actor_locations_for_gathering`) are unchanged.
- **No committed event is mutated.** The `director_gathering_state` payload, the actor lane, the canonical path, `validation_outcome`, ADR-0033 commit semantics, and ADR-0061 pause semantics are unchanged. The new diagnostic lives entirely on `graph_diagnostics` (read-side observability surface).
- **How remains first-class. Inferred Why remains soft truth.** Neither dimension is collapsed by Phase 6B-3A.

### Phase 6B-3A — `actor_locations_source` classification

The new F21/F22 diagnostic `graph_diagnostics["actor_locations_source"]["source"]` is one of:

| `source` value | Meaning | When it fires |
|----------------|---------|---------------|
| `w5_projection` | The W5 projection won; the actor_locations come from `where_summary.derived_actor_locations`. | Default-on `D` path with a well-formed `w5_latest_snapshot` in state. |
| `explicit_opt_out_legacy` | The operator opted the Director projection out; the legacy substrate is used verbatim. | `W5_AST_DIRECTOR_PROJECTION_ENABLED` ∈ `{0, false, no, off}`. |
| `malformed_w5_fallback` | The snapshot was present but `build_w5_projection_for_director(...)` raised or returned no usable derived_actor_locations; the legacy substrate is used verbatim and `failure_reason` carries a compact error string. | Default-on `M` path. |
| `old_payload_legacy` | No `w5_latest_snapshot` is present in graph state (old session predating Phase 1 wire-in, or missing wire-in); the legacy substrate is used verbatim. | Default-on `L` path. |

### Phase 6B-3A — tests added

- `ai_stack/tests/test_w5_actor_tracking_phase_6b3a_consumer_migration.py`
  - `TestF1LazyReorder` — pins `D` happy path source classification, `D` parity with the legacy completion when fed W5-derived inputs, `O` envelope bit-for-bit parity, `O` via explicit argument vs env var parity, and `M` baseline + `w5_director_projection_failed`.
  - `TestF21F22ResolveW5FirstActorLocations` — pins the four-way classification (`w5_projection`, `explicit_opt_out_legacy`, `malformed_w5_fallback`, `old_payload_legacy`), the defensive-copy semantics for the legacy input, the explicit-argument-overrides-environment behavior, and the `legacy_actor_locations=None` tolerance.
  - `test_f1_lazy_reorder_preserves_f4_w5_success_completion_call` — pins that F4 (the W5-success completion call) survives the reorder.
- Existing suites continue to pin Phase 6B-3A's contract: `ai_stack/tests/test_phase1_live_wiring.py`, `ai_stack/tests/test_pr_c_director_pause_mode.py`, `ai_stack/tests/test_w5_actor_tracking_phase_6b1_default_on_flags.py`, `ai_stack/tests/test_w5_actor_tracking_phase_6b2_fallback_inventory.py`, `ai_stack/tests/test_w5_actor_tracking_projection.py`, `ai_stack/tests/test_w5_actor_tracking_validation.py`, `ai_stack/tests/test_environment_state_contracts.py`, and `tests/test_inventory_w5_legacy_consumers.py`.

### Phase 6B-3A — what Phase 6B-3 still has to do

| Sub-phase | Scope | Status |
|-----------|-------|--------|
| **6B-3A** | F1 lazy re-order + F21/F22 W5-first reads + diagnostics. | ✅ complete (Phase 6B-3A section above). |
| **6B-3B** | F8 / F18 / F19 / F20 narrator `transition_from_previous` migration behind the new opt-in `W5_AST_NARRATOR_STRICT_ENABLED` flag (default-off). Under strict-ON: `source_facts.transition_from_previous` is demoted into `source_facts._legacy_compat`, the narrator prompt fallback paragraph is replaced with a W5-only paragraph that preserves Who / Where / What / How / Why (How first-class, inferred Why soft), and the admin parity bridge labels legacy compat as `demoted_to_legacy_compat`. Legacy code is not deleted; the strict flag default-off preserves Phase 6B-3A behavior bit-for-bit. | ✅ complete (Phase 6B-3B section below). |
| **6B-3C** | F11 NPC planner W5-first migration: under default-on with at least one usable W5 NPC projection, `_build_npc_agency_plan_projection` forwards `effective_npc_context_bundle=None` to the planner so the `npc_context_bundle` evidence row is no longer emitted; under explicit opt-out / malformed-W5 / old-payload the legacy bundle is forwarded verbatim. Per-actor diagnostics carry `npc_context_source` / `npc_context_legacy_compat_visible` / `npc_context_fallback_reason`. No legacy code is removed. | ✅ complete (Phase 6B-3C section below). |
| later ADR | F17 player-shell `current_room_id` alias and F24 WS `viewer_room_id` alias. Requires frontend / WebSocket client upgrade. | out of 6B-3 scope. |
| later ADR | F23 `narrator_consequence_contracts.py` (C7) and the sensory engine (C8). Requires a new W5-first builder for movement framing and stage-level area. | out of 6B-3 scope. |

---

## Phase 6B-3B — Narrator `transition_from_previous` migration behind strict flag (complete)

**Phase:** 6B-3B is the second commit of Phase 6B-3. It migrates the F8 / F18 / F19 / F20 narrator-transition surfaces behind the new opt-in `W5_AST_NARRATOR_STRICT_ENABLED` flag without removing any legacy code, opt-out short-circuit, malformed-W5 safety net, substrate read, or public compatibility alias. **No legacy code is removed in Phase 6B-3B. No committed event is mutated.**

### Phase 6B-3B — what changed

| # | Change | File(s) | Effect |
|---|--------|---------|--------|
| Flag | New opt-in resolver `w5_ast_narrator_strict_enabled()` | `ai_stack/actor_tracking/diagnostics.py` SOURCE_LINES; re-exported by `ai_stack/actor_tracking/__init__.py`; included in `w5_projection_flag_states()` under the `"narrator_strict"` key. | Default-off (`False` on unset / empty / explicit `0/false/no/off`). `1/true/yes/on` (case-insensitive) → strict mode. Independent of `W5_AST_NARRATOR_PROJECTION_ENABLED`. |
| F8 | `source_facts.transition_from_previous` migrated behind strict flag | `ai_stack/story_runtime/narrator/god_of_carnage_narrator_path.py::_block` SOURCE_LINES | Strict-OFF (default): legacy `source_facts["transition_from_previous"] = _transition_facts(...)` preserved bit-for-bit. Strict-ON: top-level key omitted; same payload demoted into `source_facts["_legacy_compat"]["transition_from_previous"]` with `authority="w5_projection"` and a non-authoritative `notice`. Hard-cut directed-transition still inspectable under `_legacy_compat`. |
| F18 | Narrator prompt fallback paragraph migrated behind strict flag | `world-engine/app/story_runtime/manager/narrator_output_prompts.py::_narrator_path_output_prompt` SOURCE_LINES | Strict-OFF: legacy fallback paragraph + hard-cut directed-transition guidance preserved. Strict-ON: replaced by a W5-only paragraph that names `who_summary` / `where_summary` / `what_summary` / `how_summary` / `why_summary` explicitly, keeps How first-class (forbids folding into What), marks inferred Why as soft truth (never spoken as observed fact), and instructs the narrator to ignore `source_facts.transition_from_previous` and treat `source_facts._legacy_compat` as non-authoritative debug breadcrumbs. |
| F19 | Opening-fallback observability docstring wording | `world-engine/app/story_runtime/manager/opening_fallback_observability.py::_w5_ast_narrator_projection_enabled` SOURCE_LINES | Rewritten to W5-first / `transition_from_previous`-legacy-compatibility language. Explicitly documents that under strict mode the legacy block is demoted into `source_facts._legacy_compat` and the prompt fallback paragraph is removed. Resolver behavior unchanged. |
| F20 | Admin parity bridge labels W5-first source and demotes legacy parity surface under strict | `world-engine/app/story_runtime/manager/diagnostics_api.py::get_w5_langfuse_metadata` SOURCE_LINES | New diagnostic labels added to the langfuse metadata payload: `w5.location_changed_source` (`"w5_history_projection"` / `"w5_history_insufficient"`), `w5.location_changed_compute_failed` (set only on extraction error), `w5.narrator_strict_enabled` (mirrors resolver), `w5.legacy_transition_parity` (`"legacy_compat_visible"` under strict-OFF, `"demoted_to_legacy_compat"` under strict-ON). The primary `w5.location_changed_this_turn` signal is still computed from W5 history snapshots on both postures; `transition_from_previous.location_changed` is **not** read by the admin bridge under either posture. |

### Phase 6B-3B — what is preserved

- **Explicit opt-out fallback for narrator projection** (F6 in the Phase 6B-2 inventory) is unchanged. `W5_AST_NARRATOR_PROJECTION_ENABLED=0/false/no/off` still suppresses `source_facts.w5_projection` regardless of the strict flag.
- **Malformed/missing-W5 safety fallback for narrator projection** (F7) is unchanged. Malformed snapshots still record `w5_narrator_projection_failed` and return blocks unmodified.
- **Substrate writers and readers** (S1–S8 in Phase 6A; F4 / F5 / F16 / F20 / F25 in Phase 6B-2) are unchanged.
- **Public compatibility aliases** (`current_room`, `current_room_id`, `actor_locations`, `gathering_scene_id`, `complete_actor_locations_for_gathering`) are unchanged.
- **Legacy fallback function** `_transition_facts(...)` is still computed under both strict postures. Strict mode only changes where the resulting payload lands in `source_facts` (top-level vs `_legacy_compat`).
- **No committed event is mutated.** ADR-0033 commit semantics, the Actor Lane, the Canonical Path, `validation_outcome`, ADR-0061 pause semantics, ADR-0063 W5 semantics, and W5 validation semantics are unchanged.
- **How remains first-class. Inferred Why remains soft truth.** The strict-ON narrator prompt explicitly names How attributes (tone / manner / intensity / pace / physicality / method / style) and forbids folding them into What. Inferred Why is marked as soft truth and never described as observed fact.

### Phase 6B-3B — `w5.location_changed_source` and `w5.legacy_transition_parity` classification

The new F20 diagnostic labels are one of:

| Field | Value | Meaning |
|-------|-------|---------|
| `w5.location_changed_source` | `w5_history_projection` | Per-actor `where.value` comparison across `w5_history[-2]` and `w5_history[-1]` succeeded. |
| | `w5_history_insufficient` | Fewer than two W5 snapshots are available; `w5.location_changed_this_turn` defaults to `False`. |
| `w5.location_changed_compute_failed` | `True` | Extraction raised an exception; bridge falls back to `False` (non-authoritative diagnostic). Field is omitted when the compute succeeded. |
| `w5.narrator_strict_enabled` | `True` / `False` | Mirrors the resolver. |
| `w5.legacy_transition_parity` | `legacy_compat_visible` | Strict-OFF: operators may correlate against `source_facts.transition_from_previous` from committed narrator blocks. |
| | `demoted_to_legacy_compat` | Strict-ON: legacy parity surface is non-authoritative debug breadcrumb only. |

### Phase 6B-3B — tests added / updated

- `ai_stack/tests/test_w5_actor_tracking_phase_6b3b_narrator_strict_migration.py` (new). Pins the strict-flag resolver contract (default-off / explicit on/off / independence from projection / reporter exposure) and the F8 source_facts contract under both postures (top-level vs `_legacy_compat` demotion, canonical-step / mandatory-beat parity, authored hard_cut breadcrumb survival).
- `world-engine/tests/test_story_runtime_w5_narrator_strict_migration.py` (new). Pins the F18 prompt-text contract under both postures (legacy fallback paragraph vs W5-only paragraph; Who / Where / What / How / Why guidance preserved on every posture; How first-class; inferred Why marked as soft) and the F20 admin parity bridge labels under both postures (W5-history primary signal; legacy_compat_visible vs demoted_to_legacy_compat; strict-ON ignores stray legacy `transition_from_previous.location_changed=True` claims).
- `ai_stack/tests/test_w5_actor_tracking_phase_6b1_default_on_flags.py` and `ai_stack/tests/test_w5_actor_tracking_phase_6b2_fallback_inventory.py` (updated). Reporter-shape assertions now include `"narrator_strict": False` under default-off; the Phase 6B-1 default-on contract for the five consumer flags is unchanged.
- Existing suites continue to pin Phase 6B-3B's contract under strict-OFF: `world-engine/tests/test_story_runtime_w5_narrator_projection.py`, `world-engine/tests/test_goc_narrator_path_opening.py`, `ai_stack/tests/test_god_of_carnage_narrator_path.py`, `ai_stack/tests/test_actor_tracking_diagnostics.py`, `ai_stack/tests/test_w5_actor_tracking_projection.py`, `ai_stack/tests/test_w5_actor_tracking_validation.py`, `ai_stack/tests/test_w5_actor_tracking_phase_6b3a_consumer_migration.py`, and `tests/test_inventory_w5_legacy_consumers.py`.

### Phase 6B-3B — what Phase 6B-3 still has to do

| Sub-phase | Scope | Status |
|-----------|-------|--------|
| **6B-3C** | F11 NPC planner W5-first migration: under default-on with at least one usable W5 NPC projection, `_build_npc_agency_plan_projection` forwards `effective_npc_context_bundle=None` to the planner so the `npc_context_bundle` evidence row is no longer emitted; under explicit opt-out / malformed-W5 / old-payload the legacy bundle is forwarded verbatim. Per-actor diagnostics carry `npc_context_source` / `npc_context_legacy_compat_visible` / `npc_context_fallback_reason`. No legacy code is removed. | ✅ complete (Phase 6B-3C section below). |
| 6B-4 | Fresh consumer-removal inventory under default-on + Phase 6B-3A/B/C migrations: identify which legacy NPC context / narrator transition / Director eager-baseline branches are now demonstrably unreachable on D, O, M, and L; preserve all opt-out + malformed-W5 safety fallbacks. | planned. |
| later ADR | Permanently flip `W5_AST_NARRATOR_STRICT_ENABLED` to default-on once production-side parity tests are rewritten to assert W5-only narrator prompts; then physically remove the legacy `transition_from_previous` block, the unstrict prompt paragraph, and the legacy_compat debug surface. | out of 6B-3B scope. |
| later ADR | F17 player-shell `current_room_id` alias and F24 WS `viewer_room_id` alias. Requires frontend / WebSocket client upgrade. | out of 6B-3 scope. |
| later ADR | F23 `narrator_consequence_contracts.py` (C7) and the sensory engine (C8). Requires a new W5-first builder for movement framing and stage-level area. | out of 6B-3 scope. |

---

## Phase 6B-3C — NPC planner W5-first migration (complete)

**Phase:** 6B-3C is the third commit of Phase 6B-3. It migrates the F11 attachment site for `npc_context_bundle` behind a W5-first selector so NPC planning consumes the actor-specific Phase 3B W5 NPC projection (`target_consumer="npc"`) as the primary actor-situation authority under the default-on happy path. The legacy bundle remains forwarded verbatim under explicit opt-out, malformed/missing W5, and old-payload sessions. **No legacy code is removed in Phase 6B-3C. No committed event is mutated.**

### Phase 6B-3C — what changed

| # | Change | File(s) | Effect |
|---|--------|---------|--------|
| Resolver | New public helper `resolve_w5_first_npc_context(...)` | `ai_stack/langgraph/runtime_executor/reaction_order_governance.py` SOURCE_LINES; re-exported via `ai_stack.langgraph.runtime_executor.public`. | Four-way classification mirrors Phase 6B-3A's `resolve_w5_first_actor_locations`: `w5_projection` / `explicit_opt_out_legacy` / `malformed_w5_fallback` / `old_payload_legacy`. Returns `effective_npc_context_bundle` (the bundle to forward to the planner; `None` under `w5_projection`), `legacy_compat_npc_context_bundle` (the bundle when demoted under `w5_projection`, audit-only), `npc_context_legacy_compat_visible`, `npc_context_fallback_reason`. Explicit-argument override (`w5_npc_projection_enabled=...`) wins over env to keep mid-flight flag flips off a single turn. |
| F11 | NPC planner attachment site becomes W5-first | `ai_stack/langgraph/runtime_executor/npc_agency_projection.py` SOURCE_LINES (`_build_npc_agency_plan_projection`) | After `_build_w5_npc_projection_inputs(...)`, the projection wrapper calls `resolve_w5_first_npc_context(...)` and forwards `effective_npc_context_bundle` into `build_npc_agency_simulation(...)` / `build_npc_agency_plan(...)`. Under default-on with at least one usable W5 NPC projection, the planner receives `None` and the `npc_context_bundle` evidence row is absent from the simulation's `source_evidence`. Under explicit opt-out / malformed-W5 / old-payload, the bundle is forwarded verbatim (pre-Phase-6B-3C behaviour preserved). |
| Diagnostics | Per-actor F11 diagnostic back-fill | `ai_stack/langgraph/runtime_executor/reaction_order_governance.py` SOURCE_LINES (`_build_w5_npc_projection_inputs`) | Every per-actor row in `w5_npc_projection_diagnostics` carries three new keys: `npc_context_source` (`w5_projection` / `malformed_w5_fallback` / `old_payload_legacy`), `npc_context_legacy_compat_visible` (whether the bundle is in state AND demoted), `npc_context_fallback_reason` (compact reason on fallback paths only; `None` under `w5_projection`). Opt-out short-circuit (F9) is preserved bit-for-bit: the function still returns `({}, [])` so the dramatic packet continues to omit `w5_npc_projection_diagnostics`. |

### Phase 6B-3C — what is preserved

- **Explicit opt-out fallback for NPC projection** (F9 in the Phase 6B-2 inventory) is unchanged. `W5_AST_NPC_PROJECTION_ENABLED=0/false/no/off` still short-circuits to `({}, [])` and the legacy `npc_context_bundle` is forwarded into the planner as the only NPC planning substrate.
- **Per-actor malformed-W5 safety fallback** (F10) is unchanged. Each per-actor `w5_npc_projection_failed` reason is emitted exactly as before, and the legacy bundle is forwarded into the planner.
- **Substrate writers and readers** (S1–S8 in Phase 6A; F4 / F5 / F16 / F20 / F25 in Phase 6B-2) are unchanged.
- **Public compatibility aliases** (`current_room`, `current_room_id`, `actor_locations`, `gathering_scene_id`, `complete_actor_locations_for_gathering`) are unchanged.
- **Legacy fallback function `build_npc_context_bundle(...)`** (`ai_stack/rag/retrieval_context_bundles.py`) is still computed by the retrieval-context layer. Only the *attachment site* in the NPC agency planner contract is migrated. The bundle is still attached to graph state at the same wire-in point as before.
- **No committed event is mutated.** ADR-0033 commit semantics, the Actor Lane, the Canonical Path, `validation_outcome`, ADR-0061 pause semantics, ADR-0063 W5 semantics, and W5 validation semantics are unchanged. The new diagnostics live entirely on `w5_npc_projection_diagnostics` (read-side observability surface).
- **How remains first-class. Inferred Why remains soft truth.** The W5 NPC projection embedded in each NPC proposal preserves the top-level `how_summary` (never folded into `what_summary`) and marks inferred Why via `truth_attribution[...] == "inferred"`.
- **Privacy / actor_knowledge_scope** (Phase 3B contract) is unaffected. The W5 NPC projection still enforces per-actor visibility (target NPC sees its own private inferred Why; another actor's private/inferred Why is exposed only when `actor_knowledge_scope` allows the target NPC; player-private and GM/director-only facts never leak). The legacy bundle, when used, carries only `retrieval_plan` lane allow/block lists — the planner never reads `private_memory`.

### Phase 6B-3C — `npc_context_source` classification

The new per-actor diagnostic `npc_context_source` is one of:

| `npc_context_source` value | Meaning | When it fires |
|----------------------------|---------|---------------|
| `w5_projection` | At least one per-actor W5 NPC projection succeeded; W5 is the primary actor-situation authority for this turn. | Default-on `D` path with a well-formed `w5_latest_snapshot` containing the NPC. |
| `malformed_w5_fallback` | Default-on with a snapshot present but every per-actor `build_w5_projection_for_npc(...)` call raised; legacy bundle is the safety net. | Default-on `M` path. |
| `old_payload_legacy` | Default-on with no `w5_latest_snapshot` in graph state; legacy bundle is the pre-Phase-1-session fallback. | Default-on `L` path (and the per-actor failure reason is `missing_w5_latest_snapshot`). |
| *(not emitted)* | Explicit opt-out short-circuit returns `({}, [])`; the source classification is implicit in the env. | Explicit opt-out `O` path. |

### Phase 6B-3C — tests added

- `ai_stack/tests/test_w5_actor_tracking_phase_6b3c_npc_planner_migration.py` (new).
  - `TestResolveW5FirstNpcContext` — pins the resolver's four-way classification, defensive-copy semantics, explicit-argument-overrides-env behaviour, tolerance for `None` / empty-dict bundles / `None` diagnostics, and the distinction between `missing_w5_latest_snapshot` (→ `old_payload_legacy`) and other per-actor failures (→ `malformed_w5_fallback`).
  - `TestPerActorDiagnosticsBackfill` — pins the per-actor F11 diagnostic keys across D / D-with-bundle / L / M / opt-out.
  - `TestPlannerW5First` — pins the dramatic-packet routing contract: D — `npc_context_bundle` row absent from `source_evidence`, W5 row present, every proposal carries `actor_w5_situation`, How first-class, inferred Why soft, plan-shape stable; O — bundle row present, no W5 row, no diagnostics, no `actor_w5_situation`; M / L — bundle row present, per-actor diagnostics flag the appropriate fallback source.
  - `TestPrivacyPreserved` — pins target-NPC sees own private inferred Why; another NPC's private inferred Why without `actor_knowledge_scope` does not leak; legacy bundle's `private_memory` body never appears in `source_evidence` even under opt-out.
  - Module-level `test_build_npc_agency_simulation_with_none_bundle_omits_legacy_evidence_row` and `test_build_npc_agency_plan_with_none_bundle_omits_legacy_evidence_row` pin the planner-layer guarantee directly: forwarding `npc_context_bundle=None` removes the legacy evidence row and the W5 evidence row is present.
- Existing suites continue to pin Phase 6B-3C's contract:
  - `ai_stack/tests/test_npc_agency_planner.py` — default-on actor-specific NPC projection, opt-out, malformed-W5, W5 situation contract.
  - `ai_stack/tests/test_npc_agency_contracts.py` — NPC agency contract normalization stability.
  - `ai_stack/tests/test_npc_agency_long_horizon_claim_readiness.py` — long-horizon claim readiness under the migrated planner inputs.
  - `ai_stack/tests/test_wave3_multi_actor_vitality.py` — multi-actor vitality under default-on.
  - `ai_stack/tests/test_w5_actor_tracking_phase_6b1_default_on_flags.py`, `test_w5_actor_tracking_phase_6b2_fallback_inventory.py`, `test_w5_actor_tracking_phase_6b3a_consumer_migration.py`, `test_w5_actor_tracking_phase_6b3b_narrator_strict_migration.py` — Phase 6B-1/6B-2/6B-3A/6B-3B flag matrix and migration contracts.
  - `ai_stack/tests/test_phase_c_reaction_order_governance.py`, `test_vitality_telemetry_v1.py`, `test_actor_lane_absence_governance.py` — reaction-order / vitality / absence governance surfaces.
  - `tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py` — LDSS gate stability.
  - `tests/test_inventory_w5_legacy_consumers.py` — Phase 6A inventory and R1–R5 rename guarantees.

### Phase 6B-3C — what Phase 6B-3 still has to do (carry-over)

| Sub-phase | Scope | Status |
|-----------|-------|--------|
| 6B-4 | Fresh consumer-removal inventory pass. Run the inventory script over the working tree with Phase 6B-3A/B/C migrations in place and re-classify each legacy fallback branch under D / O / M / L. Only branches that fire on **none** of those four conditions are removal candidates. | planned. |
| later ADR | Permanently flip `W5_AST_NARRATOR_STRICT_ENABLED` to default-on once parity tests are rewritten; then physically remove the legacy `transition_from_previous` block, the unstrict prompt paragraph, and the legacy_compat debug surface. | out of 6B-3 scope. |
| later ADR | F17 player-shell `current_room_id` alias and F24 WS `viewer_room_id` alias. Requires frontend / WebSocket client upgrade. | out of 6B-3 scope. |
| later ADR | F23 `narrator_consequence_contracts.py` (C7) and the sensory engine (C8). Requires a new W5-first builder for movement framing and stage-level area. | out of 6B-3 scope. |
