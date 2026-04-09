# Superpowers documentation migration — final validation report

**Date:** 2026-04-10  
**Scope:** Former `docs/superpowers/plans/` and `docs/superpowers/specs/` only, plus required consolidation artifacts and directly affected canonical pointers.

## Summary

- **37** markdown sources were **git-moved** to `docs/archive/superpowers-legacy-execution-2026/{plans,specs}/`.
- The active paths **`docs/superpowers/plans/`** and **`docs/superpowers/specs/`** no longer exist; **`docs/superpowers/`** was removed after the move.
- **Durable technical truth** was validated against the current tracked codebase and either **merged into** `docs/technical/architecture/backend-runtime-classification.md` or **confirmed pre-existing** in other canonical documents (see ledger).
- **W4 gate program** narratives were **not** promoted to the active technical surface (no safe single canonical “completion” claim without broader roadmap reconciliation).

## What was migrated (new or expanded canonical text)

| Topic | Destination |
|-------|-------------|
| Deny-by-default mutation permission vs path validity | `docs/technical/architecture/backend-runtime-classification.md` — *Mutation and reference enforcement* |
| Reference integrity (`character`, `relationship`, `scene`, `trigger`) | Same section |
| `MCP_SERVICE_TOKEN` + Bearer auth + 503 misconfiguration semantics | Same file — *API stance* |
| `AIRoleContract` / `parse_role_contract` execution vs diagnostics boundary | Same file — classification table row for `role_structured_decision.py` |
| W2 helper + presenter roles (in-process path) | Same file — clarified table rows |

## What was verified but not re-written (already canonical)

| Topic | Destination |
|-------|-------------|
| A1 play shell + `player_input` turn bridge | `docs/technical/runtime/a1_free_input_primary_runtime_path.md` + `frontend/` |
| Cross-stack observability | `docs/technical/operations/observability-and-governance.md` |
| MCP developer setup | `docs/dev/tooling/mcp-server-developer-guide.md` |
| Intra-call roles vs routing | `docs/technical/ai/llm-slm-role-stratification.md` |
| Test suite layout / smoke roots | `docs/technical/reference/test-strategy-and-suite-layout.md` |

## What was archived

- Entire former superpowers **plans** and **specs** trees under `docs/archive/superpowers-legacy-execution-2026/`, with a folder **README** explaining non-curated status.

## What was deleted

- **No** individual plan/spec files were deleted.
- **Removed empty active directories:** `docs/superpowers/` (including former `plans/` and `specs/`).

## Other canonical docs updated (cross-references)

- `docs/admin/README.md` — exclusion note now points to archive path.
- `docs/dev/README.md` — same.
- Selected `docs/audit/TASK_*` rows that cited `docs/superpowers/*` — paths updated or footnoted to archive.
- `docs/INDEX.md` — consolidation artifact list extended.
- Archived `plans/2026-03-30-w4-implementation.md` — internal self-check path updated to new spec location.

## Active role of former superpowers locations

- **`docs/superpowers/plans/` and `docs/superpowers/specs/`:** **None.** They are not part of the curated surface and do not exist on the active tree.
- **MkDocs `nav`:** Did not reference superpowers (no change required).

## Residual blockers / deferred items

- **W4 sequential gate spec** remains **historical program text** only. Promoting gate-completion claims would require reconciling against current `docs/ROADMAP_MVP_*.md` and test/persistence reality — **explicitly out of scope** for this pass.
- **Pre-built static site** under `site/` (if regenerated) may still contain old URLs until the next MkDocs build; **tracked source of truth** is `docs/`.

## Artifacts produced

1. [`SUPERPOWERS_MIGRATION_INVENTORY.md`](SUPERPOWERS_MIGRATION_INVENTORY.md)
2. [`SUPERPOWERS_DURABLE_TRUTH_MIGRATION_LEDGER.md`](SUPERPOWERS_DURABLE_TRUTH_MIGRATION_LEDGER.md)
3. [`SUPERPOWERS_MIGRATION_VERIFICATION_TABLE.md`](SUPERPOWERS_MIGRATION_VERIFICATION_TABLE.md)
4. [`SUPERPOWERS_ARCHIVE_OR_DELETE_DECISIONS.md`](SUPERPOWERS_ARCHIVE_OR_DELETE_DECISIONS.md)
5. This report.
