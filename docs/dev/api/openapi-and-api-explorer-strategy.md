# OpenAPI and API explorer strategy

Plan for how HTTP APIs are **documented** and **discovered** in World of Shadows.

## Current state

- A large **Markdown** backend reference exists: [`docs/api/REFERENCE.md`](../../api/REFERENCE.md).
- Backend serves **technical HTML** under `/backend/*` (see root `README.md`); templates live under `backend/app/info/templates/` (e.g. `api.html`).
- **OpenAPI inventory:** [`docs/api/openapi.yaml`](../../api/openapi.yaml) is generated from registered Flask routes via [`backend/scripts/generate_openapi_spec.py`](../../../backend/scripts/generate_openapi_spec.py) (`--write` / `--check`). Served at **`/backend/openapi.yaml`**; **Redoc** UI at **`/backend/api-explorer`**.
- Tag taxonomy and mapping to info pages: [`docs/api/openapi-taxonomy.md`](../../api/openapi-taxonomy.md).
- Postman assets: `docs/api/POSTMAN_COLLECTION.md` and `postman/` tree.

## Gaps

- OpenAPI operations are **stubs** (summary + generic responses); request/response shapes and examples remain in **`REFERENCE.md`** until schemas are added incrementally.
- **World Engine** (FastAPI) OpenAPI is separate; link from backend docs, do not merge into this file.

## Recommended direction

1. **Short term:** Keep `REFERENCE.md` authoritative for human readers; fix drift via PR checklist when routes change.
2. **Medium term (partially done):** Path inventory + tags + Redoc under **`/backend/api-explorer`**; extend spec with **request/response schemas** (e.g. `apispec` + decorators, or curated components) and optional **Swagger UI** for try-it-out.
3. **Play service:** If public HTTP surface grows beyond health checks, mirror the same approach for FastAPI (native OpenAPI) and **link** from developer docs—do not duplicate prose in three places.

## Consumer expectations

- **Developers** — versioned OpenAPI + examples + error contracts.
- **Operators** — health/readiness endpoints documented in runbooks, not full OpenAPI.
- **Agents/MCP** — follow `tools/mcp_server/README.md`; MCP is **not** a substitute for authenticated REST semantics.

## Related

- [`docs/api/README.md`](../../api/README.md)
- [Normative contracts index](../contracts/normative-contracts-index.md)
