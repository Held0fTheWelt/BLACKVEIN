# Canonical Player Flow Repair Record

Date: 2026-04-21

## Root Cause Closure

The break was an architectural seam: the frontend player shell mixed WebSocket run/ticket mechanics, browser-local backend session bindings, and the deprecated `/api/v1/sessions` bridge while the real story runtime lived in World-Engine story sessions. Template ids and module ids were also stitched together in frontend memory instead of resolved by the content authority.

The repaired contract makes `/api/v1/game/player-sessions` the backend-owned canonical player bridge. It binds `run_id` to the authoritative World-Engine story session server-side, resolves `template_id -> module_id` through published game content, returns a story-window projection at entry, and routes turns through the same player-session bridge.

## Files Changed

- `backend/app/api/v1/game_routes.py`
- `backend/app/services/game_content_service.py`
- `backend/app/services/game_service.py`
- `frontend/app/routes_play.py`
- `frontend/templates/session_shell.html`
- `frontend/static/play_shell.js`
- `world-engine/app/story_runtime/manager.py`
- `world-engine/app/config.py`
- `world-engine/app/web/templates/index.html`
- `backend/tests/test_game_routes.py`
- `frontend/tests/test_routes_extended.py`
- `world-engine/tests/test_story_runtime_api.py`
- `docs/technical/architecture/canonical-player-flow-contract.md`

## Player Flow Truth Record

Canonical entry: frontend `/play/start` calls backend `POST /api/v1/game/player-sessions`, then redirects to `/play/<run_id>`.

Identifier model: `template_id` selects published experience content; `module_id` selects compiled runtime module; `run_id` is the player continuity handle; `runtime_session_id` is the World-Engine story session id; ticket ids and backend session ids are outside the canonical player story path.

Continuity: backend `GameSaveSlot(kind="canonical_player_session")` stores the run/story-session binding. Browser cookies and Flask session maps are not continuity authority.

Initial story entry: World-Engine creates committed Turn 0 during story session creation. `get_state()` now exposes `story_window.entries`, including the opening.

Turn loop: player input goes to `POST /api/v1/game/player-sessions/<run_id>/turns`; backend executes the World-Engine story turn and returns refreshed `story_entries` for the same story window.

Player/operator boundary: frontend player shell renders only story entries and compact state. World-Engine web UI is relabeled as a simulator/operator surface.

Governance boundary: the live path is covered by game-content publication, canonical compilation, governed World-Engine runtime config, model routing, validation, and guardrail diagnostics. Existing administration governance remains a control plane; it is not a player UI.

## Mismatch Closure Map

| Mismatch | Old behavior | Repaired behavior | Status | Evidence |
| --- | --- | --- | --- | --- |
| Player shell was transport/debug-first | Ticket, backend session id, WebSocket tab, and placeholders dominated the UI. | Story shell renders `story_entries` from `game_player_session_v1`. | Fully closed | Frontend tests assert no WebSocket connect or backend-session data attribute. |
| Deprecated backend session used for live play | Frontend created `/api/v1/sessions` and turned through `/sessions/<id>/turns`. | Frontend calls only `/api/v1/game/player-sessions/<run_id>/turns`. | Fully closed | Frontend dispatch test verifies canonical path. |
| Template/module seam hidden in browser | Frontend YAML/session map resolved `god_of_carnage_solo -> god_of_carnage`. | Backend resolves published `canonical_compilation.module_id` and persists binding. | Fully closed | Backend player-session tests assert server-side slot metadata. |
| Refresh continuity depended on browser state | Cookie/session maps stored backend session id. | `GameSaveSlot` stores runtime story session id by `run_id`. | Fully closed | Backend tests assert persisted canonical player slot. |
| Empty initial story | Shell showed “no turns yet” until first player input. | World-Engine `story_window` exposes committed Turn 0 opening at state read. | Fully closed | World-Engine test asserts opening story entry. |
| World-Engine web UI looked like player UI | Page title said Play Service Prototype. | Page title and copy identify simulator/operator role. | Fully closed | Template/config relabeled. |
| Governance assumed, not traced to live path | Control surfaces existed but player path used another seam. | Player session bundle includes content/runtime governance boundary and uses governed story runtime. | Partially closed | Live path now uses governed runtime; broader admin UI coverage remains control-plane evidence, not full policy editor proof. |

## Validation Record

Commands run:

- `env PYTHONPYCACHEPREFIX=/tmp/wos-pycache python -m py_compile ...` passed for modified Python files.
- `env PYTHONPYCACHEPREFIX=/tmp/wos-pycache PYTEST_ADDOPTS=-s python -m pytest -q backend/tests/test_game_routes.py -k "player_session" --tb=short --no-cov` passed: 2 selected tests.
- `env PYTHONPYCACHEPREFIX=/tmp/wos-pycache PYTHONPATH=/mnt/d/WorldOfShadows/frontend PYTEST_ADDOPTS=-s python -m pytest -q frontend/tests/test_routes_extended.py -k "play_" --tb=short --no-cov` passed: 8 selected tests.

Observed request sequence covered by tests:

1. `POST /api/v1/game/player-sessions` creates run and story session.
2. Response contains `contract`, `run_id`, `template_id`, `module_id`, `runtime_session_id`, `story_entries`, `story_window`, `can_execute`.
3. `GET /play/<run_id>` renders opening story text.
4. `POST /play/<run_id>/execute` dispatches to `/api/v1/game/player-sessions/<run_id>/turns`.
5. JSON turn response returns full refreshed `story_entries`.

Remaining limitation: full browser visual verification was not run in this pass. World-Engine focused test needs a writable RAG cache root in this checkout; use `WOS_REPO_ROOT=/tmp/wosroot` with source symlinks when validating from this read-only mounted tree.
