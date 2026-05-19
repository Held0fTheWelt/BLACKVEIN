# Player Input Interpretation Contract

Status: Canonical contract for runtime input understanding.

## Purpose

Define how raw player text is interpreted into structured runtime intent.
Natural language is the primary interaction contract. Explicit commands are a
recognized special mode within the same interpretation system.

The deterministic interpreter is a thin structural preview only. Authoritative
natural-language meaning is resolved by the AI semantic adapter using
`session_input_language`, internal English normalization, and the
content-derived semantic catalog.

In the canonical LangGraph turn path, raw player text enters
`translate_player_input` before `interpret_input`. That node prepares the
semantic language-adapter contract, asks the configured model for bounded
`semantic_action` / `semantic_move` payloads when available, and records
`input_translation` diagnostics. Later graph nodes consume the normalized
English evidence instead of re-grounding German or other session input directly
against English-authored content. This ordering rule is captured in
[ADR-0055](../../ADR/adr-0055-semantic-player-input-translation-ingress.md).

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
- `intent` (optional high-level signal; unquoted natural language may use
  `semantic_resolution_required`)
- `entities` (optional extracted targets or references)
- `command_name` and `command_args` (only when `kind=explicit_command`)
- `selected_handling_path` (`nl_runtime`, `command`, `meta`)
- `runtime_delivery_hint` (`say`, `emote`, `narrative_body`, or omitted for `command` / `meta`): conservative hint for thin hosts that only support `say` vs `emote` (both `emote` and `narrative_body` map to the emote channel; `narrative_body` marks low-confidence or non-dialogue-first utterances).

## Required categories

The contract vocabulary still supports these categories for runtime envelopes
and AI semantic output:

- `speech`
- `action`
- `reaction`
- `mixed`
- `intent_only`
- `explicit_command`
- `meta` (out-of-world input)
- `ambiguous`

Pre-AI deterministic previews must be conservative. They may emit
`explicit_command`, `meta`, `speech` for structurally quoted dialogue, or
`ambiguous` for text that requires AI semantic resolution. They must not use
language-specific word lists to classify unquoted input as action, reaction,
question, movement, perception, or social intent.

Backend-local preview surfaces follow the same rule. `AdapterRequest`
diagnostics from `app.runtime.input_interpreter.interpret_operator_input` may
record unquoted text such as `I nod.` as `primary_mode=unknown` with
`semantic_ai_resolution_required`; the improvement sandbox may record
action-like free text such as `I take the lantern...` as
`interpreted_kind=ambiguous` / `triggered_tags=["uncertain"]`. These are not
regressions: action, reaction, movement, and perception labels require
structural command/dialogue syntax or downstream semantic AI evidence.

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

Empty input and punctuation-only input are valid story-play signals. They are
not treated as parser failure just because they lack dialogue text.

Explicit withheld-answer wording is not phrase-mapped by deterministic runtime
code. If the AI semantic layer resolves the turn as silence or withholding, it
emits the bounded semantic fields that carry the turn into the negative-space
path.

Canonical handling:

- Empty input and non-lexical input keep the coarse `kind=ambiguous`, low confidence, and `runtime_delivery_hint=narrative_body`, but set `intent=withheld_response_or_silence`.
- Unquoted lexical input that appears to describe withholding is marked for
  semantic AI resolution unless an upstream AI payload supplies silence
  semantics.
- The LangGraph runtime may map non-lexical signals to
  `player_input_kind=wait_or_observe`. AI-resolved withholding can carry
  `player_input_kind=social_nonverbal_action` or `semantic_category=silence_withdrawal`.
- Runtime payloads mark `silence_negative_space_signal=true` and set `semantic_category=silence_withdrawal` when the signal should continue into the Π14 negative-space path.
- Semantic interpretation may then emit `semantic_move_record.move_type=silence_withdrawal`, allowing the scene director to produce `silence_negative_space.v1` inside `silence_brevity_decision`.

This path does not authorize committed facts, does not force the player
character to speak, and does not let generated silence prose become a test
oracle.

## Semantic move and subtext handoff

After input interpretation, the GoC semantic move layer may emit
`semantic_move_record`. This record is bounded and advisory. It carries the
social move classification, ranked candidates, AI/runtime provenance, and the
Pi19 subtext payload.

The semantic move layer must read bounded AI semantic payloads and explicit
runtime signals. It must not infer `direct_accusation`, `repair_attempt`,
`probe_inquiry`, target actors, or off-scope containment from raw-text keyword
or synonym lists.

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
runtime routing surface used by the semantic language adapter, semantic-move guards,
scene-director response policy, and Langfuse deterministic scores.

Deterministic preview code is not required to fill the full taxonomy. The AI
semantic adapter or later graph stages may populate `player_input_kind` after
normalizing input to English and grounding it against content.

## Intent invariants

- `player_input_kind` values must be checked against the shared taxonomy.
- Non-speech action/perception/wait surfaces must not become NPC-answer
  `probe_inquiry` semantics solely because the raw text ends in `?`.
- Target selection for runtime intent must come from AI semantic resolution and
  canonical content IDs, not raw actor-name alias matching in engine code.
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
- Tests must not assert that literal words such as `why`, `watch`, `silent`, or
  actor display names route the turn. Those meanings require AI semantic
  payloads or explicit content IDs.

## Ambiguity and confidence

- Confidence must be explicit on every interpretation.
- Low-confidence interpretations must provide an `ambiguity` reason when the kind is `ambiguous`.
- The interpreter does **not** block turn execution: low confidence yields honest `ambiguity` / lower confidence and a conservative `runtime_delivery_hint` (typically `narrative_body` or `emote` instead of `say`).
- Downstream policy may still ask for clarification in UI; the contract keeps the story host able to proceed.

## Authoritative vs preview interpretation

- **Authoritative** interpreted payload for a story turn is the object produced
  inside the World-Engine turn graph (`interpreted_input` on the turn envelope),
  after semantic AI resolution has had access to the session language contract
  and content-derived catalog.
- The backend may expose `backend_semantic_translation_preview` and
  `backend_interpretation_preview` on session routes for debugging; these are
  **not** a second runtime truth and may be compared to the graph output for
  drift checks only.

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
2. Frontend route forwards the text to canonical player-session turns as `player_input`.
3. Backend route (`POST /api/v1/game/player-sessions/<run_id>/turns`) resolves the
   World-Engine story-session id and proxies execution to the story runtime.
4. World-Engine runtime executes the turn through `RuntimeTurnGraphExecutor`,
   whose first node is `translate_player_input`; only after that does
   `interpret_input` build the runtime intent surface.
5. Retrieval, action resolution, scene direction, model prompt shaping, and
   diagnostics use `normalized_english_text` and bounded semantic payloads when
   present, while preserving the original player input for visible echo and
   audit evidence.

Slash-command input remains supported (`/look`, `/inspect`, `!` forms), but it is handled as an explicit command specialization within the same turn execution pipeline.
