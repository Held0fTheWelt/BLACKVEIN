# Operations, deployment, localization, and live constraints

## Why these concerns belong in the canonical MVP

The early complete MVPs carried a larger set of operational truths that later slice-centered packages did not always restate explicitly.
They remain materially relevant because World of Shadows was never meant to be judged only by prose quality.
It is also judged by whether it can run credibly, scale honestly within MVP bounds, and remain operable.

## Baseline service picture

The preserved operational baseline includes these service classes:

- frontend,
- backend,
- administration tool,
- world-engine,
- relational store,
- vector or search store,
- cache / coordination layer,
- and metrics / observability support.

The reference baseline named in the earlier complete MVPs included PostgreSQL, Redis, Qdrant or equivalent, persistent lexical indexing, and metrics surfaces.
Those exact choices are not the only possible future implementation, but the service-class picture remains canonical.

## Live viability and performance budgets

The complete MVPs preserved concrete live-operation expectations rather than vague hopes.
The canonical target still includes:

- p50 turn latency under roughly two seconds,
- p95 under roughly five seconds,
- p99 under roughly ten seconds,
- bounded token budgets,
- bounded per-turn and per-session cost posture,
- and explicit degraded-mode triggers when latency, cost, or index freshness move out of range.

These are target constraints, not all guaranteed present-day measured results.

## Degraded mode must remain governed

The earlier MVPs and the later v17-v18 runtime-maturity packages agree on the core principle:

- degraded is not the same as unsafe,
- degraded-safe must remain explicit,
- different profiles may degrade differently,
- and some operations must fail closed rather than degrade casually.

This matters especially for authoritative truth, internal auth, and higher-risk semantic or ontological claims.

## Localization and i18n

The earlier complete MVPs preserved a non-trivial localization rule set:

- primary project language stays English,
- runtime language support was expected for at least English, German, and Japanese,
- canonical truth remains language-neutral in data contracts,
- translation memory stays separate from canonical memory,
- names and entity identifiers do not drift per language,
- tone must survive translation,
- and cultural adaptation must remain explicit rather than accidental.

Even if the active slice is not equally proven in all of these areas, they remain part of the canonical target picture.

## Operations and incident posture

The v16-v18 runtime-hardening family sharpened the operational stance further:

- profile classes matter,
- persistence quality must be honestly classified,
- corruption must become incident-visible rather than silently ignored,
- resume behavior must be explicit,
- and packaging / environment credibility matters to any runtime-maturity claim.

## Canonical reading

World of Shadows is not only a dramatic runtime design.
It is also an operational system with explicit live constraints, degraded-mode discipline, deployment expectations, and localization rules.
Those concerns remain canonical even where the present active slice proves only a subset directly.


## Settings governance and resolved runtime posture

The earlier complete MVPs also made an operational point that remains important:
World of Shadows should run from a **resolved runtime posture**, not from scattered hidden assumptions.

That means operators need a governable path for:

- bootstrap and trust-anchor setup,
- runtime mode selection,
- provider/model/route governance,
- retrieval and validation posture,
- and health / alert / budget interpretation.

Those governance expectations are described in more detail in `15_operational_settings_secret_cost_and_control_plane_governance.md`, but they belong in the live-constraints reading too because they affect what the system can safely do in production-like operation.

## Preview isolation and rollback belong to operational maturity

The preserved source set treated preview isolation and rollback as practical operating constraints, not only workflow niceties.
A preview package must not silently become active live truth, and an unstable promotion must remain reversible.

That means live operations maturity includes:

- isolated preview execution,
- inspectable package history,
- promotion readiness checks,
- and rollback paths that are operationally reachable.

## Runtime health and degraded execution are live constraints

World of Shadows should also treat retry/fallback behavior as live-operability signal.
High retry or fallback rates are not only quality notes for later research.
They affect player experience, operator confidence, and cost posture during real operation.

This is one more reason the canonical MVP must carry runtime health, alerts, and degraded-mode visibility as first-class operational truth.
