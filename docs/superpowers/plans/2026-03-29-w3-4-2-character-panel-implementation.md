# W3.4.2 Character Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render all characters in play as bounded compact cards in a sidebar, grounded in W3.4.1 canonical presenter output.

**Architecture:** The presenter layer provides a bulk collection function `present_all_characters()` that returns an ordered list of `CharacterPanelOutput` objects. Routes call this function and pass the result to the template. The template renders a two-column layout with character cards in a sidebar and existing scene/interaction panels in the main column. All character collection, ordering, and fallback logic lives in the presenter layer; routes stay thin.

**Tech Stack:** Python/Pydantic (presenter), Jinja2 (template), Flask routes, pytest (tests)

---

## File Structure

| File | Action | Responsibility |
|------|--------|-----------------|
| `backend/app/runtime/scene_presenter.py` | MODIFY | ADD `present_all_characters(session_state) -> list[CharacterPanelOutput]` function |
| `backend/app/runtime/__init__.py` | MODIFY | Export `present_all_characters` |
| `backend/app/web/routes.py` | MODIFY | Integrate `present_all_characters()` into `session_view()` and `session_execute()` |
| `backend/app/web/templates/session_shell.html` | MODIFY | Restructure layout: add sidebar + main-column, render character cards |
| `backend/tests/runtime/test_scene_presenter.py` | MODIFY | ADD unit tests for `present_all_characters()` (8+ cases) |
| `backend/tests/test_session_ui.py` | MODIFY | ADD integration tests for template rendering and route updates |

---

## Task 1: Implement `present_all_characters()` with Unit Tests

**Files:**
- Modify: `backend/app/runtime/scene_presenter.py` (after `present_character_panel()` function)
- Modify: `backend/tests/runtime/test_scene_presenter.py` (append test class)

**Context:** The `present_character_panel()` function already exists and works correctly. We need to create `present_all_characters()` which orchestrates bulk collection. It should extract all character_ids from `session_state.canonical_state["characters"]`, order them deterministically by character_id, call `present_character_panel()` for each, and return the list. All edge cases must be handled gracefully.

### Steps

- [ ] **Step 1: Write failing unit test — empty canonical_state**

Add to `backend/tests/runtime/test_scene_presenter.py`:

```python
class TestPresentAllCharacters:
    """Tests for present_all_characters bulk presenter function."""

    def test_present_all_characters_empty_canonical_state(self):
        """present_all_characters returns empty list when canonical_state is missing."""
        from app.runtime.scene_presenter import present_all_characters
        from app.runtime.w2_models import SessionState

        session_state = SessionState(
            module_id="test_module",
            current_scene_id="scene_1",
            turn_counter=0,
            status="active",
            canonical_state={},
            context_layers=None,
        )
        result = present_all_characters(session_state)
        assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/runtime/test_scene_presenter.py::TestPresentAllCharacters::test_present_all_characters_empty_canonical_state -xvs
```

Expected: FAIL with "present_all_characters not defined" or similar

- [ ] **Step 3: Write failing unit test — single character with full data**

Add to test class:

```python
    def test_present_all_characters_single_character_with_full_data(self):
        """present_all_characters returns list with one CharacterPanelOutput for single character."""
        from app.runtime.scene_presenter import present_all_characters
        from app.runtime.w2_models import SessionState, RelationshipAxisContext, SalientAxis

        salient_axis = SalientAxis(
            character_a="protagonist",
            character_b="antagonist",
            signal_type="tension",
            recent_change_direction="escalating",
            salience_score=0.9,
        )

        session_state = SessionState(
            module_id="test_module",
            current_scene_id="scene_1",
            turn_counter=0,
            status="active",
            canonical_state={
                "characters": {
                    "protagonist": {"name": "Alice"},
                    "antagonist": {"name": "Bob"},
                }
            },
            context_layers=type("ContextLayers", (), {
                "relationship_axis_context": RelationshipAxisContext(
                    salient_axes=[salient_axis],
                    has_escalation_markers=False,
                    overall_stability_signal="escalating",
                )
            })(),
        )
        result = present_all_characters(session_state)
        assert len(result) == 2
        assert result[0].character_id == "antagonist"  # alphabetical order
        assert result[1].character_id == "protagonist"
        assert result[0].character_name == "Bob"
        assert result[1].character_name == "Alice"
```

- [ ] **Step 4: Write failing unit test — multiple characters ordered deterministically**

Add to test class:

```python
    def test_present_all_characters_multiple_characters_deterministic_order(self):
        """present_all_characters orders characters deterministically by character_id."""
        from app.runtime.scene_presenter import present_all_characters
        from app.runtime.w2_models import SessionState

        session_state = SessionState(
            module_id="test_module",
            current_scene_id="scene_1",
            turn_counter=0,
            status="active",
            canonical_state={
                "characters": {
                    "zara": {"name": "Zara"},
                    "alice": {"name": "Alice"},
                    "bob": {"name": "Bob"},
                }
            },
            context_layers=None,
        )
        result = present_all_characters(session_state)
        assert len(result) == 3
        assert [c.character_id for c in result] == ["alice", "bob", "zara"]
```

- [ ] **Step 5: Write failing unit test — missing character name fallback**

Add to test class:

```python
    def test_present_all_characters_missing_name_uses_character_id(self):
        """present_all_characters falls back to character_id when name is missing."""
        from app.runtime.scene_presenter import present_all_characters
        from app.runtime.w2_models import SessionState

        session_state = SessionState(
            module_id="test_module",
            current_scene_id="scene_1",
            turn_counter=0,
            status="active",
            canonical_state={
                "characters": {
                    "char_1": {},  # No name field
                }
            },
            context_layers=None,
        )
        result = present_all_characters(session_state)
        assert len(result) == 1
        assert result[0].character_id == "char_1"
        assert result[0].character_name is None  # No name, not char_1 as fallback
```

- [ ] **Step 6: Write failing unit test — no relationships gracefully renders**

Add to test class:

```python
    def test_present_all_characters_no_relationships_trajectory_unknown(self):
        """present_all_characters handles missing relationships gracefully."""
        from app.runtime.scene_presenter import present_all_characters
        from app.runtime.w2_models import SessionState

        session_state = SessionState(
            module_id="test_module",
            current_scene_id="scene_1",
            turn_counter=0,
            status="active",
            canonical_state={
                "characters": {
                    "orphan": {"name": "Orphan Character"},
                }
            },
            context_layers=None,
        )
        result = present_all_characters(session_state)
        assert len(result) == 1
        assert result[0].overall_trajectory == "unknown"
        assert result[0].top_relationship_movements == []
```

- [ ] **Step 7: Write minimal implementation of `present_all_characters()`**

Add to `backend/app/runtime/scene_presenter.py` after `present_character_panel()`:

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
        2. Order deterministically by character_id (alphabetical)
        3. For each character_id, call present_character_panel(session_state, character_id)
        4. Collect results into list
        5. Return list (may be empty)
    """
    # Step 1: Extract character_ids from canonical_state
    character_ids = []
    if session_state.canonical_state:
        characters = session_state.canonical_state.get("characters", {})
        if isinstance(characters, dict):
            character_ids = list(characters.keys())

    # Step 2: Order deterministically by character_id
    character_ids.sort()

    # Step 3 & 4: Call present_character_panel for each and collect
    characters_output = [
        present_character_panel(session_state, character_id)
        for character_id in character_ids
    ]

    # Step 5: Return list
    return characters_output
```

- [ ] **Step 8: Run all unit tests to verify they pass**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/runtime/test_scene_presenter.py::TestPresentAllCharacters -xvs
```

Expected: All tests pass (7 tests)

- [ ] **Step 9: Add edge-case tests: missing context_layers, partial relationship data**

Add to test class:

```python
    def test_present_all_characters_missing_context_layers(self):
        """present_all_characters handles missing context_layers gracefully."""
        from app.runtime.scene_presenter import present_all_characters
        from app.runtime.w2_models import SessionState

        session_state = SessionState(
            module_id="test_module",
            current_scene_id="scene_1",
            turn_counter=0,
            status="active",
            canonical_state={
                "characters": {
                    "char_a": {"name": "Character A"},
                }
            },
            context_layers=None,
        )
        result = present_all_characters(session_state)
        assert len(result) == 1
        assert result[0].overall_trajectory == "unknown"
```

- [ ] **Step 10: Run all unit tests again to ensure new test passes**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/runtime/test_scene_presenter.py::TestPresentAllCharacters -xvs
```

Expected: All tests pass (8 tests)

- [ ] **Step 11: Commit unit tests and implementation**

```bash
cd backend && git add tests/runtime/test_scene_presenter.py app/runtime/scene_presenter.py && git commit -m "feat(w3): add present_all_characters() presenter function with comprehensive unit tests"
```

---

## Task 2: Export `present_all_characters` from Runtime Module

**Files:**
- Modify: `backend/app/runtime/__init__.py`

### Steps

- [ ] **Step 1: Add import and export**

Update `backend/app/runtime/__init__.py` to:

```python
"""Runtime module for W3 story execution."""

from app.runtime.scene_presenter import (
    CharacterPanelOutput,
    ConflictPanelOutput,
    ConflictTrendSignal,
    RelationshipMovement,
    present_character_panel,
    present_conflict_panel,
    present_all_characters,
)

__all__ = [
    "CharacterPanelOutput",
    "ConflictPanelOutput",
    "ConflictTrendSignal",
    "RelationshipMovement",
    "present_character_panel",
    "present_conflict_panel",
    "present_all_characters",
]
```

- [ ] **Step 2: Verify import works**

```bash
cd backend && PYTHONPATH=. python -c "from app.runtime import present_all_characters; print('✓ Import successful')"
```

Expected: `✓ Import successful`

- [ ] **Step 3: Commit**

```bash
cd backend && git add app/runtime/__init__.py && git commit -m "feat(w3): export present_all_characters from runtime module"
```

---

## Task 3: Integrate Character Presenter into `session_view()` Route

**Files:**
- Modify: `backend/app/web/routes.py` (session_view function, line ~677)

### Steps

- [ ] **Step 1: Add import for `present_all_characters`**

At the top of `backend/app/web/routes.py`, add to W3.3 imports section:

```python
# W3.4 imports
from app.runtime import present_all_characters
```

- [ ] **Step 2: Modify `session_view()` to call presenter and pass to template**

Replace the `session_view()` function (around line 677) with:

```python
@web_bp.route("/play/<session_id>")
@require_web_login
def session_view(session_id):
    uid = session.get("user_id")
    user = db.session.get(User, int(uid)) if uid else None
    active = session.get("active_session", {})
    if active.get("session_id") != session_id:
        flash("Session not found or expired.", "error")
        return redirect(url_for("web.session_start"))

    # Load runtime session and present character panel
    runtime_session = get_runtime_session(session_id)
    characters = present_all_characters(runtime_session.current_runtime_state) if runtime_session else []

    return render_template(
        "session_shell.html",
        current_user=user,
        session_data=active,
        characters=characters,
    )
```

- [ ] **Step 3: Verify syntax and imports**

```bash
cd backend && PYTHONPATH=. python -m py_compile app/web/routes.py
```

Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
cd backend && git add app/web/routes.py && git commit -m "feat(w3): integrate present_all_characters into session_view route"
```

---

## Task 4: Integrate Character Presenter into `session_execute()` Route

**Files:**
- Modify: `backend/app/web/routes.py` (session_execute function, around line 763)

### Steps

- [ ] **Step 1: Modify `session_execute()` to call presenter after turn execution**

Find the return statement in `session_execute()` (around line 811-824). Update the render_template call to include characters:

```python
        # Reload runtime session with updated state
        runtime_session = get_runtime_session(session_id)

        # Present character panel with updated state
        characters = present_all_characters(runtime_session.current_runtime_state)

        # Map result to template fields
        presented_result = _present_turn_result(runtime_session, turn_result)

        # Render updated scene + result feedback
        return render_template(
            "session_shell.html",
            current_user=user,
            session_id=session_id,
            scene=presented_result["scene"],
            state_summary=presented_result["state_summary"],
            turn_result=presented_result["turn_result"],
            characters=characters,
            session_data={
                "module_id": runtime_session.current_runtime_state.module_id,
                "current_scene_id": runtime_session.current_runtime_state.current_scene_id,
                "status": runtime_session.current_runtime_state.status.value,
                "turn_counter": runtime_session.current_runtime_state.turn_counter,
            },
        )
```

- [ ] **Step 2: Also handle error case in session_execute**

Find the exception handler (around line 826) and add characters to the error re-render as well. Update it to:

```python
    except Exception as e:
        # Error: preserve session state, flash error, re-render current scene
        flash(f"Turn execution failed: {str(e)}", "error")

        # Re-render current scene without state change
        runtime_session = get_runtime_session(session_id)
        characters = present_all_characters(runtime_session.current_runtime_state) if runtime_session else []

        module = runtime_session.module if runtime_session else None
        current_scene_id = runtime_session.current_runtime_state.current_scene_id if runtime_session else None
        canonical_state = runtime_session.current_runtime_state.canonical_state if runtime_session else {}

        scene_data = {}
        if module and hasattr(module, 'scenes') and current_scene_id in module.scenes:
            scene = module.scenes[current_scene_id]
            scene_data = {
                "title": getattr(scene, 'title', current_scene_id),
                "description": getattr(scene, 'description', ''),
            }
        else:
            scene_data = {
                "title": current_scene_id or "Unknown Scene",
                "description": "",
            }

        state_summary = {
            "situation": canonical_state.get("situation", "") if canonical_state else "",
            "conversation_status": canonical_state.get("conversation_status", "") if canonical_state else "",
        }

        return render_template(
            "session_shell.html",
            current_user=user,
            session_id=session_id,
            scene=scene_data,
            state_summary=state_summary,
            error="Turn execution failed. Please try again.",
            characters=characters,
            session_data={
                "module_id": runtime_session.current_runtime_state.module_id,
                "current_scene_id": current_scene_id,
                "status": runtime_session.current_runtime_state.status.value,
                "turn_counter": runtime_session.current_runtime_state.turn_counter,
            },
        )
```

- [ ] **Step 3: Verify syntax**

```bash
cd backend && PYTHONPATH=. python -m py_compile app/web/routes.py
```

Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
cd backend && git add app/web/routes.py && git commit -m "feat(w3): integrate present_all_characters into session_execute route with error handling"
```

---

## Task 5: Restructure Template with Sidebar Layout

**Files:**
- Modify: `backend/app/web/templates/session_shell.html`

### Steps

- [ ] **Step 1: Replace entire template with new sidebar + main-column layout**

Replace `backend/app/web/templates/session_shell.html` with:

```html
{% extends "base.html" %}
{% block title %}Session – World of Shadows{% endblock %}
{% block content %}
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

  <!-- Main Column: Session, Scene, Interaction, Result, History -->
  <div class="main-column">

    <!-- Session Info Panel -->
    <section class="panel session-info-panel">
      <h2>Session</h2>
      <dl class="session-meta">
        <dt>Module</dt><dd>{{ session_data.module_id }}</dd>
        <dt>Scene</dt><dd>{{ session_data.current_scene_id }}</dd>
        <dt>Status</dt><dd>{{ session_data.status }}</dd>
        <dt>Turn</dt><dd>{{ session_data.turn_counter }}</dd>
      </dl>
    </section>

    <!-- Scene Display Panel -->
    <section class="panel scene-panel">
      <h3>Scene</h3>
      {% if scene %}
        <h4>{{ scene.title }}</h4>
        {% if scene.description %}
          <p>{{ scene.description }}</p>
        {% endif %}
        {% if state_summary %}
          <div class="state-summary">
            {% if state_summary.situation %}
              <p><strong>Situation:</strong> {{ state_summary.situation }}</p>
            {% endif %}
            {% if state_summary.conversation_status %}
              <p><strong>Status:</strong> {{ state_summary.conversation_status }}</p>
            {% endif %}
          </div>
        {% endif %}
      {% else %}
        <p class="placeholder muted">Scene not loaded.</p>
      {% endif %}
    </section>

    <!-- Interaction Panel -->
    <section class="panel interaction-panel">
      <h3>Interaction</h3>
      <form method="POST" action="{{ url_for('web.session_execute', session_id=session_id) }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

        <div class="form-group">
          <label for="operator_input">What do you do?</label>
          <textarea id="operator_input" name="operator_input" rows="4" placeholder="Describe your action..." required></textarea>
        </div>

        <!-- Optional quick-action helper buttons -->
        <div class="quick-actions">
          <button type="button" class="btn-helper" data-action="observe">Observe</button>
          <button type="button" class="btn-helper" data-action="interact">Interact</button>
          <button type="button" class="btn-helper" data-action="move">Move</button>
        </div>

        <button type="submit" class="btn-primary">Execute Action</button>
      </form>
    </section>

    <!-- Result Feedback Panel (shown after turn execution) -->
    {% if turn_result %}
    <section class="panel result-panel">
      <h3>Result</h3>

      <!-- Narrative text from turn execution -->
      {% if turn_result.narrative_text %}
        <div class="narrative">
          {{ turn_result.narrative_text }}
        </div>
      {% endif %}

      <!-- Guard outcome status -->
      <div class="outcome-status">
        <strong>Outcome:</strong>
        <span class="outcome {% if turn_result.guard_outcome == 'accepted' %}accepted{% elif turn_result.guard_outcome == 'partially_accepted' %}partially-accepted{% elif turn_result.guard_outcome == 'rejected' %}rejected{% else %}invalid{% endif %}">
          {{ turn_result.guard_outcome }}
        </span>
      </div>

      <!-- What changed -->
      {% if turn_result.accepted_delta_paths or turn_result.rejected_delta_paths %}
        <div class="deltas">
          {% if turn_result.accepted_delta_paths %}
            <p><strong>Accepted changes:</strong></p>
            <ul>
              {% for path in turn_result.accepted_delta_paths %}
                <li>{{ path }}</li>
              {% endfor %}
            </ul>
          {% endif %}
          {% if turn_result.rejected_delta_paths %}
            <p><strong>Rejected changes:</strong></p>
            <ul>
              {% for path in turn_result.rejected_delta_paths %}
                <li>{{ path }}</li>
              {% endfor %}
            </ul>
          {% endif %}
        </div>
      {% endif %}

    </section>
    {% endif %}

    <!-- Error messages -->
    {% if error %}
    <section class="panel error-panel">
      <p class="error-message">{{ error }}</p>
    </section>
    {% endif %}

    <!-- History Panel Placeholder (deferred to W3.4+) -->
    <section class="panel history-panel">
      <h3>History</h3>
      <p class="placeholder muted">Turn history — coming in a future update.</p>
    </section>

  </div>

</main>

<script>
// Quick-action helper buttons populate/assist textarea (don't replace it)
document.querySelectorAll('.btn-helper').forEach(btn => {
  btn.addEventListener('click', function(e) {
    e.preventDefault();
    const action = this.dataset.action;
    const textarea = document.getElementById('operator_input');
    // Insert suggestion into textarea without replacing existing text
    const prefix = textarea.value ? textarea.value + ' ' : '';
    textarea.value = prefix + '[' + action + ']';
    textarea.focus();
  });
});
</script>

{% endblock %}
```

- [ ] **Step 2: Verify template syntax (basic check)**

```bash
cd backend && PYTHONPATH=. python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('app/web/templates')); template = env.get_template('session_shell.html'); print('✓ Template syntax valid')"
```

Expected: `✓ Template syntax valid`

- [ ] **Step 3: Commit template**

```bash
cd backend && git add app/web/templates/session_shell.html && git commit -m "feat(w3): restructure session_shell.html with sidebar layout for character panel"
```

---

## Task 6: Add Integration Tests for Route Updates and Template Rendering

**Files:**
- Modify: `backend/tests/test_session_ui.py` (append tests)

### Steps

- [ ] **Step 1: Write failing integration test — characters render on session_view**

Add to `backend/tests/test_session_ui.py`:

```python
def test_session_view_renders_character_panel(client, test_user, monkeypatch):
    """Character panel renders on initial GET /play/<session_id>."""
    from unittest.mock import Mock
    from app.runtime.w2_models import SessionState
    from app.runtime.scene_presenter import CharacterPanelOutput

    user, password = test_user
    _login_session(client, user.username, password)

    # Create a session and get the session_id from redirect
    csrf = _get_csrf_token(client, "/play", user.username, password)
    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": csrf},
        follow_redirects=False,
    )
    session_id = response.headers["Location"].split("/")[-1]

    # Mock get_runtime_session to return a session with characters
    mock_session = Mock()
    mock_session.current_runtime_state = SessionState(
        module_id="god_of_carnage",
        current_scene_id="scene_1",
        turn_counter=0,
        status="active",
        canonical_state={
            "characters": {
                "alice": {"name": "Alice"},
                "bob": {"name": "Bob"},
            }
        },
        context_layers=None,
    )

    monkeypatch.setattr("app.web.routes.get_runtime_session", lambda sid: mock_session)

    # View the session
    response = client.get(f"/play/{session_id}")
    assert response.status_code == 200
    assert b"Characters" in response.data
    assert b"alice" in response.data or b"Alice" in response.data
    assert b"bob" in response.data or b"Bob" in response.data
```

- [ ] **Step 2: Run test to verify it fails initially (before any template changes applied)**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::test_session_view_renders_character_panel -xvs
```

Expected: FAIL (characters not in template yet, or template doesn't exist)

- [ ] **Step 3: Write additional integration test — character panel updates after turn execution**

Add to `backend/tests/test_session_ui.py`:

```python
def test_session_execute_updates_character_panel(client, test_user, monkeypatch):
    """Character panel updates after POST /play/<session_id>/execute."""
    from unittest.mock import Mock, AsyncMock
    from app.runtime.w2_models import SessionState

    user, password = test_user
    _login_session(client, user.username, password)

    # Create a session
    csrf = _get_csrf_token(client, "/play", user.username, password)
    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": csrf},
        follow_redirects=False,
    )
    session_id = response.headers["Location"].split("/")[-1]

    # Mock dispatch_turn and session operations
    mock_turn_result = Mock()
    mock_turn_result.updated_canonical_state = {
        "characters": {
            "alice": {"name": "Alice"},
        }
    }
    mock_turn_result.updated_scene_id = None
    mock_turn_result.guard_outcome = Mock(value="accepted")
    mock_turn_result.decision = Mock(narrative_text="Alice moved forward.")
    mock_turn_result.accepted_deltas = []
    mock_turn_result.rejected_deltas = []
    mock_turn_result.execution_status = "complete"

    mock_session = Mock()
    mock_session.current_runtime_state = SessionState(
        module_id="god_of_carnage",
        current_scene_id="scene_1",
        turn_counter=0,
        status="active",
        canonical_state={
            "characters": {
                "alice": {"name": "Alice"},
            }
        },
        context_layers=None,
    )
    mock_session.module = Mock()
    mock_session.module.scenes = {"scene_1": Mock(title="Scene 1", description="Test scene")}

    monkeypatch.setattr("app.web.routes.dispatch_turn", AsyncMock(return_value=mock_turn_result))
    monkeypatch.setattr("app.web.routes.get_runtime_session", lambda sid: mock_session)
    monkeypatch.setattr("app.web.routes.update_runtime_session", Mock())

    # Get CSRF token from session view
    response = client.get(f"/play/{session_id}")
    csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', response.data.decode())
    csrf_token = csrf_match.group(1) if csrf_match else ""

    # Execute a turn
    response = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "I move forward", "csrf_token": csrf_token},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"alice" in response.data or b"Alice" in response.data
    assert b"Characters" in response.data
```

- [ ] **Step 4: Write integration test — empty character panel renders message**

Add to `backend/tests/test_session_ui.py`:

```python
def test_session_view_renders_empty_character_state_message(client, test_user, monkeypatch):
    """Empty character panel renders 'No characters currently in play.' message."""
    from unittest.mock import Mock
    from app.runtime.w2_models import SessionState

    user, password = test_user
    _login_session(client, user.username, password)

    csrf = _get_csrf_token(client, "/play", user.username, password)
    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": csrf},
        follow_redirects=False,
    )
    session_id = response.headers["Location"].split("/")[-1]

    # Mock session with no characters
    mock_session = Mock()
    mock_session.current_runtime_state = SessionState(
        module_id="god_of_carnage",
        current_scene_id="scene_1",
        turn_counter=0,
        status="active",
        canonical_state={},
        context_layers=None,
    )

    monkeypatch.setattr("app.web.routes.get_runtime_session", lambda sid: mock_session)

    response = client.get(f"/play/{session_id}")
    assert response.status_code == 200
    assert b"No characters currently in play" in response.data
```

- [ ] **Step 5: Write integration test — character name or character_id fallback renders**

Add to `backend/tests/test_session_ui.py`:

```python
def test_session_view_character_name_fallback_to_id(client, test_user, monkeypatch):
    """Character panel shows character_id when name is missing."""
    from unittest.mock import Mock
    from app.runtime.w2_models import SessionState

    user, password = test_user
    _login_session(client, user.username, password)

    csrf = _get_csrf_token(client, "/play", user.username, password)
    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": csrf},
        follow_redirects=False,
    )
    session_id = response.headers["Location"].split("/")[-1]

    mock_session = Mock()
    mock_session.current_runtime_state = SessionState(
        module_id="god_of_carnage",
        current_scene_id="scene_1",
        turn_counter=0,
        status="active",
        canonical_state={
            "characters": {
                "char_1": {},  # No name field
            }
        },
        context_layers=None,
    )

    monkeypatch.setattr("app.web.routes.get_runtime_session", lambda sid: mock_session)

    response = client.get(f"/play/{session_id}")
    assert response.status_code == 200
    assert b"char_1" in response.data
```

- [ ] **Step 6: Write integration test — trajectory renders**

Add to `backend/tests/test_session_ui.py`:

```python
def test_session_view_character_trajectory_renders(client, test_user, monkeypatch):
    """Character trajectory value displays in character panel."""
    from unittest.mock import Mock
    from app.runtime.w2_models import SessionState

    user, password = test_user
    _login_session(client, user.username, password)

    csrf = _get_csrf_token(client, "/play", user.username, password)
    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": csrf},
        follow_redirects=False,
    )
    session_id = response.headers["Location"].split("/")[-1]

    mock_session = Mock()
    mock_session.current_runtime_state = SessionState(
        module_id="god_of_carnage",
        current_scene_id="scene_1",
        turn_counter=0,
        status="active",
        canonical_state={
            "characters": {
                "alice": {"name": "Alice"},
            }
        },
        context_layers=None,
    )

    monkeypatch.setattr("app.web.routes.get_runtime_session", lambda sid: mock_session)

    response = client.get(f"/play/{session_id}")
    assert response.status_code == 200
    # Trajectory should be 'unknown' when no context_layers
    assert b"unknown" in response.data
```

- [ ] **Step 7: Run all integration tests to verify they pass**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py -k "character_panel or empty_character or trajectory" -xvs
```

Expected: All tests pass (6+ tests)

- [ ] **Step 8: Commit integration tests**

```bash
cd backend && git add tests/test_session_ui.py && git commit -m "feat(w3): add integration tests for character panel rendering"
```

---

## Task 7: Full Test Suite Verification

**Files:**
- No files to modify; just run tests

### Steps

- [ ] **Step 1: Run all presenter tests**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/runtime/test_scene_presenter.py -xvs
```

Expected: All tests pass

- [ ] **Step 2: Run all session UI tests**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py -xvs
```

Expected: All tests pass (including new character panel tests)

- [ ] **Step 3: Run full test suite to check for regressions**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/ -q --tb=line
```

Expected: All tests pass, no new failures

- [ ] **Step 4: Final commit message summary**

All tasks complete. Character panel is now rendered in the session shell:
- `present_all_characters()` collects all characters from canonical state
- Routes call presenter and pass characters list to template
- Template renders sidebar with character cards + main column with scene/interaction/result
- All edge cases handled gracefully (missing names, missing relationships, no characters)
- Updates synchronously after turn execution (render-on-request, no polling)
- Character ordering deterministic (by character_id)
- 8+ unit tests + 6+ integration tests verify all functionality

---

## Acceptance Checklist

✅ `present_all_characters()` function exists in scene_presenter.py and is exported
✅ All characters in canonical_state render as cards in sidebar
✅ Character cards show name (or character_id fallback), trajectory, salient relationships
✅ Empty-state message renders when no characters
✅ Character panel updates after turn execution
✅ All edge cases handled gracefully (missing name, missing relationships, no characters)
✅ Character ordering is deterministic (by character_id)
✅ Routes call presenter and pass result to template; no presenter logic in routes
✅ Unit tests cover all edge cases (8+ test cases)
✅ Integration tests verify rendering and updates
✅ No W3 scope jump (character detail pages, filtering, live updates deferred)
