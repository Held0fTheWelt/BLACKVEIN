# Live Play Correction and Fallbacks

## Problem statement

A governed runtime is not enough if rejection produces dead turns.
Live play needs a recovery path that preserves continuity without silently granting the model full freedom.

The runtime therefore needs a layered recovery model:

1. generate normally
2. validate
3. when invalid, build actionable validation feedback
4. retry with correction context
5. when still invalid, emit a guaranteed safe fallback

## Recovery flow

```text
player input
  -> build scene packet
  -> model generation (attempt 1)
  -> validate
     -> valid: commit and return
     -> invalid:
          -> build validation feedback
          -> corrected generation (attempt 2)
          -> validate
             -> valid: commit and return
             -> invalid:
                  -> generate safe fallback
                  -> validate fallback
                  -> commit fallback and emit runtime-health event
```

## Why corrective retry matters

Blind retry is too weak.
The model needs to know:

- what rule was violated
- what content was illegal
- which alternatives are legal
- what must be preserved if possible

This keeps retries intense and targeted instead of limp and random.

## Validation feedback shape

```python
class ValidationFeedback(BaseModel):
    passed: bool
    violations: list[ValidationViolation]
    corrections_needed: list[str]
    legal_alternatives: dict[str, list[str]]
```

Example:

```json
{
  "passed": false,
  "violations": [
    {
      "violation_type": "policy_violation",
      "specific_issue": "Physical violence violates scene policy",
      "rule_violated": "scene_02_policy.violence_threshold=verbal_only",
      "suggested_fix": "Keep confrontation verbal; use raised voice, cutting remarks, or cold withdrawal."
    }
  ],
  "corrections_needed": [
    "Remove physical violence",
    "Preserve emotional intensity",
    "Use only legal verbal confrontation triggers"
  ],
  "legal_alternatives": {
    "triggers": ["verbal_aggression", "emotional_breakdown", "confrontation_escalation"]
  }
}
```

## Safe fallback generation

Safe fallback is not a generic error string.
It is package-defined degraded content that is:

- always legal
- zero-risk on state mutation unless explicitly allowed
- narratively acceptable enough to keep play alive

### Minimum fallback rules
- no illegal triggers
- no illegal responders
- no unvalidated state effects
- no raw system commentary
- no player-facing "validation failed" message

### Scene fallback selection order
1. actor-specific safe reaction from package
2. scene stall phrase
3. scene redirect phrase
4. generic safe line

## Compiler requirements for fallback content

The package compiler should:
- validate that each included scene has fallback content
- generate default fallback bundles when authored fallback content is missing
- warn clearly when defaults were auto-generated

This prevents live runtime from depending on perfect authored coverage.

## Runtime health telemetry

Every corrective retry and safe fallback should produce structured telemetry.

Track:
- module and scene
- failure types
- attempt count
- chosen recovery strategy
- latency impact
- whether the turn ultimately required safe fallback

This telemetry feeds:
- admin runtime-health page
- notification thresholds
- research inputs for revision candidates

## Operator interpretation

High corrective retry with low safe fallback:
- runtime is surviving, but the package or policy may be too brittle

High safe fallback:
- live experience is degrading materially
- investigate scene policy, legality table, actor mind, or fallback quality

## Minimal implementation stance

Corrective retry and safe fallback belong in the MVP foundation because they close the last operational gap between:
- formally validated runtime
- actually playable live system
