# V24 God of Carnage Canonical Experience — Wave BA Core Character Voice Differentiation

## Executive summary

I audited the real accessible package state after the A-line closure artifact instead of assuming a B-wave target from prose alone.

The current package already proved:

- strong room/object/surface anchoring,
- side/pair/surface coupling,
- carryover-surface convergence,
- and compressed visible response-line framing.

The strongest unresolved B-surface was no longer room binding.
It was that the visible reply line still differentiated figures mostly by **name + side/pair geometry**, not enough by **individual performance signature**.

I therefore selected:

- **BA — Core Character Voice Differentiation**

This wave is now materially present in the actual visible response/output path.
The response line no longer says only who is answering and through which side/surface pressure.
It now also says **how that specific figure socially performs the answer**.

Examples now proven in the real shell-readout layer:

- Véronique: `... in a principle-first rebuke ...`
- Annette: `... in a cutting contradiction ...`
- Michel: `... in a smoothing deflection ...`
- Alain: `... in a tired evasive hedge ...`

## Audit findings

### Current strongest implemented surfaces before BA

- room/object/threshold anchoring was already package-truth-proven
- side/pair/surface coupling was already visible in the response line
- carryover already lived on the same active surface
- transcript prefixing already pushed the line into the player-facing narration surface

### Major B-line gap before BA

- the visible line still relied too heavily on actor identity plus social geometry
- individual character performance style was underpowered in the actual answer sentence
- this was a true B-line gap because the missing leverage was **character logic / social performance**, not UI or room mechanics

### Contradictions found

- none blocking
- accessible package truth still matched the claimed A-line closure state closely enough to begin a B-wave directly

### Why BA was the strongest next move

BA had the highest leverage because it improved the real visible response layer without redesigning architecture and without drifting into broader room or shell work.

It was stronger than BB because host-vs-guest pressure was already materially present.
It was stronger than BC/BD because hypocrisy/defensive style needed a cleaner individual voice base first.

## Starting wave status picture

| Surface | Status before BA | Evidence quality | Drift risk | Closure leverage |
|---|---|---:|---:|---:|
| Response-line room/surface anchoring | strong | high | low | low for BA |
| Side/pair response framing | strong | high | low | medium |
| Carryover in visible line | strong | high | low | low |
| Per-character performance signature in visible line | partial / weak | high | low | **high** |
| Frontend transcript carry-through | strong | medium-high | low | medium |

## What was changed

### Code

- added a narrow per-responder performance-signature helper in `world-engine/app/story_runtime_shell_readout.py`
- threaded that signature into:
  - `response_performance_signature_now`
  - `response_address_source_now`
  - `response_line_prefix_now`
  - `who_answers_now`
  - `why_this_reply_now`

### Tests

- updated world-engine exact-output tests for Véronique, Annette, Michel, and Alain
- updated backend mock-projection tests to stay synchronized with the new authoritative visible line truth
- updated frontend cached/runtime shell tests so transcript-prefix proof remains aligned with the new BA output shape

## Why those changes were necessary

Before BA, the line could already say:

- who answered,
- from which side/pair line,
- through which active surface,
- and with which carryover wound.

What it still could not say strongly enough was:

- whether the answer landed as moral indictment,
- cynical contradiction,
- pragmatic smoothing,
- or exhausted mediation/evasion.

That meant the room was already socially alive, but the **figures themselves were not yet differentiated enough as performers** in the same visible sentence.

## Validation performed

```bash
cd /mnt/data/wos_b/wave_arp_full
PYTHONPATH=world-engine /opt/pyvenv/bin/python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py --tb=short
PYTHONPATH=backend /opt/pyvenv/bin/python -m pytest -q backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine' --tb=short
PYTHONPATH=frontend /opt/pyvenv/bin/python -m pytest -q frontend/tests/test_routes_extended.py -k 'play_execute_json_merges_runtime_shell_readout_projection or play_shell_frames_latest_transcript_with_runtime_response_address or play_execute_json_prefers_turn_level_addressed_visible_output_bundle or play_execute_json_uses_turn_level_runtime_shell_readout_when_state_missing or play_shell_renders_cached_runtime_shell_readout_fields or play_shell_prefers_compressed_contextual_readout_fields or play_execute_json_returns_authoritative_shell_state_bundle or play_observe_returns_observation_meta or play_shell_embeds_initial_authoritative_shell_state_json or play_observe_returns_observation_source_and_runtime_session_flags or play_execute_json_returns_runtime_ready_and_observation_source or play_execute_json_and_followup_observe_share_coherent_bundle_shape or play_execute_json_prefers_turn_level_addressed_visible_output_bundle_over_hosting_surface' --tb=short
PYTHONPATH=. /opt/pyvenv/bin/python -m pytest -q ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py --tb=short
```

## Test / command outputs

- `world-engine/tests/test_story_runtime_shell_readout.py` -> `8 passed, 1 warning in 0.12s`
- `backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine'` -> `2 passed, 35 deselected in 8.18s`
- `frontend/tests/test_routes_extended.py -k 'play_execute_json_merges_runtime_shell_readout_projection or play_shell_frames_latest_transcript_with_runtime_response_address or play_execute_json_prefers_turn_level_addressed_visible_output_bundle or play_execute_json_uses_turn_level_runtime_shell_readout_when_state_missing or play_shell_renders_cached_runtime_shell_readout_fields or play_shell_prefers_compressed_contextual_readout_fields or play_execute_json_returns_authoritative_shell_state_bundle or play_observe_returns_observation_meta or play_shell_embeds_initial_authoritative_shell_state_json or play_observe_returns_observation_source_and_runtime_session_flags or play_execute_json_returns_runtime_ready_and_observation_source or play_execute_json_and_followup_observe_share_coherent_bundle_shape or play_execute_json_prefers_turn_level_addressed_visible_output_bundle_over_hosting_surface'` -> `14 passed, 53 deselected in 0.44s`
- `ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py` -> `5 passed in 0.48s`

## What is now proven

- BA now materially affects the actual visible response/output path
- the response line differentiates the four major God of Carnage responders by social-performance signature, not just by name/side/surface
- frontend transcript framing still carries the updated BA line into `latest_entry_text` / preview surfaces
- backend bridge projection remains intact
- prior A-line closures remain intact
- canon-corridor integrity remains intact

## What remains unresolved

- the new signatures are still compact sentence-level performance tags, not yet deeper hypocrisy or defensive-style recursion
- mask-breaking and contradiction-reuse remain candidate later B-waves
- silence/withholding rhythm is still relatively shallow outside the selected visible reply line

## Final judgment

**selected B-wave closed**

Reason:

- the chosen gap truly belonged to B
- the change was narrow and additive
- the actual player-facing response line materially improved
- executable proof exists across world-engine, backend, frontend, and narrow ai_stack regression surfaces
- no contradiction forced reconciliation instead

## Recommended next follow-up

If continuing the B-line, the strongest next move is:

- **BD — Defensive Style Differentiation**

Reason: the figures now sound more individually distinct, but the way each one deflects, moralizes, capitulates, corners, hedges, or absorbs pressure is still the next highest-leverage character-performance gap in the visible reply path.
