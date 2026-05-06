# ADR-0034: Player-Facing Narrative Shell Contract (MVP5)

## Status

Proposed

## Date

2026-05-06

## Context

MVP4 establishes truthful runtime, diagnostics, and canonical HTTP bundles for the play path. MVP5 adds modular block rendering and typewriter delivery in the player shell (`frontend/static/play_shell.js`, `play_blocks_orchestrator.js`, `play_typewriter_engine.js`, `play_block_renderer.js`).

Product feedback indicates a gap between **theatrical narrative goals** (narrator as literate scene-setter and subtle cueing; NPC speech carrying the play) and **current runtime output pacing** (narrator too “complete” in few lines, UI not yet supporting script-like reading).

Separately, ADR-0033 now requires **non-PII player-input correlation** on Backend Langfuse spans for canonical turns. This ADR covers **what the shell must prove** once narrative semantics stabilize.

## Decision

1. **Scope boundary:** ADR-0033 governs commit truth, Langfuse evidence gates, and player-input **hash correlation** on `backend.turn.execute`. **This ADR** governs the **player-visible shell contract**: block stream semantics, transcript vs. live-append rules, and acceptance tests that fail when the shell misrepresents committed runtime truth.

2. **Transcript vs. live delivery:** After each successful turn, the shell must not give the appearance that earlier committed story vanished. The HTTP contract already exposes `story_window.entries` and `visible_scene_output.blocks`; MVP5 orchestration must align with the **cumulative** block policy on the Backend bundle (see `backend/app/api/v1/game_routes.py` cumulative `scene_blocks` when entries carry `scene_blocks`).

3. **Narrator role (product, not only UI):** Narration density, “show vs tell”, and lane separation (narrator vs NPC vs stage direction) are **content and graph policy** concerns first; the shell must **render** committed lanes faithfully once the engine emits typed blocks and text. Specific literary rules belong in narrative governance / prompt packs; this ADR only records that the **shell** must not collapse distinct lanes into an indistinguishable blob when the contract provides them.

4. **Typewriter policy (to be finalized):** Default target behavior: **one** typewriter stream that types **only the latest incomplete block** while prior blocks remain fully revealed (chat-like). Current implementation queues all blocks on `loadTurn`; changing this is an MVP5 task tracked here, not in ADR-0033.

## Consequences

### Positive

- Clear split: **0033** = truth + observability, **0034** = presentation + shell acceptance.
- E2E and frontend unit tests can target a stable shell contract without overloading runtime ADRs.

### Negative / risks

- Without engine-side block typing and stable `scene_blocks` IDs, the shell cannot deliver theater-grade layout; UI work alone will not satisfy this ADR.

## Verification

Gate this ADR with **real** tests (not mock-the-whole-world stubs):

- Backend: `tests/test_mvp4_contract_playability.py` (cumulative `visible_scene_output` for MVP5).
- Backend: `tests/test_game_routes.py` (Langfuse player-input hash on canonical turn route; ADR-0033 §13.6).
- World-Engine: `tests/test_trace_middleware.py` (`test_world_engine_turn_execute_langfuse_correlates_player_input_hash`; ADR-0033 §13.6).
- Frontend: existing `frontend/tests/test_blocks_orchestrator.js` and shell integration tests must be extended when typewriter-only-last-block behavior is implemented.

CI environments that run shell gates must install frontend test dependencies and execute the configured suite via `python tests/run_tests.py` (canonical runner).

## References

- [ADR-0032](adr-0032-mvp4-live-runtime-setup-requirements.md)
- [ADR-0033](adr-0033-live-runtime-commit-semantics.md)
- `backend/app/api/v1/game_routes.py`
- `frontend/static/play_shell.js`
- `frontend/static/play_blocks_orchestrator.js`
- `frontend/static/play_typewriter_engine.js`
- `frontend/static/play_block_renderer.js`
