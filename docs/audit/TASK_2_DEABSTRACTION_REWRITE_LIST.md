# Task 2 — De-Abstraction and Readability Rewrite List

This list targets active docs where shorthand/context density is not acceptable as primary exposition.

## Rewrite queue

| Path | Why hard to read | Problem class | Required rewrite action | Priority |
|---|---|---|---|---|
| `docs/INDEX.md` | overloaded navigation, mixed legacy/process with active guidance | structure + audience mismatch | replace with audience-first map and non-curated boundary notes | P0 |
| `docs/README.md` | subject-first structure hides audience intent and authority boundaries | audience mismatch + density | add audience-first framing and authority boundary notes | P0 |
| `README.md` | broad claims without strict role framing | missing context + authority ambiguity | narrow claims and add role/scoping references | P0 |
| `docs/testing/README.md` | mixes dev test execution and admin release policy | audience mismatch | split guidance with explicit ownership | P0 |
| `docs/GATE_SCORING_POLICY_GOC.md` | gate shorthand as primary explanatory layer | shorthand-dominant exposition | add plain-language policy framing first, keep gate IDs secondary | P1 |
| `docs/rag_task3_source_governance.md` | dense policy table without reader orientation flow | table-first without orientation | add role-based orientation and examples | P1 |
| `docs/security/README.md` | mixed policy and implementation detail | audience mismatch | split admin governance vs dev implementation sections | P1 |
| `docs/architecture/area2_*` docs | shorthand-heavy naming and context dependence | shorthand + missing context | add de-abstraction index and plain-language descriptions | P2 |

## Protected exception exclusion from generic rewrite queue

Excluded from generic rewrite queue:

- `docs/CANONICAL_TURN_CONTRACT_GOC.md`
- associated unfinished G1-G10 canonical completion-chain files when acting as that chain

These files remain claim-audited and placement-governed, but are not assigned generic readability rewrites under Task 2.
