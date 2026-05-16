# Local Langfuse Docker Observability

This setup adds a complete local, self-hosted Langfuse v3 stack for development diagnostics. It is for local runtime observability only. A local Langfuse trace or score is not live/staging proof and must not mutate runtime truth, Commit, Readiness, or `validation_outcome`.

## Architecture

Langfuse runs from `docker-compose.langfuse.yml`, layered on the normal app Compose file:

```bash
python docker-up.py init-env
python docker-up.py --dry-run up
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml config
python docker-up.py up
```

The stack follows Langfuse's current Docker Compose shape: `langfuse-web`, `langfuse-worker`, Postgres, ClickHouse, Redis, and MinIO-compatible object storage. ClickHouse is required by current Langfuse self-hosting.

`python docker-up.py up` starts the app plus local Langfuse by default. `python docker-up.py langfuse-up` is an explicit alias. Use `python docker-up.py --no-langfuse up` only when you need the app-only stack.

## Services And Ports

| Service | Purpose | Host exposure |
| --- | --- | --- |
| `langfuse-web` | Langfuse UI/API | `http://localhost:3000` by default |
| `langfuse-worker` | Async ingestion/evaluation work | internal only |
| `langfuse-postgres` | Langfuse transactional DB | internal only |
| `langfuse-clickhouse` | Langfuse analytics/event store | internal only |
| `langfuse-minio` | Local S3/object storage | `127.0.0.1:9090` API, `127.0.0.1:9091` console |
| `langfuse-redis` | Langfuse queues/cache | internal only |

Runtime containers call Langfuse by Docker service name:

```env
LANGFUSE_HOST=http://langfuse-web:3000
LANGFUSE_BASE_URL=http://langfuse-web:3000
LANGFUSE_MCP_BASE_URL=http://localhost:3000
```

Browser access uses the host port:

```text
http://localhost:3000
```

## Redis Decision

The existing app Redis service is not reused. It is configured as `redis://redis:6379/0`, has no password/key prefix, uses AOF persistence, and stores runtime governance data such as token budgets, cost usage events, evaluation baselines, and rubric weights. Langfuse expects its Redis to support queue/cache workloads with `noeviction` semantics and separate credentials. Sharing DB 0 would risk key collisions and queue/cache policy coupling, so the Langfuse stack uses dedicated `langfuse-redis`.

## Required Environment

`python docker-up.py init-env` materializes generated local secrets in `.env`. Examples live in `.env.example` and `.env.langfuse.example`.

Required local Langfuse infrastructure values:

```env
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=CHANGEME
SALT=CHANGEME
ENCRYPTION_KEY=CHANGEME
LANGFUSE_DB_PASSWORD=CHANGEME
CLICKHOUSE_USER=langfuse
CLICKHOUSE_PASSWORD=CHANGEME
MINIO_ROOT_USER=langfuse
MINIO_ROOT_PASSWORD=CHANGEME
REDIS_PASSWORD=CHANGEME
```

`ENCRYPTION_KEY` must be a 256-bit hex key, equivalent to:

```bash
openssl rand -hex 32
```

Do not commit `.env` or real Langfuse project keys.

## Bootstrap Flow

1. Start the full stack:

   ```bash
   python docker-up.py up
   ```

2. Open `http://localhost:3000`.
3. Create the first Langfuse account, organization, and project.
4. Create project API keys in Langfuse.
5. Add the generated keys to `.env`:

   ```env
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=http://langfuse-web:3000
   LANGFUSE_BASE_URL=http://langfuse-web:3000
   LANGFUSE_ENVIRONMENT=local
   ```

6. Restart/rebootstrap backend and play-service:

   ```bash
   python docker-up.py up backend play-service
   ```

The backend remains the configuration authority. `docker-up.py` imports `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` into the backend observability database through `/api/v1/internal/observability/initialize` only when backend Langfuse credentials are not configured yet. Normal restarts do not overwrite Administration Center changes. To intentionally re-import `.env` credentials and replace the backend Langfuse configuration, set `WOS_LANGFUSE_BOOTSTRAP_OVERWRITE=true` for that bootstrap run. World-engine fetches the governed backend credentials via the internal runtime-config API.

## Runtime Wiring

Only server-side services receive Langfuse credentials:

```text
backend -> LANGFUSE_HOST=http://langfuse-web:3000
play-service/world-engine -> LANGFUSE_HOST=http://langfuse-web:3000
wos-mcp stdio on host -> LANGFUSE_MCP_BASE_URL=http://localhost:3000
```

Frontend services do not receive `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, or `LANGFUSE_HOST`.

`wos-mcp` usually runs as a host-side stdio process from Cursor/Codex/Claude rather than inside Docker. It therefore cannot resolve Docker DNS names like `langfuse-web`; it uses `LANGFUSE_MCP_BASE_URL` or automatically maps `http://langfuse-web:3000` to the published local URL when running outside a container.

When keys are missing, backend/world-engine stay in no-op observability mode. When Langfuse is unreachable, the SDK errors are diagnostic only; runtime execution continues and no healthy success score is fabricated.

## Local-Only Evidence

Local Compose sets:

```env
WOS_LANGFUSE_LOCAL_EVIDENCE=1
WOS_LANGFUSE_TRACING_ENVIRONMENT=local
WOS_LANGFUSE_EVIDENCE_SCOPE=local_langfuse
WOS_LANGFUSE_PROOF_LEVEL=local_only
WOS_LANGFUSE_LIVE_OR_STAGING_EVIDENCE=false
```

Backend and world-engine Langfuse metadata includes:

```json
{
  "environment": "local",
  "evidence_scope": "local_langfuse",
  "proof_level": "local_only",
  "live_or_staging_evidence": false
}
```

World-engine path summaries also expose `runtime_quality`, selected capabilities when present, validator dispatch mode when present, readiness policy input when present, and RAG retrieval provenance/authority fields when the retrieval layer provides them.

## Evaluator And Judge Bootstrap

The repo's canonical evaluator catalog is `ai_stack/langfuse_evaluator_catalog.py`; the human-maintained rubric source is `docs/llm-as-a-judge/LLM-as-a-Judge Definition Table - Judges.csv`. The MCP evaluator handlers are read-only and provide a `wos.evaluators.langfuse_sync_preview` payload; they do not write evaluator definitions or provider keys to Langfuse.

Export the local transfer bundle:

```bash
python scripts/export_langfuse_judges.py --environment local
```

This writes:

```text
docs/generated/langfuse/langfuse_judge_transfer.local.json
docs/generated/langfuse/langfuse_judge_transfer.local.md
```

For local Langfuse evaluators:

1. Configure LLM connections in the Langfuse UI. Use OpenAI, Anthropic, or a local OpenAI-compatible endpoint as appropriate. Do not put provider API keys in Compose files.
2. Create custom categorical LLM-as-a-Judge evaluators from the generated transfer JSON/Markdown.
3. Use the generated local filters; they retarget the production catalog's `Environment=live` to `Environment=local`.
4. Prefer observation-level filters targeting `story.model.generation`.
5. Treat every local judge score as `local_only`; it must not promote release readiness or live evidence.

Langfuse can also run dataset/experiment evaluators locally, but local experiment scores are still development diagnostics unless the same evaluator is explicitly run in staging/live.

## Verification

Static config:

```bash
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml config
python docker-up.py --dry-run up
```

Runtime env in containers:

```bash
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml exec backend printenv LANGFUSE_HOST
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml exec play-service printenv LANGFUSE_HOST
```

Expected value:

```text
http://langfuse-web:3000
```

Smoke trace:

1. Make sure keys are in `.env` and backend observability is enabled.
2. Run a local player turn through the app.
3. Open Langfuse and find a `backend.turn.execute` / `world-engine.turn.execute` trace.
4. Verify metadata includes `evidence_scope=local_langfuse`, `proof_level=local_only`, and `live_or_staging_evidence=false`.

Security checks:

```bash
python -m pytest tests/test_local_langfuse_docker_config.py -q
rg -n "LANGFUSE_SECRET_KEY" frontend administration-tool
```

The `rg` check should only find unrelated docs/tests if expanded beyond source bundles; Compose must not inject secret keys into frontend services.

## Stop And Reset

Stop containers:

```bash
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml down
```

This preserves Langfuse accounts, projects, keys, traces, evaluator definitions, and object storage because the named volumes remain in place.

Reset only Langfuse volumes after stopping:

```bash
docker volume ls | grep langfuse
docker volume rm worldofshadows_langfuse-postgres-data \
  worldofshadows_langfuse-clickhouse-data \
  worldofshadows_langfuse-clickhouse-logs \
  worldofshadows_langfuse-minio-data \
  worldofshadows_langfuse-redis-data
```

Avoid `down -v` with the full app Compose set unless you also intend to delete app Redis and other local state.

## Troubleshooting

- `localhost:3000` is busy: set `LANGFUSE_WEB_PORT=3001`, `NEXTAUTH_URL=http://localhost:3001`, and restart.
- Traces do not appear: confirm backend observability config is enabled and world-engine can fetch credentials from `/api/v1/internal/observability/langfuse-credentials`.
- Langfuse starts slowly: ClickHouse/Postgres/MinIO must become healthy before web/worker are ready.
- Media upload issues: keep `LANGFUSE_MINIO_API_PORT=9090` exposed on localhost for local browser uploads.
- Evaluators do not run: configure an LLM connection in Langfuse UI and target local observations/traces, not `Environment=live`.

References: [Langfuse Docker Compose self-hosting](https://langfuse.com/self-hosting/deployment/docker-compose), [official Langfuse compose file](https://github.com/langfuse/langfuse/blob/main/docker-compose.yml), and [Langfuse LLM-as-a-Judge docs](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge).
