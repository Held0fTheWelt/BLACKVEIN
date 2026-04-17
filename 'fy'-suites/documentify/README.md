# Documentify

Documentify generates **working documentation drafts** from the current repository surface.

Inputs:

- current code layout
- current documentation trees
- current technical / operations / testing documents

Outputs:

- `generated/simple/` — easy-entry explanations
- `generated/technical/` — technical reference views
- `generated/roles/` — role-bound documentation by subfolder

Documentify is additive: it drafts a maintained documentation layer without pretending to replace the repository's normative contracts.

## CLI

```bash
documentify generate --out-dir "'fy'-suites/documentify/generated"
documentify audit
```
