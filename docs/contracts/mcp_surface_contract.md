# MCP Surface Contract

## What is the MCP Surface?

Model Context Protocol (MCP) tools expose session operations safely to AI agents.
The surface is the set of available tools and their specifications.

## Available Tools

### wos.session.get
**Purpose:** Retrieve full session state (read-only)
**Input:** `{"session_id": "s_..."}`
**Output:** `{"session": {...}, "created_at": "...", "turn_number": 42}`
**Authority:** World-engine owned (backend returns mirror)
**Error Cases:** Session not found, authorization denied

### wos.session.state
**Purpose:** Get current game state snapshot
**Input:** `{"session_id": "s_..."}`
**Output:** `{"state": {...}, "version": 42}`
**Authority:** World-engine owned (backend returns mirror)
**Error Cases:** Session not found

### wos.session.logs
**Purpose:** Get turn history/logs
**Input:** `{"session_id": "s_...", "limit": 10}`
**Output:** `{"history": [{...}, {...}]}`
**Authority:** World-engine owned (backend returns copy)
**Error Cases:** Session not found

### wos.session.diag
**Purpose:** Get diagnostic information (errors, degraded states)
**Input:** `{"session_id": "s_..."}`
**Output:** `{"diagnostics": {...}, "errors": [], "degraded": false}`
**Authority:** World-engine owned (inspection only)
**Error Cases:** Session not found

### wos.session.execute_turn
**Purpose:** Execute a turn with validation
**Input:** `{"session_id": "s_...", "player_id": "p_...", "action": {...}}`
**Output:** `{"success": true, "new_turn_number": 43, "state_delta": {...}}`
**Authority:** World-engine executes, backend applies
**Error Cases:** Invalid session/player, authority denied, action invalid

## Operating Profiles

Each tool operates within a profile that controls scope:

### read-only
- Can call: wos.session.get, wos.session.state, wos.session.logs
- Cannot call: wos.session.execute_turn
- Use case: Game diagnostics, telemetry, observation

### execute
- Can call: All tools including wos.session.execute_turn
- Subject to: Authority checks (player binding, world-engine validation)
- Use case: Normal gameplay, NPC agents, story execution

### admin
- Can call: All tools with bypass of some checks
- Subject to: Full audit logging
- Use case: Operator inspection, emergency intervention

## Truth Guarantees

- All reads return world-engine truth (never stale)
- Turn execution goes through world-engine (authority preserved)
- No false authority granted (read-only tools cannot modify)
- Authorization enforced at every call
