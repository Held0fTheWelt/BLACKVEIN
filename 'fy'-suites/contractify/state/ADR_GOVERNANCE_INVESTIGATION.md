# ADR Governance Investigation State

- Status: active
- Last edited: 2026-04-17
- Canonical ADR home: `docs/ADR`
- Investigation suite: `../investigations/adr/`

## What changed

Contractify now carries a bounded ADR governance layer in addition to the runtime/MVP spine attachment work.

## Governance intent

- ADRs should converge into `docs/ADR`.
- Old duplicates should not remain as silent parallel truth.
- Naming may become more expressive than flat `ADR-000X` when that avoids false simultaneity or improves family ordering.
- Contractify may propose richer ids and file names, but human review still approves real repository moves and deletions.

## Visible outputs

- `../investigations/adr/ADR_GOVERNANCE_INVESTIGATION.md`
- `../investigations/adr/ADR_RELATION_MAP.mmd`
- `../investigations/adr/ADR_CONFLICT_MAP.mmd`
- local `../reports/_local_contract_audit.json` → `adr_governance` (machine export); tracked human review lives in `../reports/CANONICAL_REPO_ROOT_AUDIT.md`

## Open review points

- Whether the repository wants one flat `docs/ADR/` namespace or future family subfolders.
- How aggressively older ADRs should be renamed once canonical ids are adopted.
- Whether historical aliases should remain as redirect stubs or be removed entirely after link migration.

## Edit history

- 2026-04-17: Added ADR governance tracking and investigation-suite entry points.
