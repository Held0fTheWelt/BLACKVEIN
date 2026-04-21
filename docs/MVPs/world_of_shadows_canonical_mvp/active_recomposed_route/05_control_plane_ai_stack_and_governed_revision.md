# Control plane, AI stack, and governed revision

## Why this family belongs in the MVP

World of Shadows always treated:

- authoring,
- review,
- retrieval,
- AI support,
- settings,
- secrets,
- costs,
- alerts,
- preview isolation,
- rollback,
- and governed revision

as product-shaping concerns, not only later enterprise polish.

## Bounded AI stack role

The intended role split is still:

- SLMs for narrow, cheap, bounded helper work,
- LLMs for heavier scene interpretation and proposal work,
- LangGraph-style orchestration for bounded multi-step runtime or review flows,
- LangChain-style adapters for structured generation,
- RAG for governed contextual support,
- MCP for bounded tooling and capability-gated access.

None of these components outrank engine commit.

## Writers’ Room and review ecosystem

The Writers’ Room remains meaningful MVP truth because it connects:

- retrieval support,
- context-pack assembly,
- structured review artifacts,
- governance review bundles,
- and human decision before canonical promotion.

It is allowed to support canon improvement.
It is not allowed to self-publish canon.

## Settings, secrets, cost, and alerts

The three-plane settings model remains valuable:

1. bootstrap/trust-anchor plane
2. operational governance plane
3. resolved runtime execution plane

This helps prevent hidden configuration from becoming de facto tribal knowledge.

## Preview isolation and rollback

Preview is not commit.
Review artifacts, candidate revisions, and control-plane actions must remain explicitly subordinate to publish and runtime truth.

## Why this whole family needed recomposition

In the current package, these concerns are all present, but split across:

- authoring docs,
- lifecycle docs,
- settings/cost/control-plane docs,
- AI-stack docs,
- technical integrations,
- and governance-ledger material.

They form one governed revision ecosystem and are easier to understand that way.
