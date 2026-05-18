# ADR-0056: Souffleuse player guidance lane

## Status

Accepted

## Context

The runtime needs a player-facing help voice for moments where the narrator
should not explain private role pressure or playable affordances directly. This
is especially important after narrator-only passages, location changes, and
phases where the selected human character has not yet acted or spoken.

The existing language contract keeps internal grounding in English:
player input is normalized to English before semantic resolution, content facts
are grounded against English-authored module content, and visible output is
realized in `session_output_language`.

## Decision

Introduce **Souffleuse** as a Director-selected player guidance lane.

The Souffleuse:

- speaks in second person as an inner role voice;
- is player-visible as a hint/notice lane, not narrator prose;
- is selected from authored `canonical_path.*.souffleuse_cues`;
- uses `internal_resolution_language: en`;
- produces visible text through prompt-store templates for the session output
  language;
- has `commit_impact: ui_guidance_only`;
- may orient role, location, emotional pressure, and possible action surfaces;
- must not commit a player action, force an exact line, reveal hidden NPC intent,
  duplicate narrator description, or become canonical fact.

The Director must select Souffleuse only when the current content cue marks the
timing and narration alone is not the right surface. Opening role orientation is
therefore content-timed, not hardcoded as “turn 0”.

## Consequences

`souffleuse` is a valid visible block type and a dramatic capability family
(`souffleuse.role_orientation`, `souffleuse.role_pressure`). The frontend renders
it as a player hint/director notice. The narrator path remains speech-free and
NPC-agency-free; Souffleuse does not make an NPC plan applicable.

Prompt-store wording may vary by output language, but the engine must not add
hardcoded translation or verb maps for Souffleuse. Source facts and cue IDs stay
English internally.

## Verification

- `ai_stack/tests/test_goc_souffleuse.py`
- `world-engine/tests/test_goc_narrator_path_opening.py`
- `ai_stack/tests/test_player_narrative_cards.py`
- `frontend/tests/test_block_renderer.js`
