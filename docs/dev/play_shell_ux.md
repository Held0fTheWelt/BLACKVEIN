# Play shell: Player vs Operator vs WebSocket

## Player surface (authoritative)

- Route: Flask frontend `/play/<run_id>`.
- **Execute runtime turn** sends natural language to `POST /api/v1/game/player-sessions/<run_id>/turns` (via server-side `request_backend` with the user JWT).
- The **Story transcript** lists successful turns in order from `game_player_session_v1` story entries. Continuity is keyed by the backend save-slot binding for the run, not by an in-process backend session id.

## Operator surface

- **Last turn (stored)** shows a truncated JSON bundle from the last successful player-session turn response (`turn`, `state`, `diagnostics`, ...) for debugging.
- **Refresh from API** calls `GET /api/v1/game/player-sessions/<run_id>` through the frontend `/api/v1/...` proxy. This requires the same valid user JWT as the rest of the app.

## Live room WebSocket

- Uses the play ticket and world-engine `ws://…/ws?ticket=…` against the **play service host** from `ws_base_url` (not necessarily the frontend origin).
- Delivers **runtime manager** snapshots (room, transcript tail, etc.). This is **not** the same contract as the story HTTP turn executed from the Play tab.

## Roadmap

- Expose richer operator diagnostics for the World-Engine story-session id when needed.
- Keep the player-visible path single: `/api/v1/game/player-sessions`.
