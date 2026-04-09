# Release and quality gates (for operators)

This page translates **engineering release policy** into **operator-relevant expectations**. Authoritative numeric thresholds and commands live in `docs/testing/RELEASE_GATE_POLICY.md` and `docs/testing/QUALITY_GATES.md`; this summary avoids duplicating every figure.

## What “quality gates” mean for releases

Before production promotion, engineering is expected to run **automated test suites** and **checks** (backend, administration tool, world-engine, AI stack, smoke tests) according to CI workflows under `.github/workflows/`. Operators should:

- Require a **green CI** (or approved exception process) for production deploys.
- Ensure **database migrations** are applied in the correct order with backups.
- Run **smoke tests** in staging that mirror critical user journeys (login, play turn, admin login).

## Pipeline shape (conceptual)

`docs/testing/RELEASE_GATE_POLICY.md` describes a progression such as:

- Fast tests on each change
- Broader suites and coverage before merge to mainline
- Security and contract checks
- Staging validation
- Production deploy with post-deploy smoke

Operators do not need to memorize **every** gate name—**do** need a **checklist** that your organization’s release ticket enforces CI artifact + migration + smoke evidence.

## Operational “go / no-go” inputs

Before approving a deploy window, confirm:

- **Changelog** or release notes reviewed for breaking changes (see repository `CHANGELOG.md`).
- **Config diff** for environment variables (especially play service URLs and secrets).
- **Rollback path** documented (previous container image tag, migration downgrade policy).

## When tests pass but risk remains

Engineering baselines explicitly warn that **passing tests do not prove cross-stack cohesion** for large refactors (see `docs/audit/TASK_1B_CROSS_STACK_COHESION_BASELINE.md`). Operators should treat **first deploy after major AI/runtime changes** as higher risk: extend canary or staging bake time.

## Related

- `docs/testing/RELEASE_GATE_POLICY.md`
- `docs/testing/QUALITY_GATES.md`
- [Operations runbook](operations-runbook.md)
