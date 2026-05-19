# ADR-0034: Player-Facing Narrative Shell Contract (MVP5)

## Status

Accepted

## Implementation Status

**Last reviewed:** 2026-05-19. **Core shell contract implemented; some test tiers pending.**

**Implemented:**
- `frontend/static/play_block_display_text.js`: shared `blockDisplayTextForShell(block)` — `player_display_text != null ? player_display_text : text` (same rule for renderer, orchestrator fill, and typewriter duration/DOM).
- `frontend/static/play_blocks_orchestrator.js`: HTTP `loadTurn()` builds **`sliceQueue`** (indices `>= typewriter_slice_start_index`, excluding diagnostics); indices below the slice render **full text immediately**; **`this.blocks` always holds every API block** for reveal/skip/accessibility even when slice cards are not yet mounted. **Progressive DOM mount:** only the **first** slice card is **`renderer.render`** on load; further slice cards mount **when their delivery starts** (`_mountBlockIfNeeded` → empty cell → `startDelivery`). The slice is delivered **sequentially** via `TypewriterEngine.startDelivery` + **`setOnDeliveryComplete`**. **`skipCurrentBlock`** completes the active block (full text) then continues the slice; **`revealAll`** mounts any deferred slice rows, fills **full** shell text for pending slice blocks, clears the queue, and detaches the completion hook. **`setAccessibilityMode(true)`** mounts all blocks in `this.blocks` and fills full transcript. **`appendNarratorBlock`** clears slice state and keeps **one block per stream chunk** (unchanged streaming semantics).
- `frontend/static/play_typewriter_engine.js`: single active block; single `VirtualClock` listener; **`setOnDeliveryComplete(blockId)`** fires after natural completion, skip, or empty display immediate resolve; display text uses `blockDisplayTextForShell`.
- `frontend/static/play_block_renderer.js`: block rendering with `block_type` semantic distinction; optional `narration_beat` on narrator blocks for typewriter pacing and **opt-in** presentation accents (see §**narration_beat semantics** — not index-forced opening tags).
- `frontend/static/style.css`: distinct lane chrome per `block_type` (including `player_input_outcome`); `scene-block--narrator-role-anchor` only when a block **explicitly** carries `narration_beat: "role_anchor"`.
- `frontend/static/play_shell.js`: orchestrates renderer + typewriter + controls.
- `frontend/static/play_runtime_bootstrap.js`: shell-owned DOS-style startup bootstrap. It can prepend a player-visible `system_boot` block with `narration_beat: "boot"` before the first Director-owned story slice, deriving readiness lines from the bootstrap payload (`runtime_session_ready`, `can_execute`, `session_loop`, `shell_state_view`, `visible_scene_output`, and optional scene/capability plan fields). This block is a runtime UI handoff, not committed narrative content.
- Legacy fallback: if `typewriter_slice_start_index` absent, last block is animated (pre-2026-05 behavior preserved).
- `appendNarratorBlock()` finalizes in-flight typewriter before starting delivery for streamed blocks.
- No debug surface in player UI (operator diagnostics stay in Langfuse / explicit diagnostic endpoints).
- Jest tests: `frontend/tests/test_blocks_orchestrator.js`, `frontend/tests/test_typewriter_engine.js`, `frontend/tests/test_block_renderer.js`, `frontend/tests/test_runtime_bootstrap.js`.

**World-Engine — committed visible block shaping (God of Carnage live path):**
- **Invariant (no fixed card count):** The number of NPC transcript cards per turn is **not** a product constant; it emerges from structured rows, split/merge policy, validation, and prune rules. Tests assert **invariants** (no megablock jam, no colon stutter, no redundant action lane), not a fixed DOM node count.
- **One NPC, one `actor_line` block:** If the model jams multiple speakers into a single `actor_line` string (e.g. `Veronique: … Alain: …`), `_expand_multi_speaker_actor_lines` in `world-engine/app/story_runtime/manager.py` splits it into **separate** `actor_line` blocks (per `actor_id` / `speaker_label`). Speaker-prefix detection is **roster-driven** from `session.runtime_projection` via `ai_stack/goc_npc_transcript_projection.py` (not a hardcoded name union in the engine). Consecutive spans for the **same** speaker may be merged depending on governed `story_runtime_experience` flags (`goc_transcript_merge_consecutive_same_actor`, optional `goc_transcript_split_speech_stage_same_actor` after dialogue-then-stage boundaries).
- **No duplicate lane rows:** `_prune_actor_actions_subsumed_by_prior_actor_lines` drops an `actor_action` when its visible text (length-gated, normalized) is already contained in an **earlier** `actor_line` in the same turn (typical `spoken_lines` + `action_lines` echo).
- **Finalize hook:** Split + prune run inside `_finalize_visible_blocks_with_goc_actor_split` immediately before / after `ai_stack.visible_narrative_contract.finalize_visible_scene_blocks` (both the pre-built `scene_blocks` path and the bundle-built path). Effective experience flags are passed from governed `story_runtime_experience` (see `ai_stack/story_runtime_experience.py`).
- **Regie lane mapping (policy):** When `goc_map_action_lines_to_actor_line_lane` is true, structured `action_lines` rows project as `actor_line` blocks (same shell lane as speech) so staging does not force a second colour lane; default remains `actor_action` for distinct stage-direction chrome.
- **Structured row diagnostics:** If a single `spoken_lines` dict row’s text contains multiple roster speaker prefixes, `ai_stack/goc_turn_seams.run_visible_render` adds marker `goc_multi_speaker_merged_into_single_spoken_line_row` (soft signal for operators / quality gates; projection still splits at commit when the jam appears in projected `actor_line` text).
- **PLAYER-SHELL-NARRATIVE-CARD-01:** HTTP `visible_scene_output.blocks` are **player-facing narrative cards** built by `ai_stack/player_narrative_cards.build_player_facing_narrative_cards` from semantic `scene_blocks` (semantic `block_type` preserved; `card_style` / `visible_lane` / `player_display_text` added). Adjacent same-actor `actor_action` folds into the prior `actor_line` card; subsumed duplicates are dropped from the shell list; diagnostics live under `player_shell_narrative_card_diagnostics`.
- **Human-bound player transcript (GoC live):** `_player_input_scene_blocks_for_story_window` **always** emits **two** blocks when `human_actor_id` is set: `player_input` (verbatim typing) then `player_input_outcome` (diegetic attributed line; imperative greets still use the scripted polite outcome for the second card). The shell renders each as its own card (see §4b).
- **Opening literary slots vs shell `narration_beat`:** See §**narration_beat semantics** and **Removed patterns**. `_annotate_goc_opening_narration_beats` was **removed** (2026-05); do not reintroduce index-based `premise` / `scene_setup` / `role_anchor` tagging on `scene_blocks`.
- Pytests: `world-engine/tests/test_goc_multi_speaker_actor_line_split.py`, `world-engine/tests/test_goc_player_input_greeting_imperative.py`, `ai_stack/tests/test_goc_npc_transcript_projection.py`, `ai_stack/tests/test_wave3_multi_actor_vitality.py` (jammed-row marker).

**Not yet fully implemented:**
- Live Langfuse gate (`test_langfuse_live_c640_gate.py`) requires opt-in `RUN_LANGFUSE_LIVE=1` — not run in standard CI.
- Backend cumulative `scene_blocks` / `typewriter_slice_start_index` propagation from turn responses: partially implemented (verified in `tests/test_mvp4_contract_playability.py`).
- **Staging correctness** (e.g. which character may “welcome” guests) remains **model / prompt / content** responsibility; this ADR does not hard-code dialogue rewrites beyond structural de-duplication and lane split.

## Date

2026-05-06

## Context

MVP4 establishes truthful runtime, diagnostics, and canonical HTTP bundles for the play path. MVP5 adds modular block rendering and typewriter delivery in the player shell (`frontend/static/play_shell.js`, `play_blocks_orchestrator.js`, `play_typewriter_engine.js`, `play_block_renderer.js`).

Product feedback indicates a gap between **theatrical narrative goals** (narrator as literate scene-setter and subtle cueing; NPC speech carrying the play) and **current runtime output pacing** (narrator too “complete” in few lines, UI not yet supporting script-like reading).

Separately, ADR-0033 now requires **non-PII player-input correlation** on Backend Langfuse spans for canonical turns. This ADR covers **what the shell must prove** once narrative semantics stabilize.

## Decision

1. **Scope boundary:** ADR-0033 governs commit truth, Langfuse evidence gates, and player-input **hash correlation** on `backend.turn.execute`. **This ADR** governs the **player-visible shell contract**: block stream semantics, transcript vs. live-append rules, and acceptance tests that fail when the shell misrepresents committed runtime truth.

2. **Transcript vs. live delivery:** After each successful turn, the shell must not give the appearance that earlier committed story vanished. The HTTP contract already exposes `story_window.entries` and `visible_scene_output.blocks`; MVP5 orchestration must align with the **cumulative** block policy on the Backend bundle (see `backend/app/api/v1/game_routes.py` cumulative `scene_blocks` when entries carry `scene_blocks`).

3. **Narrator role (product, not only UI):** The narrator is a **literary scene presenter**: atmosphere, perception, and **light guidance** (what is noticeable, what the room offers). The shell must **not** prescribe crude player emotions (“you feel afraid”) or substitute for player agency. Narration density, “show vs tell”, and lane separation (narrator vs NPC vs stage direction) remain **content and graph policy** concerns; the shell **renders** committed lanes faithfully when the engine emits typed blocks and text. Specific literary rules live in narrative governance / prompt packs.

4. **Dramaturgical block types:** The contract assumes distinct block kinds (e.g. narrator, actor line, stage direction) when the API provides `block_type` / structure. The shell must preserve typographic and semantic distinction **when the bundle supplies it** — no collapsing lanes into an undifferentiated blob.

4b. **Extended player-facing block kinds (shell must render faithfully):**
   - **`player_input_outcome`:** Second card in the **always-two** human-bound player pair: echo (`player_input`) then diegetic shell line (`player_input_outcome`, e.g. *Annette sagt: „…“* or scripted greet outcome after *Begrüße …*). Same cumulative rules as other blocks; **distinct** CSS lane from `player_input` (darker green bar / panel — presentation only).
   - **`narration_beat` (optional on `narrator` blocks):** Typewriter profile key and optional CSS accent. **Must reflect authored or operational metadata on that block** — see §**narration_beat semantics**. Unknown values fall back to the typewriter `default` profile; consumers must not treat unknown keys as errors.
   - **`visual_emphasis` (optional):** Separate from `narration_beat` — e.g. `dramatic_moment` drives card chrome via `scene-block--visual-emphasis-*`, not the legacy opening index hack.

4c. **NPC lane cardinality (engine projection):** For God of Carnage live projection, **distinct NPC speakers must appear as separate `actor_line` blocks** when the model merged them into one visible string. The World-Engine normalizes before finalize (see Implementation Status). **One jammed string → N blocks** (N emerges from content); **redundant `actor_action` tail already present in a prior `actor_line` → dropped**. This is **structural** truthfulness of the transcript, not a substitute for model-side dramaturgy.

5. **Single-active typewriter:** Exactly **one** block uses the typewriter at a time. On HTTP `loadTurn`, the shell delivers blocks sequentially according to **`typewriter_slice_start_index`** (see §7). On streamed `appendNarratorBlock`, any in-progress queue is **finalized** (`revealAll`) before starting delivery for the new block (each appended stream chunk is one block — it animates as the active slice). `TypewriterEngine` registers **one** `VirtualClock` tick handler for its lifetime (no duplicate `onTick` listeners per block).

6. **No debug surface in player UI:** Diagnostic or technical payloads must not appear as ordinary narrative blocks in the player shell. Debug belongs in operator tools, Langfuse, or explicit diagnostics endpoints — not mixed into the theatrical transcript.

7. **Cumulative blocks + typewriter slice (HTTP):** `visible_scene_output.blocks` remains the **full committed transcript** (cumulative across `story_window.entries` when each entry carries `scene_blocks`). To animate **only the newly committed blocks** for this response — while showing earlier blocks as stable transcript — the Backend adds **`typewriter_slice_start_index`**: an integer index into `blocks` such that indices `< index` render as **full text immediately**, and indices `>= index` through `len(blocks)-1` are delivered **one after another** via the typewriter (still only one block animating at a time). **Legacy clients:** if the field is absent, the shell may fall back to animating **only the last** block (`blocks.length - 1`), preserving pre-2026-05 behavior.

8. **Streamed narrator chunks:** Each WebSocket/appended narrator block is treated as **one** new block for presentation: finalize any in-flight typewriter (`revealAll`), then run typewriter for **that** block only (decision **5**). HTTP slice indices do not apply to incremental stream delivery.

9. **Progressive DOM mount for HTTP slice cards:** Applies to **every** turn where `visible_scene_output.blocks` includes **multiple** animated slice entries (same rule as opening multi-beat flows — not opening-specific). **`this.blocks` keeps the full committed list** while **DOM insertion** for slice cards is **one card at a time**: first slice block mounts on `loadTurn`; each subsequent slice block mounts **immediately before** its typewriter run (`render` → empty displayed cell → `startDelivery`) so **empty placeholder cards are not shown ahead of animation**. **`revealAll`** and **`setAccessibilityMode(true)`** must **`render` any not-yet-mounted blocks** and fill **`blockDisplayTextForShell`** so “show all” and reduced motion expose the **complete** transcript. **Diagnostics** blocks render when encountered (not queued in `sliceQueue`). **DOM ordering:** v1 appends in API order as deliveries advance; **anchor placement** (`render before/after`) is reserved for a future refinement if diagnostics or stable rows must interleave visually between deferred slice cards.

10. **Direct narrator-tail cleanup (presentation-only):** The player-facing card builder may remove a **directly adjacent** story-lane NPC card when a preceding narrator card already fully subsumes that NPC visible text under the redundancy guardrails; this affects only the rendered player-card projection (`visible_scene_output.blocks`) and does **not** modify committed semantic runtime `scene_blocks`.

11. **Runtime bootstrap is shell-owned, not narrative-owned:** On initial page bootstrap only, the shell may prepend a `system_boot` block before `visible_scene_output.blocks` and set the displayed payload's `typewriter_slice_start_index` to `0` so the boot and then the narrative slice type sequentially. The required command line is `C:\WOS> START DIRECTOR_TICK`; subsequent warmup lines report system readiness for manager/dispatcher/capability/content/session surfaces from the payload when present and fall back to explicit `STANDBY` / `PENDING` / `WAITING` states when not present. This boot block must not be persisted as a story-window entry and must not be injected for ordinary turn updates unless a caller explicitly requests a bootstrap mode.

### narration_beat semantics (normative)

`scene_blocks[].narration_beat` is **presentation and typewriter metadata** on a **specific block**. It is **not** a substitute for canonical mandatory-beat identity, literary opening structure, or Langfuse opening-shape vocabulary.

| Source | Valid `narration_beat` values | Consumer behaviour |
|--------|------------------------------|-------------------|
| **Canonical narrator path** (`ai_stack/goc_narrator_path.py`) | Mandatory beat **id** from YAML (e.g. `park_edge_establishing_image`, `stick_strikes_face`) | Typewriter `default` profile unless id matches a named profile; **no** `scene-block--narrator-role-anchor` unless value is literally `role_anchor` |
| **Runtime bootstrap** (`play_runtime_bootstrap.js`) | `boot` | `boot` typewriter profile; operational UI only |
| **Explicit dramaturgic annotation** (rare; author/model) | `role_anchor`, `tension`, `dialogue`, `action`, `reflection` | Matching profile in `TYPEWRITER_BEAT_PROFILES`; `role_anchor` adds `scene-block--narrator-role-anchor` (sweep CSS — must not clip multi-line text; see ADR-0046 follow-up) |
| **Dramatic emphasis** | Use `visual_emphasis.kind` (e.g. `dramatic_moment`), **not** `narration_beat` | `scene-block--visual-emphasis-dramatic-moment` |

**Literary opening slots** (`premise`, `scene_setup`, `role_anchor` as *story structure*) apply to **`gm_narration` text**, not to shell block indices:

- `ai_stack/goc_opening_transition.py` — validates/reorders the first three narrator **strings** before projection.
- `ai_stack/opening_shape_normalizer.py` — normalizes model `narration_summary` into beat strings.
- `_compute_opening_shape_subgates` in `world-engine/app/story_runtime/manager.py` — Langfuse evidence; checks that indices 0–2 are `narrator` **block types** (subgate names `narrator_intro_present`, `role_anchor_present`, `scene_setup_present` are **historical labels**, not `narration_beat` values to write onto blocks).

**Do not conflate** “opening has three narrator cards” with “card 0 = premise, card 1 = scene_setup, card 2 = role_anchor”. With narrator-path openings there are **many** narrator blocks; the third visible card is ordinary canonical content.

### Removed patterns (do not restore)

| Removed | Was | Why removed |
|---------|-----|-------------|
| `_annotate_goc_opening_narration_beats` | Forced `premise` / `scene_setup` / `role_anchor` onto `blocks[0..2].narration_beat` after projection | Overwrote canonical beat ids; wrongly triggered `scene-block--narrator-role-anchor` + `overflow: hidden` on the third card; broke multi-line typewriter layout |
| Index-based opening UI tagging | Any post-projection pass that maps block index → literary slot name | Superseded by content-authored `narration_beat` + `visual_emphasis`; narrator-path uses mandatory beat ids |

**Guard test:** `world-engine/tests/test_trace_middleware.py::test_opening_scene_blocks_do_not_force_legacy_ui_narration_beat_tags` — first three projected opening blocks must not carry `premise`, `scene_setup`, or `role_anchor` as `narration_beat`.

**Internal label stripping:** Model leaks such as `role_anchor:` in **text** are removed by `visible_narrative_contract` — that is unrelated to the `narration_beat` field.

## Consequences

### Positive

- Clear split: **0033** = truth + observability, **0034** = presentation + shell acceptance.
- E2E and frontend unit tests can target a stable shell contract without overloading runtime ADRs.

### Negative / risks

- Without engine-side block typing and stable `scene_blocks` IDs, the shell cannot deliver theater-grade layout; UI work alone will not satisfy this ADR.
- **Split heuristics** build speaker-prefix alternation from the **runtime NPC roster** (`runtime_projection.npc_actor_ids`, canonical ids, alias expansion) plus display tokens; a static GoC display-name tuple remains a **fallback** only for colon-stutter dedupe when block context is missing. Novel modules/languages need their own roster/vocab, not silent extension of GoC literals in the engine core.
- **Prune rule** uses substring containment on normalized text; very short actions are kept; long duplicated stage tails are removed. False positives are unlikely but possible if an unrelated short clause repeats.

## Diagrams

Split of responsibilities with ADR-0033 and the player shell data path.

```mermaid
flowchart LR
  subgraph adr33 [ADR-0033]
    T[Commit truth + Langfuse evidence]
  end
  subgraph adr34 [ADR-0034]
    S[Block stream + typewriter + transcript]
  end
  BE[Backend bundle: story_window + visible_scene_output]
  WE[World-Engine committed blocks]
  WE --> BE
  BE --> T
  BE --> S
```

## Verification

### Test tiers (see `docs/testing/TEST_SUITE_CONTRACT.md`)

- **Contract tests:** mocks allowed for wiring (e.g. orchestrator + mock typewriter).
- **Live Langfuse gate:** opt-in `RUN_LANGFUSE_LIVE=1` — `backend/tests/test_observability/test_langfuse_live_c640_gate.py` (c640-style regression; no soft skip when live is on).

### Repository tests

- Backend: `tests/test_mvp4_contract_playability.py` (cumulative `visible_scene_output` for MVP5).
- Backend: `tests/test_game_routes.py` (Langfuse player-input hash on canonical turn; ADR-0033 §13.6).
- Backend: `tests/test_session_routes.py` (`test_execute_turn_langfuse_correlates_player_input_hash`; operator path §13.6).
- World-Engine: `tests/test_trace_middleware.py` (`test_world_engine_turn_execute_langfuse_correlates_player_input_hash`; ADR-0033 §13.6).
- Frontend: Jest — `frontend/tests/test_blocks_orchestrator.js`, `frontend/tests/test_typewriter_engine.js` (single listener; `typewriter_slice_start_index` sequential delivery when present; **deferred slice DOM mount** + `revealAll` / accessibility mount missing blocks; legacy last-block fallback when absent), `frontend/tests/test_runtime_bootstrap.js` (DOS boot block construction, no duplicate boot injection, explicit opt-out modes). Run via `npm test` in `frontend/`, orchestrated after pytest by `python tests/run_tests.py --suite frontend` or `--mvp5`.
- World-Engine: `world-engine/tests/test_goc_multi_speaker_actor_line_split.py`, `world-engine/tests/test_goc_player_input_greeting_imperative.py` (split / prune / two-card player transcript).
- World-Engine: `world-engine/tests/test_trace_middleware.py::test_opening_scene_blocks_do_not_force_legacy_ui_narration_beat_tags` (no legacy opening UI beat names on `scene_blocks[].narration_beat`).

CI environments that run shell gates must install frontend npm devDependencies so Jest can execute.

## References

- [ADR-0032](adr-0032-mvp4-live-runtime-setup-requirements.md)
- [ADR-0033](adr-0033-live-runtime-commit-semantics.md)
- [ADR-MVP5-001](MVP_Live_Runtime_Completion/adr-mvp5-001-modular-block-rendering-architecture.md) (modular renderer; block-per-div)
- [TEST_SUITE_CONTRACT](../testing/TEST_SUITE_CONTRACT.md)
- `backend/app/api/v1/game_routes.py`
- `world-engine/app/story_runtime/manager.py` (`_finalize_visible_blocks_with_goc_actor_split`, `_player_input_scene_blocks_for_story_window`, `_maybe_split_goc_opening_into_two_movements` — **not** `_annotate_goc_opening_narration_beats`, removed 2026-05)
- `ai_stack/goc_opening_transition.py`, `ai_stack/goc_narrator_path.py` (literary opening strings vs canonical `narration_beat` on blocks)
- `docs/technical/player-shell/narration_beat_and_opening_slots.md` (operator cheat sheet)
- `ai_stack/goc_npc_transcript_projection.py`, `ai_stack/story_runtime_experience.py`, `ai_stack/goc_turn_seams.py` (`run_visible_render` diagnostics)
- `frontend/static/play_shell.js`
- `frontend/static/play_runtime_bootstrap.js`
- `frontend/static/play_blocks_orchestrator.js`
- `frontend/static/play_typewriter_engine.js`
- `frontend/static/play_block_renderer.js`
- `frontend/static/style.css`
