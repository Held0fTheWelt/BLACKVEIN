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
- world-engine verifies that key on `/api/internal/join-context`

---

## Local run

```bash
cd world-engine
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Browser client: `http://127.0.0.1:8000/`

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

---

## Notes

- The play service README previously still described the backend bridge as a future step. It now documents the current integration reality.
- The Flask backend still remains the source of truth for logged-in users and launcher-facing metadata.
