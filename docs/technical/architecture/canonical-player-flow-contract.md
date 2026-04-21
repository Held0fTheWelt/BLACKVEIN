# Canonical Player Flow Contract

Date: 2026-04-21

## Canonical Entry Path

The canonical player entry path is:

1. Frontend game menu/start page.
2. `POST /api/v1/game/player-sessions` with a `template_id`.
3. Backend creates or resumes a play `run_id`, resolves the published template to a runtime `module_id`, creates or resumes a World-Engine story session, and returns `game_player_session_v1`.
4. Frontend renders `/play/<run_id>` from `GET /api/v1/game/player-sessions/<run_id>`.
5. Player turns submit to `POST /api/v1/game/player-sessions/<run_id>/turns`.

The authoritative gameplay runtime is the World-Engine story runtime behind `/api/story/sessions`. The backend owns launch, identifier resolution, and server-side continuity. The frontend is a renderer and turn composer.

## Identifier Model

| Identifier | Role | Canonical owner |
| --- | --- | --- |
| `template_id` | Launcher and published experience selection. | Backend game content/publication layer. |
| `module_id` | Compiled runtime content module used by the story runtime. | Backend content compiler and World-Engine story runtime. |
| `run_id` | Player launch and continuity handle. | World-Engine run lifecycle, bound by backend save-slot continuity. |
| `ticket_id` | WebSocket live-room simulator join token. | Simulator/operator path only; not canonical story play. |
| Backend session id | Transitional in-process compatibility session id. | `/api/v1/sessions`; not canonical player gameplay. |
| Runtime session id | World-Engine story session id. | World-Engine story runtime. |

Template-to-module mapping lives in backend game content via `canonical_compilation.module_id`, with the authored `god_of_carnage_solo -> god_of_carnage` fallback. Browser-local mappings are not authoritative.

## Session Continuity

Continuity persists server-side in `GameSaveSlot` rows with `kind="canonical_player_session"`, keyed by a deterministic hash of `run_id`. The slot stores the runtime story session id, module id, template id, run id, and continuity owner. Refresh and re-entry call `GET /api/v1/game/player-sessions/<run_id>` and do not rely on browser cookies, Flask session maps, or WebSocket tickets.

If the stored World-Engine story session is missing, the backend recreates the story session from the run/template/module binding and updates the slot. Other World-Engine failures are surfaced honestly.

## Story Entry And Turn Contract

Story state is returned as `story_window.contract == "authoritative_story_window_v1"`. It contains player-visible entries derived from committed story runtime diagnostics and history:

- opening entry from committed Turn 0;
- player turn entries from submitted input;
- runtime response entries from `visible_output_bundle`, spoken lines, and committed consequences.

The frontend story window renders `story_entries` at entry and replaces the same window after each turn with the returned authoritative entries. Transport metadata, ticket state, byte counts, backend session ids, graph internals, and operator bundles are not player story output.

The first turn is legal only when `runtime_session_ready == true`, `can_execute == true`, and the story window has received the committed opening state. The input control is disabled otherwise.

## Surface Boundaries

The World-Engine web UI is an operator/development simulator for run, lobby, WebSocket, and room-state mechanics. It is not the canonical player story surface.

The backend `/api/v1/sessions` surface remains classified as non-authoritative/transitional for live gameplay. The canonical frontend player path must not create or turn through that endpoint.

## Governance Boundary

Live player story generation is governed by:

- backend game content publication lifecycle before template/module binding;
- backend content compiler and canonical module validation;
- World-Engine governed runtime config, model routing, validation, self-correction, and guardrails;
- World-Engine committed Turn 0 and per-turn narrative commit validation.

Administration governance surfaces cover content lifecycle and operational/runtime configuration. Evidence and aggregate governance routes must be read as control-plane/diagnostic views, not player surfaces.
