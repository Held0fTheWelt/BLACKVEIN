# Contractify completion pass (state snapshot)

**Date:** 2026-04-13 (repository session). **Purpose:** record what was verified before hardening and what changed.

**Follow-up:** bounded finalization outcomes (conflict severity/kind, lifecycle row check, supersedes relations, fy-suite task discovery, extra drift passes) live in [`FINALIZATION_PASS_2026-04-13.md`](FINALIZATION_PASS_2026-04-13.md).

## Verified strengths (preserved)

- Fy-suite layout: `README.md`, `CONTRACT_GOVERNANCE_SCOPE.md`, check/solve/reset tasks, `contract_governance_input.md`, `superpowers/`, `tools/`, `examples/`, hermetic `conftest.py`.
- Core model: `ContractRecord`, `ProjectionRecord`, `DriftFinding`, `RelationEdge`, normative vs observed in `authority_level`.
- Conservative discovery with `max_contracts`, `discovery_reason`, and A–E tier vocabulary in docs.
- Deterministic drift: Postman manifest ↔ OpenAPI SHA-256.

## Verified gaps (closed in this pass)

1. **Conflicts** — moved from a single ADR keyword stub to `conflicts.py`: duplicate normative index targets, bounded ADR vocabulary buckets, projection OpenAPI fingerprint mismatch, deprecated ADR header without supersession cues.
2. **Versioning** — `versioning.py` parses `info.version` from OpenAPI and explicit `Status:` lines in ADRs; discovery writes `ContractRecord.version` / lifecycle `status` from those parses (no semantic promotion of code behaviour).
3. **Relations** — `relations.py` `extend_relations()` adds references/indexes/implements/operationalizes edges with caps and deduplication.
4. **Discovery** — bounded additions: `docs/operations/OPERATIONAL_GOVERNANCE_RUNTIME.md`, up to two `schemas/*.json` files.
5. **Evidence** — sample audit JSON now includes a populated `conflicts[]` row with `classification` metadata; tests assert shape stability.
6. **Tests** — 16 hermetic tests including conflicts, versioning, relations; still runnable from a non-monorepo `TMP` + `PYTHONPATH`.

## Intentionally deferred

- **Conflict depth:** normative doc ↔ implementation contradiction detection, test-assertion-derived conflict classes, richer supersession graph resolution, stronger multi-anchor disambiguation beyond current table patterns.
- **Versioning depth:** breaking vs non-breaking distinction, explicit migration workflows, version mismatch reporting across more anchor/projection families than OpenAPI + ADR headers.
- **Evidence layout:** full-fidelity `reports/*.json` stays local/gitignored by policy; committed **shape** samples live under `examples/` (see `reports/README.md`).
- **ZIP hygiene:** local `.gitignore` under the hub + `git archive`; `tools/tests/test_git_tracked_hygiene.py` asserts no tracked `__pycache__` / `.pyc` under `'fy'-suites/contractify`.
- Deep OpenAPI ↔ FastAPI route parity; CI workflow for `validate_contractify_skill_paths.py`.
- Automatic “breaking change” classification beyond explicit document markers.

## Next slices (recommended)

1. Optional GitHub Action: `pytest contractify.tools.tests` + `validate_contractify_skill_paths.py --check` on hub diffs.
2. One additional deterministic conflict: two different `openapi.yaml` paths both claiming canonical in index prose (if repo ever grows that pattern).
3. Projection front-matter parser tests tied to `contractify-projection:` blocks in real `docs/easy/` pages (curated fixtures).
