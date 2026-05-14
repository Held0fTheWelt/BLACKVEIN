# LLM-as-a-Judge — Canonical Evaluator Definitions

This directory is the **canonical source of truth** for the World of Shadows
LLM-as-a-Judge categorical evaluators that score Langfuse traces.

Per [ADR-0040](../ADR/adr-0040-quality-lab-mcp-runtime-diagnostics.md), each
evaluator lives in its own `<evaluator_name>.md` file with structured YAML
frontmatter and a fixed body. Code mirrors are derived from this directory;
the directory is not derived from code.

The legacy CSV (`LLM-as-a-Judge Definition Table - Judges.csv`) remains
alongside as a frozen historical export and may diverge from the per-evaluator
files. **The per-evaluator `.md` files are authoritative.**

## File format

```yaml
---
name: <evaluator_name>
group: <evaluator_group>
score_type: categorical
categories:
  - <cat>             # ORDER MATTERS — this is the order shown to Langfuse
  - <cat>
severity:
  positive: [<cat>, ...]
  weak: [<cat>, ...]
  failure: [<cat>, ...]
  neutral: [<cat>, ...]                  # often empty; e.g. not_applicable
  insufficient_evidence: [<cat>, ...]    # only newer 6-tier judges
suggested_repair_areas:
  - <area>
---
```

Body sections (markdown headings, all required):

- `## Purpose` — short qualitative description. May be German because most
  evaluators were authored that way; English is also acceptable.
- `## Prompt` — exact prompt text fed to the judge model. **English.**
- `## Score reasoning prompt` — short rationale prompt.
- `## Category selection prompt` — single-line category-pick prompt.

## Evaluator groups

| Group | Evaluators (current) |
|-------|----------------------|
| Opening quality | `opening_experience_judge`, `role_anchor_quality_judge` |
| Turn relevance | `turn_relevance_judge` |
| Player action resolution | `player_action_intent_judge`, `player_action_resolution_judge`, `affordance_plausibility_judge` |
| Authority and origin | `narrator_authority_judge`, `npc_authority_violation_judge`, `npc_reaction_appropriateness_judge`, `visible_origin_consistency_judge` |
| Actor-lane/narrative boundary | `narrator_npc_boundary_judge`, `actor_lane_narrative_violation_judge` |
| Dramatic runtime realization | `beat_realization_judge`, `dramatic_capability_realization_judge`, `relationship_pressure_judge`, `dramatic_pacing_judge` |
| Recovery and playability | `blocked_action_playability_judge`, `recoverable_outcome_quality_judge`, `player_turn_playability_judge` |
| RAG/content usefulness | `rag_context_usefulness_judge` |
| Language/style/cleanliness | `language_consistency_judge`, `visible_card_cleanliness_judge`, `theatrical_style_judge`, `goc_tone_fidelity_judge` |
| Runtime aspect integrity | `runtime_aspect_integrity_judge` |

## Severity bucket conventions

- `positive` — the result the runtime should aim for (`strong_*`,
  `excellent`, `consistent`, `playable_*`, `realized_correctly`, etc.).
- `weak` — usable but underdeveloped (`acceptable_*`, `serviceable_*`,
  `mostly_*`, `partially_*`).
- `failure` — clearly wrong, broken, or unplayable (`invalid`, `wrong_*`,
  `unplayable`, `clear_violation`, `not_realized`, `failed_recovery`,
  `contradictory`, `broken_*`).
- `neutral` — usually `not_applicable`: the evaluator does not apply to
  this generation. Not a failure.
- `insufficient_evidence` — only on newer 6-tier judges; means the
  evaluator cannot judge from the given evidence. Not a failure.

## Drift policy

A test in `ai_stack/tests/test_quality_lab_evaluator_catalog.py` asserts:

1. The set of `.md` files in this directory **equals** the set of names in
   `ai_stack/langfuse_evaluator_catalog.WOS_CATEGORICAL_JUDGES_ORDER`.
2. For each file, its frontmatter `categories` matches the categories
   exposed by `get_categorical_evaluator_spec(name)`.

Drift in either direction fails CI. Update both sides together when adding,
renaming, or removing an evaluator.

## When to edit which side

- **Add / remove an evaluator** → add or remove the `.md` file here, then
  update `WOS_CATEGORICAL_JUDGES_ORDER` and the evaluator spec in
  `ai_stack/langfuse_evaluator_catalog.py`.
- **Change a prompt** → edit the `.md` file only. Code does not store the
  prompt text.
- **Add / change a category** → edit the `.md` file AND update the spec
  in code (the spec exposes `categories` to MCP/Langfuse).
- **Change severity buckets / repair areas** → edit the `.md` file only.
  Quality Lab loads these from frontmatter.

## Related

- [ADR-0040](../ADR/adr-0040-quality-lab-mcp-runtime-diagnostics.md) —
  Quality Lab MCP runtime diagnostics
- [ADR-0009](../ADR/adr-0009-evaluation-is-a-promotion-gate.md) —
  evaluation as promotion gate (not "string-matched theatre")
- [ADR-0039](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) —
  no hardcoded oracles in gate tests
- `ai_stack/langfuse_evaluator_catalog.py` — code mirror
- `tools/mcp_server/tools_registry_handlers_evaluators.py` —
  `wos.evaluators.catalog` and `wos.evaluators.get` MCP surface
