# ADR-0042: Opt-in Meta-Narrative Awareness Runtime Aspect

## Status

Accepted

## Date

2026-05-15

## Context

Capability Matrix index Π25 historically grouped two different ideas under
"meta-awareness":

- Out-of-world player control input, now implemented as `player_input_kind=meta`
  and LangGraph `meta_control_turn`.
- In-world, character-level awareness of dramatic structure, which is higher
  risk because it can easily disclose prompts, tools, model mechanics, hidden
  facts, or seize control of player intention.

ADR-0039 also requires that legacy Pi / Π labels remain historical index
vocabulary only. Runtime code must use semantic names, contract fields,
validators, and ledger evidence.

## Decision

World of Shadows implements the first active in-world slice as
`meta_narrative_awareness`, a separate opt-in runtime aspect.

The aspect is distinct from `meta_control_turn`:

- `meta_control_turn` handles out-of-character control input and skips the
  story path.
- `meta_narrative_awareness` is a story-play runtime aspect derived on the full
  graph path before context synthesis and model routing.

Activation requires both module support and resolved Story Runtime Experience
opt-in:

- Module policy: `runtime_intelligence.meta_narrative_awareness`.
- Session/operator settings:
  `meta_narrative_awareness_enabled`,
  `meta_narrative_awareness_intensity`,
  `meta_narrative_trigger_frequency`,
  `meta_narrative_characters_with_awareness`.
- Actor eligibility: selected actors must be configured, module-supported, and
  not in the human/forbidden actor lane.

The first accepted production slice is deliberately narrow:

- Allowed intensity for the GoC module is `subtle`.
- Allowed frequency is `rare`.
- Supported actor set is module policy data, not runtime hardcoding.
- Structured output evidence uses `meta_narrative_awareness_events`.
- Validation rejects unauthorized actors, forbidden modes, system/tool/model
  disclosure, direct full fourth-wall address in subtle mode, and unbounded
  rewrite/player-control claims.

## Consequences

- The dramatic packet may expose bounded opt-in context under
  `meta_narrative_awareness`.
- `RuntimeAspectLedger` owns the per-turn projection as
  `meta_narrative_awareness`.
- Validation can reject and retry recoverable violations before commit.
- Adaptive fourth-wall dialogue, narrator negotiation, and bounded
  cross-session self-awareness are governed by ADR-0043 when the v2 policy and
  Story Runtime Experience opt-in are active. Broad authoring cognition,
  prompt/tool/model disclosure, and player-control claims remain out of scope.

## ADR-0039 Boundary

Tests for this aspect must assert policy normalization, opt-in gating,
structured event validation, graph node execution, and ledger projection.
Generated prose is not an oracle. Pi / Π labels must not appear in production
runtime identifiers, score names, schema keys, routing keys, or branch logic.

## Implementation Anchors

- `ai_stack/contracts/meta_narrative_awareness_contracts.py`
- `ai_stack/story_runtime/narrative/meta_narrative_awareness_engine.py`
- `ai_stack/story_runtime/story_runtime_experience.py`
- `ai_stack/module_runtime_policy.py`
- `ai_stack/langgraph/langgraph_runtime_executor.py`
- `ai_stack/story_runtime/runtime_aspect_ledger/__init__.py`
- `content/modules/god_of_carnage/module.yaml`

## Validation Evidence

- `PYTHONPATH=. python -m py_compile ai_stack/contracts/meta_narrative_awareness_contracts.py ai_stack/story_runtime/narrative/meta_narrative_awareness_engine.py ai_stack/story_runtime/story_runtime_experience.py ai_stack/module_runtime_policy.py ai_stack/story_runtime/runtime_aspect_ledger/__init__.py ai_stack/langgraph/langgraph_runtime_state.py ai_stack/langgraph/langgraph_runtime_executor.py`
- `PYTHONPATH=. pytest ai_stack/tests/test_meta_narrative_awareness_engine.py tests/integration/test_story_runtime_experience.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_langgraph_runtime.py -q -s`
