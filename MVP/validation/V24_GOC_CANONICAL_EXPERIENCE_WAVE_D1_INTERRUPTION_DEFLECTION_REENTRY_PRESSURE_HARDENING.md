# V24 God of Carnage Canonical Experience — Wave D1
## Interruption / Deflection / Re-Entry Pressure Hardening

### Executive summary

I audited the real accessible package state extracted from `world_of_shadows_mvp_v24_c_line_closed_FULL_MVP_DIRECTORY.zip`.

I first verified that C-line closure remained package-truth-supported by inspecting the C2 closure artifacts and re-running focused world-engine continuity proof. That confirmation was sufficient to proceed into D1.

I then implemented a narrow D1 hardening in the authoritative world-engine reply/output path.

The material gain is:

- the visible reply can now express **evasive non-answer pressure** more directly,
- the visible reply can now express **forced re-entry after dodge** more directly,
- and this happens in the actual player-facing addressed output bundle, not only shell labels.

Concrete new visible line behavior now includes:

- `trying to answer around the point on the same phone`
- `not letting the last dodge stand on the same phone`

Those phrases are not standalone metadata. They are threaded into the compact response line that prefixes the visible transcript output.

### Audit basis

Inspected before change:

- `world-engine/app/story_runtime/manager.py`
- `world-engine/app/story_runtime_shell_readout.py`
- `world-engine/tests/test_story_runtime_shell_readout.py`
- `world-engine/tests/test_story_runtime_narrative_commit.py`
- `backend/app/api/v1/session_routes.py`
- `backend/tests/test_session_routes.py`
- `frontend/app/routes.py`
- `frontend/templates/session_shell.html`
- `frontend/static/play_shell.js`
- `frontend/tests/test_routes_extended.py`
- `validation/V24_GOC_CANONICAL_EXPERIENCE_B_LINE_CLOSURE_AUDIT.md`
- `validation/CURRENT_STATE_VALIDATION_SUMMARY_B_LINE.txt`
- `validation/V24_GOC_CANONICAL_EXPERIENCE_WAVE_C1_ACTION_CAUSED_MULTI_TURN_REPLY_CONTINUITY.md`
- `validation/CURRENT_STATE_VALIDATION_SUMMARY_WAVE_C1.txt`
- `validation/V24_GOC_CANONICAL_EXPERIENCE_WAVE_C2_DELAYED_REPLY_REUSE_AND_C_LINE_CLOSURE.md`
- `validation/CURRENT_STATE_VALIDATION_SUMMARY_C_LINE.txt`

### What was actually underpowered

Before D1, the package already supported:

- responder identity,
- side/pair/exchange/carryover/surface-aware visible reply,
- immediate prior-answer continuity,
- delayed earlier-answer reuse after one intervening turn.

What remained underpowered was not continuity in general, but the specific **pressure texture of dialogue**:

- when a line is being dodged,
- when someone is answering around the point,
- when a dodge is not allowed to stand,
- and when the room forces re-entry into the live issue.

### Wave selection decision

Selected wave:

**D1 — Interruption / Deflection / Re-Entry Pressure Hardening**

Reason:

This was the strongest next narrow wave because it improved the actual reply pressure in the visible output layer without broadening into a conversation-engine rewrite.

### What changed

#### 1. Reply-pressure selection hardening in `story_runtime_shell_readout.py`

Added a narrow interruption / deflection / re-entry selector that now prefers D1-style pressure hooks when they are more specific than the existing C-line continuity hooks.

This lets the output distinguish between:

- a normal countermove,
- an evasive non-answer,
- and a pressured return after a dodge.

#### 2. Narrow manager import fallback in `manager.py`

The current container does not provide the full optional ai_stack runtime dependency set required to import the heavy runtime graph executor eagerly.

To execute manager/session proof honestly in this environment, I added a narrow optional-runtime fallback:

- if `RuntimeTurnGraphExecutor` cannot be imported, manager construction still succeeds,
- and a clear unavailable stub is used unless tests inject a turn-graph double.

This does not redesign the architecture. It only removes an import-time blocker so authoritative session proofs can run in a minimal environment.

#### 3. Focused proofs

Added focused tests covering:

- evasive same-surface non-answer pressure,
- forced re-entry after a same-surface dodge,
- manager/session continuity for those cases.

### Validation performed

#### Pre-change C-line confirmation

```bash
PYTHONPATH=world-engine FLASK_ENV=test /opt/pyvenv/bin/python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py -k 'threads_previous_visible_reply_into_same_surface_countermove or delayed_same_surface_afterlife' --tb=short
```

Output:

- `2 passed, 8 deselected, 1 warning in 0.38s`

#### D1 authoritative world-engine proof

```bash
PYTHONPATH=world-engine:. FLASK_ENV=test /opt/pyvenv/bin/python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py world-engine/tests/test_story_runtime_narrative_commit.py --tb=short
```

Output:

- `25 passed, 1 warning in 1.68s`

#### Narrow GoC regression proof

```bash
PYTHONPATH=. /opt/pyvenv/bin/python -m pytest -q ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py --tb=short
```

Output:

- `5 passed in 0.84s`

#### Attempted backend proof in current environment

```bash
PYTHONPATH=backend:world-engine:. /opt/pyvenv/bin/python -m pytest -q backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine' --tb=short
```

Output:

- blocked at import time: `ModuleNotFoundError: No module named 'flask'`

That backend/frontend environment limitation is real and recorded as external residue. It does not invalidate the authoritative world-engine D1 proof because D1 changed only the authoritative reply/output assembly path.

### What is now proven

It is now proven that:

- C-line closure remained package-truth-supported before D1 work began.
- The visible reply can now encode **evasive non-answer pressure** directly.
- The visible reply can now encode **forced re-entry after dodge** directly.
- Those changes reach the actual addressed visible output bundle.
- C-line continuity behavior remained intact.
- The shell remains compact and non-directive.

### Honest closure decision

D1 is honestly closed for the current accessible package slice.

What remains after re-audit is not another narrow D1 pass by default. The next remaining leverage would be broader rhythm/overlap/silence pressure, which is no longer the same narrow wave.
