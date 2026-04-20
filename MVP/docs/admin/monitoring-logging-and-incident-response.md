# Monitoring, logging, and incident response

Operator guide for **observing** World of Shadows and **responding** to incidents. Adapt to your hosting environment (Docker, Kubernetes, VM, PaaS).

## What to monitor

| Layer | Signals |
|-------|---------|
| **Processes** | All four services running: backend, frontend, admin tool, play service |
| **HTTP health** | Backend `/health` (or equivalent), play service health route — confirm paths in package docs |
| **Dependencies** | Database connectivity, disk usage, migration version |
| **Latency** | API p95/p99, play turn duration (SLOs are organization-specific) |
| **Errors** | 5xx rate, auth failures spike, WebSocket disconnect rate |

## Logging

- **Centralize** logs from each container/process with **timestamps** and **service labels**.
- **Redact** secrets, tokens, and personal data per policy.
- **Retain** logs long enough for security investigations (define per compliance regime).

### Correlation

Where possible, propagate a **request id** from the frontend through backend to play service calls so operators can trace one user action across services (exact header names depend on implementation—verify in code or API docs).

## Alerting (example categories)

- Health check failures for **any** core service.
- Database connection pool exhaustion.
- Sudden **zero** successful play turns while traffic exists (signals runtime or AI provider issues).
- Elevated **rate limit** or **abuse** triggers if exposed.

Configure thresholds in your observability stack; link on-call rotations in your internal wiki.

## Incident response playbook (outline)

1. **Detect** — alert or user report.
2. **Triage** — identify failing service (frontend vs backend vs play).
3. **Mitigate** — scale, restart, disable non-critical features, rollback release.
4. **Communicate** — status page or operator channel per policy.
5. **Resolve** — root cause fix, migration forward.
6. **Post-incident** — short write-up, doc update, test gap filed.

For **security** incidents, follow [Security and compliance overview](security-and-compliance-overview.md) and isolate affected systems first.

## Evidence and clone safety

Some engineering docs reference **local evidence paths** under `tests/reports/` that may be **gitignored**. **Production incidents** should rely on **centralized logs and metrics**, not repository evidence folders.

## Related

- [Operations runbook](operations-runbook.md)
- [Deployment guide](deployment-guide.md)
