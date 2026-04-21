# Delta repair report

## Executive summary

This pass closed the remaining route-normalization and evidence-lane tensions without reopening the broader MVP.

The repair did four things:

1. rerouted `docs/README.md` so the active recomposed route is now the explicit canonical first-pass entry and `docs/audit/README.md` is the explicit current evidence entrypoint;
2. rerouted `docs/audit/README.md` so the 2026-04-21 repair-implementation bundle is the primary repair/evidence bundle and the 2026-04-21 post-repair re-audit is the latest consistency judgment;
3. removed the competing “Primary canonical spine” wording from the canonical companion README and reframed the split family as a detailed companion reading sequence;
4. normalized the current evidence route across the active proof-posture surfaces and bounded the 2026-04-20 repair bundle as historical support.

## Issues addressed

- **PRR-01** — stale entrypoint routing in `docs/README.md`
- **PRR-02** — stale audit routing in `docs/audit/README.md`
- **PRR-03** — companion-route wording conflict and stale proof references in `docs/MVPs/world_of_shadows_canonical_mvp/README.md`
- **PRR-04** — no single explicit current evidence route

## Files changed

- `docs/README.md`
- `docs/audit/README.md`
- `docs/MVPs/world_of_shadows_canonical_mvp/README.md`
- `docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/06_implementation_and_proof_posture.md`
- `docs/MVPs/world_of_shadows_canonical_mvp/09_implementation_reality_runtime_maturity_and_proof.md`
- `docs/audit/world_of_shadows_canonical_mvp_repair_2026-04-20/README.md`

## Exact normalization performed

### docs/README.md
- Re-ranked the active recomposed route above the companion family.
- Removed the older 2026-04-20 repair bundle from active-first positioning.
- Added a clear role split between active canon, companion canon, current evidence lane, and historical support.

### docs/audit/README.md
- Replaced the older 2026-04-20 repair bundle as the active entrypoint.
- Declared one current repair/evidence lane and gave a fixed reader order.
- Explicitly marked the 2026-04-20 repair bundle as historical support.

### docs/MVPs/world_of_shadows_canonical_mvp/README.md
- Removed the “Primary canonical spine” heading.
- Reframed the deeper sequence as a detailed companion reading sequence.
- Updated proof/evidence guidance to point to the singular current evidence route via `docs/audit/README.md`.

### active_recomposed_route/06_implementation_and_proof_posture.md
- Added an explicit “Current evidence route” section.
- Stated the route order: audit README → 2026-04-21 repair-implementation bundle → 2026-04-21 post-repair re-audit → older bundles as historical support only.
- Preserved partial UI support obligations as partial rather than wording them closed.

### 09_implementation_reality_runtime_maturity_and_proof.md
- Updated the “newly verified evidence” pointer so it no longer names the old bundle as the active evidence location.

### world_of_shadows_canonical_mvp_repair_2026-04-20/README.md
- Bounded the older repair bundle as historical support instead of current reviewer entrypoint.

## What was not changed

- Historical report bodies under the older bundles were not rewritten wholesale. They remain as historical records.
- No runtime, UI, backend, or test logic was reopened in this pass.
- No broad MVP recomposition was re-run.

## Validation executed

- Relative markdown link checks across all changed files
- Search checks for stale current-entry wording in the current route surfaces
- Search checks for “Primary canonical spine” wording in the current route surfaces

All changed-file markdown links resolved successfully.
The stale “Primary canonical spine” wording was removed from the current route surfaces.
The only remaining direct mention of `world_of_shadows_canonical_mvp_repair_2026-04-20/` inside the targeted current surfaces is the explicit historical-support listing in `docs/audit/README.md`, which is intentional.

## Final judgment

The stale-entrypoint problem is closed for the current documentation lattice.
The package now reads as one current canon with one current evidence lane, while older bundles remain visible as bounded historical support.

## Remaining bounded residue

Historical bundle internals still speak from their original moment. That is acceptable because their entrypoints are now explicitly bounded as historical support instead of current truth posture.
