# ADR-0056: Souffleuse player guidance lane

## Status

Accepted

## Last Updated

2026-05-18

## Context

The runtime needs a player-facing help voice for moments where the narrator
should not explain a playable character's inward stance directly. This is
especially important after narrator-only passages, location changes, and phases
where the selected human character has not yet acted or spoken.

The existing language contract keeps internal grounding in English:
player input is normalized to English before semantic resolution, content facts
are grounded against English-authored module content, and visible output is
realized in `session_output_language`.

The same boundary applies to Souffleuse. The engine must not make German work by
embedding German guidance strings, German location names, or per-language cue
variants in code or content. German, English, and future player-visible
languages are output-realization concerns, not separate content-authoring
surfaces.

## Decision

Introduce **Souffleuse** as a Director-selected player guidance lane.

The Souffleuse:

- speaks as a concise inward voice in the current playable character's
  register;
- is player-visible as a hint/notice lane, not narrator prose;
- is selected from authored `canonical_path.*.souffleuse_cues`;
- uses `internal_resolution_language: en`;
- builds source guidance from English prompt-store templates and English
  content facts;
- realizes non-English player-visible text through the story output module, not
  through localized prompt-store prose;
- has `commit_impact: ui_guidance_only`;
- may orient the character's immediate stance toward the situation without
  explaining the character from the outside;
- must not commit a player action, force an exact line, reveal hidden NPC intent,
  duplicate narrator description, or become canonical fact.

The Director must select Souffleuse only when the current content cue marks the
timing and narration alone is not the right surface. Opening situation
orientation is therefore content-timed, not hardcoded as “turn 0”.

### D1 - Source language and output realization

Souffleuse source blocks SHALL carry:

- `source_language: en`;
- `internal_resolution_language: en`;
- `session_output_language`;
- `visible_output_language`, which remains `en` before output realization and is
  set to the session language after realization;
- `requires_output_realization`, true whenever `session_output_language != en`;
- source refs and source facts sufficient to explain why this cue applies.

The prompt store may keep compatibility keys such as
`world_engine.souffleuse.opening_orientation.de`, but such keys are aliases only:
their template text must remain English source material. They must not contain
German player-facing prose. If `session_output_language` is `de`, the World
Engine calls the Souffleuse output module and records
`souffleuse_output_realization` in runtime diagnostics.

### D2 - Character-specific guidance

Souffleuse guidance is not generic help text. It is scoped to the current human
actor.

The source block SHALL include `target_actor_id` and character-derived
`source_facts`, including at least the public identity, baseline attitude,
situational stance, and later-development attitude references where available.
Later references may be used only to infer baseline stance; they must not reveal
or anticipate future beats. This means the same canonical cue
may produce different source guidance for Annette and Alain:

- Annette guidance may be grounded in guest civility, maternal defense,
  restraint, and the fear that her son is already being judged.
- Alain guidance may be grounded in containment, procedural distance,
  divided attention, and exit management.

The output module may translate and phrase this guidance for the player, but it
must preserve the actor-specific stance and must not collapse different
playable characters into a single generic hint.

### D3 - Natural inward surface

Souffleuse output must read like a small thought the current character could
plausibly have, not like guidance spoken by a system about the character.

Souffleuse source and output SHOULD be compact, usually one sentence. They SHOULD
use the character's pressure vocabulary:

- Annette may frame the cue around Ferdinand, family dignity, restraint, and the
  fear of being morally cornered.
- Alain may frame the cue around procedure, wording, liability, detachment, and
  exit management.
- Véronique may frame the cue around exactness, Bruno's injury, hospitality, and
  moral seriousness.
- Michel may frame the cue around practicality, closure, and keeping the meeting
  from hardening.

Souffleuse source and output MUST NOT:

- prefix or name the lane, such as `Souffleuse:`;
- begin by telling the player who they are;
- summarize location, household side, role policy, or controls;
- explain the cue in phrases such as "for this role", "you are", or
  "this means";
- expand a compact cue into an outside-observer diagnosis.

### D4 - No hardcoded localized Souffleuse prose

Runtime code and module content SHALL NOT add localized Souffleuse text as a
shortcut. Forbidden examples include:

- German `localized_*` guidance fields used as player-visible prose;
- code-level German strings for opening orientation;
- per-character German templates that bypass the output module;
- German location-name lookup as the source of a Souffleuse sentence.

Localized UI chrome such as a language selector label remains outside this ADR.
This ADR governs story/runtime guidance text.

## Consequences

`souffleuse` is a valid visible block type and a dramatic capability family
(`souffleuse.role_orientation`, `souffleuse.role_pressure`). The frontend renders
it as a player hint/director notice. The narrator path remains speech-free and
NPC-agency-free; Souffleuse does not make an NPC plan applicable.

Prompt-store wording is now source wording, not localized player-visible
wording. The engine must not add hardcoded translation, verb maps, or
per-language Souffleuse lookup tables. Source facts, cue IDs, and actor identity
stay English internally; the output module owns the final session-language
surface.

Tests should assert structured source fields and output-realization provenance,
not exact literary wording. It is valid to use a tiny German test stub to prove
that the output module was invoked; it is not valid to store the production
German sentence in the runtime path.

## Verification

- `ai_stack/tests/test_goc_souffleuse.py`
- `world-engine/tests/test_goc_narrator_path_opening.py`
- `ai_stack/tests/test_player_narrative_cards.py`
- `frontend/tests/test_block_renderer.js`

Current focused verification:

- `pytest ai_stack/tests/test_goc_narrator_path.py ai_stack/tests/test_goc_souffleuse.py -q`
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows pytest world-engine/tests/test_goc_narrator_path_opening.py -q`

The AI-stack Souffleuse tests assert that German sessions still produce English
source guidance before output realization, and that Annette and Alain receive
different inward source text. The World-Engine opening test asserts that German
visible Souffleuse text comes from the output module, carries
`souffleuse_output_realization` diagnostics, and is not lane-prefixed.

## Related ADRs

- [ADR-0036](adr-0036-player-session-output-language.md) - player-visible output
  language.
- [ADR-0037](adr-0037-content-locale-story-runtime.md) - removal of content
  locale runtime lookups.
- [ADR-0054](adr-0054-session-input-language-english-internal-resolution.md) -
  English internal resolution.
- [ADR-0055](adr-0055-semantic-player-input-translation-ingress.md) - semantic
  input translation ingress.
