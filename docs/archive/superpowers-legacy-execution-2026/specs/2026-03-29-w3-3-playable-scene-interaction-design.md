# W3.3: Playable Scene View and Interaction Flow

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the session UI genuinely playable by wiring the scene view and interaction controls to the canonical turn executor, with real turn execution using in-memory session state.

**Architecture:** Hybrid session management (Flask session for lightweight linkage, server-side in-memory registry for full runtime state) with direct integration to the canonical W2 turn executor. All turns are real, all state updates are canonical, all execution is routed through the real runtime path.

**Tech Stack:** Flask (routes), Jinja2 (templates), Pydantic (runtime models), in-memory dict (session registry)

---

## Architecture

W3.3 makes the session UI genuinely playable by wiring the scene view and interaction controls to the canonical turn executor.

**Core components:**
- **`app/runtime/session_store.py`** (new): In-memory registry mapping `session_id → RuntimeSession` objects. Handles create/get/update/delete of runtime sessions.
- **`app/web/routes.py`** (modified): Three routes for scene display and turn execution:
  - `GET /play/<session_id>` — loads scene view with scene + state + input form
  - `POST /play/<session_id>/execute` — executes a real turn, updates runtime session, renders result feedback
  - Helper: `_resolve_runtime_session(session_id)` — validates Flask session matches requested session_id
- **`session_shell.html`** (modified): Replace placeholders with actual scene display, interaction form, and result feedback.

**Session data flow:**
1. User at `/play/<session_id>` → Flask session links to runtime session_id
2. Route resolves full RuntimeSession from `session_store.get(session_id)`
3. Template renders scene (title, description, state summary) from RuntimeSession
4. Operator submits free-text input via form
5. POST route extracts input → calls canonical turn executor on current canonical state
6. Turn executor returns TurnExecutionResult
7. Route updates RuntimeSession in-memory store with new canonical state
8. Template re-renders with new scene + result feedback

**In-memory constraints (explicitly documented):**
- Sessions exist only while server is running
- Sessions are lost on server restart
- No persistence across server restarts
- This is intentional MVP scope; persistence is deferred to W3.4+

---

## Component Details

### `app/runtime/session_store.py` (new module)

Responsibilities:
- Create runtime session: `create_session(session_id, initial_session_state) → RuntimeSession`
- Retrieve runtime session: `get_session(session_id) → RuntimeSession | None`
- Update runtime session: `update_session(session_id, updated_state) → RuntimeSession`
- Delete runtime session: `delete_session(session_id)`
- Internal registry: module-level in-memory dict (`_runtime_sessions: dict[str, RuntimeSession]`)

`RuntimeSession` dataclass/model wraps:
- `session_id`: unique identifier
- `current_runtime_state`: the full SessionState from W2 (canonical) — contains execution_mode and adapter_name for dispatch routing
- `module`: reference to loaded ContentModule — required for turn validation and state legality checks
- `turn_counter`: current turn number — incremented after each successful execution, passed to `dispatch_turn()`
- `updated_at`: timestamp of last update

**Implementation rule:** This is the ONLY server-side runtime session registry for W3.3. No parallel stores. RuntimeSession must carry all context needed to call the canonical `dispatch_turn()` entry point. The route receives no execution mode or adapter details — they come from SessionState, which dispatch_turn() reads to decide routing.

### `app/web/routes.py` (modifications)

**Helper function:**
```python
def _resolve_runtime_session(session_id: str) -> RuntimeSession | None:
    """Validates Flask session matches requested session_id and loads RuntimeSession."""
    flask_session_id = session.get("active_session", {}).get("session_id")
    if flask_session_id != session_id:
        return None
    return session_store.get_session(session_id)
```

**GET /play/<session_id>:**
- Validate Flask session matches session_id
- Resolve RuntimeSession from store
- Extract: scene_id, scene_description, state_summary from canonical state
- Render `session_shell.html` with scene + state + input form

**POST /play/<session_id>/execute (new route):**
- Validate Flask session matches session_id
- Resolve RuntimeSession from store
- Extract operator input from form
- Call **canonical runtime session execution entry point**: `dispatch_turn(RuntimeSession.current_runtime_state, RuntimeSession.turn_counter + 1, RuntimeSession.module, operator_input=form_input)`
  - This is the REAL canonical session-level router: delegates to AI or mock execution based on session.execution_mode
  - The runtime core owns all decision construction (MockDecision, AI adapter, response parsing, etc.)
  - Route does NOT construct MockDecision or manage execution mode logic — dispatcher does
  - Returns TurnExecutionResult with updated_canonical_state, guard_outcome, accepted_deltas, rejected_deltas
- Update RuntimeSession in store: replace current_runtime_state with TurnExecutionResult.updated_canonical_state, increment turn_counter
- Build result_feedback using explicit presenter mapping (see "Template Result Field Mapping" section below)
- Re-render `session_shell.html` with new scene + result feedback using mapped fields
- If execution fails, preserve in-memory session state, flash error, re-render with error feedback

**Implementation rule:** The POST route MUST submit operator_input to `dispatch_turn()`, the canonical session execution router. The route does not construct MockDecision, select execution mode, or manage adapter logic — all decision-making stays in the runtime layer. State updates must replace the in-memory runtime session with the new canonical state produced by turn execution.

### `session_shell.html` (template modifications)

**Scene display section:**
- Show `scene.title` (extracted from canonical state via presenter)
- Show `scene.description` if available (via presenter)
- Show `state_summary` (situation, conversation_status) derived from canonical state via presenter
- Do not fabricate narrative fields not provided by the runtime

**Interaction form section:**
- Free-text textarea for operator input (primary control)
- Optional quick-action helper buttons (observe, interact, move, etc.)
  - These buttons should populate/assist the textarea, not replace free-text input
- Form posts to `/play/<session_id>/execute` with CSRF token
- Implementation rule: Free-text is the primary interaction model; helpers are optional enhancements

**Result feedback section (shown after turn execution):**
- All fields mapped through explicit presenter (see "Template Result Field Mapping" section below)
- Do not assume fields exist directly in runtime objects; map explicitly
- Implementation rule: Result feedback strictly derived from canonical TurnExecutionResult and RuntimeSession, never UI-invented fields

---

### Template Result Field Mapping (Presenter Rules)

The route layer MUST include a presenter/mapping function that explicitly transforms canonical runtime data into template-facing fields. Do not assume template shape matches runtime object shape.

**Mapping from RuntimeSession + TurnExecutionResult:**

| Template Field | Source | Extraction Logic |
|---|---|---|
| `scene.title` | RuntimeSession.current_runtime_state → module.scenes[current_scene_id].title | Lookup scene from module by scene_id |
| `scene.description` | RuntimeSession.current_runtime_state → module.scenes[current_scene_id].description | Lookup scene from module by scene_id, nullable |
| `state_summary` | RuntimeSession.current_runtime_state | Extract situation, key entities (e.g., character states, relationship status) into bounded summary |
| `turn_result.narrative_text` | TurnExecutionResult (if not present, check decision.narrative_text) | Primary source is result; fallback to decision |
| `turn_result.guard_outcome` | TurnExecutionResult.guard_outcome | Canonical outcome: "accepted", "partially_accepted", "rejected", "structurally_invalid" |
| `turn_result.accepted_delta_paths` | TurnExecutionResult.accepted_deltas[*].target | List of state paths that were accepted |
| `turn_result.rejected_delta_paths` | TurnExecutionResult.rejected_deltas[*].target | List of state paths that were rejected |
| `next_scene_id` | TurnExecutionResult.updated_scene_id (if set) or RuntimeSession.current_runtime_state.current_scene_id | New scene after execution, or current if no transition |
| `execution_status` | TurnExecutionResult.execution_status | "success", "validation_failed", or "system_error" |

**Implementation requirement:** Create a `_present_turn_result(runtime_session, turn_result)` helper in routes.py that returns a dict of template-facing fields, ensuring all template rendering uses this mapping, not direct object access.

---

## Data Flow

**Initial scene load (GET /play/<session_id>):**
```
Browser request
  → Flask session lookup → session_id found
  → session_store.get(session_id) → RuntimeSession retrieved
  → extract: scene_id, scene_description, state_summary from canonical_state
  → render session_shell.html with scene + state + input form
```

**Turn execution (POST /play/<session_id>/execute):**
```
Browser form submit (operator_input)
  → Flask session lookup → session_id found
  → session_store.get(session_id) → RuntimeSession retrieved
  → call CANONICAL SESSION EXECUTION ROUTER: dispatch_turn(
      session=RuntimeSession.current_runtime_state,
      current_turn=RuntimeSession.turn_counter + 1,
      module=RuntimeSession.module,
      operator_input=form_input
    )
  → dispatcher routes to AI or mock execution based on session.execution_mode
  → dispatcher owns all decision construction (MockDecision, AI adapter, parsing, etc.)
  → dispatcher returns TurnExecutionResult (with updated_canonical_state, guard_outcome, accepted_deltas, rejected_deltas)
  → route updates RuntimeSession.current_runtime_state ← TurnExecutionResult.updated_canonical_state
  → route increments RuntimeSession.turn_counter
  → session_store.update_session(session_id, updated_RuntimeSession)
  → use _present_turn_result(RuntimeSession, TurnExecutionResult) to map result to template fields
  → re-render session_shell.html with new scene + mapped result feedback
```

**Error flow:**
```
If turn_executor raises exception or validation fails:
  → catch exception
  → preserve in-memory RuntimeSession state (no update)
  → flash error message to user
  → re-render current scene (no state change)
  → show error feedback to operator
```

**Session cleanup:**
```
User logs out or session expires:
  → session_store.delete_session(session_id)
  → Flask session cleared
```

**Implementation rules:**
- GET renders current runtime session state
- POST executes a real canonical turn and updates the in-memory session state
- Failed execution does not corrupt the in-memory session
- The UI re-renders from the authoritative runtime session state

---

## Testing Strategy

### Unit Tests: `tests/runtime/test_session_store.py` (new)

- `test_create_session`: can create and retrieve a runtime session
- `test_get_nonexistent_session`: returns None for unknown session_id
- `test_update_session`: updates in-memory session state
- `test_delete_session`: removes session from registry
- `test_multiple_concurrent_sessions`: multiple sessions coexist without state leakage

### Integration Tests: `backend/tests/test_session_ui.py` (new/updated)

**Scene view tests:**
- `test_scene_view_renders_scene_data`: GET /play/<session_id> displays scene title, description, state summary
- `test_scene_view_requires_valid_session`: GET /play/<session_id> with mismatched Flask session → error/redirect
- `test_operator_input_form_present`: GET /play/<session_id> renders textarea + quick-action helpers

**Turn execution tests:**
- `test_turn_execution_calls_dispatch_turn`: POST /play/<session_id>/execute calls canonical `dispatch_turn()`, not execute_turn directly
- `test_operator_input_passed_to_dispatcher`: operator_input (free text) is passed to dispatch_turn; no MockDecision conversion happens in route
- `test_dispatcher_routes_based_on_execution_mode`: verify session.execution_mode and adapter_name are honored by dispatcher (test with mock mode)
- `test_turn_execution_updates_session_store`: after POST, RuntimeSession in store has updated canonical state from dispatcher result
- `test_turn_result_displayed_after_execution`: POST response includes narrative, outcome, what changed, next scene
- `test_turn_execution_re_renders_from_updated_session`: POST response renders from updated in-memory session, not temporary route-local data
- `test_degraded_outcome_feedback`: if turn result is degraded/fallback/safe-turn, response renders real outcome feedback correctly
- `test_turn_failure_preserves_session_state`: if execution fails, in-memory session unchanged, error displayed

**Session isolation tests:**
- `test_session_isolation_at_route_level`: two different browser-linked sessions do not leak runtime state into each other
- `test_csrf_token_validation`: form submission requires valid CSRF token (if web layer enforces this in normal tests)

**Interaction model tests:**
- `test_quick_action_buttons_assist_free_text`: quick-action buttons populate/suggest textarea, not replace it

**Scope boundary tests:**
- `test_w3_3_scope_contained`: verify no W3.4 character depth or W3.5 history panels are implemented

---

## Scope Boundaries

**Implemented in W3.3:**
- Scene view (title, description, state summary)
- Free-text operator input (primary)
- Quick-action helpers (optional, non-replacing)
- Real turn execution via canonical executor
- Result feedback (narrative, outcome, what changed, next scene)
- In-memory session state management

**Deferred to W3.4+:**
- Persistence layer (session/turn history storage)
- Rich character detail and relationship panels
- Conflict/escalation panel depth
- Advanced debugging panels

**Deferred to W3.5:**
- Full turn history panel
- Validation/log detail panels
- Advanced diagnostics

---

## Implementation Constraints (Non-Negotiable)

1. **Canonical session execution router:** The route MUST call `dispatch_turn(session, turn_number, module, operator_input=...)`, the session-level execution entry point. No direct `execute_turn()` calls. No UI-owned decision construction.
2. **Operator input as string:** The route passes operator_input as a raw string to dispatch_turn(). All decision construction (MockDecision, AI adapter invocation, response parsing) happens inside the runtime dispatcher.
3. **Runtime owns execution mode:** The route does NOT read session.execution_mode or session.adapter_name — dispatch_turn() does. These remain owned by runtime.
4. **RuntimeSession completeness:** RuntimeSession MUST carry session_id, current_runtime_state (SessionState with execution_mode and adapter_name), module (ContentModule), turn_counter, and updated_at.
5. **Single registry:** `session_store` is the ONLY server-side runtime session registry for W3.3.
6. **Flask session linkage only:** Flask session stores only lightweight metadata (session_id), not the full runtime state.
7. **State replacement, not merge:** `/play/<session_id>/execute` MUST replace RuntimeSession.current_runtime_state with TurnExecutionResult.updated_canonical_state, not merge partial updates.
8. **Explicit presenter mapping:** All template fields MUST be derived via `_present_turn_result()` helper that maps canonical objects to template shape. No direct object access in templates.
9. **In-memory documentation:** The in-memory-only limitation is documented explicitly in code comments and developer docs.
10. **Real canonical data only:** Scene display, state summary, and result feedback derive strictly from canonical runtime/module/session data. No fabricated UI-invented fields.
11. **Free-text primary:** Interaction model is free-text input with optional helper buttons, not menu-driven or structured-choice-primary.
12. **Error preservation:** Failed turn execution preserves the last valid in-memory session state.
13. **Session isolation:** Multiple concurrent sessions must not leak runtime state into each other.

---

## Success Criteria

- ✓ A user can inspect the current scene (title, description, state summary) — derived from canonical module + state via presenter
- ✓ A user can submit free-text operator input via the UI
- ✓ Turn execution calls `dispatch_turn()`, the canonical session execution router
- ✓ Route passes operator_input as raw string; does NOT construct MockDecision or manage execution mode
- ✓ RuntimeSession carries execution context (state with execution_mode/adapter_name, module, turn counter)
- ✓ Dispatcher decides execution path (AI vs mock) and all decision construction based on session config
- ✓ Turn execution updates in-memory session state by replacing current_runtime_state with dispatcher result
- ✓ Turn result feedback is displayed (narrative, outcome, accepted/rejected deltas, next scene) — all via explicit presenter mapping
- ✓ Template rendering uses only mapped fields from presenter, never direct canonical object access
- ✓ Session isolation prevents state leakage between concurrent sessions
- ✓ Failed execution preserves session state without corruption
- ✓ All tests pass (unit + integration)
- ✓ No W3 scope jump occurred (W3.4+ features deferred)
- ✓ In-memory-only constraint is clearly documented
- ✓ Presenter mapping function is explicit and testable
- ✓ Route does not own execution mode logic or decision construction
