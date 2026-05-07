# Coverage semantics (orchestrator + pytest-cov)

This document explains **what** repository coverage numbers mean, **which files stay in sync**, and what they **do not** prove. It complements [`tests/TESTING.md`](../../tests/TESTING.md) and the implementation in [`tests/run_tests.py`](../../tests/run_tests.py).

## Single source of truth

| Location | Role |
|----------|------|
| [`tests/run_tests.py`](../../tests/run_tests.py) | `BACKEND_APP_ROOT`, …, `_cov_fail_under_for_suite()`, `_cov_sources_for_suite()`, `_append_cov_flags()`. Backend **sub-suites** (`backend_runtime`, `backend_observability`, …) set `supports_coverage=False` so partial runs do not apply the full-backend fail-under. See [ADR-0037](../ADR/adr-0037-backend-test-suite-split-runner.md). |
| [`administration-tool/pytest.ini`](../../administration-tool/pytest.ini) + [`.coveragerc`](../../administration-tool/.coveragerc) | **`--cov=.`** + **`--cov-fail-under=80`** — same as runner **administration** suite (avoids multiple `--cov=module` Coverage.py 7.x warnings). |
| [`world-engine/pytest.ini`](../../world-engine/pytest.ini) | **`--cov=app`** + **`--cov-fail-under=80`** + term-missing report (matches runner **engine** suite). |
| [`database/pytest.ini`](../../database/pytest.ini) | **`--cov=app`** (backend ORM tree) + term-missing **without** **`--cov-fail-under`** — same roots as runner **database** suite; no percentage gate (see below). |

[`administration-tool/pyproject.toml`](../../administration-tool/pyproject.toml) and [`world-engine/pyproject.toml`](../../world-engine/pyproject.toml) carry a short pointer comment; executable defaults remain in **`pytest.ini`**.

### Backend directory sub-suites (orchestrator)

The suite keys `backend_runtime`, `backend_observability`, `backend_services`, `backend_content`, `backend_routes_core`, `backend_mcp`, and `backend_rest` do **not** carry a separate row in the table above: the orchestrator **does not** enforce `--cov-fail-under` for them. Use **`--suite backend`** for the **85** gate on `backend/app`.

## What is measured

- **`pytest-cov`** records Python lines executed during **in-process** pytest runs (Flask/FastAPI test clients, mocked I/O, etc.).
- Standard suites avoid bare **`--cov=.`**; roots are explicit paths or import names (administration tool uses **import names** because the app is not a single nested package).

## Per-suite roots and gates

| Suite / tree | `--cov=` roots | `--cov-fail-under` (orchestrator) | Component `pytest.ini` |
|--------------|----------------|-------------------------------------|-------------------------|
| **backend** | `backend/app` | 85 | see `backend/pytest.ini` (own policy) |
| **frontend** | `frontend/app` | 90 | see `frontend/pytest.ini` |
| **writers_room** / **improvement** | `backend/app` | 50 | *(slice runs under `backend/`)* |
| **administration** | Project root **`.`** (tree under `administration-tool/`, tests omitted via `.coveragerc`) | 80 | **`--cov=. --cov-config=.coveragerc`**, **80** |
| **engine** | `world-engine/app` (filesystem path in runner; `app` package when `cwd` is `world-engine/`) | 80 | **`--cov=app`**, **80** |
| **database** | `backend/app` | **none** | **`--cov=app`**, no fail-under |
| **ai_stack** | `ai_stack/` | 80 | see `ai_stack/pyproject.toml` |

### Database vs backend overlap (intentional)

- There is **no** `database/` application package — only [`database/tests/`](../../database/tests/).
- Tests import SQLAlchemy models from **`backend/app`**. Measuring **`backend/app`** is therefore correct for “what exercised the schema contract,” but the suite touches **only a fraction** of that tree.
- A numeric **fail-under on the entire `backend/app`** would either fail always (~22% total line coverage on a full database run) or invite a misleadingly low bar. **Policy:** instrument with **`--cov=app`** for visibility; **do not** enforce **`--cov-fail-under`** for the **database** suite in the orchestrator or in `database/pytest.ini`.

## Direct pytest (without the orchestrator)

Equivalent **coverage** invocations (from each component root):

**Administration tool** (single trace — matches `pytest.ini` defaults):

```bash
cd administration-tool
python -m pytest tests \
  --cov=. --cov-config=.coveragerc \
  --cov-report=term-missing --cov-fail-under=80
```

**World engine:**

```bash
cd world-engine
python -m pytest tests --cov=app --cov-report=term-missing --cov-fail-under=80
```

**Database** (uses `pythonpath` in `database/pytest.ini` so `app` resolves to `../backend/app`):

```bash
cd database
python -m pytest tests --cov=app --cov-report=term-missing
```

For **partial** world-engine or administration runs, coverage percentage may drop below **80**; use **`pytest --no-cov`** or accept a red fail-under when narrowing files — the **full** suite is the reference for the **80** gate.

## Fail-under meaning

Where present, numeric gates catch **accidental loss of tests** or huge untested additions inside the **declared roots**. They are **not**:

- proof of production safety,
- proof of cross-service correctness,
- proof of browser or JS behaviour.

## What coverage does **not** measure

- Real HTTP/TLS, reverse proxies, or header edge cases.
- Browser/JavaScript (`frontend/static/`, admin static assets).
- True multi-worker concurrency or database contention under load.
- LLM output variability, token limits, or provider outages.

For those gaps, use optional Compose smoke, Playwright, and dedicated load/concurrency work — see [`tests/TESTING.md`](../../tests/TESTING.md) and [`tests/smoke/compose_smoke/README.md`](../../tests/smoke/compose_smoke/README.md).
