# ADR-MVP1-001: Experience Identity

**Status**: Accepted
**MVP**: 1 — Experience Identity and Session Start
**Date**: 2026-04-24

## Context

The God of Carnage solo experience had no formal separation between its content module (`god_of_carnage`) and its runtime profile (`god_of_carnage_solo`). The template system treated `god_of_carnage_solo` as a content template with roles, rooms, and props — conflating runtime configuration with story truth. The human role was `visitor`, a synthetic identity not present in the canonical play. This created an invalid experience identity where the runtime could not prove which content backed the session.

## Decision

1. `god_of_carnage` is the canonical content module. It owns all story truth: characters, scenes, relationships, escalation axes, props, and endings. It lives at `content/modules/god_of_carnage/`.

2. `god_of_carnage_solo` is a runtime profile only. It does not own story truth. It binds to `god_of_carnage` content. It is resolved by the runtime profile resolver at `world-engine/app/runtime/profiles.py`.

3. `visitor` is removed from the live God of Carnage solo path. It must not appear as a role, actor, session participant, prompt responder, or lobby seat.

4. The player must choose either `annette` or `alain` before a session can be created. Missing or invalid selections fail with structured error codes.

## Affected Services/Files

- `story_runtime_core/goc_solo_builtin_roles_rooms.py` — removed visitor, added annette/alain as HUMAN roles
- `world-engine/app/runtime/profiles.py` — new runtime profile resolver (MVP1-P01)
- `world-engine/app/api/http.py` — CreateRunRequest extended with runtime_profile_id, selected_player_role
- `world-engine/app/runtime/manager.py` — _bootstrap_instance extended with preferred_role_id
- `backend/app/services/game_service.py` — create_run extended with runtime_profile_id, selected_player_role
- `backend/app/api/v1/game_routes.py` — game_create_run and game_player_session_create extended

## Consequences

- Any session creation for God of Carnage solo must supply `runtime_profile_id=god_of_carnage_solo` and `selected_player_role=annette|alain`
- Sessions using only `template_id=god_of_carnage_solo` (legacy path) still work but do not get the profile-aware response fields
- `visitor` must never be reintroduced in any role, prompt, lobby seat, or compatibility fallback

## Alternatives Considered

- Keep `visitor` and use it as a role alias: rejected — visitor is not a canonical GoC character and creates false identity
- Use two separate templates (goc_solo_annette, goc_solo_alain): rejected — violates profile-only separation
- Make role selection optional: rejected — MVP1 stop condition requires mandatory selection

## Validation Evidence

- `test_visitor_absent_from_prompts_responders_lobby` — PASS
- `test_goc_solo_not_loadable_as_content_module` — PASS
- `test_profile_contains_no_story_truth` — PASS
- `test_valid_annette_start` — PASS
- `test_valid_alain_start` — PASS

## Related Findings

- GUIDE-PATCH-001 (visitor removal)
- GUIDE-PATCH-007 (role selection required)
- MVP1_SOURCE_LOCATOR.md

## Operational Gate Impact

`docker-up.py`, `tests/run_tests.py`, GitHub workflows, and TOML/tooling all remain valid. No changes to operational wiring required for this ADR.
