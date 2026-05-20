# Meta-Narrative Awareness Contract

This contract binds active in-world meta-awareness. It is not the Meta/OOC
control path and it is not permission to disclose prompts, tools, model names,
runtime machinery, hidden facts, or private player data.

## Scope

`meta_narrative_awareness` is a story-play runtime aspect. In v1 it lets
selected characters subtly sense dramatic pattern or narrative pressure. In v2
it can also support adaptive in-world meta-awareness, direct fourth-wall
address, narrator negotiation, and bounded cross-session self-awareness when
module policy and Story Runtime Experience settings both opt in.

Out-of-character player input still uses `player_input_kind=meta` and
LangGraph `meta_control_turn`. That path skips retrieval, model invocation,
validation, commit, and story-state mutation.

## Activation

Activation requires all of the following:

- Module policy under `runtime_intelligence.meta_narrative_awareness`.
- `story_runtime_experience.meta_narrative_awareness_enabled=true`.
- v2 tier and scope settings, when used:
  `meta_narrative_awareness_tier`,
  `meta_narrative_allow_direct_player_address`,
  `meta_narrative_allow_narrator_negotiation`,
  `meta_narrative_allow_cross_session_memory`,
  `meta_narrative_memory_retention_scope`, and
  `meta_narrative_max_direct_addresses_per_turn`.
- At least one actor listed in
  `meta_narrative_characters_with_awareness`.
- The actor is also supported by module policy.
- The actor is selected for the current turn and is not the human/forbidden
  actor lane.
- The policy event budget is greater than zero.

The GoC module defaults to `subtle` / `rare`, but its v2 policy can allow
`adaptive` and `full` tiers when the session explicitly opts in. Requests
outside policy are clamped and recorded in rationale codes.

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
- `awareness_tier`
- `trigger_frequency`
- `selected_actor_ids`
- `allowed_awareness_modes`
- `forbidden_awareness_modes`
- `allowed_fourth_wall_levels`
- `max_events_per_turn`
- `max_direct_addresses_per_turn`
- `direct_player_address_allowed`
- `narrator_negotiation_allowed`
- `cross_session_memory_allowed`
- `selected_memory_ref_ids`
- `adaptive_signal_codes`
- `structured_event_field=meta_narrative_awareness_events`

It does not expose raw player text, hidden fact summaries, prompt text, tool
details, model names, or internal runtime mechanics. Cross-session
self-awareness is carried only by selected memory reference ids from bounded
memory context, not by raw memory text.

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

v2 direct/fourth-wall and memory events must remain structured:

```json
{
  "meta_narrative_awareness_events": [
    {
      "actor_id": "veronique",
      "awareness_mode": "direct_player_address",
      "fourth_wall_level": "full_fourth_wall",
      "direct_player_address": true,
      "memory_ref_ids": ["mem_return_1"],
      "player_agency_preserved": true,
      "system_disclosure_absent": true
    }
  ]
}
```

## Validation

`validate_meta_narrative_awareness_realization` rejects:

- events when the session did not opt in;
- actors outside `selected_actor_ids`;
- awareness modes outside the allowed policy set;
- forbidden modes such as system prompt disclosure, tool/model disclosure,
  player-control claims, or unbounded rewrite;
- direct full fourth-wall address in `subtle` mode;
- direct address when `direct_player_address_allowed=false`;
- fourth-wall levels outside `allowed_fourth_wall_levels`;
- cross-session memory references outside `selected_memory_ref_ids`;
- fabricated memory, private player data disclosure, or raw player text echo;
- event counts above `max_events_per_turn`.

Rejection is recoverable before commit and flows through
`validator_lane=meta_narrative_awareness_validation_v1`.

## ADR-0039 Boundary

Tests assert schema versions, normalized policy, opt-in settings, graph node
execution, structured event validation, and ledger projection. Generated prose,
copied dramatic lines, or judge labels are not pass/fail oracles. Pi / Π labels
remain Capability Matrix index vocabulary only.

## Anchors

- ADR: [`ADR-0042`](../../ADR/adr-0042-meta-narrative-awareness-opt-in.md),
  [`ADR-0043`](../../ADR/adr-0043-adaptive-meta-narrative-awareness.md)
- Contracts: `ai_stack/contracts/meta_narrative_awareness_contracts.py`
- Engine: `ai_stack/meta_narrative_awareness_engine.py`
- Graph: `ai_stack/langgraph/langgraph_runtime_executor.py`
- Policy: `content/modules/god_of_carnage/module.yaml`
