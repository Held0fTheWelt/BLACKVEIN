# World of Shadows MVP-v24 — God of Carnage Canonical Experience Wave C2

## Wave title

C2 — Delayed Reply Reuse / Two-Step Conversational Afterlife

## Executive summary

I audited the real accessible package state from the Wave C1 artifact, verified that C1 was package-truth-supported in code/tests/reports, and selected the strongest next justified C-wave:

**C2 — Delayed Reply Reuse / Two-Step Conversational Afterlife**

The package materially improved.

The visible answer path no longer only reuses the immediately previous visible answer. It can now also reuse an **earlier** visible answer after an intervening turn when the same social surface comes back live again.

This keeps the reply line compact while making the conversation feel less reset-heavy and more like a chamber-play line that returns to an earlier wound after a temporary deflection.

After re-audit, no stronger remaining unresolved issue stayed narrow enough to count as another clean C-wave inside the current MVP-v24 seams.

## What was inspected

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
- `validation/V24_GOC_CANONICAL_EXPERIENCE_WAVE_C1_ACTION_CAUSED_MULTI_TURN_REPLY_CONTINUITY.md`
- `validation/CURRENT_STATE_VALIDATION_SUMMARY_WAVE_C1.txt`

## Audit findings

### What C1 already proved

The accessible package already proved:

- responder identity in the visible line
- side/pair line in the visible line
- exchange type in the visible line
- carryover wound in the visible line
- immediate prior visible reply continuity in the visible line
- backend/frontend transport of the authoritative addressed visible output bundle

### Strongest remaining gap

The strongest remaining gap was not another shell-only framing issue.

The visible line still underused a common chamber-play pattern:

- turn 1 opens a wound on a surface
- turn 2 dodges, deflects, or shifts pressure elsewhere
- turn 3 returns to the original surface and makes the earlier answer live again

That gap belonged cleanly to C and was narrower than any broader conversation-engine expansion.

## What changed

### 1. Authoritative bounded earlier-reply continuity context

Added one more bounded continuity slot in authoritative committed state:

- `earlier_reply_continuity_context`

This is not a broad memory-system rewrite. It is only a one-step extension beyond C1 so the next turn can still reach back to an earlier visible answer when the same surface reactivates.

### 2. Delayed continuity selection in the visible response layer

Hardened `story_runtime_shell_readout.py` so the visible response path now chooses the strongest compact continuity hook among:

- immediate prior reply continuity
- delayed earlier-reply continuity

When the immediate previous turn only offers a generic bridge, but an earlier reply matches the now-reactivated surface, the visible line now prefers the stronger delayed hook.

Examples:

- `pulling the earlier failed repair back onto the same books`
- `bringing the earlier accusation back onto the same books`

### 3. Focused proof additions

Added:

- a shell-readout proof for delayed same-surface afterlife
- a manager-level three-turn proof showing turn 3 can reuse turn 1 after turn 2 intervenes

## Why those changes were necessary

Without C2, the system already had:

- immediate answer-to-countermove continuity
- strong surface/wound anchoring
- strong responder specificity

But it still tended to forget an earlier answer too quickly once one intervening turn had happened.

C2 fixes that in the actual visible response layer without broadening into a dialogue-engine rewrite.

## Key proven effects

### Delayed same-surface afterlife in shell-readout

The visible line can now say:

- `pulling the earlier failed repair back onto the same books`

when an earlier books-line becomes live again after an intervening turn.

### Three-turn addressed visible output continuity

At manager level, a turn sequence can now produce a turn-3 addressed output line beginning with:

- `Annette, from the guest side across the couples, answers in accusation ... bringing the earlier accusation back onto the same books ...`

This proves delayed reply reuse reaches the actual addressed visible output bundle.

## Validation

### Command 1

```bash
PYTHONPATH=world-engine FLASK_ENV=test /opt/pyvenv/bin/python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py -k 'threads_previous_visible_reply_into_same_surface_countermove or delayed_same_surface_afterlife' --tb=short
```

Purpose:

- prove immediate C1 continuity still works
- prove delayed same-surface afterlife now works in the authoritative shell-readout layer

Result:

- `2 passed, 8 deselected in 0.16s`

### Command 2

```bash
PYTHONPATH=world-engine FLASK_ENV=test /opt/pyvenv/bin/python -m pytest -q world-engine/tests/test_story_runtime_narrative_commit.py -k 'threads_previous_visible_reply_context_into_next_addressed_output or reuse_earlier_visible_reply_after_intervening_turn' --tb=short
```

Purpose:

- prove immediate prior-reply continuity still works in manager/session truth
- prove three-turn delayed reuse reaches the addressed visible output bundle

Result:

- `2 passed, 10 deselected in 7.11s`

### Command 3

```bash
PYTHONPATH=backend /opt/pyvenv/bin/python -m pytest -q backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine' --tb=short
```

Purpose:

- prove backend/session bridge integrity remains intact

Result:

- `2 passed, 35 deselected in 9.64s`

### Command 4

```bash
PYTHONPATH=frontend /opt/pyvenv/bin/python -m pytest -q frontend/tests/test_routes_extended.py -k 'play_execute_json_merges_runtime_shell_readout_projection or play_shell_frames_latest_transcript_with_runtime_response_address or play_execute_json_prefers_turn_level_addressed_visible_output_bundle or play_execute_json_uses_turn_level_runtime_shell_readout_when_state_missing or play_shell_renders_cached_runtime_shell_readout_fields or play_shell_prefers_compressed_contextual_readout_fields or play_execute_json_returns_authoritative_shell_state_bundle or play_observe_returns_observation_meta or play_shell_embeds_initial_authoritative_shell_state_json or play_observe_returns_observation_source_and_runtime_session_flags or play_execute_json_returns_runtime_ready_and_observation_source or play_execute_json_and_followup_observe_share_coherent_bundle_shape or play_execute_json_prefers_turn_level_addressed_visible_output_bundle_over_hosting_surface' --tb=short
```

Purpose:

- prove frontend transcript/readout continuity remains intact

Result:

- `14 passed, 53 deselected in 0.47s`

### Command 5

```bash
PYTHONPATH=. /opt/pyvenv/bin/python -m pytest -q ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py --tb=short
```

Purpose:

- prove narrow GoC support surfaces were not damaged

Result:

- `5 passed in 1.61s`

## Final re-audit

C2 is honestly closed.

The C-line is honestly closed for the current accessible package slice.

What remains imaginable is broader or different in kind, for example:

- richer silence / interruption / overlap rhythm
- broader dialogue recursion across many turns
- more content-driven discourse shaping beyond bounded reply context

Those would require a broader conversation/runtime expansion rather than another narrow C-wave.

## Stop decision

Stop with **target achieved** for the current C-line in the accessible MVP-v24 package.
