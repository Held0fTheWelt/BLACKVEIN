# MCP Authorization Contract

## Operating Profile Scopes

### read-only Profile
**Tools:** get, state, logs, diag
**Enforcement:** Cannot execute turns, cannot bind players
**When Used:** Observation, debugging, game telemetry
**Authority:** Backend mirrors only (no modification)

### execute Profile
**Tools:** All (including execute_turn)
**Enforcement:** Must be bound to session, must pass world-engine validation
**When Used:** Normal gameplay, NPC behavior, story execution
**Authority:** World-engine validates, then executes

### admin Profile
**Tools:** All with some checks bypassed
**Enforcement:** Full audit logging, restricted to admins
**When Used:** Operator inspection, emergency fixes
**Authority:** World-engine still authoritative, but admin can override

## Authorization Decision Flow

1. **Identify caller:** Player ID, operating profile, session binding
2. **Check tool access:** Is this tool allowed in this profile?
3. **Check session access:** Is caller bound to this session?
4. **Check action validity:** Does world-engine accept this action?
5. **Execute or deny:** Proceed or return authorization_denied error

## Fail-Closed Principle

- Unknown profile → deny all
- Missing binding → deny execute, allow read
- Validation fails → deny and report error
- No silent fallback → error always explicit

## Audit Logging

All tool calls are logged:
- Caller identity
- Tool name
- Session ID
- Input parameters
- Success/failure
- Timestamp

Admin calls get enhanced logging (before/after state).
