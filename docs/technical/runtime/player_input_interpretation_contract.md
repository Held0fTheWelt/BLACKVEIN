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

## Meta control input

Out-of-world and out-of-character player input is represented as
`kind=meta`, `player_input_kind=meta`, and `selected_handling_path=meta`.
This is a non-story control path, not dialogue, action, narration, or the
story-play `meta_narrative_awareness` aspect.

Canonical handling:

- Meta input does not commit player action or player speech.
- Meta input does not request narrator or NPC story response.
- The turn graph handles meta input through a deterministic control path that
  skips story action resolution, retrieval, model invocation, `validate_seam`,
  and `commit_seam`.
- Runtime output may expose structured `control_events` for diagnostics or UI
  acknowledgement, but those events are not story prose and must not authorize
  fictional truth.
- Runtime diagnostics/repro metadata identify this path with
  `meta_control_path`, `adapter_invocation_mode=meta_control_path`, and
  `graph_path_summary=meta_control_deterministic`.
- Tests for this path must assert contract fields and named routing markers
  following ADR-0039, not generated acknowledgement text.

## Silence and negative-space input

Empty input, punctuation-only input, and explicit withheld-answer input are valid story-play signals. They are not treated as parser failure just because they lack dialogue text.

Canonical handling:

- Empty input and non-lexical input keep the coarse `kind=ambiguous`, low confidence, and `runtime_delivery_hint=narrative_body`, but set `intent=withheld_response_or_silence`.
- Explicit withheld-answer phrases are interpreted as silence / nonverbal withholding, not mixed dialogue/action.
- The LangGraph runtime may map these signals to `player_input_kind=wait_or_observe` for non-lexical input or `player_input_kind=social_nonverbal_action` for explicit withholding.
- Runtime payloads mark `silence_negative_space_signal=true` and set `semantic_category=silence_withdrawal` when the signal should continue into the Π14 negative-space path.
- Semantic interpretation may then emit `semantic_move_record.move_type=silence_withdrawal`, allowing the scene director to produce `silence_negative_space.v1` inside `silence_brevity_decision`.

This path is still deterministic interpretation. It does not authorize committed facts, does not force the player character to speak, and does not let generated silence prose become a test oracle.

## Semantic move and subtext handoff

After input interpretation, the GoC semantic move layer may emit `semantic_move_record`. This record is bounded and advisory. It carries the social move classification, ranked candidates, feature provenance, and the Pi19 subtext payload.

`semantic_move_record.subtext` must be built from `content/modules/god_of_carnage/direction/subtext_policy.yaml` through the policy loader. It may include:

- `surface_mode`
- `explicit_intent`
- `hidden_intent_hypothesis`
- `subtext_function`
- `sincerity_band`
- `evidence_codes`
- `policy_source`
- `policy_rule_id`

This subtext handoff may shape scene-director response and pacing, but it does not authorize facts, player actions, or hidden NPC truth. The full contract is maintained in `docs/technical/runtime/subtext_interpretation_contract.md`.

## Canonical `player_input_kind` taxonomy

The runtime's fine-grained `player_input_kind` taxonomy is defined in
`story_runtime_core/player_input_intent_contract.py` and is the shared source
of truth for interpreter rules, semantic-move alignment, observability scores,
and tests. Runtime code and gate tests must import that contract instead of
copying kind lists.

Current contract families:

- speech-like: `speech`, `question`, `reaction`, `intent_only`, `social_speech_action`
- action-like: `action`, `movement_action`, `object_interaction`, `social_nonverbal_action`, `social_speech_action`, `physical_action`, `hostile_action`, `environment_interaction`, `mixed`, `mixed_action_speech`
- perception-like: `perception`, `perception_action`
- non-speech question-shape guarded: `action`, `perception`, `movement_action`, `perception_action`, `object_interaction`, `social_nonverbal_action`, `physical_action`, `hostile_action`, `environment_interaction`, `wait_or_observe`, `ambiguous`, `unclear`
- non-story control: `meta`
- command/uncertain: `explicit_command`, `unclear`, `ambiguous`

`kind` remains the coarse interpreter category. `player_input_kind` is the
runtime routing surface used by content locale rules, semantic-move guards,
scene-director response policy, and Langfuse deterministic scores.

## Intent invariants

- `player_input_kind` values must be checked against the shared taxonomy.
- Non-speech action/perception/wait surfaces must not become NPC-answer
  `probe_inquiry` semantics solely because the raw text ends in `?`.
- Target-name matching for runtime intent must be case-insensitive and
  accent-folded. For example, GoC actor alias resolution treats `Véronique`
  and `Veronique` as the same canonical target.
- `intent_surface_contract_pass` and `semantic_move_alignment_pass` must use
  the same shared taxonomy as the interpreter and semantic-move pipeline.
- `subtext_contract_pass` must reflect the bounded subtext field contract when
  subtext fields are present in path summaries or traces.
- Π14 silence signals must remain visible as structured fields through the
  runtime path; action-resolution shortcuts must not consume them before the
  scene director can select negative space.
- Meta input must remain isolated as a non-story control path: no player
  action commit, no player speech commit, no NPC/narrator story-response
  expectation, and no story model invocation.
- Tests for these invariants must follow ADR-0039: derive primary assertions
  from this contract, canonical content, or a named invariant rather than
  duplicated hardcoded oracle lists.

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
- `selected_handling_path=meta` is consumed as a deterministic control path,
  not as story prose or as `meta_narrative_awareness`.

## Primary runtime path contract

Natural language input is treated as the default story-play path end-to-end:

1. Frontend shell form (`/play/<run_id>/execute`) submits `operator_input`.
2. Frontend route forwards the text to backend session turns as `player_input`.
3. Backend route (`POST /api/v1/sessions/<session_id>/turns`) invokes the shared interpreter and proxies execution to the World-Engine story runtime.
4. World-Engine runtime executes the turn through `RuntimeTurnGraphExecutor`, where interpreted input affects routing, **model prompt shaping** (structured interpretation summary appended before generation), and execution behavior.

Slash-command input remains supported (`/look`, `/inspect`, `!` forms), but it is handled as an explicit command specialization within the same turn execution pipeline.
