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
- `runtime_delivery_hint` (`say`, `emote`, `narrative_body`, or omitted for `command` / `meta`): conservative hint for thin hosts that only support `say` vs `emote` (both `emote` and `narrative_body` map to the emote channel; `narrative_body` marks low-confidence or non-dialogue-first utterances).

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
- Low-confidence interpretations must provide an `ambiguity` reason when the kind is `ambiguous`, or when competing signals are present (e.g. `conflicting_action_reaction` on `mixed`).
- The interpreter does **not** block turn execution: low confidence yields honest `ambiguity` / lower confidence and a conservative `runtime_delivery_hint` (typically `narrative_body` or `emote` instead of `say`).
- Downstream policy may still ask for clarification in UI; the contract keeps the story host able to proceed.

## Authoritative vs preview interpretation

- **Authoritative** interpreted payload for a story turn is the object produced inside the World-Engine turn graph (`interpreted_input` on the turn envelope), using the shared `interpret_player_input` implementation.
- The backend may expose `backend_interpretation_preview` on session routes for debugging; it is **not** a second runtime truth and may be compared to the graph output for drift checks only.

## Command compatibility policy

- Command syntax is recognized by the interpreter.
- Commands are no longer the primary architecture.
- Command inputs are routed through the same structured contract as all other input.

## Runtime integration requirement

- Story turn execution consumes interpreted input objects, not blind raw strings.
- Diagnostics must expose raw input, interpreted mode, confidence, ambiguity, and selected handling path.

## Primary runtime path contract

Natural language input is treated as the default story-play path end-to-end:

1. Frontend shell form (`/play/<run_id>/execute`) submits `operator_input`.
2. Frontend route forwards the text to backend session turns as `player_input`.
3. Backend route (`POST /api/v1/sessions/<session_id>/turns`) invokes the shared interpreter and proxies execution to the World-Engine story runtime.
4. World-Engine runtime executes the turn through `RuntimeTurnGraphExecutor`, where interpreted input affects routing, **model prompt shaping** (structured interpretation summary appended before generation), and execution behavior.

Slash-command input remains supported (`/look`, `/inspect`, `!` forms), but it is handled as an explicit command specialization within the same turn execution pipeline.
