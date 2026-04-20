# Contract governance scope (anti-bureaucracy + automation thresholds)

## What counts as in-scope “contract”

A repository artifact is contract-relevant when it **creates or stabilises expectations across a boundary** (API, runtime seam, operator workflow, governance decision, or cross-team commitment). Internal helpers with no outward expectation stay **out of scope** unless explicitly elevated.

## Rollout ceilings

| Phase | Ceiling | Intent |
|-------|---------|--------|
| Phase 1 discovery | **≤ 30** contracts per `discover`/`audit` pass | Signal density over coverage |
| Early mature inventory | **< ~200** active governed contracts | Avoid noise |
| Hard review trigger | **≥ ~500** active | Mandatory consolidation / scope review |

## Confidence → automation (conservative)

| Confidence | Automation |
|------------|------------|
| **≥ 0.90** | May auto-classify as high-confidence candidate; explicit anchors may auto-link when evidence is explicit (paths, manifests, ADR filenames). |
| **0.60 – 0.89** | **Curator review required** — never silent authoritative anchoring. |
| **< 0.60** | Candidate-only — no auto-anchor, no strong enforcement hooks. |

False authority is worse than incomplete discovery.

## Drift severity (impact-first)

| Class | Typical meaning |
|-------|-----------------|
| **critical** | Externally visible breaking mismatch, dangerous policy contradiction, manifest pointing at missing OpenAPI. |
| **high** | Stale API projections, operational contract mismatch with clear blast radius. |
| **medium** | Meaningful doc/projection staleness for engineering/admin. |
| **low** | Localised audience doc drift with limited impact. |
| **informational** | Suite handoffs, naming, optional derived artifacts missing. |

## Conflict classifications (machine rows)

Audit JSON **`conflicts[]`** rows use **`classification`**, **`severity`** (same scale as drift: critical → informational), **`kind`** (curator-facing bucket), **`normative_sources`**, **`observed_or_projection_sources`**, and optional **`normative_candidates` / `observed_candidates` / `projection_candidates`** for triage without re-parsing prose.

| `classification` | Meaning | Typical response |
|------------------|---------|------------------|
| **`normative_anchor_ambiguity`** | The normative index links the same resolved markdown path more than once (duplicate “truth” anchors). | Deduplicate index rows or split distinct contracts with clearer IDs. |
| **`normative_vocabulary_overlap`** | Two or more ADRs hit the same bounded keyword bucket (heuristic overlap, not semantic equivalence). | Human triage: merge, narrow scope, or accept with explicit disambiguation in backlog. |
| **`projection_anchor_mismatch`** | A projection’s **`contract_version_ref`** (16-hex OpenAPI SHA prefix) disagrees with the current on-disk OpenAPI prefix **or** a projection references a missing **`source_contract_id`**. | Refresh Postmanify output, fix projection metadata, or widen discovery so the anchor id exists. |
| **`supersession_gap`** | ADR header **`Status:`** is **`Deprecated`** / **`Superseded`** but navigation cues to the successor are missing or thin. | Add explicit supersession links or ADR front-matter. |
| **`superseded_still_referenced_as_current`** | A normative index table row is labelled **Active** / **Binding** but links to an ADR whose declared status is **superseded** / **deprecated** (row labelling heuristic). | Relabel the row (e.g. Retired/History) or replace the link with the current-truth anchor. |
| **`lifecycle_projection_vs_retired_anchor`** | A projection’s **`source_contract_id`** resolves to a discovered contract whose lifecycle is **superseded** / **deprecated**. | Repoint projections to the successor anchor or mark the projection explicitly as historical. |

Treat **`requires_human_review: true`** on any conflict as blocking silent automation, even when **`confidence`** is high.

## Projections (non-negotiable rule)

Every projection must declare **which anchored contract** it represents. Preferred mechanisms:

1. Normal markdown link to `docs/dev/contracts/normative-contracts-index.md` (or a specific listed contract).
2. Optional machine block:

```markdown
---
contractify-projection:
  source_contract_id: CTR-NORM-INDEX-001
  anchor: docs/dev/contracts/normative-contracts-index.md
  authoritative: false
  audience: stakeholder
  mode: easy
---
```

## Authority order (governance)

1. Normative contract truth (declared, governed).
2. Observed implementation reality (code/runtime — **evidence**, not automatic truth).
3. Objective verification artifacts (CI, signed manifests, tests).
4. Legacy or unverified intent.

## Suite boundaries

| Suite | Contractify interacts by… |
|-------|---------------------------|
| **docify** | Drift when default AST roots omit contractify; discovery surfaces **`documentation-check-task`** as a normative handoff anchor when present. |
| **postmanify** | Manifest + collections as OpenAPI projections (SHA drift); discovery surfaces **`postmanify-sync-task`**; drift when task prose **`openapi_path`** disagrees with manifest. |
| **despaghettify** | Drift when derived **`spaghetti-setup.json`** is missing; discovery keeps **`spaghetti-setup.md`** as normative hub input. |
