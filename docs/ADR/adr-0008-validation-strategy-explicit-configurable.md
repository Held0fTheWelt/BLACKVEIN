# ADR-0008: Validation strategy must be explicit and configurable

## Status

Proposed (migrated excerpt from MVP docs)

## Decision

Output validation must expose a strategy: `schema_only`, `schema_plus_semantic`, or `strict_rule_engine`.

## Consequences

- runtime behavior becomes transparent
- environments can trade latency for scrutiny
- test suites can target strategy-specific expectations

## Source

Migrated from `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md`