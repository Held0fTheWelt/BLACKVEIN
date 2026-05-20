# Subtext Interpretation Contract

Status: Canonical technical contract for the bounded GoC Pi19 subtext surface.

## Purpose

Subtext interpretation describes the gap between what a player move appears to do on the surface and what dramatic function it may carry in the current scene. It is a bounded diagnostic and shaping surface, not a truth engine and not a free-form psychology model.

The runtime uses subtext to make semantic move handling more legible:

- surface mode: what the player move looks like socially,
- hidden-intent hypothesis: the bounded dramatic hypothesis the planner is allowed to carry,
- subtext function: the scene-pressure function used by the director and generation packet,
- sincerity band: a small label for how direct or double-edged the move appears,
- evidence codes: bounded rule and feature provenance for tests and operator traces.

## Authority

Subtext records are advisory until validation and commit. They may shape responder selection, pacing, model packet context, Langfuse traces, and operator diagnostics. They must not:

- mutate canonical story truth,
- reveal hidden NPC truth directly,
- override validation or commit,
- become a second memory or fact store,
- treat generated prose as an oracle.

## Runtime Shape

`SemanticMoveRecord.subtext` carries the Pi19 payload:

```json
{
  "contract": "subtext_interpretation.v1",
  "surface_mode": "accusation|apology|alliance_bid|courtesy|deflection|escalation|exposure|neutral|off_scope|question|reveal|silence",
  "explicit_intent": "string|null",
  "hidden_intent_hypothesis": "avoid_accountability|force_accountability|force_admission|humiliate_or_expose|preserve_relationship|raise_pressure|seek_alliance|seek_repair|slice_boundary|test_boundary|test_motive|unknown",
  "subtext_function": "contain_off_scope|deflect_accountability|expose_truth|force_accountability|preserve_dignity|preserve_relationship|probe_motive|raise_pressure|reveal_under_repair|shift_alliance|test_boundary|unset",
  "sincerity_band": "high|low|mixed|unknown",
  "evidence_codes": ["bounded_rule_or_feature_code"],
  "policy_source": "content/modules/god_of_carnage/direction/subtext_policy.yaml",
  "policy_rule_id": "string"
}
```

The allowed values are declared in `content/modules/god_of_carnage/direction/subtext_policy.yaml` and mirrored by the bounded contract constants in `ai_stack/contracts/semantic_move_contract.py`. Runtime code must not invent labels outside those sets.

## Flow

1. `god_of_carnage_semantic_move_interpretation.py` classifies the player move and builds `SubtextRecord` from `god_of_carnage_subtext_policy.py`.
2. `god_of_carnage_scene_director.py` reads `semantic_move_record.subtext` for director resolution evidence and selected pacing pressure.
3. `langgraph_runtime_executor.py` serializes `subtext_interpretation` into the dramatic generation packet and adds subtext rationale codes.
4. `world-engine/app/story_runtime/manager.py` projects subtext into path summaries, Langfuse spans, deterministic scores, and score metadata.
5. Backend inspector and operator-history services surface the same fields for diagnostics.

## ADR-0039 Boundary

Gate and regression tests for this contract must derive expected labels from `subtext_policy.yaml` or from the exported contract constants. Tests may use literal player-input stimuli, but pass/fail must target policy-derived fields, schema membership, reason codes, trace propagation, score values, or inspector projection.

Forbidden primary oracles:

- generated narration wording,
- copied scene prose,
- free-form descriptions of hidden motives,
- hardcoded subtext labels that duplicate the policy instead of loading it.

## Implementation Anchors

- `content/modules/god_of_carnage/direction/subtext_policy.yaml`
- `ai_stack/story_runtime/semantic_planner/god_of_carnage_subtext_policy.py`
- `ai_stack/contracts/semantic_move_contract.py`
- `ai_stack/story_runtime/semantic_planner/god_of_carnage_semantic_move_interpretation.py`
- `ai_stack/story_runtime/director/god_of_carnage_scene_director.py`
- `ai_stack/langgraph/langgraph_runtime_executor.py`
- `world-engine/app/story_runtime/manager.py`
- `backend/app/services/inspector/inspector_turn_projection_assembly_helpers.py`
- `backend/app/services/story_runtime/operator_turn_history_service.py`
