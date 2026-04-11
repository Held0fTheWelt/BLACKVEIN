# Test strategy and suite layout

Where automated tests live and what they **approximately** cover. Counts drift — use `pytest --collect-only` for current numbers.

## Repository root `tests/`

| Path | Role |
|------|------|
| `tests/smoke/` | Cross-service smoke contracts, module structure smoke |
| `tests/goc_gates/` | CLI/helpers around gate tooling (e.g. G9 threshold validator) |

## `backend/tests/`

Flask API, services, authorization, content, and **runtime** suites under `backend/tests/runtime/` (orchestration, convergence, session contracts). Run targeted paths during development.

## `world-engine/tests/`

Play service HTTP contracts, WebSocket isolation, canonical runtime behavior, backend bridge, trace middleware. Requires `world-engine/requirements-dev.txt` for LangGraph/LangChain stacks.

## `ai_stack/tests/`

Graph executor, GoC scenarios, RAG, LangChain integration, retrieval-heavy paths. Often sensitive to `PYTHONPATH` and editable installs (see root `README.md` testing section).

## `administration-tool/tests/`

Admin UI factory and route contracts.

## `tools/mcp_server/tests/`

MCP tool handlers, filesystem safety, backend client mocks.

## `database/tests/`

Seed and core model tests where present.

## Hygiene and historical filenames

Gate- and closure-oriented **test file names** may stay explicit for engineering traceability; do not rename casually without updating gate inventories.

## Example commands

From repository root (adjust for your venv):

```bash
cd backend && python -m pytest tests/ -q --tb=short
cd ../world-engine && python -m pytest tests/ -q --tb=short
cd .. && python -m pytest tests/smoke -q --tb=short
```

Full orchestration may use `run_tests.py` as described in [`docs/testing/README.md`](../../testing/README.md) and [`docs/admin/release-and-quality-gates-for-operators.md`](../../admin/release-and-quality-gates-for-operators.md).

## Related (contributor)

- [`docs/dev/testing/test-pyramid-and-suite-map.md`](../../dev/testing/test-pyramid-and-suite-map.md) — short contributor-oriented map (kept in sync with this page)
- [`docs/testing/TEST_EXECUTION_PROFILES.md`](../../testing/TEST_EXECUTION_PROFILES.md)
