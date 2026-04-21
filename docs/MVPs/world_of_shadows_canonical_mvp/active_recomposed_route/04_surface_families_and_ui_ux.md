# Surface families and UI/UX

## Why surfaces are canonical

World of Shadows is not only a backend/runtime architecture.
The player, operator, and authoring experiences are part of the MVP definition.

## Player-shell questions that must be answered immediately

The strongest shell expectation remains that the session surface answer four questions quickly:

1. What is happening right now?
2. What changed this turn?
3. What can I do next?
4. Where does deeper help or diagnosis live?

These are not mere cosmetic preferences.
They are part of trust, legibility, and dramatic continuity.

## Current player-shell strengths

The active package already carries strong proof for:

- launcher/start flow,
- shell load continuity,
- execute → observe → render loop,
- authoritative observation refresh,
- cached fallback handling,
- and re-entry/bootstrap recovery.

## Player obligations that remain under-proven

The package still treats these as real obligations, but not as fully closed proof:

- help and recap depth,
- save/load as complete player-facing workflow,
- evaluator-grade accessibility,
- and broader productized shell support behavior.

## Surface-family split

### Player surface
Clean, committed, player-safe dramatic interface.
No privileged operator JSON.

### Operator surface
Diagnostics, governance state, run control, release posture, system health, and admin visibility.

### Authoring/review surface
Writers’ Room, review bundles, context packs, recommendation artifacts, approval and revision flows.

### Technical support surface
Observability, trace payloads, model routing evidence, capability audit, and reproduction detail.

## Ordinary-player versus operator separation

The package remains correct to insist that:

- the player shell is not an operator cockpit,
- diagnosis may be reachable, but not intrusive,
- and privileged runtime or governance data must remain capability-gated.

## What still needs clearer carrying

Admin and operator journeys are real and present, but still spread between:

- canonical docs,
- admin docs,
- technical ops docs,
- validation reports,
- and code surfaces.

This is why the surface family must be read as one system, not as unrelated UI fragments.
