# Contractify hub

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language). This suite is **contract governance**: discovery, anchoring, projection edges, drift, and backlog-friendly **actionable units** — not product feature code.

## What Contractify is

- **Discovery** — finds likely contracts using explicit A–E heuristics (see below).
- **Anchoring model** — distinguishes **normative** anchors vs **observed** surfaces vs **verification** artifacts.
- **Projections** — audience/mode views (easy, AI-reading, specialist) that **must** trace back to anchors.
- **Relations** — `derives_from`, `projects`, `documents`, … as machine edges (phase-1 subset).
- **Drift analysis (`driftify`)** — submodule `contractify.tools.drift_analysis`: deterministic checks first, heuristics labelled honestly.
- **Conflicts** — surfaces ambiguity; **no silent auto-winner** beyond documented low-risk rules.

## What Contractify is not

- Not a documentation generator — use **docify** to repair Python/docs readability.
- Not OpenAPI authoring — use product/API workflows; Contractify **reads** OpenAPI as anchor.
- Not structural refactors — use **despaghettify** after Contractify shows tangled truth.

## Core truth model

| Term | Meaning |
|------|---------|
| **Contract** | Declared or structurally inferred obligation across a boundary (API, runtime seam, workflow, policy). |
| **Anchor** | Canonical place a contract lives (OpenAPI file, normative index, ADR, workflow YAML). |
| **Projection** | Derived artefact for a tool/audience (Postman collection, easy doc). **Must** reference its anchor contract. |
| **Normative truth** | What is governed / intended / declared correct. |
| **Observed reality** | What code and runtime currently do — **evidence**, not auto-truth. |
| **Drift** | Evidence that anchor, projection, implementation, or tests diverge meaningfully. |

## Discovery heuristics (A–E)

| Tier | Meaning | Examples in this repo |
|------|---------|------------------------|
| **A** | Explicit markers or known canonical paths | `docs/dev/contracts/normative-contracts-index.md`, `docs/api/openapi.yaml`, `docs/governance/adr-*.md`, `spaghetti-setup.md` |
| **B** | Structural workflow / CI definitions | `.github/workflows/*.yml` |
| **C** | Referencing / audience artefacts | `docs/easy/**`, `docs/start-here/**` modelled as projections |
| **D** | Out of scope by default | Private helpers — not scanned |
| **E** | Confidence | Stored per record; automation policy in [`CONTRACT_GOVERNANCE_SCOPE.md`](CONTRACT_GOVERNANCE_SCOPE.md) |

Every discovered row includes `discovery_reason` so classification is **inspectable**.

## Drift detection (implemented methods)

| Drift class | Method | Deterministic? |
|-------------|--------|----------------|
| **api_runtime** | Compare `postmanify-manifest.json` `openapi_sha256` to SHA-256 of the referenced OpenAPI file | Yes |
| **anchor_projection** | Audience markdown under `docs/easy` / `docs/start-here` must link to `normative-contracts-index` or contain `contractify-projection:` | Heuristic (text signal) |
| **suite_handoff** | Docify default AST roots include `'fy'-suites/contractify` | Yes (file content check) |
| **missing_propagation** | `spaghetti-setup.md` present without `spaghetti-setup.json` | Yes (presence) |

Heuristic findings use **low** severity by default; deterministic OpenAPI hash mismatch uses **high**.

## Integration with sibling fy suites

| Suite | Handoff |
|-------|---------|
| **docify** | Contractify flags documentation/projection drift; docify runs audits/synthesizer on Python trees. Keep **contractify** in docify default `--root` list for self-governance. |
| **postmanify** | Postman JSON + manifest are **projections** of OpenAPI; regenerate when drift fires. |
| **despaghettify** | When many anchors conflict structurally, open a DS slice — Contractify does not refactor code. |

## Hub CLI

With **`pip install -e .`** at the repository root ([`pyproject.toml`](../../pyproject.toml)) the **`contractify`** console script is available. Equivalent: **`python -m contractify.tools`**.

| Command | Role |
|---------|------|
| `discover` | Contracts + projections + relations (JSON). |
| `audit` | Full pass + drift + conflicts + `actionable_units`. |
| `self-check` | Same payload as `audit` (integration sanity). |

Examples:

```bash
contractify audit --json --out "'fy'-suites/contractify/reports/contract_audit.json"
python -m contractify.tools discover --max-contracts 25 --out "'fy'-suites/contractify/reports/contract_discovery.json" --quiet
```

## Layout

| Path | Role |
|------|------|
| [`superpowers/`](superpowers/) | Cursor router `SKILL.md` files |
| [`tools/`](tools/) | Python package (`contractify.tools`) |
| [`contract_governance_input.md`](contract_governance_input.md) | **CG-*** backlog |
| [`contract-audit-task.md`](contract-audit-task.md) | Analysis procedure |
| [`contract-solve-task.md`](contract-solve-task.md) | Bounded implementation procedure |
| [`contract-reset-task.md`](contract-reset-task.md) | Recovery |
| [`CONTRACT_GOVERNANCE_SCOPE.md`](CONTRACT_GOVERNANCE_SCOPE.md) | Ceilings + automation thresholds |
| [`state/PREWORK_REPOSITORY_CONTRACT_REALITY.md`](state/PREWORK_REPOSITORY_CONTRACT_REALITY.md) | Human snapshot of pre-suite reality |
| [`reports/`](reports/) | JSON exports |

## Cursor skills

```bash
python "./'fy'-suites/contractify/tools/sync_contractify_skills.py"
python "./'fy'-suites/contractify/tools/sync_contractify_skills.py" --check
```

Do **not** hand-edit only `.cursor/skills/` copies for Contractify — sync overwrites them.

## Tests

```bash
python -m pytest "'fy'-suites/contractify/tools/tests" -q
```

## Extending the suite

1. Add a **deterministic** check when a new machine manifest exists (copy the Postmanify pattern).
2. Add **heuristics** with conservative confidence and clear `discovery_reason` text.
3. Never mark `<0.6` confidence items as `source_of_truth: true`.
4. Prefer new **relations** over duplicating contract rows.

## Versioning

Contract rows carry a `version` string (`unversioned` until the repository adopts explicit semver per contract). Breaking vs non-breaking change tracking is **manual** in backlog rows for v0.1; future tooling can read front-matter.
