# Pacing Rhythm Contract

Status: Canonical technical contract for the bounded Pi18 pacing-rhythm runtime aspect.

## Purpose

`pacing_rhythm` is the runtime contract for turn cadence. It selects the
structural rhythm the next visible turn should realize, validates that rhythm
against machine-readable output counts, records the result in the runtime
aspect ledger, and carries a bounded rhythm snapshot into the next turn.

The aspect exists to make cadence observable without turning rhythm into a
free-form prose judgment.

Pacing rhythm is:

- policy-backed by `runtime_intelligence.pacing_rhythm`;
- derived from structured runtime state;
- validated against visible-block and actor-turn counts;
- persisted through planner truth after commit;
- exposed through `turn_aspect_ledger`, Langfuse, and the MCP runtime-aspect matrix.

Pacing rhythm is not:

- a replacement for `scene_energy`;
- a style or quality judge over generated narration;
- a second story-truth store;
- a frontend-owned inference;
- a Table-B label that production code may reference outside reviewed canonical surfaces.

`scene_energy` chooses pressure, density, volatility, and transition intent.
`pacing_rhythm` consumes that context and asks whether the visible turn shape
realizes the selected cadence.

## Authority

The authoritative value source is module policy:

```text
content/modules/god_of_carnage/module.yaml
runtime_intelligence.pacing_rhythm
```

`ModuleRuntimePolicy` normalizes that policy into
`runtime_governance_policy.pacing_rhythm`. Runtime code must consume the
normalized policy and exported contract constants rather than duplicating
cadence truth in tests or scattered implementation branches.

The World-Engine remains the authority for committed session state. Pacing
rhythm may shape the next prompt and recovery feedback, but it does not mutate
canon by itself and does not bypass validation or the commit seam.

## Runtime Shape

The core schemas are:

```json
{
  "policy": "pacing_rhythm_policy.v1",
  "state": "pacing_rhythm.v1",
  "target": "pacing_rhythm.v1",
  "validation": "pacing_rhythm.v1",
  "aspect": "turn_aspect_ledger.pacing_rhythm"
}
```

`PacingRhythmState` carries bounded current/prior rhythm feedback:

- `current_cadence`
- `prior_cadence`
- `recent_cadences`
- `repeated_cadence_count`
- `pressure_streak`
- `release_due`
- `pause_obligation_active`
- `last_pacing_mode`
- `last_scene_function`
- `last_beat_id`
- `source_evidence`

`PacingRhythmTarget` selects the expected turn shape:

- `cadence`
- `tempo_arc`
- `response_shape`
- `turn_change_policy`
- `min_visible_blocks`
- `max_visible_blocks`
- `min_actor_turns`
- `max_actor_turns`
- `requires_pause`
- `blocks_forced_speech`
- `release_due_after_turn`
- `rationale_codes`

`PacingRhythmValidation` records deterministic realization evidence:

- `status`
- `contract_pass`
- `failure_codes`
- `feedback_code`
- `target`
- `actual.visible_block_count`
- `actual.actor_turn_count`
- `actual.actor_turn_ids`
- `actual.spoken_line_count`
- `actual.repeated_cadence_count`
- `actual.release_due`

## Policy and Bounds

The normalized policy contains:

```json
{
  "schema_version": "pacing_rhythm_policy.v1",
  "enabled": true,
  "cadence_profiles": {},
  "pacing_mode_profiles": {},
  "scene_function_profiles": {},
  "max_repeated_cadence_count": 2,
  "default_max_visible_blocks": 6,
  "source": "module_runtime_policy.pacing_rhythm"
}
```

Cadence and target vocabularies are exported from
`ai_stack/pacing_rhythm_contracts.py`:

- cadence: `breathe`, `hold`, `press`, `release`, `pivot`, `interrupt`;
- tempo arc: `still`, `compressed`, `standard`, `accelerating`, `releasing`;
- response shape: `pause`, `single_beat`, `exchange`, `multi_reaction`;
- turn-change policy: `allow_hold`, `prefer_actor_turn_change`,
  `require_actor_turn_change`, `silence_or_action_only`.

Policy numbers are clamped by the contract normalizer. Tests should load the
policy and assert normalized fields instead of copying module YAML values into
hardcoded expected dictionaries.

## Flow

1. `ModuleRuntimePolicy` normalizes `runtime_intelligence.pacing_rhythm`.
2. LangGraph derives `scene_energy_target`.
3. LangGraph derives `pacing_rhythm_state` and `pacing_rhythm_target` from scene
   plan, pacing mode, silence decision, selected responders, prior planner
   truth, narrative-thread pressure, callback-web feedback, and prior rhythm.
4. The dramatic generation packet receives the target as bounded structural
   guidance.
5. Validation evaluates the structured output only: `spoken_lines`,
   `action_lines`, `initiative_events`, `state_effects`, and summary fields.
6. `pacing_rhythm_validation` updates `turn_aspect_ledger.pacing_rhythm`.
7. Recoverable failures feed self-correction with a bounded `feedback_code`.
8. World-Engine persists `pacing_rhythm_state`, `pacing_rhythm_target`, and
   `pacing_rhythm_validation` in planner truth and governance surfaces.
9. The next turn receives the latest committed state as
   `prior_pacing_rhythm_state`.
10. Langfuse scores/spans and the MCP runtime-aspect matrix expose the same
    target, pass/fail, density, pause, and failure-code evidence.

## Validation and Recovery

Validation failure codes are contract constants:

- `pacing_rhythm_underrealized_cadence`
- `pacing_rhythm_visible_density_exceeded`
- `pacing_rhythm_required_turn_change_missing`
- `pacing_rhythm_pause_obligation_lost`
- `pacing_rhythm_forced_speech_violation`
- `pacing_rhythm_flat_repetition`
- `pacing_rhythm_target_mismatch`

Rejected rhythm validation is recoverable dramatic failure evidence. It may
trigger rewrite feedback and retry. It must not be satisfied by rewriting a test
fixture to match generated narration.

Forced-speech protection is structural: validation checks explicit
`forced_player_speech`, `forced_speech_detected`, or human/player forced/coerced
flags on structured rows. Ordinary NPC speech does not count as forced player
speech.

## Diagnostics

Runtime diagnostics should use structured fields:

- `turn_aspect_ledger.pacing_rhythm.expected.policy_present`
- `turn_aspect_ledger.pacing_rhythm.expected.policy_enabled`
- `turn_aspect_ledger.pacing_rhythm.selected.target`
- `turn_aspect_ledger.pacing_rhythm.selected.cadence`
- `turn_aspect_ledger.pacing_rhythm.selected.response_shape`
- `turn_aspect_ledger.pacing_rhythm.actual.contract_pass`
- `turn_aspect_ledger.pacing_rhythm.actual.failure_codes`
- `pacing_rhythm_target_present`
- `pacing_rhythm_contract_pass`
- `pacing_rhythm_density_respected`
- `pacing_rhythm_pause_respected`
- `pacing_rhythm_failure_codes`

Operator and frontend surfaces may display backend-provided diagnostics. They
must not infer rhythm correctness from card count, visual spacing, prose length,
or perceived writing style.

## ADR-0039 Boundary

Gate and regression tests for this contract must derive expectations from
normalized module policy, exported contract constants, schema versions, ledger
fields, MCP row fields, and structured realization counts.

Allowed test stimuli:

- literal player inputs;
- fixture scene-plan fields;
- fixture structured output rows;
- fixture prior rhythm state;
- fixture narrative-thread or callback-web feedback ids.

Forbidden primary oracles:

- generated narration wording;
- copied dialogue or scene prose;
- LLM-as-a-Judge pacing categories;
- visual/frontend card shape;
- hardcoded Pi18/Table-B control labels in production logic outside reviewed
  canonical surfaces;
- duplicated policy truth in tests when the policy can be loaded.

Tests may assert that evidence fields name structured sources such as
`scene_energy_target`, `silence_brevity_decision`, `prior_pacing_rhythm_state`,
or `callback_web_feedback`. They must not assert that a specific story sentence
has the correct rhythm.

## Implementation Anchors

- `content/modules/god_of_carnage/module.yaml`
- `ai_stack/pacing_rhythm_contracts.py`
- `ai_stack/pacing_rhythm_engine.py`
- `ai_stack/module_runtime_policy.py`
- `ai_stack/langgraph/langgraph_runtime_state.py`
- `ai_stack/langgraph/langgraph_runtime_executor.py`
- `ai_stack/runtime_aspect_ledger.py`
- `ai_stack/story_runtime/story_runtime_playability.py`
- `world-engine/app/story_runtime/manager.py`
- `tools/mcp_server/tools_registry_handlers_langfuse_verify.py`

## Verification Anchors

- `ai_stack/tests/test_pacing_rhythm_engine.py`
- `ai_stack/tests/test_module_runtime_policy.py`
- `ai_stack/tests/test_runtime_aspect_ledger.py`
- `ai_stack/tests/test_story_runtime_playability.py`
- `ai_stack/tests/test_langgraph_runtime.py`
- `world-engine/tests/test_story_runtime_aspect_ledger.py`
- `world-engine/tests/test_planner_truth_and_runtime_surfaces.py`
- `tools/mcp_server/tests/test_langfuse_verify_tools.py`
- `tests/gates/test_table_b_anti_hardcoding_gate.py`
