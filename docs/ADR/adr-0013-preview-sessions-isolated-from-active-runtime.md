# ADR-0013: Preview sessions must be isolated from active runtime

## Status

Proposed (migrated excerpt from MVP docs)

## Decision

Preview packages are executable only inside explicitly isolated preview sessions. Active live sessions may never accidentally resolve against a preview package.

## Consequences

- preview execution must use explicit session namespace or isolated loader
- reload semantics for active and preview paths must stay distinct
- admin actions must show whether a package is active or preview-only

## Source

Migrated from `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md`