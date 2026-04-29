# Test Suite Contract

**Status:** Active — 2026-04-26

---

## Canonical Runner

The one canonical test runner is:

```
tests/run_tests.py
```

No other root-level runner may remain active. `tests/run_tests.py`, `run-tests.py`, and any
root-level `run_tests.py` are legacy artifacts and must be absent from the repository root.

---

## Suite Model

| Suite Key | Content | Primary Gate |
|-----------|---------|--------------|
| `backend` | Flask API, services, session surface | YES |
| `frontend` | Player UI service | YES |
| `administration` | Admin proxy and UI | YES |
| `engine` | World-engine runtime, HTTP/WS | YES |
| `database` | Migrations and ORM tooling | YES |
| `ai_stack` | LangGraph runtime, RAG, planning | YES |
| `story_runtime_core` | Builtin templates, adapters, delivery | YES |
| `gates` | MVP foundation gates (architecture enforcement) | YES |
| `root_smoke` | GoC module structure, contract docs smoke | YES |
| `root_integration` | Cross-component integration | YES |
| `root_e2e_python` | Python E2E play flow | YES |
| `root_branching` | Branching logic | YES |
| `root_tools` | Tooling tests | YES |

Optional lanes (not primary gates):
- `playwright_e2e` — requires `--with-playwright`
- `compose_smoke` — requires `--with-compose-smoke`

---

## Primary Suite Prohibitions

No primary suite may contain:

| Pattern | Classification |
|---------|---------------|
| `assert True` | stub — FORBIDDEN |
| `assert 1 == 1` | stub — FORBIDDEN |
| `pass` (as sole test body) | stub — FORBIDDEN |
| `pytest.skip` (required coverage) | FORBIDDEN |
| `pytest.mark.xfail` (required coverage) | FORBIDDEN |
| Field presence only (file exists, JSON has key) | presence-only — FORBIDDEN as gate proof |
| Status code only (returns 200) | string/status-only — FORBIDDEN as gate proof |
| Mock-only for claimed service-boundary behavior | forbidden primary proof |
| Legacy visitor role validation | FORBIDDEN |
| god_of_carnage_solo as canonical content | FORBIDDEN |
| Built-in fallback as canonical proof | FORBIDDEN |

---

## Mock Integration Rules

Mocks are **allowed** for minimal deterministic runtime base:
- Fake external LLM provider while testing engine validation/commit
- Fake Langfuse sink that captures actual emitted payload
- Fake backend HTTP boundary while testing admin rendering of real diagnostics
- Deterministic runtime fixture data for unit/contract tests

Mocks are **forbidden** as primary proof:
- `mock create_run` claimed as live session proof
- `mock backend API` claimed as frontend/backend integration proof
- `mock diagnostics` claimed as diagnostics proof
- `local trace_id field` claimed as Langfuse trace proof
- `patch backend request` claimed as E2E proof

---

## Suite Invocation

```bash
# Run all primary suites
python tests/run_tests.py --suite all

# Run specific suite
python tests/run_tests.py --suite engine
python tests/run_tests.py --suite gates
python tests/run_tests.py --suite story_runtime_core

# Run with scope filter
python tests/run_tests.py --suite backend --scope contracts
python tests/run_tests.py --suite engine --scope integration

# Quick mode (stop on first failure)
python tests/run_tests.py --suite all --quick
```

---

## CI Mirror Requirement

CI must run the same suites as `tests/run_tests.py --suite all`.
CI must NOT use `continue-on-error` or `|| true` for primary suite gates.
