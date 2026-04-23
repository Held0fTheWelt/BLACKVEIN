# Story Runtime Experience — Test / Validation Summary

## Results

**20/20 tests pass.**

```
tests/integration/test_story_runtime_experience.py ........... 14 passed
backend/tests/services/test_story_runtime_experience_service.py 6 passed
```

## What the tests prove

### `tests/integration/test_story_runtime_experience.py` (14 tests)

| Test | Proves |
|---|---|
| `test_canonical_defaults_are_recap_and_safe` | Fresh-bootstrap default is recap, classic_recap, 1 pulse, no auto-progress. |
| `test_normalize_drops_unknown_keys_and_coerces` | Operator payload is coerced (string ints, booleans) and unknown keys are dropped. |
| `test_delivery_profile_overrides_apply_before_advanced_fields` | `delivery_profile` picks apply before advanced overrides, so choosing a preset does something real. |
| `test_validate_catches_misleading_live_combination` | Live mode with 1 pulse and no exchange is flagged with warnings rather than silently accepted. |
| `test_validate_catches_auto_progress_on_recap` | Gating of `allow_scene_progress_without_player_action` is enforced. |
| `test_recap_policy_caps_pulses_and_exchange` | Recap mode caps pulses to 1 and forces exchange intensity to off, with explicit degradation markers. |
| `test_dramatic_turn_caps_to_two_pulses` | Dramatic_turn mode caps pulses to 2. |
| `test_live_mode_is_marked_partial_foundation` | Live mode always carries the `live_simulator_partial_foundation` marker — the UI cannot claim full support. |
| `test_extract_policy_from_resolved_config_missing_section_uses_defaults` | Missing-section path safely returns defaults (first-boot safety). |
| `test_recap_packaging_is_narration_dominant` | Recap packaging respects the narration-first contract. |
| `test_dramatic_turn_packaging_promotes_dialogue_and_action` | Dramatic_turn emits higher spoken-line caps, narration_blocks, action_pulses. |
| `test_live_packaging_may_emit_multiple_pulses` | Live mode honors up to 3 pulses and signals `scene_continues: true`. |
| `test_modes_produce_materially_different_packaging` | Recap / dramatic_turn / live produce monotonically-increasing spoken-line and pulse caps — proof the modes are really different, not just differently labeled. |
| `test_truth_surface_includes_degradation_markers` | The truth surface carries degradation markers and packaging contract version so admin UIs cannot lie. |

### `backend/tests/services/test_story_runtime_experience_service.py` (6 tests)

| Test | Proves |
|---|---|
| `test_baseline_seeds_defaults` | `ensure_governance_baseline()` seeds Story Runtime Experience on first run (no manual admin step required). |
| `test_seed_is_idempotent` | Repeated boots don't double-seed or overwrite operator changes. |
| `test_update_path_normalizes_and_persists` | Admin PUT coerces, persists, and round-trips. |
| `test_update_returns_warnings_for_misleading_live_combo` | Update returns operator-visible warnings for misleading combinations. |
| `test_admin_truth_surface_reports_degradation_for_live` | Admin truth surface returns `experience_mode_honored_fully: false` and lists `live_simulator_partial_foundation` when live mode is picked. |
| `test_resolved_runtime_config_carries_story_runtime_experience_section` | Resolved runtime config propagates the full section (configured, effective, degradation_markers, packaging_contract_version) to the world-engine. |

## Coverage of success-bar criteria

| Success-bar item | Evidence |
|---|---|
| Operators can configure scene delivery form through the Administration Tool | `runtime_settings.html` section + `PUT /admin/story-runtime-experience`, covered by backend service tests. |
| Operators can configure bounded NPC/Narrator behavior through governed settings | Settings model includes npc_verbosity/npc_initiative/inter_npc_exchange_intensity; normalization + validation tested. |
| Backend resolves and validates these settings as first-class runtime truth | `_collect_scope_settings()` embeds section; `test_resolved_runtime_config_carries_story_runtime_experience_section`. |
| World-engine/runtime path actually consumes them | `manager._story_runtime_experience_policy` + `_apply_experience_packaging` applied inside `_finalize_committed_turn`. |
| turn_based_narrative_recap and dramatic_turn are observably different in real runtime terms | `test_modes_produce_materially_different_packaging` + packaging module behavior. |
| live_dramatic_scene_simulator is either truly implemented or explicitly marked degraded/partial | `test_live_mode_is_marked_partial_foundation` + `test_admin_truth_surface_reports_degradation_for_live`. |
| Player-facing output packaging reflects the selected mode | Packaging module produces distinct `gm_narration`, `spoken_lines`, `narration_blocks`, `action_pulses`, `scene_motion_summary` per mode. |
| Diagnostics / truth surfaces expose the actual active behavior | `runtime_config_status().story_runtime_experience` + per-turn `event["story_runtime_experience"]`. |
| docker-up.py can bring up a fresh working system with no manual pre-configuration | `INTERNAL_RUNTIME_CONFIG_TOKEN` already auto-generated by docker-up.py; `BACKEND_RUNTIME_CONFIG_URL` already in compose; `ensure_governance_baseline()` seeds defaults; `test_baseline_seeds_defaults` verifies the seed. |

## How to run

```
# ai_stack / packaging / policy tests (no backend DB needed):
python -m pytest tests/integration/test_story_runtime_experience.py -v --confcutdir=tests/integration

# Backend service + DB-backed tests:
cd backend && python -m pytest tests/services/test_story_runtime_experience_service.py -v
```
