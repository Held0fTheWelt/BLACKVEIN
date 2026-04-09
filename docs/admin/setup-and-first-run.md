# Setup and first run

Operator-focused **first boot** of the four-application stack: **backend**, **play service** (world-engine), **frontend**, and **administration tool**.

## Read first

- [Deployment guide](deployment-guide.md) — Docker Compose topology, environment variables, TLS notes.
- [Operations Runbook (Local)](../operations/RUNBOOK.md) — concrete start commands and default URLs for developer-style machines.

## Minimum sequence

1. Provision a **database** and run **migrations** from the backend (`flask db upgrade` or your release automation).
2. Start the **play service** with secrets aligned to backend `PLAY_SERVICE_*` variables.
3. Start the **backend** with CORS, frontend URL, and play integration variables set.
4. Start **frontend** and **administration tool** with `BACKEND_API_URL` (and play public URL on the frontend) pointing at running services.

Misaligned `PLAY_SERVICE_PUBLIC_URL` (browser) vs `PLAY_SERVICE_INTERNAL_URL` (server-to-server) is a **frequent** cause of “play loads but turns fail.”

## Compose quick reference

See the table in [Deployment guide](deployment-guide.md) for default published ports (`backend`, `frontend`, `administration-tool`, `play-service`).

## After boot

Run the **functional smoke checks** in [Operations runbook](operations-runbook.md) (registration, play session, admin login).

## Related

- [Services and health checks](services-and-health-checks.md)
- [System map (services and data stores)](../start-here/system-map-services-and-data-stores.md)
