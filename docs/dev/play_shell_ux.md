# Play shell: Player vs Operator vs WebSocket

## Player surface (authoritative)

- Route: Flask frontend `/play/<run_id>`.
- **Execute runtime turn** sends natural language to `POST /api/v1/sessions/<backend_session_id>/turns` (via server-side `request_backend` with the user JWT).
- The **Story transcript** lists successful turns in order. Entries are stored in the **Flask session** (browser cookie), capped (last 50). They are lost when that session expires or is cleared.

## Operator surface

- **Last turn (stored)** shows a truncated JSON bundle from the last successful turn response (`turn`, `state`, `diagnostics`, …) for debugging.
- **Refresh from API** calls `GET /api/v1/sessions/<backend_session_id>/play-operator-bundle` through the frontend `/api/v1/...` proxy. This requires:
  - a valid user JWT (same as the rest of the app), and
  - the backend session to have been created **while authenticated**, so metadata contains `play_shell_owner_user_id` matching the JWT subject.
- If the session was created without JWT (e.g. MCP tools), refresh returns **403** `OWNER_NOT_BOUND`.

## Live room WebSocket

- Uses the play ticket and world-engine `ws://…/ws?ticket=…` against the **play service host** from `ws_base_url` (not necessarily the frontend origin).
- Delivers **runtime manager** snapshots (room, transcript tail, etc.). This is **not** the same contract as the story HTTP turn executed from the Play tab.

## Roadmap

- Persist transcript server-side or via world-engine history APIs when available.
- Unify or explicitly productize the two runtime paths if both should be player-visible long term.
