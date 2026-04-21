# Dependency Blocker Closure Report — 2026-04-21

## Executive summary

This continuation **materially removed the previously active dependency blocker family** that had been recorded as:

- `flask`
- `sqlalchemy`
- `langchain`
- `langgraph`

The repository is now hydratable from repository truth in this environment, the previously blocked Flask- and LangGraph-bearing lanes are runnable, and fresh replays demonstrate that the blocker family is no longer real.

This is **dependency-blocker closure achieved** for the recorded blocker family.
It is **not** a claim that full runtime-proof closure is now complete across every broader ambition lane.

## Starting blocker map

At the start of this continuation, the active blocker record still classified the following as external blockers:

- backend replay blocked by missing `flask` / `sqlalchemy`
- full LangGraph/LangChain replay blocked by missing `langchain` / `langgraph`
- cross-service canonical E2E replay blocked downstream of those missing runtime libraries

## Hydration waves executed

### Wave H1 — Python runtime hydration from repository truth

Used repository manifests and setup surfaces:

- `backend/requirements-test.txt`
- `story_runtime_core/pyproject.toml`
- `ai_stack/pyproject.toml`
- root `pyproject.toml`
- `setup-test-environment.sh`

Executed installs:

- `python -m pip install -r backend/requirements-test.txt`
- `python -m pip install -e ./story_runtime_core`
- `python -m pip install -e './ai_stack[test]'`
- `python -m pip install -e .`

### Wave H2 — Frontend/admin suite boot-path repair

Newly exposed issue after hydration:

- `frontend/tests/conftest.py` still failed at `from app import create_app` under pytest
- root/smoke backend plugin loading also failed because `backend/tests/conftest.py` imported `app` without first binding the backend package root

Repaired files:

- `frontend/tests/conftest.py`
- `frontend/pytest.ini`
- `administration-tool/pytest.ini`
- `backend/tests/conftest.py`

### Wave H3 — Fresh proof replays on unlocked lanes

After hydration and boot-path repair, the previously blocked lanes were rerun.

## What changed materially

1. The missing runtime libraries are now installed and importable.
2. The editable package path from repo root now works (`world-of-shadows-hub` installs successfully).
3. Frontend pytest can now import its own `app` package without manual shell-only `PYTHONPATH` workarounds.
4. Backend-root smoke tests can now load `backend.tests.conftest` under hydrated root execution.
5. Previously blocked Flask-bearing and graph-bearing proof lanes now replay cleanly.

## Current closure judgment

### Closed blocker family

Closed as real blockers:

- `flask`
- `sqlalchemy`
- `langchain`
- `langgraph`

### What is now freshly replay-proven

- frontend full suite: **104 passed**
- ai_stack full suite: **208 passed, 14 skipped**
- backend smoke startup: **29 passed**
- admin smoke startup: **35 passed**
- engine smoke startup: **50 passed**
- backend canonical slices (startup / staged bootstrap / playservice integration / GoC lifecycle / writers-room / game routes): all freshly passing
- administration representative slices (app factory / manage routes / proxy / security headers): all freshly passing
- world-engine graph-bearing slices (`test_story_runtime_rag_runtime`, `test_story_runtime_api`, `test_api`): freshly passing

### What remains outside this closure claim

The remaining non-pass area observed here is **not the original dependency blocker family**.
The remaining partial area is the embedding-backed fastembed model path, where the package is installed but the model asset cannot be acquired in this host DNS context.
That leaves 14 AI-stack tests skipped. This is a **model-artifact/runtime-network residual**, not a missing `langchain` / `langgraph` / `flask` / `sqlalchemy` dependency blocker.
