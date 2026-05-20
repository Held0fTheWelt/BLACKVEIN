# ADR-0059: Semantic NPC Motivation Score

## Status

Accepted

## Date

2026-05-20

## Related ADRs

- [ADR-0039](adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) — no Pi/Π runtime keys; no hardcoded oracle bypass.
- [ADR-0041](adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md) — semantic capability selection.
- [ADR-0058](adr-0058-director-driven-pulse-and-block-stream-bus.md) — Director-Pulse tick architecture; motivation score is the per-NPC input to initiative selection.
- [ADR-0061](adr-0061-director-pause-mode-for-gathering-interruption.md) — gathering_paused; motivation scoring continues during pause (shadow diagnostics).

## Context

Today NPC initiative is driven by the LDSS plan: the plan lists NPCs in an
initiative order determined by the scene planner before the turn begins. This
is not a live evaluation of who is currently most motivated — it is a pre-turn
batch assignment.

Phase 2 requires a per-tick, per-NPC motivation score so the Director can
decide, at the moment a tick fires, which NPC has the strongest motivation to
act now. This decision must be:

- **Principled-deterministic**: transparent inputs, transparent aggregation,
  no AI-judge call per tick (that would be expensive and non-reproducible).
- **Per-NPC**: each NPC gets its own score; no shared-pool or average.
- **Content-driven**: weights and thresholds come from `module.yaml` and
  `actor_pressure_profiles.yaml`; no literals hardcoded in Python.
- **Semantic**: input names are semantic capability names; no Pi/Π-numbered keys.
- **Diagnosable**: all sub-components are recorded, including below-threshold scores.

## Decision

### 1. Score formula

```
score(npc) = clamp(
    weighted_sum(
        scene_energy_contribution   * w_scene_energy,
        social_pressure_contribution * w_social_pressure,
        relationship_axis_pressure  * w_relationship_dynamics,
        narrative_momentum_contribution * w_narrative_momentum,
    ) * (0.5 + pressure_baseline * 0.5),
    0.0, 1.0
)
```

The `pressure_baseline` per NPC is derived from `actor_pressure_profiles.yaml`
(number and density of `pressure_markers`), not from hardcoded constants. It
acts as a multiplier on the weighted score, not a fifth addend — so a highly-
motivated NPC in a low-pressure scene still needs actual scene signals to cross
threshold.

### 2. Weights

Weights are loaded from `module.yaml.runtime_intelligence.npc_motivation_score.score_weights`.
No weight is hardcoded in Python. The keys are semantic names:

- `scene_energy`
- `social_pressure`
- `relationship_axis_pressure`
- `narrative_momentum`

Weights are normalized to sum to 1.0 before use.

### 3. Threshold

```
threshold(npc) = clamp(base_threshold * actor_pressure_modifier(npc), 0.0, 1.0)
```

- `base_threshold` — from `module.yaml.runtime_intelligence.npc_motivation_score.base_threshold`.
- `actor_pressure_modifier(npc)` — from
  `module.yaml.runtime_intelligence.npc_motivation_score.actor_pressure_modifiers[npc_id]`.
  Default is `1.0` (neutral). Values `< 1.0` lower the threshold (NPC speaks
  readily); values `> 1.0` raise it (NPC waits longer).

The code reads `actor_pressure_modifiers` as a generic dict; it does not
branch on specific NPC IDs. Content YAML supplies the values.

### 4. Initiative selection

```
initiative(npc_ids) = argmax(score(npc) for npc in npc_ids if score(npc) >= threshold(npc))
                   or None if no npc crosses threshold
```

- No speaker queue.
- No roundtable rotation.
- No fixed turn-order roster.
- If nobody crosses threshold → Director emits silence (`chosen_action_kind: "silence"`).
- Initiative changes tick-to-tick as scores change.

### 5. Contract: `npc_motivation_score.v1`

One record per NPC per tick. Below-threshold NPCs are included in the output.

| Field | Type | Notes |
|---|---|---|
| `schema_version` | `"npc_motivation_score.v1"` | constant |
| `npc_id` | string | actor ID |
| `tick_id` | UUID string | references the tick |
| `score` | float 0..1 | normalized combined score |
| `score_components` | dict[str, float] | semantic sub-scores |
| `threshold` | float 0..1 | threshold used for this NPC this tick |
| `crossed_threshold` | bool | `score >= threshold` |
| `source_capabilities` | list[str] | semantic names of inputs used; **no Pi/Π IDs** |

`score_components` keys:

- `scene_energy`
- `social_pressure`
- `relationship_axis_pressure`
- `narrative_momentum`
- `pressure_baseline`

### 6. Inputs: semantic capability output extraction

Each semantic input is extracted from the structured output dict of the
corresponding runtime capability. No field name in the extraction logic may
contain Pi/Π-numbered keys. Extraction falls back to neutral defaults
(`0.50`) if structured output is absent or malformed.

| Input | Source dict field (semantic) | Fallback |
|---|---|---|
| `scene_energy` | `energy_level`, `score` | 0.50 |
| `social_pressure` | `score`, `band` | 0.50 |
| `relationship_axis_pressure` | per-NPC pair tension from `pair_states` | 0.50 |
| `narrative_momentum` | `score`, `state` | 0.50 |
| `pressure_baseline` | derived from `actor_pressure_profiles.profiles[npc_id].pressure_markers` count | 0.50 |

### 7. No LLM call per tick

The motivation score is computed by a pure Python function. No AI model is
invoked during score evaluation. This keeps tick latency negligible and results
deterministic for the same inputs.

### 8. Diagnostics

All `npc_motivation_score.v1` records are included in the shadow-path output
regardless of threshold crossing. This lets an operator or test see exactly
why a given NPC was selected (or not selected) for initiative on any tick.

### 9. Stage F — three-tier source classification (closed enum)

Phase 2 Stage F (ADR-0058 §"Stage F") adds a per-component **source
classification** that records, for every tick, *where* each motivation
component's signal came from. The classification is a closed enum with
exactly three labels:

| Source label | Meaning |
|---|---|
| `real_runtime_signal` | A structured runtime capability output was supplied for this component (e.g. `scene_energy_output`, `social_pressure_output`, `relationship_state_output`, `narrative_momentum_output`) and was used directly. |
| `module_policy_default` | No structured runtime output was supplied for this component, but the module policy provided a usable default (e.g. weight values from `module.yaml.runtime_intelligence.npc_motivation_score.score_weights`, or actor pressure markers from `actor_pressure_profiles.yaml`). |
| `missing_signal` | Neither a structured runtime output nor a module-policy default was available; the engine fell back to a neutral mid-range constant (`0.50`). |

Implementation: `ai_stack/phase2_stream_readiness.classify_motivation_component_sources()`.
The autonomous-tick coordinator
(`ai_stack/phase2_autonomous_tick.AutonomousTickOutcome`) surfaces:

- `motivation_score_component_sources: dict[str, str]` — one label per
  component (`scene_energy`, `social_pressure`,
  `relationship_axis_pressure`, `narrative_momentum`,
  `pressure_baseline`).
- `capability_outputs_used: list[str]` — Stage F surfaces that were
  actually supplied for this tick.
- `capability_outputs_missing: list[str]` — Stage F surfaces that were
  absent for this tick.

The same labels are forwarded to the WS `autonomous_tick_evaluated`
summary, the `diagnostics.director_pulse.motivation_score_sources`
field, and the
`diagnostics.phase2_event_stream_readiness.motivation_score_sources`
readiness surface.

### 10. Initiative discipline (closed-enum invariants)

The motivation-score engine never:

- maintains a speaker queue, roundtable rotation, or fixed turn-order
  roster;
- branches on hardcoded NPC IDs (the engine reads
  `actor_pressure_modifiers` as a generic dict);
- promotes an NPC below the resolved threshold;
- fakes a `real_runtime_signal` label when the structured runtime
  output is absent — the source label degrades through
  `module_policy_default` to `missing_signal` rather than asserting
  evidence the engine did not see.

Silence is the *active*, recorded outcome when no NPC crosses
threshold. The director tick decision carries
`chosen_action_kind="silence"` and a closed-enum `silence_reason`
(`no_npc_above_motivation_threshold`,
`gathering_paused_off_stage_only`, or `director_chose_silence`).

## Consequences

**Positive:**

- Score is transparent and reproducible: same inputs → same score.
- Threshold is content-driven, not hardcoded; a new module supplies its own values.
- Per-NPC granularity is fully observable; no aggregate-only reporting.
- Below-threshold scores are retained for retrospective analysis.
- No AI call per tick: inexpensive and suitable for frequent evaluation.

**Negative / Trade-offs:**

- Pressure baseline is derived from a heuristic (marker count); a future content
  change might add a more explicit `pressure_baseline_score` field to
  `actor_pressure_profiles.yaml`.
- The relationship_axis_pressure extraction requires structured `pair_states` in
  the relationship_dynamics output; if that output is absent, the fallback is
  neutral (0.50) which reduces NPC differentiation in relationship-heavy scenes.

## Implementation

- `ai_stack/npc_motivation_score_engine.py` — `compute_npc_motivation_scores()` and
  `select_initiative_actor()`.
- `ai_stack/phase2_stream_readiness.py` —
  `classify_motivation_component_sources()` and
  `classify_capability_availability()` (Stage F three-tier source
  labelling).
- `ai_stack/phase2_autonomous_tick.py` — surfaces
  `motivation_score_component_sources`,
  `capability_outputs_used`, and `capability_outputs_missing` on
  every `AutonomousTickOutcome`.
- `content/modules/god_of_carnage/module.yaml` — `runtime_intelligence.npc_motivation_score`
  section with weights, base_threshold, and actor_pressure_modifiers.
- `ai_stack/tests/test_phase2_director_pulse.py` — `TestNpcMotivationScoreEngine`,
  `TestInitiativeSelection`.
- `ai_stack/tests/test_phase2_stage_f_capability_feeding.py` —
  Stage F capability feeding and source-label classification tests.
