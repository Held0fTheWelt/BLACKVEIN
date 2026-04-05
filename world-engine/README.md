# World of Shadows Play Service Prototype

FastAPI-based realtime play service for:

- single-player authored stories
- group story instances with lobby / seats / rejoin
- a future persistent open world

This service now supports the current Flask backend bridge.
The backend owns account authentication and character/save-slot metadata.
The play service owns live runtime state, lobbies, participant presence, and snapshots.

---

## Integration contract

The two services share a ticket contract:

- backend signs short-lived websocket tickets with `PLAY_SERVICE_SHARED_SECRET`
- world-engine verifies them with `PLAY_SERVICE_SECRET`
- as a compatibility convenience, world-engine also accepts `PLAY_SERVICE_SHARED_SECRET` as an env alias

Optional hardening for backend-only endpoints:

- backend sends `X-Play-Service-Key` when `PLAY_SERVICE_INTERNAL_API_KEY` is configured
- world-engine verifies that key on `/api/internal/join-context` and on internal run termination

---

## Local run

```bash
cd world-engine
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Browser client: `http://127.0.0.1:8000/`

---

## Tests (CI, Linux, and dev containers)

Tests import the repository-root `ai_stack` package (see `tests/conftest.py`). Install **development** dependencies so LangChain / LangGraph and **`langchain-core`** (declared in `requirements.txt`) are present:

```bash
# From repository root (same as GitHub Actions engine workflows)
pip install -r world-engine/requirements-dev.txt
```

Or from this directory:

```bash
pip install -r requirements-dev.txt
```

Run pytest:

```bash
cd world-engine
python -m pytest tests/ -q --tb=short
```

**GitHub Actions:** `.github/workflows/engine-tests.yml` and `.github/workflows/pre-deployment.yml` run `pip install -r world-engine/requirements-dev.txt` before engine tests. A Windows-only `.venv` checked into or copied from an archive is **not** usable on Linux (CI, Codespaces, Dev Containers); always install with `pip` in that environment.

**Dev Containers / GitHub Codespaces:** open the repo using `.devcontainer/devcontainer.json`; `postCreateCommand` performs the install above and sets `PYTHONPATH` for `ai_stack` imports.

For SQL-backed local testing:

```bash
docker compose -f docker-compose.play-local.yml up --build
```

---

## Environment

Copy `.env.example` to `.env` and set:

- `PLAY_SERVICE_SECRET` or `PLAY_SERVICE_SHARED_SECRET`
- `PLAY_SERVICE_INTERNAL_API_KEY` when the backend uses one
- `RUN_STORE_BACKEND=json|sqlalchemy`
- `RUN_STORE_URL` for Postgres / SQLite SQL storage
- `BACKEND_API_URL` when you want the play service to sync published authored content from the Flask backend
- `BACKEND_CONTENT_FEED_URL` if you need an explicit published-content feed URL

---

## Notes

- The play service README previously still described the backend bridge as a future step. It now documents the current integration reality.
- The Flask backend still remains the source of truth for logged-in users and launcher-facing metadata.


## Authored content sync

When `BACKEND_API_URL` or `BACKEND_CONTENT_FEED_URL` is configured, the play service can pull the backend-authored published content feed and override matching built-in templates. This makes `God of Carnage` and future adventures available through the same publish path used by the administration tooling while still preserving built-ins as a fallback for local development.
