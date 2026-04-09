# Test pyramid and suite map

Where tests live and what they **approximately** cover. Counts change—use `pytest --collect-only` for current numbers.

## Repository-root `tests/`

| Path | Role |
|------|------|
| `tests/smoke/` | Cross-service smoke contracts, module structure smoke |
| `tests/goc_gates/` | CLI/helpers around gate tooling (e.g. G9 threshold validator) |

## `backend/tests/`

Flask API, services, authorization, content, and **runtime** suites under `backend/tests/runtime/` (orchestration, convergence, session contracts, etc.). Large breadth—run targeted paths during development.

## `world-engine/tests/`

Play service HTTP contracts, WebSocket isolation, canonical runtime behavior, bridge to backend, trace middleware, etc. Requires `world-engine/requirements-dev.txt` for LangGraph/LangChain stacks.

## `ai_stack/tests/`

Graph executor, GoC phase scenarios, RAG, LangChain integration, retrieval-heavy paths. Often sensitive to `PYTHONPATH` and editable installs (see root `README.md` Testing section).

## `administration-tool/tests/`

Admin UI factory and route contracts.

## `tools/mcp_server/tests/`

MCP tool handlers, filesystem safety, backend client mocks.

## `database/tests/`

Seed and core model tests where present.

## Hygiene notes

- Task 3 documented renames/splits of historical filenames—see `docs/audit/TASK_3_P0_P1_EXECUTION_INVENTORY.md` and `docs/audit/TASK_3_VALIDATION_REPORT.md`.
- **Gate** and **closure** filenames may remain **intentionally** explicit for engineering traceability—do not rename casually.

## Suggested commands (examples)

From repository root (adjust for your venv):

```bash
cd backend && python -m pytest tests/ -q --tb=short
cd world-engine && python -m pytest tests/ -q --tb=short
cd .. && python -m pytest tests/smoke -q --tb=short
```

Full orchestration may use `run_tests.py` as described in `docs/testing/README.md` and release gate docs.

## Related

- [Test strategy and suite layout (technical)](../../technical/reference/test-strategy-and-suite-layout.md)
- `docs/testing/README.md`
- `docs/testing/TEST_EXECUTION_PROFILES.md`
- [Release and quality gates for operators](../../admin/release-and-quality-gates-for-operators.md)
