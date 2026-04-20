# Better Tomorrow / World of Shadows Backend

Flask-based control plane for the project. The backend owns:

- account and session/JWT authentication
- admin and moderation features
- news, wiki, forum, slogans, site settings
- game launcher data such as character profiles and save-slot metadata
- ticket issuance and authority bridging into the separate `world-engine` play service

The backend is **not** the realtime runtime. Multiplayer state, lobbies, and snapshots live in `../world-engine`.

---

## Local development

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment

Copy `backend/.env.example` to `backend/.env` or use the repo-root `.env`.
Set at least:

- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `FLASK_APP=run:app`

For the game launcher bridge also set:

- `PLAY_SERVICE_INTERNAL_URL`
- `PLAY_SERVICE_PUBLIC_URL`
- `PLAY_SERVICE_SHARED_SECRET`
- optional `PLAY_SERVICE_INTERNAL_API_KEY`

### 3. Initialize the database

```bash
cd backend
flask init-db
flask db upgrade
```

### 4. Start the backend

```bash
cd backend
python run.py
```

Default local URL: `http://127.0.0.1:5000`

---

## Backend ↔ play-service integration

The backend remains the authority for authenticated users.
The `world-engine` remains the authority for live runtime state.

Current launcher flow:

1. user logs into the Flask backend
2. `/game-menu` loads launcher bootstrap data from `/api/v1/game/bootstrap`
3. backend lists templates/runs through the play service internal API
4. backend resolves the join context with the play service
5. backend signs the final short-lived websocket ticket
6. browser connects directly to the play service websocket

This means the shared secret must match across both services:

- backend: `PLAY_SERVICE_SHARED_SECRET`
- world-engine: `PLAY_SERVICE_SECRET` or `PLAY_SERVICE_SHARED_SECRET`

---

## Game-facing backend endpoints

- `GET /api/v1/game/bootstrap`
- `GET /api/v1/game/templates`
- `GET /api/v1/game/runs`
- `POST /api/v1/game/runs`
- `POST /api/v1/game/tickets`
- `GET /api/v1/game/characters`
- `POST /api/v1/game/characters`
- `PATCH /api/v1/game/characters/<id>`
- `DELETE /api/v1/game/characters/<id>`
- `GET /api/v1/game/save-slots`
- `POST /api/v1/game/save-slots`
- `DELETE /api/v1/game/save-slots/<id>`
- `GET /api/v1/game/content/published`
- `GET /api/v1/game/content/experiences` (moderator/admin)
- `POST /api/v1/game/content/experiences` (moderator/admin)
- `GET /api/v1/game/content/experiences/<id>` (moderator/admin)
- `PATCH /api/v1/game/content/experiences/<id>` (moderator/admin)
- `POST /api/v1/game/content/experiences/<id>/publish` (moderator/admin)
- `GET /api/v1/game/ops/runs` (moderator/admin)
- `GET /api/v1/game/ops/runs/<run_id>` (moderator/admin)
- `GET /api/v1/game/ops/runs/<run_id>/transcript` (moderator/admin)
- `POST /api/v1/game/ops/runs/<run_id>/terminate` (moderator/admin)

---

## Tests

Run from `backend/`:

```bash
PYTHONPATH=. pytest --no-cov
```

Focused launcher/game route tests:

```bash
PYTHONPATH=. pytest tests/test_game_routes.py tests/test_config.py --no-cov -q
```

---

## Docker

`backend/Dockerfile` builds the Flask backend and runs it with Gunicorn.
For a quick local integration setup, use:

```bash
docker compose -f backend/docker-compose.play-local.yml up --build
```

That compose file starts:

- the Flask backend
- the `world-engine` play service
- Postgres for the play service runtime store

---

## Notes

- The backend README previously drifted into play-service prototype documentation; this file now reflects the actual Flask backend again.
- The backend requirements and Dockerfile also align with Flask/Gunicorn again rather than FastAPI/Uvicorn.


## Authored content and operations

The backend now owns authored experience definitions and publishing state. Published experiences are exposed through `/api/v1/game/content/published`, which the world-engine may consume as its authored content feed. Moderator/admin tooling can inspect, edit, publish, and operate runs through the `game/content/*` and `game/ops/*` endpoints while the regular launcher flow continues to use `/api/v1/game/bootstrap`, `/api/v1/game/runs`, and `/api/v1/game/tickets`.
