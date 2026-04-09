# Task 2 — Documentation Link and Reference Repair List

This list captures required reference repairs to keep curated docs navigable and truth-safe.

## Priority repair items

| Source doc | Link/reference issue | Repair action | Priority |
|---|---|---|---|
| `docs/INDEX.md` | no explicit separation between curated audience docs and non-curated control/audit surfaces | add explicit split sections and links | P0 |
| `docs/README.md` | quick links do not route by `dev/admin/user` audience taxonomy | add audience-first links and root pointers | P0 |
| `docs/audit/gate_summary_matrix.md` | references to `tests/reports/evidence/...` can be read as clone-stable | retain explicit clone-local caveat and link to policy baseline | P0 |
| `docs/g9_evaluator_b_external_package/README.md` | mirror ownership may be unclear versus `outgoing/**` | add canonical mirror-owner statement and cross-links | P1 |
| `README.md` | broad references without explicit contract precedence routing | add precedence pointers to canonical contract/authority docs | P1 |
| `docs/testing/README.md` | release-policy links mixed with developer workflow links | split and relink to dev/admin audience docs | P1 |

## Repair verification requirements

Each repaired reference entry must capture:

- source path
- previous link target
- new link target
- reason for repair
- verification result (resolved/unresolved)
