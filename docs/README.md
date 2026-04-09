# WorldOfShadows documentation

Audience-first documentation entrypoint.

## Start here (everyone)

- Plain-language orientation: [`docs/start-here/README.md`](start-here/README.md)
- Master index: [`docs/INDEX.md`](INDEX.md)
- Full glossary: [`docs/reference/glossary.md`](reference/glossary.md)
- Short glossary: [`docs/start-here/glossary.md`](start-here/glossary.md)
- Doc registry: [`docs/reference/documentation-registry.md`](reference/documentation-registry.md)

## Audience roots

- **Users:** [`docs/user/README.md`](user/README.md)
- **Administrators / operators:** [`docs/admin/README.md`](admin/README.md)
- **Developers:** [`docs/dev/README.md`](dev/README.md)
- **Technical system (architecture, AI, runtime):** [`docs/technical/README.md`](technical/README.md)
- **Stakeholder slides:** [`docs/presentations/`](presentations/)
- **ADRs:** [`docs/governance/README.md`](governance/README.md)

## Optional static site (MkDocs)

From repository root (after `pip install -r requirements-docs.txt`):

```bash
python -m mkdocs serve
```

Build output is gitignored at `/site/` (see `mkdocs.yml`). CI builds on changes to `docs/`, `mkdocs.yml`, and `requirements-docs.txt`.

## Legacy and evidence

- **Archived** architecture and RAG task narratives: [`docs/archive/`](archive/)
- **Audit baselines:** [`docs/audit/`](audit/) — engineering evidence, not primary onboarding

## Consolidation record

See [`docs/archive/documentation-consolidation-2026/`](archive/documentation-consolidation-2026/) for topic maps, migration ledgers, and the final validation report from the 2026 documentation overhaul.
