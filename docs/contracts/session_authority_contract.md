# Session Authority Contract

## Ownership
World-engine owns all session authority:
- Session creation and initialization
- Player binding to sessions
- Turn numbering and sequencing
- Turn execution and results
- Final world state after each turn

## Backend Authority Scope (Read-Only)
Backend has read-only authority to:
- Query session status
- Read turn history
- Read current game state
- Serve this to authorized operators/players
- BUT: Cannot modify any session state

## Truth Boundary Rules
1. Only world-engine can create a session
2. Only world-engine can execute a turn
3. Only world-engine can commit turn results
4. Backend mirrors: pull-only, never push-write
5. Conflicts: world-engine is always correct

## Session Lifecycle
- Created by: world-engine.SessionManager.create_session()
- Bound by: backend.SessionService.bind_player()
- Executed by: world-engine.TurnExecutor.execute_turn()
- Mirrored by: backend.SessionMirror.sync_from_world_engine()
- Queried by: backend.API endpoints (read-only)

## Authority Enforcement
- Player actions go: frontend → backend → world-engine
- State queries go: frontend → backend → world-engine (if not cached)
- All writes: world-engine only
- All reads: backend mirrors (or direct world-engine if fresh data needed)
