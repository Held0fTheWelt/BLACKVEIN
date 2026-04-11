# Superpowers archive or delete decisions

**Rule:** Exactly one disposition per source file.

| Source path (under `docs/archive/superpowers-legacy-execution-2026/`) | Final disposition | Rationale | Historical value | Active curated value |
|------------------------------------------------------------------------|-------------------|-----------|------------------|----------------------|
| All 37 files in `plans/*.md` and `specs/*.md` | **Migrated and archived** | Dated agent-execution artifacts; retain git history and readable context for “what was planned when” | High (process + design snapshots) | None — truth lives in canonical `docs/technical/` et al. |

**Delete:** None of the 37 sources were deleted. They remain valuable as **historical execution-control** evidence and were moved off the active tree into a single archive prefix.

**Directories removed from active layout:** `docs/superpowers/plans/`, `docs/superpowers/specs/`, and parent `docs/superpowers/` (empty after move).

**Companion README:** [`../superpowers-legacy-execution-2026/README.md`](../superpowers-legacy-execution-2026/README.md)
