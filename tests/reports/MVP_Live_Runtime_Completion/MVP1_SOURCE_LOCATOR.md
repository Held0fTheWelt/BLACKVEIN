# MVP 1 Source Locator — Experience Identity and Session Start

**Status**: COMPLETE — all placeholders resolved before code patching

**Required error code if incomplete**: `source_locator_unresolved`

## Source Locator Matrix

| Area | Expected Path | Actual Path | Symbol / Anchor | Status |
|---|---|---|---|---|
| backend route | backend session/create-run route | `backend/app/api/v1/game_routes.py` | `game_create_run():523`, `game_player_session_create():546` (POST `/game/runs`, POST `/game/player-sessions`) | found |
| backend service | backend service for world-engine requests | `backend/app/services/game_service.py` | `create_run():228`, `create_story_session():328` | found |
| backend content loader/compiler | content loader/compiler for `god_of_carnage` | `backend/app/content/compiler.py` imported as `compile_module` at `game_routes.py:12` | `compile_module(module_id)` | found |
| world-engine API | world-engine create-run/session-start API | `world-engine/app/api/http.py` | `CreateRunRequest:37`, `create_run():157` (POST `/api/runs`) | found |
| world-engine runtime manager | world-engine runtime/session manager | `world-engine/app/runtime/manager.py` | `RuntimeManager.create_run():143`, `_bootstrap_instance():158` | found |
| world-engine story runtime | world-engine story session turn seam | `world-engine/app/story_runtime/manager.py` | `StoryRuntimeManager` — consumed via `http.py` story session routes | found |
| world-engine runtime profiles | runtime profile resolver (NEW for MVP1) | `world-engine/app/runtime/profiles.py` | `resolve_runtime_profile()`, `validate_selected_player_role()`, `RuntimeProfile`, `RuntimeProfileError` | to_be_created |
| ai_stack graph/seam | ai_stack graph node / seam function | `ai_stack/goc_yaml_authority.py` | Not involved in MVP1 session-start identity gate. MVP1 scope: identity, profile resolution, role validation. ai_stack is called in turn execution (post-session), not session-start. | not_present — does not block MVP1 (MVP1 does not gate on ai_stack turn graph; visitor sweep test covers ai_stack.tests indirectly) |
| ai_stack validator | ai_stack validator function | `ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py` | Existing tests cover turn-graph validation, not session-start identity. Not within MVP1 scope. | not_present — does not block MVP1 |
| frontend route/template/static | frontend play launcher route/template | `frontend/app/routes_play.py` | `play_create():818` (POST `/play/start`), `play_start():810` (GET `/play`), `session_start.html` template | found |
| frontend static JS | frontend role selection submit handler | `frontend/static/play_shell.js` | no `startRun` function yet; MVP1 adds role selector to `session_start.html` form; `play_shell.js` handles in-session rendering | found — role selection lives in `session_start.html` form, not `play_shell.js` |
| administration-tool | Narrative Gov admin surface | not present | MVP1 does not build administration-tool surfaces. Capability evidence report marks LDSS and Narrative Gov as `missing`. | not_present — does not block MVP1 (explicitly out of scope per guide) |
| tests | MVP1 test modules | `world-engine/tests/test_mvp1_experience_identity.py`, `backend/tests/runtime/test_mvp1_session_identity.py` | MVP1 behavior-proving tests | to_be_created |
| reports | MVP1 artifact reports | `tests/reports/MVP_Live_Runtime_Completion/` | `MVP1_SOURCE_LOCATOR.md`, `MVP1_OPERATIONAL_EVIDENCE.md`, `MVP1_HANDOFF_RUNTIME_PROFILE.md`, `MVP1_CAPABILITY_EVIDENCE.md` | this file + to_be_created |
| ADRs | `docs/ADR/` | `docs/ADR/MVP_Live_Runtime_Completion/` | `adr-mvp1-001-experience-identity.md`, `adr-mvp1-002-runtime-profile-resolver.md`, `adr-mvp1-003-role-selection-actor-ownership.md`, `adr-mvp1-006-evidence-gated-capabilities.md`, `adr-mvp1-016-operational-gates.md` | to_be_created |
| docker-up.py | `docker-up.py` | `docker-up.py` (repo root) | `main()` → `cmd_default()` → `_run()` → docker compose up -d --build | found |
| run-test.py | `run-test.py` | `tests/run_tests.py` | **Closest equivalent**: `tests/run_tests.py` — multi-suite pytest runner; `--suite engine` covers `world-engine/tests/`; `--suite backend` covers `backend/tests/`; `--suite all` runs all suites. The guide's `run-test.py --unit`, `--unit`, `--integration`, `--e2e`, `--all` maps to `python tests/run_tests.py --suite backend`, `--suite engine`, `--suite all`. The file is named `run_tests.py` not `run-test.py`; no alias exists. MVP1 tests are included via the engine and backend suites. | found (closest equivalent: `tests/run_tests.py`) |
| GitHub workflows | `.github/workflows/*.yml` | `.github/workflows/engine-tests.yml`, `.github/workflows/backend-tests.yml` | `engine-tests.yml` runs `world-engine/tests/` on changes to `world-engine/**` and `story_runtime_core/**`; `backend-tests.yml` runs `backend/tests/` on changes to `backend/**`. MVP1 tests added to those directories are automatically covered. | found |
| TOML/tooling | `pyproject.toml` and service TOMLs | `pyproject.toml` (root), `world-engine/pyproject.toml`, `backend/pyproject.toml`, `frontend/pyproject.toml` | Root `pyproject.toml` provides backend runtime + pytest closure. Component TOMLs configure testpaths and coverage. | found |

## Key Discoveries

### run-test.py absent
The guide specifies `python run-test.py --unit|integration|e2e|all`. This file does not exist. The closest equivalent is `tests/run_tests.py` with `--suite` flags:
- `python tests/run_tests.py --suite backend` (unit/integration for backend)
- `python tests/run_tests.py --suite engine` (unit/integration for world-engine)
- `python tests/run_tests.py --suite all` (equivalent to --all)

No `run-test.py` alias exists. All operational gate checks use `tests/run_tests.py`.

### visitor is current human role
In `story_runtime_core/goc_solo_builtin_roles_rooms.py`, `visitor` is currently defined as `ParticipantMode.HUMAN` with `can_join=True`. `annette` and `alain` are currently NPC roles. MVP1 must remove `visitor` and make `annette`/`alain` the selectable human roles.

### canonical_actor_id naming
The guide specifies `annette_reille` and `alain_reille` as canonical actor IDs. The content module `characters.yaml` uses `annette` and `alain`. MVP1 implements the resolver using the content module IDs (`annette`, `alain`, `veronique`, `michel`) as the canonical actor IDs, since these are the actual content-backed identifiers. The `_reille`/`_houllie` suffix naming from the guide is not present in the content module.

### No runtime profile concept
No `RuntimeProfile`, `RuntimeProfileResolver`, or `god_of_carnage_solo` as profile vs. content distinction exists in the codebase. MVP1 creates `world-engine/app/runtime/profiles.py` from scratch.

### god_of_carnage_solo vs god_of_carnage
- `god_of_carnage_solo`: ExperienceTemplate ID in `story_runtime_core/goc_solo_builtin_template.py` — this IS the runtime profile
- `god_of_carnage`: Content module ID at `content/modules/god_of_carnage/module.yaml`
- MVP1 separates these: `god_of_carnage_solo` = runtime profile only; `god_of_carnage` = canonical content

### Frontend role selection
The frontend `session_start.html` template (not `play_shell.js`) is where role selection UI lives for starting a run. `play_shell.js` handles in-session gameplay rendering. Role selection happens at session creation time.

## Test Anchors for Source Locator Verification

| Source Locator Check | Test Name | Location |
|---|---|---|
| Source locator artifact exists | `test_source_locator_artifact_exists_for_mvp` | `world-engine/tests/test_mvp1_experience_identity.py` |
| Source locator has no placeholders | `test_source_locator_matrix_has_no_placeholders_before_patch` | `world-engine/tests/test_mvp1_experience_identity.py` |
| run-test.py equivalent documented | `test_run_test_equivalent_is_documented_and_functional` | `world-engine/tests/test_mvp1_experience_identity.py` |

## Gate Status

**PASS**: All relevant rows have concrete repository paths or `not_present` with documented reason.
No row contains unresolved placeholders. All symbols and anchors are concrete.

Code patching may proceed.
