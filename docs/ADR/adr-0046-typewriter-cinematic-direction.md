# ADR-0046: Typewriter Cinematic Direction

Transform the player-shell typewriter from a constant-speed text reveal into a beat-aware, cinematic delivery layer that feels live-directed by a human GM.

## Status

`Accepted`

## Implementation Status

**Last reviewed:** 2026-05-19.

| ADR bullet | Status | Evidence |
|------------|--------|----------|
| §1 Per-char `<span class="char">` model | **Done** | `frontend/static/play_typewriter_engine.js` |
| §2 Live `play-cursor` + variants | **Done** | same; `style.css` `data-cursor-variant` |
| §3 Punctuation pauses | **Done** (live mode) | `PUNCTUATION_PAUSE_MS`; off in `test_mode` |
| §4 Micro-jitter (seeded PRNG) | **Done** (live mode) | `_mulberry32` / `_seedFromString` |
| §5 `pause_before` / `pause_after` between slices | **Done** | `play_blocks_orchestrator.js` profile gaps |
| §6 `TYPEWRITER_BEAT_PROFILES` map | **Done** | `DEFAULT_BEAT_PROFILES`; unknown → `default` |
| §7 Beat-change decompression | **Partial** | `scene-block--beat-decompress` + profile gap; not a fixed 250 ms orchestrator hold |
| §8 Composing / player-echo / typing pulse | **Done** | `frontend/static/play_cinematic.js` |
| §9 Skip speedrun | **Done** | `is-speedrun` on `.play-shell` |
| §9 `role_anchor` sweep | **Done (opt-in)** | CSS on `.scene-block--narrator-role-anchor` only when block has `narration_beat: "role_anchor"` |
| §9 Matrix +12% / +8% while typing | **Partial** | CSS glow on `body.is-typing .matrix-layer__glow`; play route often has no matrix layer |
| §10 `test_mode` determinism | **Done** | 37 Jest cases in `frontend/tests/test_typewriter_engine.js` |
| §11 `prefers-reduced-motion` | **Done** | `style.css` media query |
| §13 `boot` profile | **Done** | `play_runtime_bootstrap.js` |

**Opening `narration_beat` semantics** (normative, not typewriter-specific): [ADR-0034](adr-0034-player-facing-narrative-shell-contract.md) §**narration_beat semantics**. Do **not** reintroduce `_annotate_goc_opening_narration_beats` or index-based `premise` / `scene_setup` / `role_anchor` on `scene_blocks`. Canonical narrator-path blocks use **mandatory beat ids** (e.g. `stick_strikes_face`); typewriter uses the `default` profile unless the id matches a named profile key.

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

**As of 2026-05-19** the player-shell typewriter is **no longer** a flat `textContent.substring` stream. `play_typewriter_engine.js` reveals per-character spans, drives a live `play-cursor`, and resolves tempo from `TYPEWRITER_BEAT_PROFILES` keyed by each block's `narration_beat` (unknown values → `default`). `play_blocks_orchestrator.js` applies profile-based gaps between slices; `play_cinematic.js` wires composing pulse, player-echo fade, and typing/stream surface classes.

**Historical problem (pre-implementation):** constant 44 cps, unused beat metadata, dead legacy `.block-typewriter::after` cursor CSS, and hard-cut slice transitions.

**Historical opening bug (removed 2026-05):** `_annotate_goc_opening_narration_beats` forced `premise` / `scene_setup` / `role_anchor` onto `blocks[0..2].narration_beat`, which wrongly applied `scene-block--narrator-role-anchor` (`overflow: hidden`) to the third opening card and broke multi-line layout. That pass is **deleted**; guard: `world-engine/tests/test_trace_middleware.py::test_opening_scene_blocks_do_not_force_legacy_ui_narration_beat_tags`. Full semantics: ADR-0034 §**narration_beat semantics**.

**Current opening behaviour:** GoC **narrator-path** sets `narration_beat` to each block's **canonical mandatory beat id** (`ai_stack/narrator/goc_narrator_path.py`). Dramatic emphasis uses `visual_emphasis` (e.g. `dramatic_moment`), not literary slot names on the field. The `role_anchor` typewriter/CSS sweep runs **only** when a block explicitly has `narration_beat: "role_anchor"`.

**Remaining gaps vs this ADR:** beat-change timing is profile-driven, not a fixed 250 ms decompression; matrix “coupling” is a light CSS glow, often inert on `/play` where `#matrix-layer` is absent; dedicated Jest tests for render-shape / beat-profile dispatch called out below are not all present yet.

The product goal remains: the typewriter should feel **live-directed** — punctuation breaths, beat-coded tempo, cursor presence, and composing/echo signals — not a uniform machine stream.

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
   - **`role_anchor` sweep (opt-in):** When a block's `narration_beat` is **literally** `role_anchor` (author/model annotation, not index-forced opening tags), card-border glow sweeps left→right (800 ms) before the first char is scheduled. Canonical narrator-path openings use mandatory beat **ids** and `visual_emphasis` for dramatic moments — they do **not** get this sweep unless explicitly tagged.
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
- **CSS:** `scene-block--narrator-role-anchor { overflow: hidden }` can clip multi-line typewriter text — if `role_anchor` styling is used, remove or relax overflow (ADR-0034 §**narration_beat semantics**).
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

- **Unit suite (current):** `cd frontend && npm test -- --testPathPattern=test_typewriter_engine` — **37 passed** (2026-05-19). `test_mode === true` disables jitter/punctuation for determinism; public surface (`getQueueState`, `skipBlock`, `revealAll`, `setOnDeliveryComplete`) unchanged.
- **Render-shape contract test (follow-up):** assert post-delivery `.char` count equals display text length and `.play-cursor` is present — not yet a dedicated case.
- **Beat-profile dispatch test (follow-up):** block with `narration_beat: 'tension'` → tension `cps` / `data-cursor-variant` — not yet a dedicated case.
- **Runtime boot profile test (follow-up):** `boot` in `DEFAULT_BEAT_PROFILES` + `play_runtime_bootstrap.js` — covered indirectly; no isolated Jest case yet.
- **World-Engine opening guard:** `world-engine/tests/test_trace_middleware.py::test_opening_scene_blocks_do_not_force_legacy_ui_narration_beat_tags`.
- **Frontend pytest suite:** `cd frontend && python -m pytest tests/` must remain green when touching the shell.
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
- [ADR-0034](adr-0034-player-facing-narrative-shell-contract.md) §7 and §**narration_beat semantics** — display text, slice rules, opening field semantics.
- `docs/technical/player-shell/narration_beat_and_opening_slots.md` — operator cheat sheet (literary slots vs shell field).
- `ai_stack/narrator/goc_narrator_path.py`, `ai_stack/goc_opening_transition.py` — canonical opening content vs gm_narration slots.
- `world-engine/tests/test_trace_middleware.py::test_opening_scene_blocks_do_not_force_legacy_ui_narration_beat_tags`.
