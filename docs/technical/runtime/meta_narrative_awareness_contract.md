# Meta-Narrative Awareness Contract

This contract binds the first active in-world meta-awareness slice. It is not
the Meta/OOC control path and it is not full fourth-wall play.

## Scope

`meta_narrative_awareness` is a story-play runtime aspect. It lets selected
characters subtly sense dramatic pattern or narrative pressure when the module
supports it and the resolved Story Runtime Experience settings opt in.

Out-of-character player input still uses `player_input_kind=meta` and
LangGraph `meta_control_turn`. That path skips retrieval, model invocation,
validation, commit, and story-state mutation.

## Activation

Activation requires all of the following:

- Module policy under `runtime_intelligence.meta_narrative_awareness`.
- `story_runtime_experience.meta_narrative_awareness_enabled=true`.
- At least one actor listed in
  `meta_narrative_characters_with_awareness`.
- The actor is also supported by module policy.
- The actor is selected for the current turn and is not the human/forbidden
  actor lane.
- The policy event budget is greater than zero.

The GoC module currently allows only `subtle` intensity and `rare` trigger
frequency. Requests for wider intensity/frequency are clamped into policy and
recorded in rationale codes.

## Runtime Path

Story-play path:

```text
derive_dramatic_irony
-> derive_relationship_state
-> derive_meta_narrative_awareness
-> synthesize_context
-> assemble_model_context
```

`derive_meta_narrative_awareness` writes
`meta_narrative_awareness_target` to `RuntimeTurnState` and records
`RuntimeAspectLedger.meta_narrative_awareness`.

## Model-Visible Context

The dramatic generation packet includes only bounded structural context:

- `intensity`
- `trigger_frequency`
- `selected_actor_ids`
- `allowed_awareness_modes`
- `forbidden_awareness_modes`
- `max_events_per_turn`
- `structured_event_field=meta_narrative_awareness_events`

It does not expose raw player text, hidden fact summaries, prompt text, tool
details, model names, or internal runtime mechanics.

## Structured Events

When realized, the model should emit:

```json
{
  "meta_narrative_awareness_events": [
    {
      "actor_id": "veronique",
      "awareness_mode": "dramatic_pattern_sense",
      "fourth_wall_level": "subtle",
      "direct_player_address": false
    }
  ]
}
```

No event is required every turn. If no event is emitted while the target is
active, validation approves the aspect as unused.

## Validation

`validate_meta_narrative_awareness_realization` rejects:

- events when the session did not opt in;
- actors outside `selected_actor_ids`;
- awareness modes outside the allowed policy set;
- forbidden modes such as system prompt disclosure, tool/model disclosure,
  player-control claims, or unbounded rewrite;
- direct full fourth-wall address in `subtle` mode;
- event counts above `max_events_per_turn`.

Rejection is recoverable before commit and flows through
`validator_lane=meta_narrative_awareness_validation_v1`.

## ADR-0039 Boundary

Tests assert schema versions, normalized policy, opt-in settings, graph node
execution, structured event validation, and ledger projection. Generated prose,
copied dramatic lines, or judge labels are not pass/fail oracles. Pi / Π labels
remain Capability Matrix index vocabulary only.

## Anchors

- ADR: [`ADR-0042`](../../ADR/adr-0042-meta-narrative-awareness-opt-in.md)
- Contracts: `ai_stack/meta_narrative_awareness_contracts.py`
- Engine: `ai_stack/meta_narrative_awareness_engine.py`
- Graph: `ai_stack/langgraph_runtime_executor.py`
- Policy: `content/modules/god_of_carnage/module.yaml`
