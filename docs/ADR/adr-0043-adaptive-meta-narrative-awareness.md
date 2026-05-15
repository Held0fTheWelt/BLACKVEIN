# ADR-0043: Adaptive Meta-Narrative Awareness and Fourth-Wall Play

## Status

Accepted

## Date

2026-05-15

## Context

ADR-0042 introduced the first safe `meta_narrative_awareness` slice: opt-in,
actor-lane-gated, subtle, rare, and structurally validated. This ADR adds
adaptive in-world meta-awareness, broad fourth-wall play, and cross-session
self-awareness without turning meta-awareness into prompt/tool disclosure,
player-control claims, or invented memory.

ADR-0039 still applies: Pi / Π labels remain Capability Matrix index language
only. Runtime behavior must use semantic contracts, policy, structured events,
ledger evidence, and bounded memory references.

## Decision

World of Shadows extends `meta_narrative_awareness` with a v2 contract:

- `meta_narrative_awareness.v2`
- `meta_narrative_awareness_policy.v2`
- Story Runtime Experience gates:
  `meta_narrative_awareness_tier`,
  `meta_narrative_allow_direct_player_address`,
  `meta_narrative_allow_narrator_negotiation`,
  `meta_narrative_allow_cross_session_memory`,
  `meta_narrative_memory_retention_scope`, and
  `meta_narrative_max_direct_addresses_per_turn`.

The v2 aspect remains separate from `meta_control_turn`. It is a story-play
runtime aspect and only activates when module policy, Story Runtime Experience
settings, selected actor lanes, event budgets, and consent scope all align.

Adaptive awareness may use structured runtime signals such as social pressure,
dramatic irony, relationship state, semantic move records, and bounded
hierarchical memory references. It must not read raw prompts, tool names, model
names, hidden internal machinery, or raw private player text.

Cross-session self-awareness is represented through verified memory reference
ids supplied by bounded memory context. The model may reference only selected
memory ids; it must not invent remembered sessions or expose private player
data.

## Consequences

- The GoC module policy can allow `subtle`, `adaptive`, and `full` tiers while
  keeping `subtle` as the default.
- Direct player address is allowed only in the `full` tier and within the
  per-turn direct-address budget.
- Cross-session references require `selected_memory_ref_ids`; missing,
  unowned, fabricated, or private memory claims are recoverable validation
  failures before commit.
- `RuntimeAspectLedger.meta_narrative_awareness` records tier, adaptive signal
  codes, direct-address counts, memory refs, and failure codes.

## ADR-0039 Boundary

Tests must assert schema versions, policy normalization, opt-in settings,
selected memory ref ids, structured event validation, graph packet bounds, and
ledger projection. Generated fourth-wall prose, copied dialogue, and judge
labels are not pass/fail oracles.

## Implementation Anchors

- `ai_stack/meta_narrative_awareness_contracts.py`
- `ai_stack/meta_narrative_awareness_engine.py`
- `ai_stack/story_runtime_experience.py`
- `ai_stack/langgraph_runtime_executor.py`
- `ai_stack/runtime_aspect_ledger.py`
- `content/modules/god_of_carnage/module.yaml`
