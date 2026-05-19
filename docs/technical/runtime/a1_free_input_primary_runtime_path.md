# A1 Repair Note — Free Input as Primary Runtime Path

Status: implemented for the playable frontend shell and canonical player session path.

## Objective

Ensure that free natural player input is executed as a real runtime turn, not queued as a frontend-only note.

## Runtime path after repair

1. Player opens `/play/<run_id>`.
2. Frontend shell resolves or creates the canonical player session for that run:
   - `POST /api/v1/game/player-sessions` with `run_id` or a runtime profile/template selection.
3. Player submits text at `/play/<run_id>/execute`.
4. Frontend forwards input to:
   - `POST /api/v1/game/player-sessions/<run_id>/turns`
   - payload: `{ "player_input": "<free text>" }`
5. Backend resolves the stored World-Engine story session and proxies turn execution through `game_service`.
6. World-Engine executes the turn through the runtime graph and returns interpreted turn output.

**Player-turn graph (ADR-0062):** `resolve_player_action` → `director_compose_realization` → `realize_via_capabilities` → model invoke → validate → commit. See [director_realization_thin_path_contract.md](director_realization_thin_path_contract.md).

## Command compatibility

- Explicit commands (`/` and `!` forms) remain supported.
- They are treated as a recognized special case of the same turn execution contract.
- Free natural language remains the default player-facing input style.

## UI truthfulness updates

- Shell copy now states natural language as the primary input path.
- The execute action runs a real runtime turn via the backend -> world-engine bridge.
- After each successful turn, the play shell stores a **compact projection** of the bridge JSON and renders:
  - **Narration** from `turn.visible_output_bundle.gm_narration` (truth-aligned staging returned by the runtime).
  - **Scene / commit summary** from `state.committed_state` when present (committed scene id, reason code, validation status, graph error count).
  - **Committed consequences** tail when the engine exposes `last_committed_consequences` (continuity signal for evaluators).
  - A collapsible **raw projection** block for operators (same fields as stashed in the Flask session, not a second authority).

## Known limits (still in scope boundary)

- Player-session binding stores run id, module id, template/runtime profile, owner, and World-Engine story-session id in the backend save-slot continuity layer.
- The removed in-process `/api/v1/sessions` bridge is no longer part of the player runtime path.

## Play shell UX (frontend)

- **Play** tab: chronological transcript from `GET/POST /api/v1/game/player-sessions/<run_id>` responses and the primary **Execute runtime turn** composer. XHR + `Accept: application/json` updates the transcript without a full page reload.
- **Operator** tab: last truncated turn bridge payload and copy helpers; diagnostics use World-Engine story-session ids through governance/operator endpoints, not a backend session bundle.
- **Live room** WebSocket remains a separate world-engine runtime-manager path; see `docs/dev/play_shell_ux.md`.
