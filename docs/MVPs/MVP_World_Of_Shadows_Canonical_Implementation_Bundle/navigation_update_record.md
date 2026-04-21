# Navigation Update Record

## Updated Navigation Files

- `docs/INDEX.md`
- `docs/README.md`
- `docs/MVPs/README.md`

## Link Changes

- Added canonical route reference to:
  - `docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/README.md`
- Updated MVP section wording to identify this bundle as canonical implementation route.

## Canonical MVP Route Declaration

Canonical MVP documentation entrypoint is:

`docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/README.md`

## 2026-04-21 verification pass

Re-checked `docs/README.md`, `docs/INDEX.md`, and `docs/MVPs/README.md`: all primary MVP links resolve to the canonical implementation bundle (or other `docs/MVPs/…` bundles), not to a raw repository-root `MVP/` documentation path.

## 2026-04-21 reconcile tooling note

`scripts/mvp_reconcile.py` now documents excluded path classes in [`integration_conflict_register.md`](./integration_conflict_register.md) (see **Paths excluded from comparison**). Navigation entrypoints were unchanged; this entry records traceability only.
