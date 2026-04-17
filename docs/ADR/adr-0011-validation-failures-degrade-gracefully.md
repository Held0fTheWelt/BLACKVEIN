# ADR-0011: Validation failures in live play must degrade gracefully

## Status

Proposed (migrated excerpt from MVP docs)

## Decision

A rejected model output must not produce a player-visible dead end. Runtime must attempt corrective recovery and, if needed, emit a guaranteed safe fallback response.

## Consequences

- every playable scene needs fallback content
- runtime needs explicit retry/fallback telemetry
- operator tooling must surface fallback spikes
- degraded quality is acceptable for continuity; broken turns are not

## Source

Migrated from `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md`