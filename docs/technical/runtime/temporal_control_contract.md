# Temporal Control Contract

`temporal_control` is the bounded runtime aspect for Π28 time manipulation. It
does not grant the model free-form authority to rewrite chronology. It selects
one structural time operation for the turn from committed runtime evidence and
validates optional `temporal_control_events` before commit/recovery.

## Scope

The contract supports five operations:

- `hold_current_moment`
- `advance_elapsed_time`
- `recall_committed_past`
- `summarize_gap`
- `resume_present`

Runtime derivation uses structured inputs only: `scene_plan_record`,
`scene_energy_target`, `pacing_rhythm_target`, `semantic_move_record`,
`prior_consequence_cascade_state`, `prior_callback_web_state`, prior
`temporal_control_state`, and normalized module policy.

`temporal_control` may shape prompt context and diagnostics. It must not mutate
canonical state, adopt inactive branch state, or treat generated narration as
proof that time handling is valid.

## Runtime Policy

Modules opt in through `runtime_intelligence.temporal_control`, normalized into
`ModuleRuntimePolicy.runtime_governance_policy.temporal_control`.

Important fields:

- `schema_version`: `temporal_control_policy.v1`
- `enabled`
- `allowed_operations`
- `require_structured_events`
- `max_recalled_turns`
- `max_elapsed_turns`
- `default_commit_impact`
- `model_context_visibility`

The GoC slice enables the aspect with bounded committed refs, optional
structured events, at most three recalled turns, and at most four elapsed turn
units.

## Realization

When the selected operation is explicitly realized, structured output may emit:

```json
{
  "temporal_control_events": [
    {
      "operation": "recall_committed_past",
      "source_turn_ids": ["turn-alpha"],
      "source_consequence_ids": ["cons-alpha"],
      "elapsed_turns": 0
    }
  ]
}
```

Validation checks:

- operation is selected and allowed;
- recalled turn ids are selected committed refs;
- recalled consequence ids are selected committed consequence refs;
- elapsed turn count stays within policy bounds;
- no event rewrites history;
- no event adopts inactive branch state;
- required structured events are present when policy requires them.

## Diagnostics

Runtime diagnostics should use structured fields:

- `turn_aspect_ledger.temporal_control.expected.policy_present`
- `turn_aspect_ledger.temporal_control.expected.policy_enabled`
- `turn_aspect_ledger.temporal_control.expected.allowed_operations`
- `turn_aspect_ledger.temporal_control.selected.operation`
- `turn_aspect_ledger.temporal_control.selected.recalled_turn_ids`
- `turn_aspect_ledger.temporal_control.selected.recalled_consequence_ids`
- `turn_aspect_ledger.temporal_control.actual.realized_operations`
- `turn_aspect_ledger.temporal_control.actual.realized_turn_ids`
- `turn_aspect_ledger.temporal_control.actual.elapsed_turns`
- `turn_aspect_ledger.temporal_control.actual.contract_pass`
- `turn_aspect_ledger.temporal_control.actual.failure_codes`
- `temporal_control_policy_present`
- `temporal_control_target_selected`
- `temporal_control_operation`
- `temporal_control_committed_sources_bounded`
- `temporal_control_history_rewrite_absent`
- `temporal_control_contract_pass`
- `temporal_control_failure_codes`

Operator and frontend surfaces may display these backend-provided fields. They
must not infer time-control correctness from prose flashbacks, pacing, visible
length, UI shape, or judge labels.

## ADR-0039 Boundary

Gate and regression tests for this contract must derive expectations from
normalized module policy, exported constants, schema versions, ledger fields,
MCP row fields, planner-truth rehydration, and structured
`temporal_control_events`.

Allowed test stimuli:

- normalized module policy;
- fixture scene-plan, scene-energy, pacing, semantic-move, callback, and
  consequence-cascade records;
- fixture prior temporal-control state;
- fixture structured `temporal_control_events`.

Forbidden primary oracles:

- generated narration wording;
- copied dialogue or scene prose;
- LLM-as-a-Judge chronology categories;
- branch preview text;
- hardcoded Pi28/Table-B labels in production logic outside reviewed canonical
  surfaces;
- duplicated policy truth in tests when the policy can be loaded or normalized.

## Implementation Anchors

- `content/modules/god_of_carnage/module.yaml`
- `ai_stack/contracts/temporal_control_contracts.py`
- `ai_stack/story_runtime/narrative/temporal_control_engine.py`
- `ai_stack/module_runtime_policy.py`
- `ai_stack/langgraph/langgraph_runtime_state.py`
- `ai_stack/langgraph/langgraph_runtime_executor.py`
- `ai_stack/story_runtime/runtime_aspect_ledger/__init__.py`
- `ai_stack/story_runtime/story_runtime_playability.py`
- `world-engine/app/story_runtime/commit_models.py`
- `world-engine/app/story_runtime/manager/`
- `tools/mcp_server/tools_registry_handlers_langfuse_verify.py`

## Verification Anchors

- `ai_stack/tests/test_temporal_control_engine.py`
- `ai_stack/tests/test_module_runtime_policy.py`
- `ai_stack/tests/test_runtime_aspect_ledger.py`
- `world-engine/tests/test_planner_truth_and_runtime_surfaces.py`
- `tests/gates/test_table_b_anti_hardcoding_gate.py`
