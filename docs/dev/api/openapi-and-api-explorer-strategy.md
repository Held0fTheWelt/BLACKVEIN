# OpenAPI and API explorer strategy

Plan for how HTTP APIs are **documented** and **discovered** in World of Shadows.

## Current state

- A large **Markdown** backend reference exists: [`docs/api/REFERENCE.md`](../../api/REFERENCE.md).
- Backend serves **technical HTML** under `/backend/*` (see root `README.md`); templates live under `backend/app/info/templates/` (e.g. `api.html`).
- Postman assets: `docs/api/POSTMAN_COLLECTION.md` and `postman/` tree.

## Gaps

- No single **generated OpenAPI** artifact is guaranteed to track every Flask route in this repository snapshot—treat route lists as **code-derived truth** when in doubt (search `backend/app/api/`).

## Recommended direction

1. **Short term:** Keep `REFERENCE.md` authoritative for human readers; fix drift via PR checklist when routes change.
2. **Medium term:** Introduce **OpenAPI generation** for Flask (e.g. `apispec` + decorators, or manual YAML curated per version) and publish:
   - Static **Redoc** or **Swagger UI** under `/backend/api-explorer` (or dedicated docs site via MkDocs).
3. **Play service:** If public HTTP surface grows beyond health checks, mirror the same approach for FastAPI (native OpenAPI) and **link** from developer docs—do not duplicate prose in three places.

## Consumer expectations

- **Developers** — versioned OpenAPI + examples + error contracts.
- **Operators** — health/readiness endpoints documented in runbooks, not full OpenAPI.
- **Agents/MCP** — follow `tools/mcp_server/README.md`; MCP is **not** a substitute for authenticated REST semantics.

## Related

- [`docs/api/README.md`](../../api/README.md)
- [Normative contracts index](../contracts/normative-contracts-index.md)
