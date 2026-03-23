# Verification

How to verify the backend and what each command guarantees. Run all commands from the **backend/** directory (repository path `backend/`).

## Prerequisites

- Python 3.10+ (3.13 recommended)
- Dependencies: `pip install -r requirements.txt` (and `requirements-dev.txt` for pytest-cov if not already present)
- No database or env secrets required for tests: `TestingConfig` uses in-memory SQLite and fixed test secrets.

## Commands

### Full suite (coverage-gated)

```bash
cd backend
pytest
```

- **What it does:** Runs all tests under `backend/tests/` with coverage on `app`. Default `pytest.ini` adds `--cov=app --cov-report=term-missing --cov-fail-under=85`.
- **Expected success:** Exit code 0; all tests pass; coverage report shows ≥85% for `app` (otherwise pytest fails).
- **Note:** Repo-wide 85% coverage is enforced only when this command is run. Do not claim "85% coverage" without having run this and seen a passing result.

### Full suite without coverage (faster)

```bash
cd backend
pytest --no-cov
```

- **What it does:** Runs all tests; no coverage report; no coverage gate.
- **Expected success:** Exit code 0; all tests pass.
- **Use when:** Quick sanity check or CI that does not enforce coverage.

### Targeted modules

```bash
cd backend
pytest tests/test_forum_api.py -v
pytest tests/test_news_api.py -v
pytest tests/test_wiki_public.py -v
pytest tests/test_data_api.py -v
pytest tests/test_api.py tests/test_web.py -v
```

- **What it verifies:** Only the listed modules (forum API, news API, wiki public, data API, auth/web). Does **not** verify the rest of the suite or global coverage.
- **Expected success:** Exit code 0 for the selected tests only.

## What counts as success

- **Exit code 0** and no failing tests in the scope of the command run.
- For **coverage-gated** run: coverage report must show `app` at or above 85%; otherwise pytest exits non-zero.

## Interpreting failures

- **Import errors / missing deps:** Install `requirements.txt` and `requirements-dev.txt` from `backend/`.
- **Database/constraint errors:** Ensure you are using the test config (no custom DATABASE_URI needed; conftest uses in-memory DB). If you see legacy path references, run from `backend/` and use `backend/tests/` in commands.
- **Coverage below 85%:** Either add tests or run without the gate (`pytest --no-cov`) for local iteration; do not claim coverage compliance without a passing gated run.

## Manual verification

- **Management UI / forum / news / wiki:** Manual in-browser checks; no automated E2E in this repo. Postman (or similar) can be used for API flows; see `docs/POSTMAN_FORUM_ENDPOINTS.md` and the Postman collection under `postman/`.
- **Remote backend (PythonAnywhere):** Behaviour against the default remote backend is not automatically tested; local tests run against in-memory DB and test config.

## Summary

| Command | Verifies | Coverage gate |
|--------|----------|----------------|
| `pytest` (from backend/) | Full backend test suite | Yes (85% on app) |
| `pytest --no-cov` | Full backend test suite | No |
| `pytest tests/test_<module>.py -v` | Selected module(s) only | No |

Do not state that "all tests pass" or "QA complete" for the whole repo without having run the full suite from `backend/`. Do not state that 85% coverage is met without a successful `pytest` run (with default options) from `backend/`.
