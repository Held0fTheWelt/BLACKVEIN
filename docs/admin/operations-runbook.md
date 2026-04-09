# Operations runbook

Canonical **operator entry** for running and troubleshooting World of Shadows. Detailed step-by-step local procedures remain in [Operations Runbook (Local)](../operations/RUNBOOK.md); this page adds **cross-links** and **escalation** guidance for production-minded operators.

## Quick reference: service URLs

Defaults differ between **Docker Compose** and **bare-metal** dev; confirm your deployment sheet.

| Service | Typical purpose |
|---------|-----------------|
| Frontend | Player/public UI |
| Administration tool | Admin UI |
| Backend | APIs, auth, persistence |
| Play service | Authoritative runtime |

See [Deployment guide](deployment-guide.md) for Compose port mapping and [Local development and test workflow](../dev/local-development-and-test-workflow.md) for developer defaults.

## Startup order

1. Database available and migrated.
2. **Play service** reachable.
3. **Backend** up with correct play integration env vars.
4. **Frontend** and **administration tool** pointing at the backend.

The local runbook spells out commands: `docs/operations/RUNBOOK.md`.

## Functional smoke checks

From `docs/operations/RUNBOOK.md`:

- Player can register/login via frontend.
- Play session can start and accept input.
- Admin can sign in via administration tool.

Re-run these after any infrastructure change.

## Logs and debugging

| Symptom | First checks |
|---------|----------------|
| 401/403 from APIs | JWT secret drift, clock skew, cookie/TLS settings |
| CORS errors | `CORS_ORIGINS` vs actual browser origin |
| Play disconnects | `PLAY_SERVICE_PUBLIC_URL` from browser vs internal URLs; WebSocket proxy timeouts |
| Stuck turns | Play service logs; backend proxy logs; see [AI stack seams](../dev/architecture/ai-stack-rag-langgraph-and-goc-seams.md) for engineering escalation |

Aggregate logs in your platform (systemd journal, Docker logging driver, ELK, CloudWatch, etc.)—implementation-specific.

## Escalation to engineering

Escalate with:

- Timestamp, request id/correlation id if present.
- Affected user/session id (redacted as per policy).
- Whether failure is **backend**, **play**, or **frontend** scoped.
- Repro steps on **staging** if available.

Developers use [Test pyramid and suite map](../dev/testing/test-pyramid-and-suite-map.md) and [Test strategy (technical)](../technical/reference/test-strategy-and-suite-layout.md) to reproduce with pytest.

## Incidents and security

- [Monitoring, logging, and incident response](monitoring-logging-and-incident-response.md)
- [Security and compliance overview](security-and-compliance-overview.md)

## Related

- [Deployment guide](deployment-guide.md)
- [Release and quality gates for operators](release-and-quality-gates-for-operators.md)
