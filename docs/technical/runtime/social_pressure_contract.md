# Social Pressure Contract

Status: Canonical technical contract for the bounded Pi22 social-pressure runtime aspect.

## Purpose

`social_pressure` is the runtime contract for a continuous, bounded pressure
metric. It derives a normalized score from structured director/social/runtime
signals, maps that score to a low/moderate/high band, records the result in the
runtime aspect ledger, and carries the bounded snapshot into the next turn.

The aspect exists to make pressure calibration observable without turning it
into a free-form prose judgment.

Social pressure is:

- policy-backed by `runtime_intelligence.social_pressure`;
- derived from structured runtime state;
- represented as a `0.0..1.0` score plus a bounded band and trend;
- persisted through planner truth after commit;
- exposed through `turn_aspect_ledger`, Langfuse, and the MCP runtime-aspect matrix.

Social pressure is not:

- a replacement for `social_risk_band`;
- a style or quality judge over generated narration;
- a second story-truth store;
- a frontend-owned inference;
- a Table-B label that production code may reference outside reviewed canonical surfaces.

## Authority

The authoritative value source is module policy:

```text
content/modules/god_of_carnage/module.yaml
runtime_intelligence.social_pressure
```

`ModuleRuntimePolicy` normalizes that policy into
`runtime_governance_policy.social_pressure`. Runtime code must consume the
normalized policy and exported contract constants rather than duplicating
threshold truth in tests or scattered implementation branches.

The World-Engine remains the authority for committed session state. Social
pressure may shape the next prompt and diagnostics, but it does not mutate
canon by itself and does not bypass validation or the commit seam.

## Runtime Shape

The core schemas are:

```json
{
  "policy": "social_pressure_policy.v1",
  "state": "social_pressure.v1",
  "target": "social_pressure.v1",
  "validation": "social_pressure.v1",
  "aspect": "turn_aspect_ledger.social_pressure"
}
```

`SocialPressureState` carries bounded current/prior metric feedback:

- `current_score`
- `current_band`
- `prior_score`
- `prior_band`
- `trend`
- `velocity`
- `active_source_count`
- `source_evidence`
- `rationale_codes`

`SocialPressureTarget` carries the generation-facing bounded target:

- `target_score`
- `target_band`
- `trend`
- `pressure_floor`
- `requires_visible_pressure`
- `release_allowed`
- `source_evidence`
- `rationale_codes`

## Flow

1. `ModuleRuntimePolicy` normalizes `runtime_intelligence.social_pressure`.
2. LangGraph derives `scene_energy_target` and `pacing_rhythm_target`.
3. LangGraph derives `social_pressure_state` and `social_pressure_target` from
   `scene_assessment`, `social_state_record`, scene energy, pacing rhythm,
   prior planner truth, and committed narrative-thread pressure.
4. The dramatic generation packet receives the bounded target as structural
   pressure guidance.
5. Validation checks schema and policy-threshold consistency only.
6. `social_pressure_validation` updates `turn_aspect_ledger.social_pressure`.
7. World-Engine persists `social_pressure_state`, `social_pressure_target`, and
   `social_pressure_validation` in planner truth and governance surfaces.
8. The next turn receives the latest committed state as
   `prior_social_pressure_state`.
9. Langfuse scores/spans and the MCP runtime-aspect matrix expose score, band,
   trend, pass/fail, and failure-code evidence.

## ADR-0039 Boundary

Gate and regression tests for this contract must derive expectations from
normalized module policy, exported contract constants, schema versions, ledger
fields, MCP row fields, and structured source fields.

Allowed test stimuli:

- fixture `scene_assessment` fields;
- fixture `social_state_record` fields;
- fixture prior social-pressure state;
- fixture prior planner truth;
- fixture narrative-thread pressure metrics;
- module policy thresholds and source-score maps.

Forbidden primary oracles:

- generated narration wording;
- copied dialogue or scene prose;
- LLM-as-a-Judge pressure categories;
- frontend card shape;
- hardcoded Pi22/Table-B control labels in production logic outside reviewed
  canonical surfaces;
- duplicated policy truth in tests when the policy can be loaded.

## Implementation Anchors

- `content/modules/god_of_carnage/module.yaml`
- `ai_stack/social_pressure_contracts.py`
- `ai_stack/social_pressure_engine.py`
- `ai_stack/module_runtime_policy.py`
- `ai_stack/langgraph_runtime_state.py`
- `ai_stack/langgraph_runtime_executor.py`
- `ai_stack/runtime_aspect_ledger.py`
- `world-engine/app/story_runtime/commit_models.py`
- `world-engine/app/story_runtime/manager.py`
- `tools/mcp_server/tools_registry_handlers_langfuse_verify.py`
