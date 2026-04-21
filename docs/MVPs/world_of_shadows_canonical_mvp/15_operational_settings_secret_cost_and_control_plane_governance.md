# Operational settings, secret, cost, and control-plane governance

## Why this document is needed

Another underrepresented truth in the earlier source family is that World of Shadows was never supposed to operate through hidden configuration folklore.

The MVP already assumed that important runtime behavior would eventually need to be:

- discoverable,
- governable,
- secure,
- inspectable,
- and attributable.

That applies to runtime modes, provider routing, retrieval posture, validation posture, credentials, usage, costs, alerts, and control-plane visibility.

## Three-plane settings model

The preserved settings-governance MVPs described a stable three-plane model:

### 1. Bootstrap / trust-anchor plane
This plane exists so the system can be initialized safely and predictably.
It covers first-admin bootstrap, trust-anchor decisions, storage mode, first runtime preset, and first provider setup.

### 2. Operational governance plane
This is the normal administration layer after bootstrap.
It governs providers, models, routes, runtime modes, retrieval modes, validation modes, health, alerts, and budgets.

### 3. Resolved runtime execution plane
This is the server-side resolved configuration that backend, world-engine, AI stack, and related tooling actually consume at runtime.
It exists so execution depends on resolved governed state rather than scattered raw UI values, hidden environment assumptions, or ad hoc code defaults.

## Hidden-config elimination is part of MVP usability

The source set repeatedly pushed against a pattern where critical behavior is hidden in:

- environment variables,
- deployment-only defaults,
- hardcoded runtime choices,
- or scattered registries.

The canonical operator rule is therefore:
normal operational choices should not require code spelunking or tribal memory.

## Runtime mode and route governance remain canonical

World of Shadows preserved a clear expectation that operators should be able to reason about and govern:

- mock mode,
- AI mode,
- hybrid mode,
- retrieval mode,
- validation mode,
- provider/model routing,
- and the active runtime profile.

This does not make admin a second runtime truth boundary.
It makes admin the place where allowed operating posture becomes visible and governable.

## Secret handling rules

The older settings-governance material was explicit enough to remain canonical:

- secrets must be write-only from the UI,
- secrets must be encrypted at rest,
- administration-tool should not become a raw secret reader,
- backend remains the authority for secret storage and resolved runtime configuration,
- and runtime consumers should receive resolved config rather than direct raw secret administration behavior.

The exact storage topology can vary across environments, but the principle does not.

## Cost and usage belong to the MVP, not only to later scale work

The source set did not treat cost visibility as a post-MVP enterprise concern.
It treated cost as part of operator safety for a routed multi-model system.

The canonical MVP therefore carries the expectation that operators can inspect:

- provider and model usage,
- workflow-level usage,
- retry and fallback cost contribution,
- expensive route concentrations,
- and budget-warning or budget-exceeded states.

This matters because runtime mode and route choice are operational product decisions, not invisible engineering details.

## Budget and alert posture

The preserved expectations include at least these policy classes:

- global budgets,
- provider budgets,
- workflow budgets,
- warning thresholds,
- optional hard-stop behavior where justified,
- provider health warnings,
- degraded runtime alerts,
- and unusual fallback-cost spikes.

The MVP does not need a huge financial platform.
It does need enough budget and alert posture that operators can understand whether current runtime behavior is sustainable.

## Administration-tool settings suite remains canonical

The earlier settings-governance MVPs preserved a readable operator-facing suite, including:

- overview,
- providers,
- models,
- routes,
- runtime modes,
- backend settings,
- world-engine settings,
- retrieval,
- costs and usage,
- health and alerts,
- and audit.

The canonical expectation is that current active behavior is inspectable in human language.
The operator should not need to infer actual behavior from a pile of flags.

## MCP control-plane visibility belongs here too

The MCP operations cockpit material remains source-supported and still useful.
Its canonical contribution is not that MCP becomes a second runtime.
Its contribution is that control-plane activity becomes visible and diagnosable.

The minimally preserved operator questions are:

1. Which MCP suites are active?
2. What activity happened recently?
3. What is failing?
4. Which suite is affected?
5. What is the likely diagnosis?
6. Which safe action is available now?

That visibility-first posture fits the broader World of Shadows rule:
control planes may observe, explain, and safely operate, but they may not self-authorize story truth.

## Safe action rule for control-plane operations

The MCP cockpit and related admin actions remain bounded by a strong principle:

- visibility comes before control,
- diagnosis comes before broad mutation,
- and any action surface must stay narrow, explicit, auditable, and capability-gated.

This is why actions such as refresh, retry of bounded jobs, audit-bundle generation, or diagnostic reclassification can be canonical while unrestricted truth mutation cannot.

## Current status reading

This document should be read as follows:

- **Enduring target:** settings governance, secret discipline, cost visibility, alert posture, and MCP control-plane visibility belong to the intended WoS MVP.
- **Implemented in part:** the supplied repository already contains real configuration, route, audit, and diagnostic surfaces, plus operational documentation and tests around pieces of this area.
- **Bounded residue:** the present final archive still should not claim that every one of these governance surfaces has been freshly replayed as a complete polished administration flow in this container.

The material remains canonical because losing it would misdescribe the product.
It remains bounded because honesty still matters more than documentation neatness.
