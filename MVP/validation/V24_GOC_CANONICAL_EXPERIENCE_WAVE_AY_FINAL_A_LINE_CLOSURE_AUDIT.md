# V24 God of Carnage Canonical Experience — Wave AY Final A-Line Closure Audit

## Executive summary

I continued from the real accessible Wave AU package and did not assume closure from prior prose alone.

The package already proved AT and AU in accessible package truth.
The strongest remaining work was no longer reconciliation or a fresh hot-surface discovery wave.
It was to:

1. couple the speaking side/pair line more tightly to the same visible surface,
2. make earlier wounds live on that same surface,
3. and compress the line so the result reads faster and less diagnostically.

That produced a chained continuation across:

- AV — Side/Pair/Surface Coupling Hardening
- AW — Carryover-Surface Convergence
- AX — Transcript-Line Compression / Vividness Polish
- AY — Final A-Line Closure Audit

The visible response/output layer is now materially stronger.
The reply line no longer just says that a prior wound exists somewhere in the room.
It now lets that earlier wound sit on the same doorway/books/phone/hosting surface where the current reply is landing.

Example truths now proven in the real readout layer:

- doorway: `Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, the earlier failed exit still sitting at the doorway`
- books: `Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, the earlier taste-and-status wound still sitting on the books`
- hosting surface: `Michel, from the host side, answers in brittle repair with host-side hospitality strain over the hosting surface, the earlier hospitality-and-hosting line still sitting over the hosting surface`
- phone: `Alain, from the guest side across the couples, answers in evasive pressure with cross-couple humiliation on the phone, the earlier humiliation line still sitting on the phone`

## What was inspected

- `world-engine/app/story_runtime_shell_readout.py`
- `world-engine/tests/test_story_runtime_shell_readout.py`
- `backend/tests/test_session_routes.py`
- `frontend/tests/test_routes_extended.py`
- `validation/CURRENT_STATE_VALIDATION_SUMMARY_WAVE_AU.txt`
- `validation/V24_GOC_CANONICAL_EXPERIENCE_WAVE_AU_SURFACE_PRIORITY_COMPRESSION_REPORT.md`

## Wave selection decision

Because the user explicitly asked to continue until the A-line was finished, I re-audited after AU and then chained only the remaining high-leverage A-line work until closure.

The strongest remaining sequence was:

- AV before AW/AX, because the visible line still needed tighter social-side / pair-line / surface binding.
- AW next, because the carryover was present but still too room-general in phrasing.
- AX after that, because once coupling and convergence improved, the visible line could be compressed without losing truth.
- AY last, because only then was an honest closure call possible.

I rejected a new reconciliation wave because accessible package truth remained consistent during the pass.
I rejected broader shell/UI work because it would have exceeded the A-line scope.

## What changed

### Code

- tightened surface-heat phrasing so side/pair/surface coupling reads more specifically in the visible reply line
- changed carryover tails from generic `still carrying ...` language into surface-convergent phrasing like `the earlier ... still sitting on/at/over ...`
- compressed exchange-cause phrasing from `made the live pressure point` to `put ... under pressure again`
- tightened why-this-reply explanations so they route the answer through the same active surface
- kept changes inside the existing shell-readout/visible-output path

### Tests

- updated world-engine exact-output proofs to match the stronger coupled/convergent/compressed lines
- updated backend/frontend mocked projection strings so accessible artifact truth stays synchronized with the new visible output truth
- preserved focused bridge/frontend proof coverage for the authoritative shell-state path

## Why those changes were necessary

AU solved dominant-surface prioritization.
But the line still had three remaining weaknesses:

1. the social side/pair axis and the surface were not always coupled tightly enough,
2. the carryover wound was often named as prior context rather than as something still living on the same object/zone,
3. the line still used mildly diagnostic phrasing where chamber-play compression was stronger.

Without AV/AW/AX, the room was already socially anchored, but not yet as tightly side-bound, surface-bound, and continuously wound-bound as the A-line intended.

## Validation performed

### Pre-existing package-truth stance carried forward from AU

- AT verified as already real in package truth
- AU verified as already real in package truth

### Focused post-change proof commands

```bash
cd /mnt/data/wos_continue/wave_arp_full
PYTHONPATH=world-engine /opt/pyvenv/bin/python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py --tb=short
PYTHONPATH=backend /opt/pyvenv/bin/python -m pytest -q backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine' --tb=short
PYTHONPATH=frontend /opt/pyvenv/bin/python -m pytest -q frontend/tests/test_routes_extended.py -k 'play_execute_json_merges_runtime_shell_readout_projection or play_shell_frames_latest_transcript_with_runtime_response_address or play_execute_json_prefers_turn_level_addressed_visible_output_bundle or play_execute_json_uses_turn_level_runtime_shell_readout_when_state_missing or play_shell_renders_cached_runtime_shell_readout_fields or play_shell_prefers_compressed_contextual_readout_fields or play_execute_json_returns_authoritative_shell_state_bundle or play_observe_returns_observation_meta or play_shell_embeds_initial_authoritative_shell_state_json or play_observe_returns_observation_source_and_runtime_session_flags or play_execute_json_returns_runtime_ready_and_observation_source or play_execute_json_and_followup_observe_share_coherent_bundle_shape or play_execute_json_prefers_turn_level_addressed_visible_output_bundle_over_hosting_surface' --tb=short
PYTHONPATH=. /opt/pyvenv/bin/python -m pytest -q ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py --tb=short
```

## Test / command outputs

- `world-engine/tests/test_story_runtime_shell_readout.py` -> `8 passed, 1 warning in 0.18s`
- `backend/tests/test_session_routes.py ...` -> `2 passed, 35 deselected in 8.26s`
- `frontend/tests/test_routes_extended.py ...` -> `14 passed, 53 deselected in 0.43s`
- `ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py` -> `5 passed in 0.51s`

## What is now proven

- the visible response/output line is now more tightly side/pair/surface coupled
- carryover is no longer just prior-room context; it now lives on the same surface as the current answer
- transcript/readout phrasing is materially shorter and less diagnostic without losing runtime truth
- doorway / books / phone / hosting surface examples all prove this in executable output expectations
- backend bridge and frontend shell projections remain intact
- no package-truth mismatch was introduced during the continuation pass

## What remains unresolved

Only bounded polish-level residue remains inside the A-line.
No higher-leverage A-wave remains open in the accessible package truth.

Residual non-blocking observations:

- some non-primary informational helper fields remain more explanatory than the compressed headline line
- the broader shell still exposes multiple contextual fields, even though the visible lead line is now sharply compressed

## Closure call

For the current accessible package truth, the A-line is honestly closed.

Reason:

- the visible response line is socially specific
- it is side/pair/surface/carryover bound
- the apartment now reads more clearly as a socially loaded domestic play surface
- re-centering remains socially emergent rather than system-explicit
- no stronger remaining A-wave survives the focused closure audit

## Exact files changed in this continuation

- `world-engine/app/story_runtime_shell_readout.py`
- `world-engine/tests/test_story_runtime_shell_readout.py`
- `backend/tests/test_session_routes.py`
- `frontend/tests/test_routes_extended.py`
- `validation/CURRENT_STATE_VALIDATION_SUMMARY_WAVE_AY.txt`
- `validation/V24_GOC_CANONICAL_EXPERIENCE_WAVE_AY_FINAL_A_LINE_CLOSURE_AUDIT.md`

## Recommended next follow-up

Do not open a new A-wave by default.

The strongest next move is to begin the B-line, unless a future artifact-truth mismatch forces A0 reconciliation back into scope.
