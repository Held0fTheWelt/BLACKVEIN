# Story Runtime Experience — Implementation Report

## What was implemented

A governed, operator-configurable **Story Runtime Experience** surface spanning
the Administration Tool, backend governance, resolved-runtime-config
propagation, world-engine runtime policy consumption, and visible-output
packaging.

### Settings model (canonical)

Canonical settings live in `ai_stack/story_runtime_experience.py` as a single
source of truth shared by backend and world-engine. Includes:

- `experience_mode` (`turn_based_narrative_recap`, `dramatic_turn`,
  `live_dramatic_scene_simulator`)
- `delivery_profile` (`classic_recap`, `lean_dramatic`, `cinematic_live`,
  `npc_forward`, `operator_custom`)
- Delivery controls: `prose_density`, `explanation_level`, `narrator_presence`,
  `dialogue_priority`, `action_visibility`, `repetition_guard`,
  `motif_handling`
- Character dynamics: `npc_verbosity`, `npc_initiative`,
  `inter_npc_exchange_intensity`
- Scene motion: `pulse_length`, `max_scene_pulses_per_response`,
  `allow_scene_progress_without_player_action`, `beat_progression_speed`
- Defaults (fresh-bootstrap safe): recap + classic_recap + 1 pulse + no
  auto-progress.
- Normalization, validation, caps, and a `StoryRuntimeExperiencePolicy` with
  `configured` / `effective` / `degradation_markers` / `packaging_contract_version`.

### Backend governance integration

`backend/app/services/story_runtime_experience_service.py`:

- Persists settings via existing `SystemSettingRecord` rows on scope
  `story_runtime_experience`.
- Audits changes via existing `SettingAuditEvent` model.
- Seeds defaults in the governance baseline so first `docker-up.py` boot has
  a working configuration with no manual admin step.
- Builds the operator truth surface (configured vs effective, degradation
  markers, validation warnings, `experience_mode_honored_fully`).

Wired into `governance_runtime_service.py`:

- `_collect_scope_settings()` now embeds the truth surface under the
  resolved-runtime-config key `story_runtime_experience`, so the world-engine
  receives it on its standard internal-config fetch.
- `ensure_governance_baseline()` seeds default settings on first run.

New admin routes in `backend/app/api/v1/operational_governance_routes.py`:

- `GET  /api/v1/admin/story-runtime-experience` — truth surface.
- `PUT  /api/v1/admin/story-runtime-experience` — normalize + validate +
  persist + rebuild resolved config + return truth surface with
  `update_warnings`.

### World-engine consumption

`world-engine/app/story_runtime/manager.py`:

- New `_story_runtime_experience_policy()` extracts the policy from the
  governed resolved config; returns safe defaults when the section is
  missing or the first-boot config has not yet been seeded.
- New `_apply_experience_packaging()` re-packages the visible output bundle
  according to the policy; failures in packaging never break the turn.
- Turn-event emission now carries both the repackaged `visible_output_bundle`
  and a dedicated `story_runtime_experience` truth field.
- `runtime_config_status()` now exposes `story_runtime_experience` so the
  admin's world-engine control-center and play-service-control surfaces see
  observed runtime state, not just configured state.

### Packaging (real runtime behavior difference)

`ai_stack/story_runtime_experience_packaging.py`:

- Recap mode: narration-dominant, low spoken-line cap, one action pulse max.
- Dramatic_turn: splits narration into `narration_blocks`, emits
  `action_pulses` (up to 2), promotes spoken lines, adds `continuation_state`.
- Live_dramatic_scene_simulator: multiple pulses (up to 3), weaves dialogue
  between beats, includes scene motion summary, reports
  `scene_continues: true`.
- All modes emit: `narration_blocks`, `action_pulses`, `spoken_lines`,
  `responder_trace`, `scene_motion_summary`, `continuation_state`,
  `experience_packaging` (with pulse/line caps, guard strengths, degradation
  markers).
- Repetition guard operates at packaging time (not only in prompts).

### Administration Tool UI

`administration-tool/templates/manage/runtime_settings.html`:

- New "Story Runtime Experience" section grouped as Mode / Delivery /
  Character Dynamics / Scene Motion per the plan.
- "Configured vs Observed" panel: lists degradation markers, validation
  warnings, and full effective values.
- Truthful labeling: `live_dramatic_scene_simulator` option is explicitly
  labeled "(partial foundation)".

`administration-tool/static/manage_story_runtime_experience.js`:

- Fetches from `/api/v1/admin/story-runtime-experience`, writes configured
  values to form fields, renders truth surface (degradation markers +
  validation warnings + effective values + raw payload).
- Save PUTs normalized payload; surfaces `update_warnings` as a visible
  banner so the operator sees misleading combinations rather than silently
  accepting them.

## What is partially implemented

### `live_dramatic_scene_simulator`

The runtime has the foundational pulse-based packaging contract and
continuation-state surface, but autonomous scene motion without player input
and free-running NPC↔NPC exchange beyond packaging are **not** implemented at
the executor level. The truth surface declares this honestly via the
`live_simulator_partial_foundation` degradation marker, which is surfaced
both in the per-turn event and in `runtime_config_status()`. The admin UI
reads these markers rather than claiming full honor.

### Frontend player-shell projection

The frontend `routes_play.py` has not been modified. The new packaging
fields (`narration_blocks`, `action_pulses`, `spoken_lines`,
`scene_motion_summary`, `continuation_state`) flow through unchanged — the
frontend can begin consuming them when the player shell is updated. Until
then, players continue to see the original `gm_narration` + `spoken_lines`
surfaces (which are still populated), just with mode-aware content.

## What remains intentionally gated

- Write-capable mutation of scene motion beyond pulse-count governance.
- Multi-turn autonomous scene advancement without player action.
- Dedicated beat-progression storage separate from existing
  `narrative_threads` / continuity impacts.

These are explicitly reserved for future waves per the approved plan and
would require deeper executor rewiring.

## Files changed

See `CHANGED_FILES_STORY_RUNTIME_EXPERIENCE.txt`.

## Tests added

| Test file | Count | What it proves |
|---|---|---|
| `tests/integration/test_story_runtime_experience.py` | 14 | Defaults, normalization, validation, policy caps, degradation markers, mode-difference packaging, truth surface |
| `backend/tests/services/test_story_runtime_experience_service.py` | 6 | Baseline seeding, idempotent seed, update persistence, warnings on misleading combos, admin truth surface for live mode, resolved-runtime-config carries the section |

**All 20 tests pass.**

## Truth / degradation constraints still in force

- Admin UI must not present `live_dramatic_scene_simulator` as fully active —
  it is labeled "(partial foundation)" in the mode dropdown and the truth
  surface always emits `live_simulator_partial_foundation`.
- `turn_based_narrative_recap` hard-caps pulses to 1 and disables inter-NPC
  exchange and auto-progress at the policy layer; the admin cannot configure
  otherwise without visible degradation markers.
- `dramatic_turn` hard-caps pulses to 2.
- The experience policy is authoritative; packaging respects the effective
  (capped) values, not the configured ones, and reports any gap.

## Docker / bootstrap

No manual first-run setup required. `docker-up.py` already generates
`INTERNAL_RUNTIME_CONFIG_TOKEN`; `docker-compose.yml` wires
`BACKEND_RUNTIME_CONFIG_URL` for the play service;
`ensure_governance_baseline()` seeds Story Runtime Experience defaults on
backend startup. Fresh clone → `python docker-up.py up` → recap mode is the
default and operator changes through the admin take effect on next reload.
