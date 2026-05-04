# ADR-0030: docker-up.py Complete Bootstrap Implementation

## Status

Accepted

## Date

2026-05-04

## Intellectual property rights

Repository authorship and licensing: see project LICENSE; contact maintainers for clarification.

## Privacy and confidentiality

This ADR contains no personal data. Implementers must follow repository confidentiality policies and avoid committing secrets to .env examples.

## Related ADRs

- [ADR-0026](adr-0026-mcp-host-and-runtime-phase-a.md) — MCP transport foundations for internal endpoints
- [ADR-0028](adr-0028-mcp-security-baseline-phase-a.md) — Security baseline for internal endpoints (`/api/v1/internal/*`)

## Context

`docker-up.py` is the canonical entry point for local development and operator-guided first startup. Before this decision, it would start containers and report "Bootstrap is required" but leave operators to:

1. Discover and navigate to the Bootstrap UI endpoint
2. Create admin users manually (outside docker-up.py)
3. Troubleshoot failures without clear error reporting

This created friction and hidden failure modes. **The decision:** docker-up.py becomes a **zero-click, fully automated bootstrap** that guarantees a ready-to-use system or fails loudly with diagnostic guidance.

**Key constraint:** No silent failures on configured features. If a feature is enabled (e.g., `LANGFUSE_ENABLED=true`), it must initialize successfully or docker-up.py must block.

## Decision

1. **docker-up.py enforces a strict initialization sequence:**
   - Ensure `.env` with all required secrets
   - `docker compose up -d --build` (backend runs migrations + automatic base governance seeding in entrypoint before becoming healthy)
   - Poll backend healthcheck (wait for migrations and seeding to complete)
   - Create admin user via `POST /api/v1/internal/bootstrap/admin-user`
   - Initialize Langfuse (if configured) via `POST /api/v1/internal/observability/initialize`
   - Report final bootstrap status

2. **Automatic base governance seeding (backend entrypoint):**
   - After migrations (`flask db upgrade`), backend automatically seeds foundational governance data
   - Seeding includes: bootstrap presets, mock provider, mock models, default AI task routes
   - Implementation: `backend/docker-entrypoint.sh` calls `flask seed-base-governance-setup`
   - `flask seed-base-governance-setup` (in `cli_ops.py`) invokes idempotent service functions
   - This ensures operators never have an empty AI runtime config after docker-compose up

3. **Error handling:** Each step has a distinct exit code (0=success, 1=docker, 2=migrations, 3=admin-user, 4=langfuse, 5=backend, 6=env). No silent failures on configured features.

4. **Idempotency:** Running docker-up.py twice is safe — admin user creation succeeds silently if user already exists. Seeding functions skip if data already present.

5. **Implementation:** Use stdlib only (no external pip packages). Timeout all HTTP calls to 5s. All errors to stderr.

## Consequences

**Positive**

- ✓ Operators run `python docker-up.py up` once. System is ready.
- ✓ Consistent workflows; no hidden setup tasks or shell commands.
- ✓ Retry-safe; running twice produces the same result.
- ✓ CI/CD friendly; differentiated exit codes enable scripting.
- ✓ Clear error messages guide operators to recovery steps.

**Negative / risks**

- ⚠ Default admin credentials (admin/Admin123) are discoverable in code. Operator must change password immediately. Documented in UI.
- ⚠ If initialization fails, docker-up.py blocks. Operator must fix root cause and retry (intentional; silent failures hide problems).

**Follow-ups**

- Add /api/v1/internal/bootstrap/admin-user endpoint to backend (see Implementation below)
- Add comprehensive test suite (see Testing below)
- Consider future password rotation / multi-admin support

## Testing

### Verification Checklist

**First run (clean environment):**
- [ ] `rm -rf .env backend/instance/wos.db` + `docker-compose down -v`
- [ ] `python docker-up.py init-env` creates `.env` with all secrets
- [ ] `python docker-up.py up` succeeds, exit code 0
- [ ] Migrations completed (backend entrypoint runs `flask db upgrade`)
- [ ] Base governance seeded (backend entrypoint runs `flask seed-base-governance-setup`): presets, mock provider, mock models, default routes present
- [ ] Admin user created: `curl http://localhost:8000/api/v1/bootstrap/public-status`
- [ ] Bootstrap page loads: `curl http://localhost:5001/manage/operational-governance/bootstrap`
- [ ] Admin login works: `curl -X POST http://localhost:8000/api/v1/auth/login -d '{"username":"admin","password":"Admin123"}'`
- [ ] Admin user is SuperAdmin: role.name="admin" and role_level=100 per ROLE_HIERARCHY.md; can access admin features
- [ ] AI Runtime initialized: `/api/v1/admin/ai/providers` returns empty provider list (seeding did not create real providers, only mock)

**Idempotency test (second run):**
- [ ] `python docker-up.py up` succeeds again, exit code 0
- [ ] No "user already exists" error (silent continue)
- [ ] Admin login still works

**Error scenarios:**
- [ ] Delete `users` table → `python docker-up.py up` exits with code 3 (admin user creation failed)
- [ ] Break migrations → exit code 2 (migrations failed)
- [ ] Set `LANGFUSE_ENABLED=true` with bad credentials → exit code 4 (langfuse failed, not silent)
- [ ] Make `/api/v1/health` hang → exit code 5 (backend healthcheck timeout)

### Acceptance Test Suite Location

`tests/test_docker_up_complete_bootstrap.py` (TBD)

**Tests must cover:**
- First-run initialization (all steps complete)
- Idempotent retry (second run succeeds)
- Each error scenario returns correct exit code
- Error messages are actionable (not vague)

## Known Limitations

1. **First startup timing:** On very first startup, admin user creation may silently continue if backend is not yet fully initialized (healthcheck says healthy, but migrations still running). Running docker-up.py twice is idempotent and will complete the initialization.

## References

- `docker-up.py` — Entry point implementation and bootstrap orchestration
- `backend/run.py` — Flask CLI command `seed-base-governance-setup`
- `backend/app/cli_ops.py` — `seed_base_governance_setup()` function
- `backend/docker-entrypoint.sh` — Runs migrations + automatic seeding before healthcheck
- `backend/app/services/governance_runtime_service.py` — `_seed_default_presets()`, `_ensure_default_mock_path()`
- `backend/app/api/v1/operational_governance_routes.py` — `/api/v1/internal/bootstrap/admin-user` endpoint  
- `docker-compose.yml` — Healthcheck configuration, dependency ordering
- `backend/docs/ROLE_HIERARCHY.md` — Role and SuperAdmin definition
