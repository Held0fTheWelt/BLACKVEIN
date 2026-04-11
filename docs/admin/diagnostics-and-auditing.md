# Diagnostics and auditing

## Trace correlation

The platform propagates **`X-WoS-Trace-Id`** from browsers/tools through the backend into the play service and LangGraph payloads so operators can tie HTTP calls, turns, and graph diagnostics to one id. Full matrix: [`docs/technical/operations/observability-and-governance.md`](../technical/operations/observability-and-governance.md).

## Capability audit

Governed **MCP-aligned capabilities** (`wos.context_pack.build`, `wos.review_bundle.build`, `wos.transcript.read`) emit **audit rows** with mode, actor, and outcome. Backend exposes session-scoped capability audit for inspection; details in [`docs/technical/integration/MCP.md`](../technical/integration/MCP.md).

## Admin and moderator APIs

Observability doc lists **admin AI-stack** evidence endpoints, **release-readiness** aggregates, **system diagnosis**, and **play-service control** semantics—including honest **`partial`** postures when subsystems are stubbed or environment-sensitive.

## Auditing and improvement workflows

Improvement experiment endpoints return capability audit rows in-band when configured; treat these as **governance evidence**, not player-facing narrative.

## Related

- [Monitoring, logging, and incident response](monitoring-logging-and-incident-response.md)
- [Services and health checks](services-and-health-checks.md)
- [Release and quality gates for operators](release-and-quality-gates-for-operators.md)
