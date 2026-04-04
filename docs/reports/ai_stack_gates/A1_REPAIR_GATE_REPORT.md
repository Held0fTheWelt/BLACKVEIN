# A1 Repair Gate Report — Free Natural Input as Dominant Story-Play Path

Date: 2026-04-04

Verification run: 2026-04-04 (repair block re-audit)

## 1. Scope completed

- Confirmed the main product play shell (`/play/<run_id>`) presents natural language as the default and dispatches real story turns to the backend, which proxies to World-Engine `StoryRuntimeManager`.
- Confirmed World-Engine prototype Web UI accepts `player_input` as the primary WebSocket message shape; explicit `action` payloads remain a supported special case.
- Documented the architectural split between HTTP authoritative story turns and WebSocket live-run simulation so user-facing copy stays truthful.
- Tightened play-shell validation feedback to describe the natural-language-first contract.
- Extended frontend route test to assert the play template exposes natural input as the primary path (not only backend dispatch mocks).

## 2. Files changed

- `frontend/app/routes.py`
- `frontend/templates/session_shell.html` (unchanged this pass; already NL-primary)
- `frontend/tests/test_routes_extended.py`
- `world-engine/app/web/templates/index.html`
- `world-engine/app/web/static/styles.css`
- `docs/reports/ai_stack_gates/A1_REPAIR_GATE_REPORT.md`

## 3. Player-facing paths where natural input is primary

| Surface | Role | Execution |
|--------|------|-----------|
| Frontend play shell `/play/<run_id>` | Primary intended narrative play UX | `POST /api/v1/sessions/<id>/turns` with `player_input` → World-Engine `POST /api/story/sessions/<id>/turns` → `StoryRuntimeManager.execute_turn` |
| World-Engine web prototype | Developer/live-run demo | WebSocket `player_input` / `input` → `RuntimeManager._normalize_player_message` → `RuntimeEngine.apply_command` (committed room transcript / state) |

## 4. Command-first or secondary paths that remain

- **World-Engine prototype — Say / Emote / Inspect controls:** Intentionally secondary quick actions for the live-run simulator; natural textarea remains first in layout and copy.
- **Explicit slash or bang commands:** Still supported anywhere the shared interpreter maps them; treated as a special case of the same normalization layer (WebSocket) or story turn string (HTTP path).

## 5. Why remaining paths exist

- Quick **action** buttons and **slash** forms are retained for testing, accessibility, and parity with legacy run-control flows without making them the default assumption.
- The **WebSocket run runtime** is not replaced by the story graph; it is a distinct, older execution host for room-scale simulation. The report and UI note clarify that the **authoritative narrative graph** path is the HTTP story API used by the frontend play shell.

## 6. Tests added/updated

- Updated: `frontend/tests/test_routes_extended.py::test_play_shell_ticket_ok_and_error` — asserts NL-primary copy and `player_input` field in rendered HTML.
- Existing coverage retained:
  - `test_play_execute_empty_and_runtime_dispatch` — proves `player_input` is posted to backend turns API.
  - `world-engine/tests/test_websocket.py` — natural speech, ambiguous natural input, explicit command special case.
  - `world-engine/tests/test_story_runtime_api.py::test_story_turns_cover_primary_free_input_paths` — HTTP story turns for speech / action / mixed / ambiguous / explicit command.
  - `story_runtime_core/tests/test_input_interpreter.py` — interpreter contract.
  - Backend: `test_execute_turn_proxies_to_world_engine` and related session route tests.

## 7. Exact test commands run

```powershell
cd frontend
python -m pytest tests/test_routes_extended.py -k "play_" -v
```

```powershell
cd world-engine
python -m pytest tests/test_websocket.py tests/test_story_runtime_api.py -v --tb=short
```

```powershell
cd ..
$env:PYTHONPATH='.'
python -m pytest story_runtime_core/tests/test_input_interpreter.py -v --tb=short
```

```powershell
cd backend
python -m pytest tests/test_session_routes.py tests/test_session_api_closure.py -k "turns or execute_turn" -v --tb=short
```

## 8. Verdict: Pass / Partial / Fail

**Pass**

## 9. Reason for verdict

- At least one intended main path (frontend play shell) defaults to natural language and reaches real story-turn execution on World-Engine.
- Interpreter output is part of executed turn payloads; WebSocket natural input produces committed transcript events, not log-only behavior.
- Explicit commands remain supported but are not the dominant UX assumption.
- Tests prove route-level dispatch and story/WebSocket execution behavior, and the play shell HTML test proves the primary path is user-visible.

## 10. Remaining risk

- Frontend session state holds run→backend session bindings; losing session requires re-entering the play flow.
- Run/template id alignment for backend session creation can drift if content pipelines change module identifiers.
