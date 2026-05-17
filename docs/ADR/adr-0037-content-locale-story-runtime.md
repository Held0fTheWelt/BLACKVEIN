# ADR-0037: Semantic Language Adapter for Story Runtime Shell

## Status

Superseded by the universal semantic language adapter.

## Context

The old implementation treated player language as a module-owned lookup
problem: module string files, phrase rules, and per-language directives tried to
map utterances into runtime actions. That created a second description database
beside locations, objects, characters, and canonical path content.

## Decision

1. `story_runtime_core.language_adapter` exposes a content-derived semantic
   catalog and an AI resolution contract.
2. Player input supplies `session_input_language`; player-visible output uses
   `session_output_language`.
3. The AI normalizes player input into English for internal grounding against
   English-authored content, then produces visible narration in the requested
   output language.
4. Content modules must not ship language lookup directories, phrase-rule files,
   action maps, or duplicate description databases.

## Consequences

- Meaning is resolved semantically against authored locations, objects,
  characters, and policy surfaces.
- Unknown or underspecified actions remain clarification requests instead of
  being guessed by code-level phrase rules.
- Runtime language support scales through the AI adapter contract rather than
  per-module lookup tables.
