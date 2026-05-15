# Tonal Consistency Contract

`tonal_consistency` is a bounded local runtime-aspect surface for tonal drift
evidence. It is not a hard live drift loop, not a replacement for
`voice_consistency`, and not an LLM-as-a-Judge promotion gate.

## Contract

- Policy is declared under `runtime_intelligence.tonal_consistency` and
  normalized by `ModuleRuntimePolicy`.
- The runtime target is `tonal_consistency.v1`: selected profile id, target and
  required tone-dimension ids, allowed registers, forbidden marker classes, and
  diagnostic/recover/reject behavior.
- Validation consumes structured `tonal_consistency_classification` plus
  policy-declared forbidden marker classes.
- Runtime evidence projects through `RuntimeAspectLedger.tonal_consistency` and
  MCP `tonal_consistency_*` matrix fields.

## Runtime Fields

Policy fields:

- `tone_profiles`
- `default_profile_id`
- `profile_by_scene_function`
- `allowed_registers`
- `forbidden_genre_labels`
- `forbidden_marker_map`
- `require_structured_classification`
- `min_required_dimensions_present`
- `max_forbidden_marker_hits`
- `default_drift_behavior`

Target fields:

- `profile_id`
- `target_dimension_ids`
- `required_dimension_ids`
- `allowed_registers`
- `forbidden_genre_labels`
- `forbidden_marker_map`
- `scene_function`
- `pressure_band`
- `source_evidence`
- `rationale_codes`

Validation fields:

- `structured_classification_present`
- `realized_dimension_ids`
- `missing_required_dimension_ids`
- `register_label`
- `genre_label`
- `forbidden_marker_hits`
- `marker_hit_count`
- `contract_pass`
- `failure_codes`

## Current Scope

The current implementation is local contract evidence:

- `ai_stack/tonal_consistency_contracts.py`
- `ai_stack/tonal_consistency_engine.py`
- `ModuleRuntimePolicy.runtime_governance_policy.tonal_consistency`
- `RuntimeAspectLedger.tonal_consistency`
- MCP runtime-aspect matrix fields named `tonal_consistency_*`
- GoC module policy in `content/modules/god_of_carnage/module.yaml`

The generation/runtime orchestration does not yet derive or validate this
aspect in the authoritative live LangGraph turn path. The default drift
behavior for the GoC policy is `diagnostic`, so local tonal findings do not
become commit/readiness authority by themselves.

## Relationship To Voice

`voice_consistency` checks actor-specific speech profile consistency and can
reject forbidden language markers or strict cross-actor semantic voice drift.
`tonal_consistency` checks turn-level tonal target evidence: tone dimensions,
register, genre drift, and policy-declared marker classes. The two aspects may
share source content, but they answer different questions and expose separate
ledger/MCP fields.

## Diagnostics

Diagnostics should use structured fields:

- `turn_aspect_ledger.tonal_consistency.expected.policy_present`
- `turn_aspect_ledger.tonal_consistency.expected.policy_enabled`
- `turn_aspect_ledger.tonal_consistency.selected.profile_id`
- `turn_aspect_ledger.tonal_consistency.selected.required_dimension_ids`
- `turn_aspect_ledger.tonal_consistency.actual.realized_dimension_ids`
- `turn_aspect_ledger.tonal_consistency.actual.structured_classification_present`
- `turn_aspect_ledger.tonal_consistency.actual.marker_hit_count`
- `turn_aspect_ledger.tonal_consistency.actual.contract_pass`
- `turn_aspect_ledger.tonal_consistency.actual.failure_codes`
- `tonal_consistency_policy_present`
- `tonal_consistency_target_selected`
- `tonal_consistency_classification_present`
- `tonal_consistency_marker_hits_absent`
- `tonal_consistency_contract_pass`
- `tonal_consistency_failure_codes`

Operator and frontend surfaces may display these backend-provided fields. They
must not infer tonal correctness from visible prose, judge labels, card layout,
or voice-profile results.

## ADR-0039 Boundary

Tests assert schema constants, normalized policy, target dimensions, structured
classification, marker-class counts, ledger projection, and MCP fields. They do
not match generated narration, copied dialogue, or judge categories as oracles.

Allowed test stimuli:

- normalized module policy;
- fixture scene-plan, scene-energy, pacing, and social-pressure records;
- fixture structured `tonal_consistency_classification`;
- policy-declared marker classes;
- ledger and MCP projection fields.

Forbidden primary oracles:

- generated narration wording;
- copied dialogue examples;
- `goc_tone_fidelity_judge` or other LLM-as-a-Judge categories;
- active Pi / Π control-flow keys;
- duplicated policy truth in tests when the policy can be loaded or normalized.

## Promotion Boundary

This slice remains local/partial evidence. Moving beyond partial requires an
ADR-0009 promotion update with deterministic evidence, evaluator baselines,
staging/live traces, and explicit readiness coupling.
