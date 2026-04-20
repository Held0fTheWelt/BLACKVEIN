# V24 God of Carnage Canonical Experience — Wave F1
## Multi-Speaker Pressure Relay Hardening

### Executive summary

Wave F1 was implemented on the real accessible E-line package state.

The package already supported:
- side/pair/exchange/carryover/surface-aware visible reply,
- immediate prior-answer continuity,
- delayed earlier-answer reuse,
- interruption / dodge / forced re-entry pressure,
- rhythm / hesitation / stalled-line return,
- and same-surface 2–3 reply weave.

The strongest remaining narrow gap was short **multi-speaker pressure relay**.

This wave hardens the visible response/output layer so a line can now feel like it is handed across the room rather than merely continued by one responder thread.

### What changed

Primary change:
- Added a narrow relay selector in `world-engine/app/story_runtime_shell_readout.py`.

The selector now recognizes compact relay cases where:
- one speaker opens or presses a same-surface line,
- another speaker picks it up across the room,
- or an earlier line plus a later dodge produce a three-speaker relay before the dodge can settle.

Focused proof additions:
- shell-readout proof for two-speaker relay across the room
- shell-readout proof for three-speaker relay through a dodge
- manager/session proof for the same two relay patterns

### Why this was necessary

Before F1, the package could already produce strong individual reply continuity.

What it still underpowered was the sense that pressure had changed hands.

That meant short exchanges could still feel like:
- one good reply after another

instead of:
- a live handoff of pressure across the room.

F1 closes that gap without lengthening the line or broadening architecture.

### What is now proven

The authoritative visible reply path can now produce compact relay hooks such as:
- `picking up the same phone across the room before it can cool`
- `letting the same phone pressure jump speakers across the room before the dodge can settle`

These hooks reach the addressed visible output bundle and preserve earlier B/C/D/E surfaces.

### Validation executed

Commands run:

```bash
PYTHONPATH=world-engine:. FLASK_ENV=test /opt/pyvenv/bin/python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py -k 'picks_up_same_surface_across_the_room_before_it_can_cool or lets_same_pressure_jump_speakers_before_the_dodge_can_settle or reopens_same_surface_through_dodge_before_point_can_die or forces_reentry_after_same_surface_dodge' --tb=short
PYTHONPATH=world-engine:. FLASK_ENV=test /opt/pyvenv/bin/python -m pytest -q world-engine/tests/test_story_runtime_narrative_commit.py -k 'relay_picks_same_surface_up_across_the_room or lets_same_pressure_jump_speakers_before_the_dodge_can_settle or reopens_same_surface_through_dodge_before_point_can_die or forces_reentry_after_same_surface_dodge' --tb=short
PYTHONPATH=world-engine:. FLASK_ENV=test /opt/pyvenv/bin/python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py world-engine/tests/test_story_runtime_narrative_commit.py --tb=short
PYTHONPATH=. /opt/pyvenv/bin/python -m pytest -q ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py --tb=short
PYTHONPATH=backend:world-engine:. /opt/pyvenv/bin/python -m pytest -q backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine' --tb=short
```

Key outputs:
- targeted shell-readout proof: `4 passed, 14 deselected, 1 warning`
- targeted manager/session proof: `4 passed, 14 deselected, 1 warning`
- full world-engine re-proof: `36 passed, 1 warning`
- narrow ai_stack proof: `5 passed`
- attempted backend bridge proof: `ModuleNotFoundError: No module named 'flask'`

### Closure judgment

Wave F1 is honestly closed for the current accessible MVP-v24 package slice.

No stronger remaining unresolved issue stays narrow enough to count as another honest F-wave inside the current seams.

What remains would require broader dialogue/runtime expansion rather than another compact relay pass.
