# Evaluation and Quality Gates

## Principle

Evaluation is not an afterthought.
It decides whether preview content is safe and useful enough to promote, and it should also expose whether live execution is staying in the high-quality path or degrading too often.

## Evaluation run types

- `golden` — regression baseline against canonical expected behavior
- `preview` — compares preview package to active package
- `rollback_verification` — verifies rollback target still behaves acceptably
- `preview_branching` — optional simulated multi-turn branch comparison for preview vs active

## Required scoring dimensions

- `policy_compliance_score`
- `actor_consistency_score`
- `trigger_accuracy_score`
- `drift_score`
- `regression_risk_score`
- `improvement_effect_score`

## Live execution quality dimensions

For production visibility, the system should also track:

- `first_pass_success_rate`
- `corrective_retry_rate`
- `safe_fallback_rate`

These are not only operational metrics.
They are quality signals.
A scene that is constantly falling back is narratively unhealthy even if the runtime never crashes.

## Hard gate rules

A preview package may only be promotable when:
- compliance is above configured threshold
- regression risk is below configured threshold
- no hard policy failures occur
- no invalid trigger emissions occur
- required evaluation coverage minimum is met
- approval workflow reached promotable state

## Coverage metrics

Coverage should answer:
- which scenes have no evaluation scenarios
- which triggers are never tested
- which actors are underrepresented
- which policy branches remain unexercised

## Coverage report example

```json
{
  "module_id": "god_of_carnage",
  "package_version": "2.1.4-preview-03",
  "coverage_percentage": 0.71,
  "missing_scene_refs": ["scene_04_confrontation"],
  "missing_trigger_refs": ["hidden_truth_discovered"],
  "missing_actor_refs": ["alain"],
  "missing_policy_refs": ["scene_04.escalation_window"]
}
```

## Delta-aware evaluation

Preview evaluation should compare preview package against the active baseline and answer:

- did compliance improve or worsen
- did actor consistency improve or worsen
- did trigger accuracy change
- did drift increase
- is there any sign of overfitting to a narrow scenario band
- did first-pass success improve or worsen
- did corrective retry rate increase
- did safe fallback rate increase

## Promotion-readiness summary

Each preview package should have a derived readiness view:

```python
class PromotionReadiness(BaseModel):
    module_id: str
    preview_id: str
    preview_package_version: str
    evaluation_run_id: str | None = None

    package_validation_passed: bool
    workflow_ready: bool
    conflicts_resolved: bool
    compliance_gate_passed: bool
    regression_gate_passed: bool
    coverage_gate_passed: bool

    is_promotable: bool
    blocking_reasons: list[str]
```

## Runtime-health-aware quality interpretation

A package may still be considered unhealthy even when hard gates pass if:
- safe fallback rate is meaningfully elevated in a critical scene
- corrective retry rate clusters around a newly changed policy layer
- contradiction warnings increase after a preview promotion

These signals should route back into research and revision generation.

## Evaluation suite additions in `ai_stack`

```text
ai_stack/
  narrative/
    evaluation/
      golden_runs.py
      preview_comparator.py
      delta_metrics.py
      coverage_tracker.py
      promotion_readiness.py
      live_quality_metrics.py
      preview_branching.py
```

## Semantic validator implementation note

`SCHEMA_PLUS_SEMANTIC` should be implemented as a bounded secondary validation pass rather than an open-ended rewrite loop.

Recommended pattern:
1. run deterministic schema and legality checks first
2. when configured, run a bounded semantic verdict call against:
   - proposed effects
   - scene constraints
   - effective policy
   - contradiction-sensitive state
3. return machine-usable violations, not prose-only commentary

This keeps semantic validation inspectable and suitable for corrective feedback generation.
