# Sensory Context Contract

Status: Canonical technical contract for the bounded Pi26 sensory-context runtime aspect.

## Purpose

`sensory_context` is the runtime contract for bounded sensory layering. It
selects authored sensory layers for the next visible turn, validates structured
realization evidence for those layers, records the result in the runtime aspect
ledger, and carries a compact sensory snapshot into the next turn.

The aspect exists to make sensory texture observable without turning it into a
free-form prose judgment.

Sensory context is:

- policy-backed by `runtime_intelligence.sensory_context`;
- derived from authored sensory palette and scene-affordance content;
- selected as bounded layer ids with source references;
- validated against structured `sensory_context_events`;
- persisted through planner truth after commit;
- exposed through `turn_aspect_ledger`, Langfuse, and the MCP runtime-aspect matrix.

Sensory context is not:

- a replacement for environment state, scene energy, pacing rhythm, or social pressure;
- a style or quality judge over generated narration;
- a second story-truth store;
- a frontend-owned inference;
- a Table-B label that production code may reference outside reviewed canonical surfaces.

## Authority

The authoritative value sources are module policy and authored content:

```text
content/modules/god_of_carnage/module.yaml
runtime_intelligence.sensory_context

content/modules/god_of_carnage/knowledge/narrator_sensory_palette.yaml
content/modules/god_of_carnage/locations/**/*.yaml
content/modules/god_of_carnage/objects/**/*.yaml
```

`ModuleRuntimePolicy` normalizes the policy into
`runtime_governance_policy.sensory_context`. Runtime code must consume the
normalized policy, authored source fields, and exported contract constants
rather than duplicating sensory truth in tests or scattered implementation
branches.

The World-Engine remains the authority for committed session state. Sensory
context may shape the next prompt and recovery feedback, but it does not mutate
canon by itself and does not bypass validation or the commit seam.

## Runtime Shape

The core schemas are:

```json
{
  "policy": "sensory_context_policy.v1",
  "state": "sensory_context.v1",
  "target": "sensory_context.v1",
  "validation": "sensory_context.v1",
  "aspect": "turn_aspect_ledger.sensory_context"
}
```

`SensoryContextState` carries bounded current/prior sensory feedback:

- `current_layer_ids`
- `prior_layer_ids`
- `repeated_layer_count`
- `location_id`
- `object_id`
- `mood_key`
- `intensity`
- `source_evidence`

`SensoryContextTarget` selects the expected sensory layer set:

- `intensity`
- `location_id`
- `object_id`
- `mood_key`
- `selected_layers`
- `required_layer_ids`
- `min_layers_per_turn`
- `max_layers_per_turn`
- `require_structured_events`
- `source_evidence`
- `rationale_codes`

Each selected layer carries `layer_id`, `layer_kind`, `source`, `source_field`,
`source_ref`, optional language, optional text, and `required`.

`SensoryContextValidation` records deterministic realization evidence:

- `status`
- `contract_pass`
- `failure_codes`
- `feedback_code`
- `target`
- `actual.event_count`
- `actual.realized_layer_ids`
- `actual.required_layer_ids`
- `actual.selected_layer_ids`
- `actual.repeated_layer_count`

## Policy and Bounds

The normalized policy contains:

```json
{
  "schema_version": "sensory_context_policy.v1",
  "enabled": true,
  "min_layers_per_turn": 1,
  "max_layers_per_turn": 3,
  "require_structured_events": true,
  "model_context_visibility": "bounded_authored_layers",
  "intensity_by_pressure_band": {},
  "mood_by_scene_energy": {},
  "mood_by_scene_function": {},
  "source": "module_runtime_policy.sensory_context"
}
```

Layer and intensity vocabularies are exported from
`ai_stack/sensory_context_contracts.py`:

- layer kind: `mood`, `room_ambient`, `location_entry`, `object_perception`;
- intensity: `low`, `medium`, `high`;
- validation status: `approved`, `degraded`, `rejected`, `not_applicable`.

Policy numbers are clamped by the contract normalizer. Tests should load the
policy and assert normalized fields instead of copying module YAML values into
hardcoded expected dictionaries.

## Flow

1. `ModuleRuntimePolicy` normalizes `runtime_intelligence.sensory_context`.
2. LangGraph derives `scene_energy_target`, `pacing_rhythm_target`, and
   `social_pressure_target`.
3. LangGraph derives `sensory_context_state` and `sensory_context_target` from
   current scene/location, player action frame, local context transition,
   authored sensory palette, scene affordances, adjacent runtime targets, prior
   planner truth, and output language.
4. The dramatic generation packet receives the target as bounded authored layer
   guidance.
5. Structured output may emit `sensory_context_events` with `layer_id` and
   `source_ref`.
6. Validation checks selected layer ids, required layers, source references,
   and layer budget.
7. `sensory_context_validation` updates
   `turn_aspect_ledger.sensory_context`.
8. Recoverable failures feed self-correction with a bounded feedback code.
9. World-Engine persists `sensory_context_state`,
   `sensory_context_target`, and `sensory_context_validation` in planner truth
   and governance surfaces.
10. Langfuse scores/spans and the MCP runtime-aspect matrix expose target,
    layer, pass/fail, source-reference, and failure-code evidence.

## Validation and Recovery

Validation failure codes are contract constants:

- `sensory_context_target_mismatch`
- `sensory_context_missing_required_layer`
- `sensory_context_unselected_layer`
- `sensory_context_source_ref_mismatch`
- `sensory_context_layer_budget_exceeded`
- `sensory_context_structured_event_missing`

Rejected sensory-context validation is recoverable dramatic failure evidence. It
may trigger rewrite feedback and retry. It must not be satisfied by copying a
sentence from generated narration into a test.

## Diagnostics

Runtime diagnostics should use structured fields:

- `turn_aspect_ledger.sensory_context.expected.policy_present`
- `turn_aspect_ledger.sensory_context.expected.policy_enabled`
- `turn_aspect_ledger.sensory_context.selected.target`
- `turn_aspect_ledger.sensory_context.selected.selected_layer_ids`
- `turn_aspect_ledger.sensory_context.selected.required_layer_ids`
- `turn_aspect_ledger.sensory_context.actual.contract_pass`
- `turn_aspect_ledger.sensory_context.actual.failure_codes`
- `sensory_context_target_present`
- `sensory_context_intensity`
- `sensory_context_location_id`
- `sensory_context_object_id`
- `sensory_context_contract_pass`
- `sensory_context_required_layers_realized`
- `sensory_context_source_refs_valid`
- `sensory_context_failure_codes`

Operator and frontend surfaces may display backend-provided diagnostics. They
must not infer sensory correctness from prose vividness, card layout, image
choice, or judge labels.

## ADR-0039 Boundary

Gate and regression tests for this contract must derive expectations from
normalized module policy, exported contract constants, schema versions, authored
palette/affordance content, ledger fields, MCP row fields, and structured
`sensory_context_events`.

Allowed test stimuli:

- fixture scene-plan fields;
- fixture player action frames;
- fixture local context transitions;
- fixture prior sensory-context state;
- canonical narrator sensory palette rows;
- canonical scene-affordance rows;
- fixture structured output rows.

Forbidden primary oracles:

- generated narration wording;
- copied dialogue or scene prose;
- LLM-as-a-Judge sensory/style categories;
- frontend card shape or visual density;
- hardcoded Pi26/Table-B control labels in production logic outside reviewed
  canonical surfaces;
- duplicated policy or authored-content truth in tests when the content can be loaded.

Tests may assert that evidence fields name structured sources such as
`narrator_sensory_palette`, `scene_affordances`, `scene_energy_target`,
`social_pressure_target`, or `prior_sensory_context_state`. They must not assert
that a specific story sentence has the correct sensory quality.

## Implementation Anchors

- `content/modules/god_of_carnage/module.yaml`
- `ai_stack/sensory_context_contracts.py`
- `ai_stack/sensory_context_engine.py`
- `ai_stack/module_runtime_policy.py`
- `ai_stack/langgraph_runtime_state.py`
- `ai_stack/langgraph_runtime_executor.py`
- `ai_stack/runtime_aspect_ledger.py`
- `ai_stack/story_runtime_playability.py`
- `world-engine/app/story_runtime/commit_models.py`
- `world-engine/app/story_runtime/manager.py`
- `tools/mcp_server/tools_registry_handlers_langfuse_verify.py`

## Verification Anchors

- `ai_stack/tests/test_sensory_context_engine.py`
- `ai_stack/tests/test_module_runtime_policy.py`
- `ai_stack/tests/test_runtime_aspect_ledger.py`
- `ai_stack/tests/test_goc_structured_setting_knowledge.py`
- `ai_stack/tests/test_narrator_consequence_contract.py`
- `tools/mcp_server/tests/test_langfuse_verify_tools.py`
- `tests/gates/test_table_b_anti_hardcoding_gate.py`
