# Docker stack state

- Status: active
- Last edited: 2026-04-17
- Scope: Docker entry path, compose posture, migrations, smoke evidence
- Primary machine report: ../reports/dockerify_audit.json
- Primary markdown report: ../reports/dockerify_audit_report.md

## Current stance

Dockerify treats `docker-up.py` as the canonical operator entrypoint for the local stack and `docker-compose.yml` as the canonical stack declaration.

## Tracking focus

- stable startup without extra local modifications
- visible database / migration posture
- smoke evidence for startup surfaces
- explicit unresolved gaps instead of silent optimism
