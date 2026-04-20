# World of Shadows MVP-v24 — God of Carnage Canonical Experience B-Line Closure Audit

## Executive outcome

I audited the real accessible post-BA package state and found that the strongest unresolved B-surface was **BD — Defensive Style Differentiation**.

I implemented that wave narrowly in the real visible response/output path, then re-audited the result against the rest of the B-line target.

The resulting package now makes the responding figure legible not only by **who answers**, **which side/pair line answers**, and **which room surface carries the pressure**, but by:

- **how the figure defends themself socially**,
- **where the mask is slipping**,
- and **how the figure tries to pull the scene back into the canon corridor through character logic rather than system steering**.

That closes the remaining high-leverage B-line work for the current accessible MVP-v24 player-facing slice.

## What was inspected

- `world-engine/app/story_runtime/manager.py`
- `world-engine/app/story_runtime_shell_readout.py`
- `world-engine/tests/test_story_runtime_shell_readout.py`
- `backend/app/api/v1/session_routes.py`
- `backend/tests/test_session_routes.py`
- `frontend/app/routes.py`
- `frontend/templates/session_shell.html`
- `frontend/static/play_shell.js`
- `frontend/tests/test_routes_extended.py`
- prior A-line and BA validation artifacts
- supporting authored character direction:
  - `content/modules/god_of_carnage/direction/character_voice.yaml`
  - `content/modules/god_of_carnage/characters.yaml`

## Wave-selection reasoning

### Strongest already-implemented surfaces

- room/object/surface anchoring in the visible response line
- side/pair/surface coupling
- carryover-on-surface continuity
- compact responder identity in the response line
- baseline per-character performance signatures from BA

### Strongest remaining gap

The player-facing line still needed the response to feel more like a **performed social move by that exact figure** rather than only a named voice.

That meant the strongest unresolved gap was not generic host-vs-guest differentiation or broader room mechanics. It was the B-specific question:

**What kind of defensive move is this figure making right now, where is the mask slipping, and how are they trying to re-center the room through that move?**

This belongs cleanly to B.

## What changed

### World-engine readout logic

Added and integrated:

- richer responder performance signatures
- responder mask-slip summaries
- responder recentering-pull summaries

These now materially affect:

- `response_performance_signature_now`
- `response_mask_slip_now`
- `response_recentering_now`
- `response_exchange_now`
- `who_answers_now`
- `why_this_reply_now`
- `observation_foothold_now`
- the visible `response_line_prefix_now`

### Focused proof updates

Updated the focused world-engine / backend / frontend tests so the package truth is synchronized with the new visible line behavior.

## Character-level effect now proven

### Véronique

The line now reads as principle used as correction, with civility hardening rather than soothing.

Example shape:

- `a principle-first rebuke that uses civility as correction`
- `with civility hardening into correction`
- `pull the moment back under principle instead of letting the exit close it`

### Michel

The line now reads as smoothing/accommodation that is already starting to look like capitulation.

Example shape:

- `a smoothing deflection that offers manners instead of alignment`
- `a smoothing deflection that offers hospitality instead of alignment`
- `with smoothing starting to read as capitulation`

### Annette

The line now reads as contradiction used to expose principle as pose or to turn care into something naive.

Example shape:

- `a cutting contradiction that treats principle as performance`
- `a contemptuous dismantling that makes concern sound naive`
- `with wit exposing morality as pose`

### Alain

The line now reads as mediation-shaped evasion rather than neutral calm.

Example shape:

- `a tired evasive hedge dressed up as mediation`
- `with mediation thinning into evasion`
- `pull the room toward manageability without ever resolving it`

## Why this closes the B-line for the current package slice

After the implementation, I re-audited the remaining B-line candidate surfaces.

What remains is either:

- already materially represented by the upgraded response-layer truth, or
- lower-leverage refinement that would require broader conversation/runtime redesign beyond the justified scope of this line.

Concretely:

- hypocrisy is now visibly present through performance phrasing rather than only scene inference
- failed repair / accusation recursion is now visible in `why_this_reply_now` and `response_exchange_now`
- shame / embarrassment return dynamics are now visible where doorway, bathroom, and hosting pressures recur through the same figure
- character-led re-centering is now visible in the actual answer path rather than implied only by system behavior

Further gains from the B label would now mostly be stylistic or would require broader systemic work outside the narrow additive seams used here.

## Validation

### Command 1

```bash
PYTHONPATH=world-engine /opt/pyvenv/bin/python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py --tb=short
```

Purpose: prove the authoritative world-engine shell-readout now carries defensive style, mask slip, and recentering truth.

Result: `8 passed, 1 warning in 0.21s`

### Command 2

```bash
PYTHONPATH=backend /opt/pyvenv/bin/python -m pytest -q backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine' --tb=short
```

Purpose: prove the backend bridge still carries the authoritative B-line response bundle.

Result: `2 passed, 35 deselected in 9.94s`

### Command 3

```bash
PYTHONPATH=frontend /opt/pyvenv/bin/python -m pytest -q frontend/tests/test_routes_extended.py -k 'play_execute_json_merges_runtime_shell_readout_projection or play_shell_frames_latest_transcript_with_runtime_response_address or play_execute_json_prefers_turn_level_addressed_visible_output_bundle or play_execute_json_uses_turn_level_runtime_shell_readout_when_state_missing or play_shell_renders_cached_runtime_shell_readout_fields or play_shell_prefers_compressed_contextual_readout_fields or play_execute_json_returns_authoritative_shell_state_bundle or play_observe_returns_observation_meta or play_shell_embeds_initial_authoritative_shell_state_json or play_observe_returns_observation_source_and_runtime_session_flags or play_execute_json_returns_runtime_ready_and_observation_source or play_execute_json_and_followup_observe_share_coherent_bundle_shape or play_execute_json_prefers_turn_level_addressed_visible_output_bundle_over_hosting_surface' --tb=short
```

Purpose: prove the frontend transcript/shell still renders the updated visible response truth coherently.

Result: `14 passed, 53 deselected in 0.66s`

### Command 4

```bash
PYTHONPATH=. python -m pytest -q ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py --tb=short
```

Purpose: prove the narrow ai_stack GoC support surfaces were not damaged.

Result: `5 passed in 0.79s`

## Final re-audit decision

For the current accessible MVP-v24 package truth, the B-line target is honestly achieved.

Remaining potential improvements are either:

- lower-leverage polish, or
- broadening that would no longer cleanly belong to B without unjustified redesign.

So the correct stop is:

**stop with target achieved**
