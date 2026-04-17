# ADR-0010: Governance workflows are event-driven

## Status

Proposed (migrated excerpt from MVP docs)

## Decision

Critical governance events must be emitted and may trigger admin banners, email, Slack, or webhooks.

## Consequences

- operators do not need to manually poll all pages
- failed evaluations and urgent findings become visible
- async multi-role workflows become operational

## Source

Migrated from `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md`