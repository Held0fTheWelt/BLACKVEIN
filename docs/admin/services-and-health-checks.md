# Services and health checks

Use **health** and **ready** endpoints in load balancers and monitoring. Exact paths are defined in each service’s README; common themes:

- **Backend** exposes API health suitable for orchestrators.
- **Play service** exposes `/api/health` and readiness variants used by the backend’s **system diagnosis** path.

## Operator diagnosis UI

The administration tool exposes read-only **diagnosis** views backed by backend APIs (JWT + feature flags). For behavior, limits, and trace correlation, see:

- [`docs/technical/operations/observability-and-governance.md`](../technical/operations/observability-and-governance.md) — trace id propagation, audit streams, governance endpoints, **Play-Service control** caveats.

## Environment alignment checklist

| Check | Why it matters |
|-------|----------------|
| `CORS_ORIGINS` includes real browser origins | Prevents silent API failures in admin/player UIs |
| `PLAY_SERVICE_SHARED_SECRET` matches play service | Auth failures on internal play calls |
| `PLAY_SERVICE_PUBLIC_URL` reachable from **browsers** | WebSocket / play bootstrap |
| `PLAY_SERVICE_INTERNAL_URL` reachable from **backend** | Server-side story calls |

## Related

- [Setup and first run](setup-and-first-run.md)
- [Monitoring, logging, and incident response](monitoring-logging-and-incident-response.md)
- [Diagnostics and auditing](diagnostics-and-auditing.md)
