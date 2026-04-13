# Contractify hub

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language). This suite is **contract governance**: discovery, anchoring, projection edges, drift, and backlog-friendly **actionable units** — not product feature code.

## What Contractify is

- **Discovery** — finds likely contracts using explicit A–E heuristics (see below).
- **Anchoring model** — distinguishes **normative** anchors vs **observed** surfaces vs **verification** artifacts.
- **Projections** — audience/mode views (easy, AI-reading, specialist) that **must** trace back to anchors.
- **Relations** — discovery emits core edges; [`contractify.tools.relations`](tools/relations.py) **`extend_relations()`** adds bounded **`references`**, **`indexes`**, **`implements`**, and **`operationalizes`** links where evidence is explicit.
- **Drift analysis (`driftify`)** — [`contractify.tools.drift_analysis`](tools/drift_analysis.py): deterministic checks first, heuristics labelled honestly.
- **Conflicts** — [`contractify.tools.conflicts`](tools/conflicts.py) **`detect_all_conflicts()`**: duplicate normative index targets, ADR vocabulary buckets, projection↔OpenAPI fingerprint mismatches, and bounded lifecycle/supersession header gaps — each row carries **`classification`** plus normative vs projection source lists.
- **Versioning (operational)** — [`contractify.tools.versioning`](tools/versioning.py) parses **`info.version`** from OpenAPI and explicit **`Status:`** lines in ADR headers so `ContractRecord.version` / lifecycle **`status`** reflect declared anchors (not inferred code behaviour).

## What Contractify is not

- Not a documentation generator — use **docify** to repair Python/docs readability.
- Not OpenAPI authoring — use product/API workflows; Contractify **reads** OpenAPI as anchor.
- Not structural refactors — use **despaghettify** after Contractify shows tangled truth.

## Maturity (known boundaries)

Phase-1 tooling is **deliberately shallow** in places: conflicts are real but not semantic (no normative↔implementation contradiction mining, no test-derived conflict classes, no rich supersession graph). Versioning reads **declared** OpenAPI and ADR header signals only — no automatic breaking-change taxonomy or cross-family migration workflows. Use **CG-*** backlog rows and human review for anything that needs semantic judgement. For **ZIP / copy exports**, strip `__pycache__` / `*.pyc` or use `git archive`; see [`examples/README.md`](examples/README.md) and [`reports/README.md`](reports/README.md).

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
| **B** | Structural workflow / CI / ops / shared schemas | `.github/workflows/*.yml`, `docs/operations/OPERATIONAL_GOVERNANCE_RUNTIME.md` (when present), up to **two** `schemas/*.json` files per pass |
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

## Conflict detection (implemented)

| Signal | Deterministic? | `classification` (typical) |
|--------|----------------|-----------------------------|
| Same resolved markdown target linked twice from the normative index | Yes | `normative_anchor_ambiguity` |
| Two+ ADRs hit the same bounded vocabulary bucket | No (keyword bucket) | `normative_vocabulary_overlap` |
| Projection `contract_version_ref` (16-hex OpenAPI prefix) ≠ current file SHA prefix | Yes | `projection_anchor_mismatch` |
| `Status: Deprecated/Superseded` in ADR head without supersession navigation cues | No | `supersession_gap` |

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
| [`state/COMPLETION_PASS_STATE.md`](state/COMPLETION_PASS_STATE.md) | Completion / hardening pass record |
| [`examples/`](examples/) | Committed JSON **shape** samples + [`examples/README.md`](examples/README.md) |
| [`reports/`](reports/) | JSON exports (local `*.json` gitignored) + [`reports/README.md`](reports/README.md) |

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

**Hermetic default:** unit tests patch ``repo_root()`` to a **synthetic mini-repo** (see ``tools/tests/conftest.py``) so ``pytest`` passes in **ZIP extracts** and partial trees without the full monorepo ``pyproject.toml`` next to your checkout layout. Pure logic tests (``test_models.py``, sample JSON shape tests) skip the patch.

**Optional CLI override:** set ``CONTRACTIFY_REPO_ROOT`` to an existing directory that contains a hub ``pyproject.toml`` marker for ``world-of-shadows-hub`` so ``python -m contractify.tools …`` resolves the repo without walking from the installed package path.

**Committed samples:** ``examples/contract_discovery.sample.json`` and ``examples/contract_audit.sample.json`` illustrate JSON shape; ``tools/tests/test_example_artifacts.py`` guards compatibility when fields change.

## Extending the suite

1. Add a **deterministic** check when a new machine manifest exists (copy the Postmanify pattern).
2. Add **heuristics** with conservative confidence and clear `discovery_reason` text.
3. Never mark `<0.60` confidence items as `source_of_truth: true`.
4. Prefer new **relations** over duplicating contract rows.

## Versioning

OpenAPI contracts use **`info.version`** when present; ADRs use explicit **`Status:`** lines for lifecycle (`active`, `deprecated`, `superseded`, …). Other anchors remain **`unversioned`** until the repository adds machine-readable markers. Breaking vs non-breaking change tracking stays **manual** in **CG-*** backlog rows; projection rows may carry **`contract_version_ref`** (e.g. manifest SHA prefix) for drift and conflict checks.
