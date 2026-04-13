# Research-to-Revision Suite

## Problem statement

A research suite that stops at findings and prose recommendations is not enough.
It must become useful for controlled content improvement without becoming an uncontrolled auto-author.

## Design rule

Research is **package-aware, target-aware, and revision-capable**, but still **review-bound**.

## Expanded research pipeline

**ingest -> aspects -> exploration -> claims -> findings -> revision_candidates -> draft_patch_bundles -> preview_build_request**

## Required research outputs

### Findings
A finding states what appears wrong or weak.

Examples:
- actor inconsistency
- underused trigger
- weak escalation gradient
- phase constraint too restrictive
- policy ambiguity

### Revision candidates
A revision candidate states a proposed structured change against a concrete content unit.

Examples:
- target `scene_guidance/scene_03`
- target `actor_mind/veronique`
- target `trigger_map/phase_2`
- target `legality_table/scene_04`

### Draft patch bundles
A draft patch bundle is the actual change unit applied to draft workspace.

It may contain:
- JSON merge patch
- YAML subtree replacement
- text clause insert/replace operations
- metadata about downstream rebuild and evaluation needs

## Required research capabilities

### 1. Target localization
Research must localize a weakness to specific content targets whenever possible.

### 2. Expected effect declaration
Each revision candidate should declare expected effects such as:
- stronger trigger precision
- more stable actor voice
- reduced drift
- wider legal action space
- tighter scene legality

### 3. Risk flags
Candidates should declare risks such as:
- possible over-restriction
- actor flattening
- escalation overshoot
- policy conflict
- regression risk in linked scenes

### 4. Package context
Candidates should record:
- based-on package version
- related scene IDs
- related policy layers
- affected evaluation scenarios if known

## Example contract

```python
class DraftPatchBundle(BaseModel):
    patch_bundle_id: str
    module_id: str
    draft_workspace_id: str
    revision_ids: list[str]
    target_refs: list[str]
    patch_operations: list[dict]
    requires_preview_rebuild: bool = True
    requires_evaluation: bool = True
    created_at: str
```

## Guardrails

Research may not:
- publish active packages
- alter active policy directly
- bypass conflict resolution
- bypass workflow approval
- delete package history

## Research suite extensions in `ai_stack`

Recommended additions:

```text
ai_stack/
  narrative/
    research/
      findings.py
      revision_candidates.py
      conflict_hints.py
      delta_formats.py
      draft_patch_bundles.py
      package_aware_analysis.py
      evaluation_linkage.py
```

## Evaluation linkage

Research output should indicate which evaluation scenarios are relevant.
This avoids blind preview evaluation and supports targeted regression checks.

## Writers-room boundary

Writers-room remains the curated source-editing environment.
Research may prepare structured changes for draft, but writers-room remains the place where source-level authored material can still be refined by a human or tightly bounded agent.
## Runtime-health-driven research inputs

The research suite should also be able to ingest live runtime degradation evidence, especially:

- repeated safe fallback events in the same scene
- repeated corrective retries on the same violation type
- high-rate invalid trigger failures
- contradiction failures after preview promotion

This allows research to propose revisions against:
- fallback content quality
- scene guidance clarity
- legality-table tuning
- actor-mind over-aggression
- policy over-tightness that causes repeated degradation

## New target kinds worth supporting

- `scene_fallback`
- `runtime_feedback_hint`
- `emotional_state_rule`
- `contradiction_guard_rule`

The suite still remains review-bound.
It may recommend improvements to these content units, but may not auto-publish them.
