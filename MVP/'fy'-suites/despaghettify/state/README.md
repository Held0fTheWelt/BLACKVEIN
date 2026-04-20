# Execution state hub

This folder is the canonical restart layer for state-changing execution work in the repository.

Core principles:
- State documents preserve continuity.
- Artefacts preserve evidence.
- Closure claims are only valid when pre and post artefacts are linked and comparable.
- **Governance artefacts:** human-readable pre/post files and related state notes must be **strict English** — [`../../docs/dev/contributing.md#repository-language`](../../docs/dev/contributing.md#repository-language).

Note: `artifacts/workstreams/…/pre|post/` may be **empty** between waves (e.g. after cleanup). New structural waves add session files again; missing old paths do **not** replace Git history, CI, or tests.

Canonical entry points:
- `EXECUTION_GOVERNANCE.md`
- `WORKSTREAM_INDEX.md`

Structural code refactors (spaghetti / module boundaries) use the same pre/post paths: [`despaghettify/despaghettification_implementation_input.md`](../despaghettification_implementation_input.md).
