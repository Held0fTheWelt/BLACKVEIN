# Session Sync Contract

## Sync Direction: One-Way (World-Engine → Backend)

Backend mirrors only pull from world-engine.
World-engine never pulls from backend.

## Sync Trigger Points
1. **After turn execution** — world-engine pushes to backend
2. **On sync request** — backend pulls current state from world-engine
3. **On session creation** — world-engine pushes to backend
4. **Periodic sync** — backend reconciles every N seconds (health check)

## Sync Payload Format
```json
{
  "session_id": "s_...",
  "version": 42,
  "state": {...},
  "history": [...],
  "last_sync_timestamp": "2026-04-20T14:40:00Z"
}
```

## Sync Guarantees
- Eventual consistency: backend will match world-engine
- No data loss: all turns recorded in world-engine
- Idempotent: same turn sync'd twice = idempotent
- Causally ordered: turns arrive in order

## Conflict Resolution
- Backend sees divergence: pull fresh from world-engine
- Player sees old state: request fresh sync and retry
- World-engine authority wins (always)
