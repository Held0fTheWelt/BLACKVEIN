# Expectation Variation Contract

Bounded expectation variation is the runtime contract for Pi29 / surprise
budget. It lets a turn realize one small variation only when earlier structured
runtime evidence selected it. It is not a free-form surprise judge and it does
not authorize new world branches, hidden-truth leaks, or unbounded twists from
generated prose.

## Authority

- `ModuleRuntimePolicy` normalizes `runtime_intelligence.expectation_variation`
  into `runtime_governance_policy.expectation_variation`.
- LangGraph derives `expectation_variation_state` and
  `expectation_variation_target` from selected setup evidence such as
  information disclosure, dramatic irony, social pressure, relationship state,
  sensory context, callback web, consequence cascade, and prior cooldown state.
- The dramatic generation packet receives only selected variation ids, selected
  variation types, budget, and required setup refs.
- Model output may realize a selected variation only through structured
  `expectation_variation_events`.
- Validation checks event ids, variation types, per-turn budget, setup refs,
  cooldown blocks, and selected target alignment before commit or recovery.
- `turn_aspect_ledger.expectation_variation`, Langfuse scores, MCP matrix rows,
  planner truth, and World-Engine governance surfaces expose the same evidence.

## Runtime Fields

Primary state:

- `expectation_variation_state.schema_version`
- `expectation_variation_state.recent_variation_ids`
- `expectation_variation_state.cooldown_blocked_ids`
- `expectation_variation_state.selected_variation_ids`
- `expectation_variation_state.budget_remaining`

Primary target:

- `expectation_variation_target.selected_variation_ids`
- `expectation_variation_target.selected_variation_types`
- `expectation_variation_target.withheld_variation_ids`
- `expectation_variation_target.required_setup_refs`
- `expectation_variation_target.max_variation_units_per_turn`
- `expectation_variation_target.cooldown_turns`
- `expectation_variation_target.require_structured_events`

Primary validation:

- `expectation_variation_validation.status`
- `expectation_variation_validation.contract_pass`
- `expectation_variation_validation.actual.realized_variation_ids`
- `expectation_variation_validation.actual.realized_variation_types`
- `expectation_variation_validation.actual.budget_used`
- `expectation_variation_validation.failure_codes`

## Diagnostics

Runtime diagnostics should use structured fields:

- `turn_aspect_ledger.expectation_variation.expected.policy_present`
- `turn_aspect_ledger.expectation_variation.expected.policy_enabled`
- `turn_aspect_ledger.expectation_variation.expected.max_variation_units_per_turn`
- `turn_aspect_ledger.expectation_variation.selected.selected_variation_ids`
- `turn_aspect_ledger.expectation_variation.selected.selected_variation_types`
- `turn_aspect_ledger.expectation_variation.selected.required_setup_refs`
- `turn_aspect_ledger.expectation_variation.actual.realized_variation_ids`
- `turn_aspect_ledger.expectation_variation.actual.realized_variation_types`
- `turn_aspect_ledger.expectation_variation.actual.budget_used`
- `turn_aspect_ledger.expectation_variation.actual.contract_pass`
- `turn_aspect_ledger.expectation_variation.actual.failure_codes`
- `expectation_variation_policy_present`
- `expectation_variation_target_selected`
- `expectation_variation_selected_ids`
- `expectation_variation_selected_types`
- `expectation_variation_realized_ids`
- `expectation_variation_realized_types`
- `expectation_variation_budget_used`
- `expectation_variation_budget_pass`
- `expectation_variation_setup_supported`
- `expectation_variation_contract_pass`
- `expectation_variation_failure_codes`

Operator and frontend surfaces may display these backend-provided fields. They
must not infer surprise quality from visible prose, punchline shape, player
reaction, judge labels, or output length.

## ADR-0039 Boundary

Gate and regression tests for this contract must derive expectations from
normalized module policy, exported constants, schema versions, ledger fields,
MCP row fields, planner-truth rehydration, and structured
`expectation_variation_events`.

Allowed test stimuli:

- normalized module policy;
- fixture scene-plan and runtime-aspect records;
- fixture information-disclosure, dramatic-irony, social-pressure, sensory,
  relationship, callback, and consequence setup refs;
- fixture prior expectation-variation state;
- fixture structured `expectation_variation_events`.

Forbidden primary oracles:

- generated narration wording;
- copied dialogue or scene prose;
- LLM-as-a-Judge surprise categories;
- hardcoded Pi29/Table-B labels in production logic outside reviewed canonical
  surfaces;
- duplicated policy truth in tests when the policy can be loaded or normalized.

## Implementation Anchors

- `content/modules/god_of_carnage/module.yaml`
- `ai_stack/contracts/expectation_variation_contracts.py`
- `ai_stack/expectation_variation_engine.py`
- `ai_stack/module_runtime_policy.py`
- `ai_stack/langgraph/langgraph_runtime_state.py`
- `ai_stack/langgraph/langgraph_runtime_executor.py`
- `ai_stack/runtime_aspect_ledger.py`
- `ai_stack/story_runtime/story_runtime_playability.py`
- `world-engine/app/story_runtime/commit_models.py`
- `world-engine/app/story_runtime/manager.py`
- `tools/mcp_server/tools_registry_handlers_langfuse_verify.py`

## Verification Anchors

- `ai_stack/tests/test_expectation_variation_engine.py`
- `ai_stack/tests/test_module_runtime_policy.py`
- `ai_stack/tests/test_runtime_aspect_ledger.py`
- `world-engine/tests/test_planner_truth_and_runtime_surfaces.py`
- `tools/mcp_server/tests/test_langfuse_verify_tools.py`
- `tests/gates/test_table_b_anti_hardcoding_gate.py`
