# W3.4.2: Bounded Character Panel UI Rendering

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render all characters in play as bounded compact cards in a sidebar, grounded in W3.4.1 canonical presenter output.

**Architecture:** The UI layer integrates W3.4.1 presenter output into the session shell template. Character state updates synchronously after turn execution; no live polling or speculative state. All character collection, ordering, and fallback logic lives in the presenter layer; routes stay thin.

**Tech Stack:** Python/Pydantic (presenter), Jinja2 (template), Flask routes.

---

## Context

**W3.4.1** established `CharacterPanelOutput` — a bounded Pydantic model mapping canonical SessionState character data to UI-facing contracts.

**W3.4.2** now renders this data. The character panel displays:
- All characters currently in play (no filtering by salience)
- One compact card per character
- Character name, overall trajectory, top relationships
- Graceful fallbacks for missing data
- Empty-state message if no characters

---

## Design

### Scope

**In scope:**
- Render all characters in a sidebar column
- Keep scene/interaction flow in main column (unchanged)
- Update character panel after turn execution (render-on-request, no live polling)
- Graceful edge case handling (missing name, missing relationships, no characters)
- Deterministic character ordering

**Out of scope:**
- Salience-based filtering (defer to W3.4.3+)
- Player-side character selection
- Live polling / WebSocket updates
- Character-specific detail pages

---

### File Structure

| File | Change | Responsibility |
|------|--------|-----------------|
| `backend/app/runtime/scene_presenter.py` | ADD `present_all_characters()` | Collect all characters, order deterministically, call `present_character_panel()` per character, return list |
| `backend/app/web/routes.py` | MODIFY `session_view()` + `session_execute()` | Load runtime session, call `present_all_characters()`, pass result to template |
| `backend/app/web/templates/session_shell.html` | MODIFY layout + ADD sidebar | Restructure to sidebar + main-column layout; render character cards from list |
| `backend/app/runtime/__init__.py` | UPDATE exports | Export `present_all_characters` |
| `backend/tests/runtime/test_scene_presenter.py` | ADD tests | Unit tests for `present_all_characters()` edge cases |

---

### Data Flow

**GET /play/<session_id> (initial view):**
```
session_view()
  → _resolve_runtime_session() → RuntimeSession
  → present_all_characters(runtime_session.current_runtime_state)
  → list[CharacterPanelOutput]
  → render_template("session_shell.html", characters=..., ...)
```

**POST /play/<session_id>/execute (after turn):**
```
session_execute()
  → dispatch_turn()
  → update_runtime_session()
  → present_all_characters(updated_state)
  → list[CharacterPanelOutput]
  → render_template("session_shell.html", characters=..., turn_result=..., ...)
```

Both flows produce the same character list; UI stays synchronized with canonical state.

---

### Presenter Function: `present_all_characters()`

```python
def present_all_characters(
    session_state: SessionState,
) -> list[CharacterPanelOutput]:
    """Map all characters in play to bounded character panel outputs.

    Collects all characters from canonical_state, orders deterministically,
    calls present_character_panel for each, handles all edge cases gracefully.

    Args:
        session_state: The active SessionState.

    Returns:
        List of CharacterPanelOutput for all characters in play, deterministically ordered.
        Empty list if no characters in canonical_state or canonical_state is missing.

    Logic:
        1. Extract character_ids from canonical_state.characters (empty dict if not present)
        2. Order deterministically by character_id (or name if available, then fallback to id)
        3. For each character_id, call present_character_panel(session_state, character_id)
        4. Collect results into list
        5. Return list (may be empty)
    """
```

---

### Template Structure

**Layout: Sidebar + Main Column**

```html
<main class="app-shell app-shell-with-sidebar">
  <!-- Sidebar: Character Panel -->
  <aside class="sidebar character-sidebar">
    <h3>Characters</h3>
    {% if characters %}
      {% for character in characters %}
        <div class="character-card">
          <h4>{{ character.character_name or character.character_id }}</h4>
          <dl class="character-meta">
            <dt>Trajectory</dt>
            <dd class="trajectory {{ character.overall_trajectory }}">
              {{ character.overall_trajectory }}
            </dd>
          </dl>

          {% if character.top_relationship_movements %}
            <div class="relationships">
              <p class="label">Salient Relationships</p>
              <ul>
                {% for movement in character.top_relationship_movements %}
                  <li>
                    <span class="other-id">{{ movement.other_character_id }}</span>:
                    <span class="signal-type">{{ movement.signal_type }}</span>
                    <span class="recent-change">({{ movement.recent_change }})</span>
                  </li>
                {% endfor %}
              </ul>
            </div>
          {% endif %}
        </div>
      {% endfor %}
    {% else %}
      <p class="character-empty-state">No characters currently in play.</p>
    {% endif %}
  </aside>

  <!-- Main Column: Existing panels -->
  <div class="main-column">
    <!-- Session info, scene, interaction, result, history panels (unchanged) -->
  </div>
</main>
```

**Character Card CSS** (compact, readable):
- Card: ~250px width, padding 12px, border, rounded corners
- H4: 14px font, bold, no margin-top
- DL: 12px font, compact spacing
- Relationships UL: 11px font, bullet list, subtle styling
- Overall trajectory: color-coded class (escalating=red, stable=neutral, de-escalating=green, unknown=gray, mixed=yellow)

---

### Route Integration

**session_view():**
```python
@web_bp.route("/play/<session_id>")
@require_web_login
def session_view(session_id):
    # ... auth and session loading ...
    runtime_session = _resolve_runtime_session(session_id)
    if not runtime_session:
        # ... error handling ...

    characters = present_all_characters(runtime_session.current_runtime_state)

    return render_template(
        "session_shell.html",
        current_user=user,
        session_id=session_id,
        characters=characters,
        session_data={...},
    )
```

**session_execute():**
```python
# ... after turn execution and state update ...
updated_runtime_session = get_runtime_session(session_id)
characters = present_all_characters(updated_runtime_session.current_runtime_state)

return render_template(
    "session_shell.html",
    current_user=user,
    session_id=session_id,
    characters=characters,
    scene=...,
    state_summary=...,
    turn_result=...,
    session_data={...},
)
```

---

### Edge Case Handling

| Scenario | Behavior | Reasoning |
|----------|----------|-----------|
| No characters in canonical_state | Render "No characters currently in play." | Explicit empty state, no silent failure |
| Character name missing | Display `character_id` as fallback | Always show the character, never omit |
| No relationship data | `overall_trajectory = "unknown"`, `top_relationship_movements = []` | Character still renders, clearly degraded |
| Missing canonical_state | Empty characters list | Graceful degrade to empty state |
| Missing context layers | `present_character_panel` returns "unknown" for trajectory | Already handled by W3.4.1; presenter degrades gracefully |

---

### Deterministic Ordering

Characters ordered by:
1. Primary: `character_id` (canonical identifier, always present)
2. Fallback (unused in practice): alphabetical by `character_id`

This ensures:
- Same session always renders characters in same order
- No UI flickering on re-renders
- Testable and reproducible

---

## Testing Strategy

### Unit Tests for `present_all_characters()`

**Test cases:**
- Empty canonical_state → empty list
- One character with full data → list with one item, correct structure
- Multiple characters (3+) → list with all characters, correct order
- Character with no name → uses `character_id`, no exception
- Character with no relationships → `overall_trajectory = "unknown"`, `top_relationship_movements = []`
- Character with partial relationship data (missing some axes) → graceful render with available data
- Missing canonical_state entirely → empty list
- Missing context layers → still renders with "unknown" trajectory

**Expected output:** All tests pass, 8+ test cases covering normal and edge cases.

### Integration Tests (Template + Route)

- Character panel renders on initial GET `/play/<session_id>`
- Character panel updates after POST `/play/<session_id>/execute`
- Empty-state message renders when no characters
- Character name or character_id fallback renders
- Overall trajectory renders
- Top relationship movements render (when present)
- No HTML rendering errors (all Jinja syntax valid)

---

## Hard Constraints

1. **Show all characters.** No salience-based filtering or omission.
2. **Graceful fallbacks.** Missing data → fallback values, never omit characters.
3. **Render-on-request only.** Updates synchronously after turn execution; no live polling, no WebSocket, no typing-time updates.
4. **Bounded output.** Use `CharacterPanelOutput` from W3.4.1; no invented UI-only state.
5. **Thin routes.** Presenter orchestrates; routes only call presenter and pass result.
6. **Deterministic ordering.** Same session always renders characters in same order.
7. **No module-specific hacks.** Design must work for all modules without adaptation.

---

## Acceptance Criteria

- ✅ `present_all_characters()` function exists in scene_presenter.py and is exported
- ✅ All characters in canonical_state render as cards in sidebar
- ✅ Character cards show name (or character_id fallback), trajectory, salient relationships
- ✅ Empty-state message renders when no characters
- ✅ Character panel updates after turn execution
- ✅ All edge cases handled gracefully (missing name, missing relationships, no characters)
- ✅ Character ordering is deterministic (by character_id)
- ✅ Routes call presenter and pass result to template; no presenter logic in routes
- ✅ Unit tests cover all edge cases (8+ test cases)
- ✅ Integration tests verify rendering and updates
- ✅ No W3 scope jump (character detail pages, filtering, live updates deferred)

---

## Out of Scope (Deferred)

- Salience-based filtering or sorting
- Player-side character selection / pinning
- Live polling or WebSocket updates
- Character detail pages or expanded views
- Conflict panel (W3.4.3+)
- Scene panel (W3.4.4+)
- Interaction history panel (W3.4.5+)
- Module-specific character adaptations

---

## Implementation Notes

1. **File location:** `backend/app/runtime/scene_presenter.py` (extend)
2. **Dependencies:** `SessionState`, `CharacterPanelOutput`, `present_character_panel` (already present)
3. **Route files:** `backend/app/web/routes.py` (modify session_view + session_execute)
4. **Template file:** `backend/app/web/templates/session_shell.html` (restructure layout)
5. **Integration point (W3.4.3+):** Conflict panel will occupy a separate sidebar section or modal

---

## Suggested Commit Message

```
feat(w3): add bounded character panel to playable ui
```

---
