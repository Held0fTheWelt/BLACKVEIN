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

---

## Contract vs live test tiers (Langfuse / runtime evidence)

**Contract tests (primary suites):** Mocks/spies are **allowed** when they prove **local wiring and schema contracts** (for example: `LangfuseAdapter.start_trace` receives `player_input_sha256`; World-Engine span names and score hooks are invoked). These tests must not claim full-cloud or full-stack truth.

**Live tests (opt-in gate):** A **running HTTP stack**, **real Langfuse ingestion**, and **no adapter mocks** for the asserted path. When `RUN_LANGFUSE_LIVE=1` and credentials/URLs are present, failures are **hard** (no `pytest.skip` because `get_trace` failed). The canonical strict gate is `backend/tests/test_observability/test_langfuse_live_c640_gate.py` (marker `langfuse_live`). Standard `python tests/run_tests.py --suite backend` remains green without live secrets because that test skips unless `RUN_LANGFUSE_LIVE=1`.

Live-gate semantics must include both:
- **positive reference** (c640-style): healthy, non-fallback, `live_runtime_contract_pass=1`
- **negative reference** (a599-style): visible output may exist, but fallback/degraded traces **must** stay red (`live_runtime_contract_pass=0`)

**Trace-level score duplicates (Langfuse):** Observation-level scores alone are **not** sufficient for operator UX and JSON export parity. For every deterministic gate score emitted during story execution, the implementation must **also** submit a **trace-level** duplicate (see ADR-0033 §13.5). Contract tests assert the wiring; live tests assert end-to-end scores on the fetched trace.

---

## Frontend JS unit tests (MVP5)

`frontend/tests/*.js` Jest specs are part of the **frontend** and **mvp5** suites. After the pytest slice for `frontend/tests` (Python), `tests/run_tests.py` runs `npm test` in `frontend/` so `.js` tests are not a false-green dead lane.

MVP5 renderer/typewriter contract:
- single active typewriter block at a time
- latest unresolved block is active; prior blocks are finalized immediately
- dramatic block families (`narrator_scene`, `narrator_perception`, `actor_line`, `actor_action`, `stage_shift`) are player-visible blocks
- diagnostics/debug blocks are not rendered as normal player-visible narrative content
