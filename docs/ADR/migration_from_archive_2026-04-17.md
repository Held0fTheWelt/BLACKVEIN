# Migration summary — archive → ADR (2026-04-17)

This file records consolidation actions taken on **2026-04-17** to centralize decision texts in `docs/ADR/`.

**Human index:** [`README.md`](README.md) lists every ADR and status. **Record shape:** [`adr-template.md`](adr-template.md).

## Migrated items

- `docs/archive/architecture-legacy/runtime_authority_decision.md` → [`adr-0001-runtime-authority-in-world-engine.md`](adr-0001-runtime-authority-in-world-engine.md)
  - Canonical runtime authority summary, ownership boundaries, and migration policy. The narrative MVP index [`docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md`](../MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md) now **only** points here; normative wording lives in ADR-0001 and [`docs/technical/runtime/runtime-authority-and-state-flow.md`](../technical/runtime/runtime-authority-and-state-flow.md).
- `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md` (ADR-001 … ADR-014 headings) → matching `adr-0001` … `adr-0014` files (see README index).
- Duplicate stub [`adr-0021-runtime-authority.md`](adr-0021-runtime-authority.md) → **superseded** by ADR-0001 (same subject; keep 0021 as historical id only).

## Candidate archive/spec files (manual review)

- `docs/archive/documentation-consolidation-2026/DURABLE_TRUTH_MIGRATION_VERIFICATION_TABLE.md`
- `docs/archive/documentation-consolidation-2026/DURABLE_TRUTH_MIGRATION_LEDGER.md`
- `docs/archive/superpowers-legacy-execution-2026/specs/2026-03-29-w2-4-4-role-diagnostics.md`
- `docs/archive/superpowers-legacy-execution-2026/specs/2026-03-28-w2-2-2-mutation-policy-design.md`

## Next steps (ongoing)

- Prefer **one normative home**: extend an existing ADR or add a new `adr-00XX` instead of duplicating decision paragraphs in specs or archives.
- When an archive file only restates an ADR, replace its body with a short pointer: `ARCHIVED — canonical: docs/ADR/adr-XXXX-….md`.
- Update cross-links in the docs tree to `docs/ADR/…` (this README is the catalogue).

---

_Generated for documentation consolidation; edit this file when large migration batches land._
