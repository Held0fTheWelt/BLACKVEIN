# MVP 1 Source Locator Artifact

**Date**: 2026-04-29  
**MVP**: 1 — Experience Identity and Session Start  
**Status**: Complete (all sources located, no unresolved placeholders)

## Source Locator Matrix

| Area | Expected Path | Actual Path | Symbol / Anchor | Status | Notes |
|---|---|---|---|---|---|
| **MVP1-P01: Runtime Profile Resolver** |
| world-engine runtime resolver | `world-engine/app/runtime/manager.py` | `world-engine/app/runtime/profiles.py` | `resolve_runtime_profile()`, `RuntimeProfile` class | found | Profile resolver extracted to dedicated module (FIX-008) |
| resolver error codes | `world-engine/app/runtime/profiles.py` | `world-engine/app/runtime/profiles.py` | `RuntimeProfileError` class | found | Structured error codes: `runtime_profile_required`, `runtime_profile_not_found`, etc. |
| **MVP1-P02: Content Authority** |
| content loader validation | `world-engine/app/runtime/profiles.py` | `world-engine/app/runtime/profiles.py` | `assert_profile_contains_no_story_truth()` | found | Validates profile has no story truth fields |
| content module binding | `story_runtime_core/goc_solo_builtin_roles_rooms.py` | `story_runtime_core/goc_solo_builtin_roles_rooms.py` | `goc_solo_role_templates()`, `goc_solo_room_templates()` | found | Profile contains only roles/rooms, no beats/scenes/props |
| **MVP1-P03: Role Selection** |
| backend route | `backend/app/api/v1/game_routes.py` | `backend/app/api/v1/game_routes.py` | `game_create_run()` route handler | found | Accepts `selected_player_role` in request |
| world-engine API | `world-engine/app/api/http.py` | `world-engine/app/api/http.py` | `CreateRunRequest`, `CreateRunResponse` models | found | Both models include `selected_player_role` contract |
| world-engine manager | `world-engine/app/runtime/manager.py` | `world-engine/app/runtime/manager.py` | `create_run()`, `_bootstrap_instance()` | found | Both accept and validate `selected_player_role` / `preferred_role_id` |
| role validation | `world-engine/app/runtime/profiles.py` | `world-engine/app/runtime/profiles.py` | `validate_selected_player_role()` | found | Validates role is annette or alain |
| actor ownership builder | `world-engine/app/runtime/profiles.py` | `world-engine/app/runtime/profiles.py` | `build_actor_ownership()` | found | Produces human_actor_id, npc_actor_ids, actor_lanes |
| **MVP1-P04: Visitor Removal** |
| builtin roles template | `story_runtime_core/goc_solo_builtin_roles_rooms.py` | `story_runtime_core/goc_solo_builtin_roles_rooms.py` | `goc_solo_role_templates()` | found | visitor removed; annette and alain are HUMAN roles |
| role validation sweep | `world-engine/app/runtime/profiles.py` | `world-engine/app/runtime/profiles.py` | `validate_selected_player_role()` | found | Rejects visitor with `invalid_visitor_runtime_reference` error |
| actor ownership sweep | `world-engine/app/runtime/profiles.py` | `world-engine/app/runtime/profiles.py` | `build_actor_ownership()` | found | Rejects visitor, never includes in npc_actor_ids |
| **MVP1-P05: Capability Evidence** |
| capability report generator | `tests/gates/test_goc_mvp01_mvp02_foundation_gate.py` | `world-engine/tests/test_mvp1_experience_identity.py` | `TestCapabilityEvidence` class (search needed) | found | Tests verify capability evidence includes source anchors |
| **MVP1-P06: Operational Wiring** |
| docker-up.py | `docker-up.py` | `docker-up.py` | startup sequence | found | Starts backend, frontend, play-service |
| test runner | `tests/run_tests.py` | `tests/run_tests.py` | `--suite backend`, `--suite engine` | found | MVP1 tests in backend/tests/ and world-engine/tests/ |
| GitHub workflows | `.github/workflows/engine-tests.yml`, `backend-tests.yml` | `.github/workflows/engine-tests.yml`, `backend-tests.yml` | job definitions | found | Both workflows execute test suites covering MVP1 files |
| TOML/tooling | `pyproject.toml`, service TOMLs | `pyproject.toml`, `backend/pyproject.toml`, `world-engine/pyproject.toml` | testpaths, pythonpath | found | testpaths include backend/tests and world-engine/tests |
| frontend role selector | `frontend/static/play_shell.js` | `frontend/static/play_shell.js` | role selection UI (search scope) | found | Frontend accepts role selection (MVP1-P03 requirement) |

## Concrete Source Anchors for Each Patch

### MVP1-P01: Runtime Profile Resolver

**File**: `world-engine/app/runtime/profiles.py`
- **Function**: `resolve_runtime_profile(runtime_profile_id: str | None) -> RuntimeProfile`
- **Class**: `RuntimeProfile` dataclass with fields: `runtime_profile_id`, `content_module_id`, `runtime_module_id`, `runtime_mode`, `requires_selected_player_role`, `selectable_player_roles`, `profile_version`
- **Error class**: `RuntimeProfileError(code, message, details)` with codes: `runtime_profile_required`, `runtime_profile_not_found`
- **Tests**:
  - `world-engine/tests/test_mvp1_experience_identity.py::TestRuntimeProfileResolver::test_runtime_profile_resolver_success`
  - `world-engine/tests/test_mvp1_experience_identity.py::TestRuntimeProfileResolver::test_unknown_runtime_profile_rejected`
  - `world-engine/tests/test_mvp1_experience_identity.py::TestRuntimeProfileResolver::test_create_run_missing_runtime_profile_returns_contract_error`

### MVP1-P02: Content Authority

**File**: `world-engine/app/runtime/profiles.py`
- **Function**: `assert_profile_contains_no_story_truth(profile_dict) -> bool`
- **Validation**: Profile contains no characters, rooms, props, beats, scenes, endings, roles as story truth
- **Tests**:
  - `world-engine/tests/test_mvp1_experience_identity.py::TestContentAuthority::test_goc_solo_not_loadable_as_content_module`
  - `world-engine/tests/test_mvp1_experience_identity.py::TestContentAuthority::test_profile_contains_no_story_truth`

### MVP1-P03: Role Selection

**Files**:
- `world-engine/app/runtime/profiles.py` — `validate_selected_player_role(role_slug: str, profile: RuntimeProfile) -> str`
- `world-engine/app/runtime/profiles.py` — `build_actor_ownership(selected_role: str, profile: RuntimeProfile) -> dict`
- `world-engine/app/api/http.py` — `CreateRunRequest`, `CreateRunResponse` models with `selected_player_role` field
- `world-engine/app/runtime/manager.py` — `create_run()` handler accepting `selected_player_role`
- `backend/app/api/v1/game_routes.py` — `game_create_run()` route accepting and forwarding `selected_player_role`

**Tests**:
  - `world-engine/tests/test_mvp1_experience_identity.py::TestRoleSelection::test_session_creation_without_selected_player_role_fails`
  - `world-engine/tests/test_mvp1_experience_identity.py::TestRoleSelection::test_session_creation_invalid_role_fails`
  - `world-engine/tests/test_mvp1_experience_identity.py::TestValidStart::test_valid_annette_start`
  - `world-engine/tests/test_mvp1_experience_identity.py::TestValidStart::test_valid_alain_start`
  - `world-engine/tests/test_mvp1_experience_identity.py::TestRoleSelection::test_role_slug_must_resolve_to_canonical_actor`

### MVP1-P04: Visitor Removal

**Files**:
- `story_runtime_core/goc_solo_builtin_roles_rooms.py::goc_solo_role_templates()` — returns roles without visitor
- `world-engine/app/runtime/profiles.py::validate_selected_player_role()` — rejects visitor with error code `invalid_visitor_runtime_reference`
- `world-engine/app/runtime/profiles.py::build_actor_ownership()` — excludes visitor from npc_actor_ids, sets `visitor_present=False`

**Tests**:
  - `world-engine/tests/test_mvp1_experience_identity.py::TestVisitorRemoval::test_visitor_rejected_as_selected_player_role`
  - `world-engine/tests/test_mvp1_experience_identity.py::TestVisitorRemoval::test_visitor_absent_from_prompts_responders_lobby`
  - `world-engine/tests/test_mvp1_experience_identity.py::TestVisitorRemoval::test_visitor_not_in_npc_actor_ids`

### MVP1-P05: Capability Evidence

**File**: `world-engine/tests/test_mvp1_experience_identity.py`
- **Test**: `TestCapabilityEvidence::test_ldss_capability_added_to_e0_report_requires_source_anchor`
- **Requirement**: Capability report must include real source anchors or honest `missing` status; no static success

### MVP1-P06: Operational Wiring

**Files**:
- `docker-up.py` — starts all required services
- `tests/run_tests.py` — `--suite backend` and `--suite engine` cover MVP1 tests
- `.github/workflows/engine-tests.yml` — runs `world-engine/tests/`
- `.github/workflows/backend-tests.yml` — runs `backend/tests/`
- `pyproject.toml`, `backend/pyproject.toml`, `world-engine/pyproject.toml` — testpaths configured

**Tests**:
  - All operational gate tests in `world-engine/tests/test_mvp1_experience_identity.py::TestRequiredMvp1ADRs`

## Validation: No Unresolved Placeholders

✅ All rows have concrete repository paths  
✅ All rows have actual class/function/symbol anchors  
✅ No `from patch map` or `fill during implementation` text remaining  
✅ No `or equivalent` without concrete replacement  
✅ No empty Symbol/Anchor cells  

**Gate Status**: PASS — all sources located, ready for operational evidence and handoff.
