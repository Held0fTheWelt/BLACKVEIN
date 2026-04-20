# Pre-work: repository contract reality (before Contractify automation)

This file captures **observed repository structure** used to shape Contractify v0.1. It is **not** a second normative layer — product and runtime truth remain in `docs/dev/contracts/normative-contracts-index.md`, OpenAPI, ADRs, and code.

## Fy-suite ecosystem (observed)

| Suite | Role (maturity snapshot) | Primary anchors |
|-------|-------------------------|-----------------|
| **despaghettify** | Mature execution/structure hub: CLI, setup markdown + JSON sync, autonomous helpers, skills | `spaghetti-setup.md`, DS input list, `state/` |
| **docify** | Mature Python docstring audit + git-path drift hints; backlog `DOC-*` | `documentation-check-task.md`, `python_documentation_audit.py` |
| **postmanify** | Mature OpenAPI → Postman projection with **versioned manifest** | `docs/api/openapi.yaml`, `postman/postmanify-manifest.json` |
| **contractify** | New: discovery + drift + relations; does **not** replace siblings | This suite |

## Contract-like artifacts already present (non-exhaustive)

1. **Normative index** — `docs/dev/contracts/normative-contracts-index.md` binds slice/runtime docs.
2. **OpenAPI** — `docs/api/openapi.yaml` declares HTTP surface (machine contract).
3. **ADRs** — `docs/ADR/adr-*.md` record architecture decisions.
4. **Despaghettify** — explicit “canonical / derived” split for setup JSON vs markdown.
5. **Postmanify manifest** — fingerprints OpenAPI (`openapi_sha256`) for projection drift checks.
6. **Easy / start-here docs** — audience projections; historically link normative docs inconsistently.
7. **CI workflows** — `.github/workflows/*.yml` encode verification obligations.
8. **Operational / governance runtime** — `docs/operations/OPERATIONAL_GOVERNANCE_RUNTIME.md` and backend governance modules (policy/runtime split).

## Known ambiguity (honest)

- **Normative vs shipped** — roadmap and freeze docs mix aspirational and binding language; Contractify must not auto-promote intent to truth.
- **Overlapping ADR vocabulary** — multiple ADRs may touch session/runtime wording; humans resolve supersession — tool surfaces *candidates* only.
- **Audience markdown** — `docs/easy/**` can drift from slice contracts unless backlinks or `contractify-projection:` markers are maintained.

## Duplication / drift hotspots (initial)

- Postman collections vs OpenAPI when manifest hash disagrees with file bytes (**deterministic** drift).
- Projections without explicit back-references to the normative index (**heuristic** drift).

This snapshot should be refreshed when major governance layout changes; Contractify `audit` JSON remains the primary verification artifact for automation.
