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
| **docify** | Flagging doc/projection drift; docify repairs readable Python/docs — Contractify does not synthesise prose. |
| **postmanify** | Treating collections + manifest as **projections** of OpenAPI; drift on `openapi_sha256`. |
| **despaghettify** | Surfacing fragmented truth / tangled anchors; structural repair stays in Despaghettify. |
