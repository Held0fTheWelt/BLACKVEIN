# ADR-0046: Typewriter Cinematic Direction

Transform the player-shell typewriter from a constant-speed text reveal into a beat-aware, cinematic delivery layer that feels live-directed by a human GM.

## Status

`Accepted`

## Date

2026-05-17

## Intellectual property rights

Repository authorship and licensing: see project **LICENSE**; contact maintainers for clarification.

## Privacy and confidentiality

This ADR contains no personal data. The typewriter operates on the **player-visible** projection only (ADR-0034 §7) — `player_display_text` or `text` — and never reveals diagnostic or operator-only fields.

## Related ADRs

- [ADR-0034](adr-0034-player-facing-narrative-shell-contract.md) — Player-facing narrative shell contract; defines `visible_scene_output.blocks`, `typewriter_slice_start_index`, `narration_beat`, and the display-text rule the engine must honour.
- [ADR-0033](adr-0033-live-runtime-commit-semantics.md) — Live runtime commit semantics; this ADR styles the surface that consumes commits.
- [ADR-0038](adr-0038-canonical-turn-lifecycle-single-commit-path.md) — Single-commit lifecycle; the typewriter renders post-commit blocks only.

## Context

The current `play_typewriter_engine.js` ships a working but flat experience:

- **Constant tempo** (`characters_per_second: 44`) for every block → reads as a machine streaming, not a human directing.
- **Dead config fields**: `pause_before_ms` (150) and `pause_after_ms` (650) are defined in the engine constructor but never consulted by `_onClockTick`. Between-block silence is therefore zero.
- **Beat metadata is decorative only**: `BlockRenderer` writes `data-narration-beat="<beat>"` and the `role_anchor` value flips a CSS border colour to amber — no other beat affects timing, cursor shape, or atmosphere.
- **No cursor in practice**: `.block-typewriter::after { content: '|'; animation: blink 1s infinite }` exists in `style.css` but the `block-typewriter` class is never set by any JavaScript path. The cursor is dead CSS.
- **`textContent.substring()` rendering** prevents any per-character styling — no glow trail, no character-by-character reveal, no localised animation around the live position.
- **Slice transitions are hard cuts**: `_onSliceDeliveryComplete` immediately starts the next block; no breath, no beat-change cue.

The product goal — quoted from the player-frontend brief — is for the typewriter to be a **central, exciting, spectacular experience** that lets the player feel the action is **happening live, as if a human were directing it**. The beat system is the rail on which this cinematic direction should ride; today it is unused at runtime.

This ADR commits to a refactor that activates the beat rail, replaces the substring renderer with a per-character span model, and layers in live-direction signals so the player perceives a director on the other end of the wire, not a stream.

## Decision

The typewriter pipeline (`play_typewriter_engine.js`, `play_blocks_orchestrator.js`, `play_block_renderer.js`, `play_shell.js`, `style.css`) will be modified so that each of the following bullets is true and verifiable:

1. **Per-character DOM model.** `play_typewriter_engine.js` reveals text by appending `<span class="char">…</span>` elements (one per code-point, whitespace preserved as visible spans), not by mutating `textContent.substring`. The block element's final `textContent` equals the source string. Each appended span receives a CSS reveal animation (`opacity` + `transform: translateY` + `filter: blur`) so each character resolves into place rather than popping.
2. **Live cursor.** A single `<span class="play-cursor" aria-hidden="true">` element is appended after the last revealed char-span on every tick. The cursor's variant (`data-cursor-variant`) is driven by the active block's beat profile. The cursor breathes (sinusoidal opacity + glow), and pulses sharply on each newly-revealed char. When a block completes the cursor performs a "settle" animation (pulse, shrink, fade) before the next slice begins.
3. **Punctuation-aware pauses.** After a char is revealed the engine schedules the next char's reveal at `now + base_interval + jitter + punctuation_pause(char)`, where `punctuation_pause` is sourced from a constant map (`. ! ?` → 280–420 ms; `, ;` → 110–160 ms; `—` → 180 ms; `…` → 650 ms cumulative; `\n` → 200 ms). This activates the "sentence breath" that today is absent.
4. **Micro-jitter.** Per-char interval is multiplied by `(1 + noise)` where `noise ∈ [-0.12, +0.12]` from a deterministic PRNG seeded with the block id (so the same block id produces the same rhythm on replay/debug). This removes the machine-cadence.
5. **`pause_after_ms` activated.** Block completion holds the slice queue for the next slice's `pause_before_ms` then starts; default profile values are tuned per beat (see §6). The orchestrator owns the gap (engine reports complete; orchestrator schedules next via the existing `setOnDeliveryComplete` callback).
6. **Beat profile map.** A single profile object in the engine maps every supported `narration_beat` to: `cps`, `jitter`, `cursor_variant`, `atmosphere_class`, `pause_before_ms`, `pause_after_ms`. Beats covered: `boot` (runtime shell bootstrap only), `role_anchor`, `tension`, `dialogue`, `action`, `reflection`, plus a `default` fallback. The orchestrator switches profile on block start and applies `atmosphere_class` to the scene-block element.
7. **Beat-change decompression.** When the next slice's beat differs from the current one, the orchestrator inserts a 250 ms gap during which the outgoing cursor fades and the incoming scene-block border pulses once with the incoming beat's atmosphere colour, before the first char of the new block is scheduled.
8. **Live-direction signals.** Between player-submit and the first scene block arriving, `play_shell.js` shows a `play-composing` indicator (three pulsing glyphs in mono, beat-coloured). The signal dissolves into the position of the first revealed char. Player-echo: the player's own most-recent input fades to 0.55 opacity while the engine is delivering. The story window border carries a 60-bpm heartbeat while a WebSocket narrator stream is open; the heartbeat goes matte when the stream closes.
9. **Spektakel layer.**
   - **Skip** becomes a speed-run: remaining chars reveal at 8× current beat cps with the cursor flattened to a line and a chromatic-aberration tint; no instant `textContent` swap.
   - **`role_anchor` opening**: card-border glow sweeps left→right (800 ms) before the first char is scheduled.
   - **Matrix coupling**: while a typewriter slice is active the matrix-rain layer runs +12% speed and +8% density; otherwise it relaxes to baseline.
10. **Determinism guarantee for tests.** When `TypewriterEngine` is constructed with `test_mode === true`, jitter, punctuation pauses, beat-change decompression, and matrix coupling are bypassed. The existing `getQueueState()` shape (`current_block_id`, `current_visible_chars`, `queue_length`, `queue[]`) is preserved. `clock.advanceBy()` continues to drive deterministic time. The existing test suite (`frontend/tests/test_typewriter_engine.js`) must remain green without modification.
11. **Accessibility & reduced motion.** `prefers-reduced-motion: reduce` suppresses char-reveal animation, cursor breathing, sweeps, and matrix coupling — char-spans appear instantly and the cursor is static. The existing `accessibility_mode` toggle on `BlocksOrchestrator` continues to render every block in full immediately.
12. **No content/contract changes.** Block schema, `player_display_text`/`text` selection rules (ADR-0034 §7), `typewriter_slice_start_index` semantics, and diagnostics-block suppression rules are unchanged.
13. **Runtime boot delivery is a first-class profile, not a story beat.** `play_runtime_bootstrap.js` may create a `system_boot` block with `narration_beat: "boot"` and a per-block delivery cps override. The TypewriterEngine honours `block.delivery.characters_per_second` for such operational blocks while preserving the existing global default for ordinary unannotated narrative blocks. The `boot` profile exists to style shell startup text and must not be interpreted as canonical narrative pacing.

## Consequences

**Positive:**

- Player perceives a directed performance: punctuation breaths, beat-coded tempo, and a cursor that reacts to the engine make every turn feel hand-paced.
- Beat metadata is now load-bearing — authoring beats on a block has visible runtime impact, encouraging dramaturgs to use it.
- Live signals (composing pulse, heartbeat, echo) make the runtime's *presence* visible to the player; loss of connectivity is felt, not just logged.
- Per-char span model unlocks future effects (highlight on player-mentioned entities, in-line tooltips, evidence-anchor underlines) without another rewrite.

**Negative / risks:**

- DOM cost rises from one `textContent` write per tick to one `<span>` append per char. Mitigated by short block sizes typical for narrative beats and by `documentFragment` batching where useful. Profiled budget: < 4 ms scripting cost per 100 chars on a mid-range laptop.
- Determinism: jitter + punctuation pauses change tick math. Mitigated by `test_mode` short-circuit (no jitter, no pauses) and by deriving block-level jitter from a seeded PRNG so the same id replays identically.
- Beat profile drift: if dramaturgs author beats inconsistently, players see incoherent tempo. Mitigated by collapsing unknown beats to the `default` profile and by logging unknown beat names once per session in dev mode.

**Follow-ups:**

- Profile-tune the beat map after first playtests (the values in §6 are first-pass estimates).
- Consider an opt-in audio layer (subtle tipping ticks, beat-tinted; default off) — explicitly out of scope for this ADR.
- Consider an in-game "Director cadence" preset (slow/normal/fast) exposed in the play-controls bar, multiplying every beat's `cps` uniformly.

## Diagrams

```
turn submit                first block arrives          block N renders
     │                            │                          │
     │  ┌────────────────────┐    │                          │
     ├─►│ play-composing     │────┼───►dissolves into char 0 │
     │  │ (3 pulsing glyphs) │    │                          │
     │  └────────────────────┘    │                          │
     │                            │                          │
     │                            ▼                          │
     │            ┌────────── BlocksOrchestrator ───────┐    │
     │            │ beat-change?  ─► 250 ms decompress  │    │
     │            │ start delivery via TypewriterEngine │    │
     │            └─────────────────┬───────────────────┘    │
     │                              ▼                        │
     │            ┌────────── TypewriterEngine ─────────┐    │
     │            │ for each char k of block:           │    │
     │            │   schedule_at[k] = sum( base/cps    │    │
     │            │     × (1 + jitter)                  │    │
     │            │     + punctuation_pause(prev) )     │    │
     │            │ append <span class="char"> on tick  │    │
     │            │ move <span class="play-cursor">     │    │
     │            └─────────────────┬───────────────────┘    │
     │                              ▼                        │
     ▼                       block complete                  │
player-echo fades              cursor settle                 │
                              pause_after_ms                 ▼
                              next slice or end           ───── continues
```

## Testing

How we **verify** this decision:

- **Existing unit suite preserved**: `frontend/tests/test_typewriter_engine.js` (32 cases covering VirtualClock, single-active wiring, progressive rendering exact char counts, `skipBlock`, `revealAll`, `reset`, `setOnDeliveryComplete`, `getQueueState`) must run unchanged. The implementation guarantees this via `test_mode === true` disabling jitter/punctuation/decompression and via preserving the public method surface.
- **Render-shape contract test (new)**: a unit test in `frontend/tests/test_typewriter_engine.js` (or a sibling file) asserts that after delivery completes, `blockEl.querySelectorAll('.char').length === text.length` and `blockEl.querySelector('.play-cursor') !== null`.
- **Beat-profile dispatch test (new)**: given a block with `narration_beat: 'tension'`, the engine consults the tension profile (cps, cursor variant). Asserted by spying on the profile resolver or by inspecting `data-cursor-variant` on the rendered cursor.
- **Runtime boot profile test (new)**: `frontend/tests/test_typewriter_engine.js` asserts the `boot` profile exists and that per-block `delivery.characters_per_second` controls startup-block pacing.
- **Determinism replay test (new)**: in test mode, two consecutive `startDelivery(block)` calls with the same block id produce identical `scheduled_at` sequences (PRNG seeded by block id).
- **Frontend pytest suite**: `cd frontend && python -m pytest tests/` must remain green (105 cases at time of writing).
- **Manual smoke**: open `/play/<session_id>` in Chrome and Firefox with a real backend + world-engine; confirm composing pulse → first char dissolve → punctuation breaths → cursor variant per beat → settle → next slice. Repeat with `prefers-reduced-motion: reduce` set.

**Failure modes that should trigger an ADR review:**

- Tests in `frontend/tests/test_typewriter_engine.js` need to be modified to pass — that means we broke the determinism guarantee in §10.
- Players report the new cadence "feels slower than reading" — beat profile values in §6 need re-tuning; that is a tuning patch, not an ADR change. An ADR change is required if a beat is *added* to the schema or *removed* from the profile map.
- Per-char rendering exceeds the 4 ms scripting budget on baseline hardware — implementation must batch via `DocumentFragment` or fall back to chunked reveal.

Gate and promotion-style tests must comply with **[ADR-0039](adr-0039-gate-tests-no-hardcoded-oracle-bypass.md)** (no hardcoded primary oracles); the typewriter is a display surface and never an oracle — no compliance change required.

## References

- `frontend/static/play_typewriter_engine.js` — the engine being refactored.
- `frontend/static/play_blocks_orchestrator.js` — slice queue + delivery sequencing; gains beat-change decompression.
- `frontend/static/play_block_renderer.js` — sets `data-narration-beat`; unchanged by this ADR but consumed by the new profile resolver.
- `frontend/static/play_block_display_text.js` — single source of display text; unchanged.
- `frontend/static/play_shell.js` — gains composing pulse and player-echo wiring.
- `frontend/static/play_runtime_bootstrap.js` — builds the shell-owned `system_boot` block consumed by the typewriter before Director-owned story blocks.
- `frontend/static/style.css` §"Phase D: QA Canonical Turn Diagnostics Panel" neighbourhood — gains `.play-cursor`, `.char`, beat atmosphere classes, settle/sweep/speedrun keyframes.
- `frontend/tests/test_typewriter_engine.js` — existing unit suite the determinism guarantee protects.
- [ADR-0034](adr-0034-player-facing-narrative-shell-contract.md) §7 — display text and slice rules.
