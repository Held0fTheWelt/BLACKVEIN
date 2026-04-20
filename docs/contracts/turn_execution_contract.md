# Turn Execution Contract

## Turn Execution Authority
World-engine is sole executor:
- Receives turn request
- Validates against current state
- Executes game logic
- Commits results to storage
- Broadcasts state to backend mirror

## Turn Request Format
```json
{
  "session_id": "s_...",
  "turn_number": 42,
  "player_id": "p_...",
  "action": {
    "type": "move|interact|speak|...",
    "target": "...",
    "parameters": {...}
  }
}
```

## Turn Response Format
```json
{
  "session_id": "s_...",
  "turn_number": 42,
  "status": "success|blocked|failed",
  "state_delta": {...},
  "messages": [...]
}
```

## Execution Sequence
1. Backend receives action from player
2. Backend validates format
3. Backend forwards to world-engine
4. World-engine executes and commits
5. World-engine returns results
6. Backend applies to session mirror
7. Backend returns to player API

## Failure Modes
- Invalid action: reject at world-engine (backend propagates error)
- Authority violation: reject with "auth_denied"
- Resource conflict: reject with "conflict"
- World-engine error: return "world_engine_error" (never hide)

## Truth Guarantees
- Turn numbers are sequential (no gaps)
- State after turn N is deterministic given history
- All turns are recoverable from storage
- No transaction loss at world-engine
