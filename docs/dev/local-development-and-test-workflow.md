# Local development (developer entry)

Canonical **developer** quick start for bare-metal runs. **Docker Compose** uses different published ports for some services—see [Deployment guide](../admin/deployment-guide.md).

## Full detail

Continue here for commands, env vars, and platform notes:

- **[LocalDevelopment.md](../development/LocalDevelopment.md)** — authoritative step-by-step for backend, frontend, admin tool, and play service.

## Defaults at a glance (bare-metal)

| Service | Typical URL |
|---------|-------------|
| Backend | `http://127.0.0.1:5000` |
| Frontend | `http://127.0.0.1:5002` |
| Administration tool | `http://127.0.0.1:5001` |
| Play service | `http://127.0.0.1:8001` |

## Compose vs bare-metal

Root `docker-compose.yml` maps **backend** to host port **8000** (not `5000`). When switching modes, update:

- `BACKEND_API_URL` / `CORS_ORIGINS` / `PLAY_SERVICE_*` variables to match **actual** browser and container DNS names.

## Cross-service testing

- World-engine tests that load `ai_stack` need deps from `world-engine/requirements-dev.txt` (see LocalDevelopment.md Linux/CI section).
- Repo-root smoke: `tests/smoke/` (see [Test pyramid](testing/test-pyramid-and-suite-map.md)).

## Related

- [Contributing and repo layout](contributing.md)
- [Runtime authority and session lifecycle](architecture/runtime-authority-and-session-lifecycle.md)
