# ADR-0037: Remove Content Locale Runtime Lookups

## Status

Accepted. Superseded the earlier content-locale design.

## Context

The earlier story-runtime shell treated player language as a module-owned
lookup problem. Module string files, locale directories, phrase rules, actor
alias matchers, and per-language action maps tried to map utterances into
runtime actions.

That design was not general. It created a second description database beside
locations, objects, characters, canonical path content, and module policy. It
also made German support look correct only for the phrases already written into
the engine.

## Decision

1. Content modules must not ship locale lookup directories, phrase-rule files,
   verb maps, action maps, actor-name text matchers, or duplicate language
   description databases.
2. `story_runtime_core.language_adapter` exposes a content-derived semantic
   catalog and an AI resolution contract.
3. Player input is labeled with `session_input_language`. Player-visible output
   is governed separately by `session_output_language`.
4. The AI normalizes player input into English for internal grounding against
   English-authored content, then produces visible narration in the requested
   output language.
5. Thin deterministic interpreters may recognize structural control surfaces
   such as empty input, punctuation-only input, slash commands, meta control,
   and quoted speech previews. They must not decide natural-language actions,
   target actors, scene functions, or social moves through word lists.
6. Output-language support is owned by the story output module. Deterministic
   source paths, narrator-path openings, and Souffleuse guidance may produce
   English source blocks, but they must not satisfy German output by reading
   localized content fields, per-language prompt prose, or code-level German
   strings.
7. Tests may use tiny language-specific stubs to prove that the output module
   was invoked. They must not encode production story prose as the expected
   answer.

## Consequences

- Meaning is resolved semantically against authored locations, objects,
  characters, and policy surfaces.
- Unknown or underspecified actions remain clarification requests instead of
  being guessed by code-level phrase rules.
- Runtime language support scales through the AI adapter contract rather than
  per-module lookup tables.
- Runtime tests must assert the semantic contract, content IDs, and structured
  diagnostics, not phrase fixtures.
- Player-visible German can still be tested, but the provenance must identify
  the output module rather than a content-locale lookup.

## Implementation Notes

The removed approach included these obsolete surfaces:

- `story_runtime_core/content_locale.py`
- `ai_stack/action_ontology.py`
- content `locale/` directories
- `action_outcome_map.yaml`
- GoC semantic priority phrase rules
- GoC legacy keyword scene candidates
- GoC actor alias matching from raw player text
- localized narrator-path or Souffleuse prose used as story-runtime source

Remaining telemetry fields with historical names, such as
`legacy_keyword_scene_candidates_used`, are compatibility diagnostics only and
must remain false on the current semantic path.
