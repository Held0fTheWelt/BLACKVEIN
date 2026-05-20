# Story runtime: complete playable MVP (authoritative path)

This document describes the **authoritative** World of Shadows story runtime behaviour needed for a minimal playable experience: committed Turn 0 opening, governed model routing, bounded self-correction, degraded-but-valid continuation, diagnostics, and operator-visible repro metadata.

## Turn 0 opening (session create)

When `POST /api/internal/story/sessions` creates a session, the World Engine runs a **graph opening** turn (unless test fixtures inject `registry` or `adapters`, which skips opening for isolation). The committed opening is appended to session history and the last diagnostics row is returned as **`opening_turn`** in the create response.

Clients should treat `opening_turn` as **committed narration** (same envelope shape as later diagnostics rows), not as a speculative draft.

## Player turns

`POST …/sessions/{id}/turns` executes the LangGraph runtime turn graph. Story-play input follows interpretation, action resolution, retrieval, routing, model invoke (LangChain-structured primary for capable adapters), optional graph-managed fallback, proposal normalisation, validation seam, commit seam, visible render, and package output.

Meta/OOC input is a deterministic control turn: interpretation routes `player_input_kind=meta` to `meta_control_turn`, which records structured `control_events`, marks generation as not required, sets `commit_not_applicable=true`, and packages diagnostics without story retrieval, model invocation, `validate_seam`, or `commit_seam`. This is the bounded Π25 control surface; the separate story-play `meta_narrative_awareness` aspect is opt-in, module-policy-backed, and validated through structured events, including v2 fourth-wall scope and selected-memory-ref checks when fully enabled.

### Self-correction

Validation may reject a seam outcome. The executor retries generation for exactly **`max_self_correction_attempts`** rewrite attempts (from governed runtime settings, default 3) with bounded, feedback-coded repair instructions. Parser/validation failures and runtime-aspect failures share the same recovery loop: narrator/NPC authority violations, structured NPC coercion of the human actor, missing narrator authority, missing required dramatic capabilities, and forbidden capability realization are captured before the retry decision and surfaced as self-correction trigger evidence.

After retries, **`allow_degraded_commit_after_retries`** may downgrade validation only on later turns when policy allows and the rejection is safe to degrade. Actor-lane, authority, structured NPC coercion, required-narrator, protected-delta, and dramatic capability contract failures remain commit-blocking rather than silently becoming degraded story truth.

### Authority and protected deltas

The live graph writes narrator/NPC authority records before final validation. If an NPC action structurally targets the selected human actor with a coercive action/coercion type, validation records `npc_action_controls_human_actor`, marks the matching forbidden capability, and rejects the turn.

The commit seam also receives `candidate_deltas` and `state_delta_boundary` from graph state. Protected identity or canonical-truth mutations return `state_delta_rejection`, set `commit_applied=False`, and are recorded in the commit aspect ledger.

### Retrieval context

Retrieval hits are assembled into `context_text` and passed into LangChain invocation. Adapter-level `retrieval_context` may reflect the **last** invocation after retries; operator diagnostics remain authoritative for “what was attached when”.

## Backend play bridge

`POST /api/v1/game/player-sessions/<run_id>` creates or resumes the World Engine story session before play, and `POST /api/v1/game/player-sessions/<run_id>/turns` executes turns against that story-session id. The player-session response may include:

- **`opening_turn`** — Turn 0 envelope from the create call
- **`world_engine_opening_meta`** — `current_scene_id`, `turn_counter`, `module_id` for UI projection

The frontend play shell renders the opening row **before** the first player turn in the transcript.

## Runtime config reload

The World Engine exposes `POST /api/internal/story/runtime/reload-config` to re-fetch governed runtime configuration from the backend and rebuild registry, routing, and the turn graph executor.

## Related code

- World Engine: `world-engine/app/story_runtime/manager.py`, `world-engine/app/api/http.py`
- AI stack: `ai_stack/langgraph/langgraph_runtime_executor.py`, `ai_stack/langchain/bridges.py`, `ai_stack/story_runtime/story_runtime_playability.py`
- Play UI: `frontend/app/routes_play.py`, `frontend/static/play_shell.js`
