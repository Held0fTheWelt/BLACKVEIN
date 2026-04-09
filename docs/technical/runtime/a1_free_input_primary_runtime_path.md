# A1 Repair Note — Free Input as Primary Runtime Path

Status: implemented for the playable frontend shell and backend session bridge.

## Objective

Ensure that free natural player input is executed as a real runtime turn, not queued as a frontend-only note.

## Runtime path after repair

1. Player opens `/play/<run_id>`.
2. Frontend shell resolves or creates a backend runtime session for that run:
   - `POST /api/v1/sessions` with `module_id` derived from the selected run template.
3. Player submits text at `/play/<run_id>/execute`.
4. Frontend forwards input to:
   - `POST /api/v1/sessions/<backend_session_id>/turns`
   - payload: `{ "player_input": "<free text>" }`
5. Backend executes `interpret_player_input(...)` and proxies turn execution to World-Engine story runtime.
6. World-Engine executes the turn through the runtime graph and returns interpreted turn output.

## Command compatibility

- Explicit commands (`/` and `!` forms) remain supported.
- They are treated as a recognized special case of the same turn execution contract.
- Free natural language remains the default player-facing input style.

## UI truthfulness updates

- Shell copy now states natural language as the primary input path.
- The execute action now runs a real runtime turn and surfaces runtime interpretation kind in user feedback.

## Known limits (still in scope boundary)

- Backend session binding currently uses the chosen run template id as the module identifier for backend session creation.
- This keeps runtime execution real and authoritative, but cross-service run metadata normalization can still be improved in later milestones.
