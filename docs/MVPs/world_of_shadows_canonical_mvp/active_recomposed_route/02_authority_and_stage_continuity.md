# Authority and stage continuity

## Constitutional core

The same laws still govern the package:

- one truth boundary,
- commit is truth,
- Turn 0 is canonical,
- ordinary player route purity,
- publish-bound authoritative birth,
- fail closed at authority seams,
- explicit degraded-safe semantics,
- incident-visible persistence,
- non-graph seam testability,
- payload self-classification,
- and release honesty.

## Service ownership

### world-engine
Owns live story-session execution, validation, commit, and authoritative runtime state.

### backend
Owns auth, policy, persistence, publish/release control, administrative APIs, and bridge orchestration.

### frontend
Owns the ordinary player shell and player-visible route layer.

### administration-tool
Owns operator/admin/inspection surfaces.

### writers-room
Owns authoring-side and review-side interaction surfaces, but not canonical promotion by itself.

### ai_stack and story_runtime_core
Own interpretation, retrieval, orchestration, packaging, adapters, and bounded support.
They do not outrank engine commit.

## The stage chain that must stay legible

### Stage 1 — authored source
Structured authored modules define dramatic possibility space.
For the active slice, YAML under `content/modules/god_of_carnage/` is the primary authored source.

### Stage 2 — review and publish governance
Writers’ Room, review bundles, admin governance, and publishability checks prepare changes for human-reviewed promotion.

### Stage 3 — published activation surface
Backend exposes published playable truth through the publish/feed path.
Published truth is primary.
Builtins are secondary fallback only.

### Stage 4 — runtime birth and execution
world-engine consumes published content, births runs, executes turns, validates proposals, and commits truth.

### Stage 5 — player-visible shell
Frontend renders only player-safe, committed, or lawfully derived shell surfaces.
Operator-only detail must not leak into the ordinary player route.

### Stage 6 — operator observation and diagnosis
Admin/operator surfaces may inspect runtime health, diagnostics, traces, and governance state without becoming a second truth boundary.

## Source-precedence ladder

For the active slice:

1. canonical authored source
2. publish-governed released content
3. committed runtime truth for a given live run
4. player-safe shell projection derived from committed/runtime-safe observation
5. operator/diagnostic bundles
6. support trees, retrieval context, cached observations, mirrors, and residue

Lower lanes may support or explain higher lanes.
They may not silently replace them.

## Why this stage continuity matters

This chain is the main reason WoS still reads as one system rather than as:

- a content package,
- a runtime package,
- a frontend package,
- and an AI package
that merely happen to sit in one repository.
