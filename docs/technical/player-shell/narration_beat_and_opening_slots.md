# narration_beat and opening slots (player shell)

**Last updated:** 2026-05-20
**Normative ADRs:** [ADR-0034](../../ADR/adr-0034-player-facing-narrative-shell-contract.md) (shell contract), [ADR-0046](../../ADR/adr-0046-typewriter-cinematic-direction.md) (typewriter), [ADR-0035](../../ADR/adr-0035-story-opening-economy-and-warmup.md) (opening economy)

This page exists so engineers do not reintroduce a removed pattern: **forcing literary opening slot names onto `scene_blocks[].narration_beat` by card index**.

It also records the narrated-speech rule added on 2026-05-20: a narrator card may contain direct NPC speech when prose and speech are one literary unit. In that case the card is still `block_type: narrator`, but the actor's authority lives in `embedded_speech_spans[]`.

---

## Three different “opening” concepts

| Concept | Where it lives | Names like `premise`, `scene_setup`, `role_anchor` |
|---------|----------------|-----------------------------------------------------|
| **Literary opening slots** | `gm_narration` strings (model path) | Yes — text structure validated by `ai_stack/goc_opening_transition.py` |
| **Opening-shape evidence** | Langfuse subgates in `world-engine/app/story_runtime/manager.py` | Subgate keys `narrator_intro_present`, `role_anchor_present`, `scene_setup_present` are **historical labels** for “block 0/1/2 is narrator” — not values to write on blocks |
| **Shell block metadata** | `visible_scene_output.blocks[]` | **No** index-forced literary slot names on `narration_beat` |

---

## What `scene_blocks[].narration_beat` is

Presentation + typewriter metadata **on that block only**.

| Source | Typical value | Shell / typewriter |
|--------|---------------|-------------------|
| **GoC narrator-path** | Canonical mandatory beat id, e.g. `park_edge_establishing_image`, `stick_strikes_face` | `ai_stack/story_runtime/narrator/goc_narrator_path.py` sets `narration_beat` to beat id → typewriter `default` profile unless id matches a profile key |
| **Runtime bootstrap** | `boot` | `play_runtime_bootstrap.js` → `boot` profile |
| **Explicit dramaturgy** (rare) | `role_anchor`, `tension`, `dialogue`, `action`, `reflection` | Matching entry in `TYPEWRITER_BEAT_PROFILES`; `role_anchor` adds `scene-block--narrator-role-anchor` (sweep CSS) |
| **Dramatic emphasis** | Use `visual_emphasis.kind` (e.g. `dramatic_moment`) | `scene-block--visual-emphasis-*` — **not** `narration_beat` |

---

## Narrated actor speech

Some theatrical prose cannot be represented correctly as "narrator card, then actor card". The narrator may frame an actor's gesture, speech, and aftermath in one sentence or paragraph:

```text
Kuehl hob er die Stirn und sagte: "Du kannst mich mal!"
```

Runtime shape:

```json
{
  "block_type": "narrator",
  "composition_kind": "narrated_actor_speech",
  "text": "Veronique las mit fester Stimme vom Bildschirm: ...",
  "embedded_speech_spans": [
    {
      "actor_id": "veronique_vallon",
      "speaker_label": "Veronique",
      "speech_text": "...",
      "speech_act": "read_aloud_first_half_of_written_statement"
    }
  ]
}
```

Rules:

- Do not split this into two visible cards unless the source content is already structurally split.
- Do not treat the narrator card as a narrator summary. The embedded quote is the actor's direct speech.
- Do not infer speaker ownership from the visible card lane alone. Use `embedded_speech_spans[].actor_id`.
- Actor-response diagnostics must count embedded speech spans as visible NPC speech.
- Player ownership never follows from proximity to a player input card; it follows from the structured actor id.

This is different from a jammed actor-line string such as `A: ... B: ...`, which the engine may split into separate `actor_line` blocks by roster-driven speaker prefixes.

---

## Removed anti-pattern (do not restore)

**`_annotate_goc_opening_narration_beats`** (deleted from `manager.py`, 2026-05):

- After projection, set `blocks[0].narration_beat = "premise"`, `blocks[1] = "scene_setup"`, `blocks[2] = "role_anchor"`.
- **Why wrong:** Overwrote canonical beat ids; third card got `overflow: hidden` from role-anchor CSS; broke multi-line typewriter.

**Guard test:** `world-engine/tests/test_trace_middleware.py::test_opening_scene_blocks_do_not_force_legacy_ui_narration_beat_tags`

---

## Quick decision tree

```
Need to style the third opening card as “dramatic”?
  → Author visual_emphasis on the mandatory beat in YAML / narrator-path
  → NOT narration_beat: "role_anchor" by index

Need slower typewriter on a role-orientation line?
  → Set narration_beat: "role_anchor" on THAT block in content/projection
  → NOT a post-projection loop over indices 0..2

Need premise / room / role text order?
  → goc_opening_transition + opening_shape_normalizer on gm_narration
  → NOT scene_blocks[].narration_beat

Need Langfuse “opening shape” pass?
  → _compute_opening_shape_subgates (narrator blocks at indices 0–2)
  → NOT writing subgate names onto narration_beat

Need to show NPC direct speech embedded in prose?
  → block_type: narrator + composition_kind: narrated_actor_speech
  → embedded_speech_spans[] carries actor_id / speech_text
  → NOT a narrator summary and NOT a separate forced actor_line
```

---

## Code pointers

- Canonical opening blocks: `ai_stack/story_runtime/narrator/goc_narrator_path.py` (`build_goc_narrator_path_opening`)
- Narrated actor speech realization: `world-engine/app/story_runtime/manager.py` (`_realize_npc_speak_block`)
- Embedded-speech responder detection: `world-engine/app/story_runtime/manager.py` (`_build_live_scene_turn_envelope`)
- gm_narration slots: `ai_stack/goc_opening_transition.py` (`enforce_opening_transition_on_beats`)
- Renderer: `frontend/static/play_block_renderer.js` (`narration_beat === 'role_anchor'` → CSS class)
- Typewriter profiles: `frontend/static/play_typewriter_engine.js` (`DEFAULT_BEAT_PROFILES`)
- Label leak in text (not field): `ai_stack/visible_narrative_contract.py` strips `role_anchor:` prefixes from visible strings
