# Player Input Interpretation Contract

Status: Canonical contract for runtime input understanding.

## Purpose

Define how raw player text is interpreted into structured runtime intent.
Natural language is the primary interaction contract. Explicit commands are a
recognized special mode within the same interpretation system.

## Input

- `raw_text`: original player text.
- Runtime may include optional contextual metadata (session, scene, actor role).

## Output shape

Interpreter returns a structured object containing:

- `raw_text`
- `normalized_text`
- `kind`
- `confidence` (0.0-1.0)
- `ambiguity` (optional reason when confidence is low)
- `intent` (optional high-level inferred intent)
- `entities` (optional extracted targets or references)
- `command_name` and `command_args` (only when `kind=explicit_command`)
- `selected_handling_path` (`nl_runtime`, `command`, `meta`)

## Required categories

- `speech`
- `action`
- `reaction`
- `mixed`
- `intent_only`
- `explicit_command`
- `meta` (out-of-world input)
- `ambiguous`

## Ambiguity and confidence

- Confidence must be explicit on every interpretation.
- Low-confidence interpretations must provide an `ambiguity` reason.
- Runtime can ask for clarification when confidence is below policy threshold.

## Command compatibility policy

- Command syntax is recognized by the interpreter.
- Commands are no longer the primary architecture.
- Command inputs are routed through the same structured contract as all other input.

## Runtime integration requirement

- Story turn execution consumes interpreted input objects, not blind raw strings.
- Diagnostics must expose raw input, interpreted mode, confidence, ambiguity, and selected handling path.
