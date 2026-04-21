# Session runtime contract (canonical redirect anchor)

This path is preserved as a continuity anchor for package-level smoke tests,
closure bundles, and older documentation references.

The active current source is:

- [`docs/technical/architecture/session_runtime_contract.md`](../technical/architecture/session_runtime_contract.md)

## Why it remains load-bearing

The session runtime contract connects the player-visible experience to the
actual enforced runtime lifecycle. It is therefore part of the runtime-proof
surface for:

- session creation and activation,
- ownership of authoritative state,
- continuity across turn execution,
- and the boundary between backend surfaces and world-engine truth.

The active technical document above is the normative source. This file remains
in place so repository-truth smoke tests and historical evidence continue to
resolve to a real, maintained anchor.
