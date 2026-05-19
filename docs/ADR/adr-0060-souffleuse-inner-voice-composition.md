# ADR-0060: Souffleuse Inner Voice Composition

## Status

Accepted

## Date

2026-05-19

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
- Future: Director-composed Souffleuse blocks in `director_pulse_shadow.py` when
  pressure escalation is live-wired.
