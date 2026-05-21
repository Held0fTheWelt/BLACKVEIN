# Session Loop

This package owns the pure WebSocket session-loop helpers formerly concentrated
in `ai_stack/story_runtime/ws_session_loop.py`.

The stable compatibility module remains at `ai_stack.story_runtime.ws_session_loop`,
but implementation now lives here by responsibility:

- `constants.py` closed enums, schema ids, and Director Pulse imports
- `feature_flags.py` server-side feature flags
- `state.py` per-connection loop state
- `replanning.py` future-only replanning request/decision artifacts
- `player_input.py` promoted input helpers
- `voice_profiles.py` voice-profile lookup and template rendering
- `safety_gates.py` closed-enum follow-up safety gates
- `composition.py` template/semantic NPC follow-up composition
- `handoff.py` cut-in handoff and post-cut-in replanning records
- `follow_up_event.py` Stage L/M follow-up event assembly
- `cut_in.py` cut-in application semantics
- `messages.py` server-to-client WebSocket message builders

The package remains I/O-free: no sockets, no asyncio, no persistence mutation.
