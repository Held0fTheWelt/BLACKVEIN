# Improvisational Coherence Contract

Improvisational coherence is the bounded runtime contract for accepting a
player contribution without letting that contribution silently rewrite committed
truth, teleport the scene, or force a revised player intention. Historical
Table-B language calls this Pi24, but production code uses the generic aspect
name `improvisational_coherence`.

The contract is structural. It does not judge whether generated narration
"feels yes-and"; it selects a bounded target and validates structured event
evidence.

## Policy

Modules configure the aspect under
`runtime_intelligence.improvisational_coherence`:

- `schema_version`: `improvisational_coherence_policy.v1`
- `enabled`
- `allowed_acceptance_modes`
- `allowed_advance_classes`
- `require_structured_events`
- `min_anchor_refs`
- `max_anchor_refs`
- `default_commit_impact`
- `model_context_visibility`
- `boundary_reason_required`

`ModuleRuntimePolicy.runtime_governance_policy.improvisational_coherence`
normalizes this policy for LangGraph, validation, ledger projection, Langfuse,
and MCP diagnostics.

## Runtime Flow

1. LangGraph derives an `ImprovisationalCoherenceTarget` from the player input
   kind, semantic move record, scene plan, visible responders, scene-energy
   target, and pacing-rhythm target.
2. The dramatic generation packet receives only bounded structured context:
   contribution id/kind, acceptance mode, allowed classes, required anchor refs,
   visible actor ids, and boundary reason requirements.
3. Structured model output may emit `improvisational_coherence_events`.
4. Validation compares those events with the selected target.
5. `RuntimeAspectLedger.improvisational_coherence` records expected, selected,
   actual, status, failure codes, and recovery reason.
6. World-Engine Langfuse scores and the MCP runtime-aspect matrix expose the
   same structured fields for operator debugging.

## Validation

Validation is schema and policy based. It can reject with these failure codes:

- `improv_player_contribution_dropped`
- `improv_scene_anchor_missing`
- `improv_unbounded_world_expansion`
- `improv_contradicts_committed_truth`
- `improv_forced_player_revision`
- `improv_no_playable_boundary_reason`

The validator checks that the selected contribution is acknowledged when
structured events are required, that acceptance modes and advance classes are
allowed by policy, that enough scene anchors are preserved, and that boundary
redirects include a playable reason when required.

## Diagnostics

Runtime diagnostics should use structured fields:

- `turn_aspect_ledger.improvisational_coherence.expected.policy_present`
- `turn_aspect_ledger.improvisational_coherence.selected.contribution_id`
- `turn_aspect_ledger.improvisational_coherence.selected.acceptance_mode`
- `turn_aspect_ledger.improvisational_coherence.actual.advance_class`
- `turn_aspect_ledger.improvisational_coherence.actual.contribution_acknowledged`
- `turn_aspect_ledger.improvisational_coherence.actual.contract_pass`
- `turn_aspect_ledger.improvisational_coherence.actual.failure_codes`
- `improvisational_coherence_policy_present`
- `improvisational_coherence_target_selected`
- `improvisational_coherence_acknowledged`
- `improvisational_coherence_scene_anchor_preserved`
- `improvisational_coherence_contract_pass`

Operator and frontend surfaces may display these fields. They must not infer
improvisational correctness from phrasing, output length, button/card shape, or
judge labels.

## ADR-0039 Boundary

Gate and regression tests for this contract must derive expectations from
normalized module policy, exported constants, schema versions, ledger fields,
MCP row fields, and structured realization events.

Allowed test stimuli:

- literal player inputs;
- fixture interpreted input and semantic move records;
- fixture scene-plan fields;
- fixture structured `improvisational_coherence_events`;
- normalized module policy.

Forbidden primary oracles:

- generated narration wording;
- copied dialogue or scene prose;
- LLM-as-a-Judge "yes-and" categories;
- hardcoded Pi24/Table-B labels in production logic outside reviewed canonical
  surfaces;
- duplicated policy truth in tests when the policy can be loaded or normalized.

Tests may assert structured source fields such as `scene_plan_record`,
`pacing_rhythm_target`, `scene_energy_target`, and
`improvisational_coherence_events`. They must not assert that a specific story
sentence is the correct improvisational response.

## Implementation Anchors

- `content/modules/god_of_carnage/module.yaml`
- `ai_stack/improvisational_coherence_contracts.py`
- `ai_stack/improvisational_coherence_engine.py`
- `ai_stack/module_runtime_policy.py`
- `ai_stack/langgraph_runtime_state.py`
- `ai_stack/langgraph_runtime_executor.py`
- `ai_stack/runtime_aspect_ledger.py`
- `world-engine/app/story_runtime/manager.py`
- `tools/mcp_server/tools_registry_handlers_langfuse_verify.py`

## Verification Anchors

- `ai_stack/tests/test_improvisational_coherence_engine.py`
- `ai_stack/tests/test_module_runtime_policy.py`
- `ai_stack/tests/test_runtime_aspect_ledger.py`
- `tools/mcp_server/tests/test_langfuse_verify_tools.py`
- `tests/gates/test_table_b_anti_hardcoding_gate.py`
