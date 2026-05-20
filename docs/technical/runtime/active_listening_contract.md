# Active Listening Contract

This document binds the bounded Pi34 active-listening runtime surface. It is a
local/partial contract for structured player-input understanding, committed
memory continuity, and model-visible prompt authority. It is not a claim of
live/staging proof, broad production NLU gating, generated dialogue
understanding, or changed commit/readiness authority.

## Runtime Surface

The active runtime derives three semantic aspect records:

- `broad_nlu_listening.v1`: structured discourse evidence from
  `interpreted_input` and, when available, `semantic_move_record`. It records
  `primary_discourse_act`, `player_input_kind`, confidence, ambiguity/repair
  signals, response expectation, target/object refs, and source refs. It does
  not store raw player input.
- `conversational_memory.v1`: bounded continuity evidence from
  `hierarchical_memory_context`. It exposes selected tier ids and selected
  committed memory refs only. It does not store raw player input or raw prompt
  text.
- `prompt_authority.v1`: a model-visible authority packet declaring which
  structured sections may constrain generation. It names source refs,
  selected/observed capabilities, selected memory refs, and forbidden
  inferences. It must not mutate commit gates, readiness gates, or validation
  outcomes.

`ai_stack/langgraph/langgraph_runtime_executor.py` places these records into the
dramatic generation packet and model prompt, then writes them to
`RuntimeAspectLedger` as `broad_nlu_listening`, `conversational_memory`, and
`prompt_authority`.

## Authority Boundary

These records help the model listen to the player's move without stealing the
player lane or inventing continuity. They are diagnostic/envelope evidence, not
commit authority. The existing input, action-resolution, actor-lane,
validation, and commit seams remain authoritative for session truth.

Forbidden uses:

- treating raw player input as durable memory truth;
- treating generated prose as a validator oracle;
- disclosing prompt, tool, or model internals;
- claiming unverified memories;
- reclassifying a player turn as an NPC turn because an NPC response is
  expected.

## ADR-0039 Boundary

Tests and gates use schema constants, structured fields, source refs,
RuntimeAspectLedger projection, and prompt-packet presence as oracles.
Generated dialogue quality, copied example prose, Pi-number runtime keys, and
LLM-as-a-judge claims are not valid pass/fail evidence.

Primary implementation anchors:

- `ai_stack/active_listening_contracts.py`
- `ai_stack/langgraph/langgraph_runtime_executor.py`
- `ai_stack/runtime_aspect_ledger.py`
- `ai_stack/capabilities/capability_selector.py`
- `ai_stack/capabilities/capability_validator_plan.py`
- `ai_stack/capabilities/capability_validator_registry.py`
