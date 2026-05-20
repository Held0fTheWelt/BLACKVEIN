# ADR-0060: Souffleuse Inner Voice Composition

## Status

Accepted

## Date

2026-05-20

## Related ADRs

- [ADR-0035](adr-0035-story-opening-economy-and-warmup.md) — opening economy; Souffleuse cues are
  content-authored in canonical_path steps.
- [ADR-0039](adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) — no Pi/Π keys; semantic names only.
- [ADR-0041](adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md) — Director
  composes from semantic capability matrix; Souffleuse is one composition lane.
- [ADR-0053](adr-0053-bounded-semantic-scene-planner.md) — Director is advisory; Souffleuse blocks
  are player_hint lane, not story-truth lane.
- [ADR-0058](adr-0058-director-driven-pulse-and-block-stream-bus.md) — block_stream_event.v1; Souffleuse
  blocks are `souffleuse` type, `player_hint` lane, `skip_to_end` cut-in kind.

## Context

The existing `goc_souffleuse.py` generates opening-phase Souffleuse blocks from
canonical_path cue content. That implementation is correct for Phase 1 (opening
cues) but it does not specify:

1. How the Souffleuse operates during live play (after opening).
2. What the Souffleuse's voice identity is in relation to the player character.
3. How the Director decides whether and when to compose a Souffleuse block.
4. How the Souffleuse block interacts with pressure escalation from the Director.

Phase 2 requires these decisions to be canonical so that the Souffleuse can be
composed by the Director Pulse path without ambiguity.

## Decision

### 1. Souffleuse identity: inner voice of the played character

The Souffleuse is the inner voice of the player's selected character — not a
narrator, not an assistant, not a generic hint system. It speaks as the
character's own inner monologue: evaluation, self-talk, weighing options, feeling
pressure, recalling past events as the character would.

Invariants:

- Always uses second-person address (`du`, `you`) in the character's own voice.
- Never uses generic assistant phrasing ("You might want to...", "Consider...").
- Never uses generic narrator phrasing ("The room is tense.").
- Always speaks from within the character's perspective, knowledge, and affect.
- Character voice profile (`characters/voices/character_voice_*.yaml`) is
  mandatory input; a missing voice profile must be diagnosed and surfaced, not
  silently skipped.

### 2. Voice profile is mandatory

The Souffleuse composition path must read the character voice profile for the
selected player character. If the profile is absent or fails to load:

- Log a diagnostic warning.
- Set `diagnostics.errors` in the output with an `"missing_character_voice_profile"` code.
- Return an empty block list (graceful degradation).
- Do **not** substitute a generic fallback voice.

### 3. Composition is semantic, not mode lookup

The Director does not select Souffleuse behavior from a lookup table of named
modes (e.g. `mode: "pressure"`, `mode: "orientation"`). It composes semantically
over the available capability outputs:

- `scene_energy` — how intense is the current scene?
- `social_pressure` — what is the social pressure state?
- `relationship_dynamics` — what is the player character's relational state?
- `narrative_momentum` — what is the dramatic momentum?
- `actor_pressure_profiles` — what are this character's core pressures and fears?

These inputs inform the Souffleuse's emotional tone and content without hard-
wiring any response to a specific scene function or beat ID. The canonical_path
`souffleuse_cues` remain the primary trigger source; Director-composed (non-cue)
Souffleuse blocks may be added in a future phase but are **not** part of Phase 2.

### 4. Pressure escalation is Director-arranged

When the Director detects that an NPC push is underway (high motivation score on
one or more NPCs), it may arrange a Souffleuse block to convey the character's
subjective sense of pressure. The escalation is:

- Arranged by the Director based on motivation scores and scene state.
- Never a direct report of NPC intent ("Veronique is about to say X").
- Always expressed as the character's own experience ("Something in her tone
  makes you wary.").
- Subject to all existing `player_hint` lane constraints.

In Phase 2 the Souffleuse pressure escalation is shadow-path only. The
Director's tick decision may include `chosen_action_kind: "souffleuse_hint"`
in a future extension; Phase 2 exposes the capability contract, not live delivery.

### 5. No hardcoded sentence templates

The Souffleuse text is produced by the prompt store or, in Phase 1, from
canonical_path cue content. The implementation must not contain hardcoded
German or English sentence fragments. All surface text must come from:

- `canonical_path/*.yaml` `souffleuse_cues[*].prompt_key` → prompt store
- Character voice profile fields used as variables in the prompt

### 6. Block shape

Souffleuse blocks in the block stream have:

- `block_type: "souffleuse"`
- `lane: "player_hint"`
- `cut_in_kind: "skip_to_end"` (from ADR-0058 §6)
- `visible_lane: "player_hint"`
- `card_style: "director_notice"` (existing convention, unchanged)

### 7. No Souffleuse in `director_gathering_state_contracts.py`

The Souffleuse is a Phase-2 / ADR-0060 concern. The `director_gathering_state_contracts.py`
module (ADR-0061 domain) must not reference Souffleuse, motivation scores, or
block stream concepts. This is enforced by existing PR-C guardrail tests.

### 8. Existing `goc_souffleuse.py` unchanged

`ai_stack/goc_souffleuse.py` and `build_goc_opening_souffleuse_projection()` are
not modified by this ADR. The opening Souffleuse path continues to work as
implemented under ADR-0035. This ADR governs the rules that any future Souffleuse
composition path must follow.

### 9. Stage M follow-up composition (NPC reply after a player cut-in)

ADR-0058 §"Stage M" ships the dispatcher that composes the
`post_cut_in_follow_up_event.v1` block when an NPC is selected to reply
to a promoted player cut-in. The Stage-M follow-up is *not* the
Souffleuse (it is an NPC reply, not the played character's inner voice),
but it inherits the same voice discipline that this ADR establishes —
voice-profile-driven, content-authored, never generic — and the
shared safety-gate vocabulary listed in §10.

**Composition modes (closed enum):**

| Mode | When it fires |
|---|---|
| `template_render` | Deterministic render of an authored template from the NPC voice profile (`follow_up_composition`, `speech_patterns`, or top-level template keys). |
| `semantic_generation` | A `FollowUpSemanticProvider` is injected and `PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED=true`. The provider receives a `follow_up_composition_request.v1` projection and returns text only — never a safety verdict. |
| `template_fallback_after_semantic_failure` | Semantic generation was attempted but the provider raised, returned non-text, or its text was rejected by a safety gate. The dispatcher renders the deterministic template and tags the result with this mode plus a `semantic_attempt_metadata` block. |
| `not_applicable` | No voice profile available, or composition was not attempted (e.g. the selected next-action source was `silence`). |

The feature flag *and* an injected provider are both required to take
the semantic path. Setting the flag alone leaves the dispatcher on the
deterministic template path. Production provider wiring on the WS
endpoint is **not** active in Phase 2; see
`docs/MVPs/phase_2_director_pulse_status.md` §5.2 for the deliberate
deferral.

Template-path placeholders are restricted to a closed allowlist:
`actor_id`, `baseline_tone`, `current_phase_voice_hint`,
`interrupted_block_id`, `interrupted_block_type`, `motivation_score`,
`player_input`, `promoted_player_input`, `promoted_player_input_id`,
`voice_hint`. An unrecognised placeholder rejects the render with
`unsupported_follow_up_template_placeholder`.

### 10. Stage M safety gates (closed enum, applied to template AND semantic output)

Every gate runs on whichever text reaches the rendered stage. Any
single `reject` fails the composition; the dispatcher records the first
failing gate's reason and stays on the deterministic template (or, if
the template path also fails, emits a no-follow-up event with a
closed-enum reason).

| Gate | What it checks |
|---|---|
| `length` | Non-empty and ≤ `MAX_COMPOSED_FOLLOW_UP_CHARS` (280 chars). |
| `actor_lane` | Actor ID is not in the AI-forbidden actor lane (human player, `ai_forbidden_actor_ids`, or `actor_lane_context.ai_forbidden_actor_ids`). |
| `voice_forbidden_markers` | Output contains no `voice_consistency.forbidden_language_markers` declared on the actor's voice profile. |
| `no_new_people` | Output contains no token in `forbidden_new_person_tokens`. |
| `no_new_rooms` | Output contains no token in `forbidden_new_room_tokens`. |
| `no_forbidden_plot_facts` | Output contains no token in `forbidden_plot_fact_tokens`. |
| `information_disclosure` | Output contains no `forbidden_disclosure_tokens` from `information_disclosure_target.withheld_units`. |

Each gate returns `pass` / `reject` / `not_applicable` deterministically.
The provider's `success` flag is *advisory*; the gates own the final
decision.

### 11. Inherited invariants — no generic assistant phrasing, no hardcoded NPC lines

The Stage M follow-up composition inherits §1, §2, §3, and §5 of this
ADR:

- The voice profile is the mandatory primary source of text. Without
  a voice profile the dispatcher returns `composition_mode="not_applicable"`
  with `reason="voice_profile_unavailable"`; it never substitutes
  generic copy.
- No hardcoded NPC lines. Template strings live in the authored voice
  profile YAML, not in Python. Tests that exercise the dispatcher
  drive it with fixture profiles built from policy/contract constants,
  not from authored prose.
- No generic assistant phrasing ("You might want to...",
  "Consider...") and no generic narrator phrasing ("The room is
  tense."). These would fail either the `voice_forbidden_markers`
  gate (when the voice profile lists them) or trip the
  `actor_lane`/`no_new_people` gates on lane-breaking content.

### 12. Stage M ≠ live Souffleuse pipeline

Stage M composes an NPC reply (e.g. an `actor_line` follow-up); it does
*not* compose new Souffleuse blocks. Live Director-composed Souffleuse
blocks (pressure-escalation inner-voice cues outside the opening
canonical_path cues) remain deferred — see §3 and §4 above. Phase 2
ships:

- The Souffleuse block-type / lane / cut-kind contract surface
  (`director_pulse_contracts.BLOCK_TYPE_SOUFFLEUSE`,
  `LANE_PLAYER_HINT`, `CUT_KIND_SKIP_TO_END`).
- The opening Souffleuse path via `goc_souffleuse.py` (unchanged).
- The Stage M follow-up composition for NPC replies, sharing the
  voice-profile discipline and safety-gate vocabulary above.

Live Director-composed Souffleuse pressure-escalation blocks are
explicit future work and are not part of Phase 2 closure.

## Consequences

**Positive:**

- Souffleuse voice is defined precisely; future implementations cannot drift into
  generic assistant phrasing without violating this ADR.
- Semantic composition removes the need for a mode-lookup table.
- Shadow path compatibility means Souffleuse pressure escalation is diagnosable
  in Phase 2 without live delivery risk.

**Negative / Trade-offs:**

- Live Director-composed Souffleuse (non-cue) is deferred to a future phase; Phase 2
  only covers the contract and existing cue-based path.
- Character voice profile being mandatory means any missing profile immediately
  surfaces as a diagnostic gap (intended behavior, but may require content work).

## Implementation

- `ai_stack/goc_souffleuse.py` — unchanged; existing opening-phase Souffleuse path.
- `ai_stack/director_pulse_contracts.py` — `BLOCK_TYPE_SOUFFLEUSE`, `LANE_PLAYER_HINT`,
  and `CUT_KIND_SKIP_TO_END` constants define the Souffleuse's stream position.
- `ai_stack/phase2_ws_session_loop.py` — Stage M follow-up composition
  dispatcher (`_compose_npc_follow_up`, `_compose_template_render_follow_up`,
  `_compose_semantic_npc_follow_up`, `_run_safety_gates`,
  `_build_follow_up_composition_request`). Closed-enum vocabulary:
  `COMPOSITION_MODES`, `SAFETY_GATES`, `SOURCE_CONTEXTS`,
  `PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED`,
  `MAX_COMPOSED_FOLLOW_UP_CHARS`.
- `ai_stack/tests/test_phase2_ws_session_loop.py` — dispatcher,
  template, semantic, fallback, and per-gate test coverage (98 tests
  on the WS pure helpers).
- Future: Director-composed Souffleuse blocks in `director_pulse_shadow.py` when
  pressure escalation is live-wired (not part of Phase 2).
- Future: production semantic-provider wiring for the Stage M
  dispatcher on the WS endpoint (not part of Phase 2; see
  `docs/MVPs/phase_2_director_pulse_status.md` §5.2).
