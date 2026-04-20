# Dockerify audit report

## Summary

- **required_service_count**: `4`
- **present_service_count**: `4`
- **finding_count**: `0`
- **warning_count**: `3`
- **migration_on_start**: `True`

## Compose services

- **administration-tool** — ports: `['5001:5001']`, healthcheck: `False`, depends_on: `[]`
- **backend** — ports: `['8000:8000']`, healthcheck: `False`, depends_on: `['play-service']`
- **frontend** — ports: `['5002:5002']`, healthcheck: `False`, depends_on: `['backend']`
- **play-service** — ports: `['8001:8000']`, healthcheck: `True`, depends_on: `[]`

## Strengths

- No deterministic Docker governance gaps were detected in the audited surfaces.
- play-service healthcheck is explicitly declared in compose.
- backend waits for play-service health before startup.
- backend Docker entrypoint upgrades the database schema on startup.
- Repository contains startup smoke tests for backend, admin tool, and engine.

## Warnings

- administration-tool has no compose healthcheck; startup confidence relies on smoke tests and dependent service readiness.
- backend has no compose healthcheck; startup confidence relies on smoke tests and dependent service readiness.
- frontend has no compose healthcheck; startup confidence relies on smoke tests and dependent service readiness.

## Findings

- None.

## Database evidence

- `backend/docker-entrypoint.sh` — exists: `True`
- `backend/migrations` — exists: `True`
- `database/tests/test_database_migrations_and_files.py` — exists: `True`
- `database/tests/test_database_upgrades.py` — exists: `True`
