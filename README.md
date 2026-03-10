# World of Shadows (Blackveign)

Flask-based backend (API, auth, dashboard, news, DB) and a separate Flask frontend (public site, news pages). The frontend consumes the backend API only; no database in the frontend.

## Repository structure

```
Backend/                 # API, auth, dashboard, DB, migrations, tests
  app/                    # create_app, config, models, services, api, web, auth
  migrations/             # Flask-Migrate (Alembic)
  tests/                  # pytest (test_api, test_web, test_news_api, …)
  run.py                  # entrypoint; CLI: init-db, seed-dev-user, seed-news
  requirements.txt, requirements-dev.txt, Dockerfile, pytest.ini
Frontend/                 # Public website
  frontend_app.py         # Flask app: /, /news, /news/<id>
  templates/, static/
  requirements.txt, Dockerfile
README.md, CHANGELOG.md, docker-compose.yml, docs/, .env.example at repo root.
```

## Prerequisites

- Python 3.10+ (3.13 recommended)
- pip

## Environment

Copy `.env.example` to `.env` at the **repo root**. Backend and Frontend both read from the root `.env` when run locally. Set at least:

- **SECRET_KEY**, **JWT_SECRET_KEY** (required in production; or set **DEV_SECRETS_OK=1** for local dev fallbacks).
- **FLASK_APP=run:app** (so Flask finds the app when running from `Backend/`).

Optional for local dev:

- **PORT** – Backend default 5000, Frontend default 5001.
- **BACKEND_API_URL** – Frontend: backend base URL (default `http://127.0.0.1:5000`). No trailing slash.
- **CORS_ORIGINS** – Backend: comma-separated origins allowed to call the API (e.g. `http://127.0.0.1:5001,http://localhost:5001`). Required when the frontend runs on another port.
- **FRONTEND_URL** – Backend: when set, `GET /` and `GET /news` redirect to this URL (e.g. `http://127.0.0.1:5001`).
- **DEV_SECRETS_OK=1** – Enables dev fallback secrets and CLI commands `flask seed-dev-user`, `flask seed-news`.

## Run workflow (local)

### 1. Backend

```bash
cd Backend
pip install -r requirements.txt
flask init-db
flask db upgrade
```

- **init-db** creates tables (optional if you use migrations).
- **db upgrade** applies Alembic migrations (e.g. users, news, role column).

Optional seed (requires **DEV_SECRETS_OK=1**):

```bash
flask seed-dev-user --username dev --password YourPassword1
flask seed-news
```

Start the backend:

```bash
# From Backend/
export FLASK_APP=run:app   # or set in .env
python run.py
# or: flask run
```

Default: **http://127.0.0.1:5000**. Health: `GET /api/v1/health`.

### 2. Frontend

```bash
cd Frontend
pip install -r requirements.txt
python frontend_app.py
```

Default: **http://127.0.0.1:5001**. Open in browser; login/register/dashboard links point to the backend (using **BACKEND_API_URL**). News list and detail load data from `GET /api/v1/news` and `GET /api/v1/news/<id>`.

### 3. CORS (when Backend and Frontend on different ports)

Set in `.env` (or backend environment):

```bash
CORS_ORIGINS=http://127.0.0.1:5001,http://localhost:5001
```

Otherwise the browser blocks frontend requests to the backend API.

## Migrations

From **Backend/**:

```bash
export FLASK_APP=run:app
flask db upgrade
```

Create a new migration after model changes:

```bash
flask db revision -m "description"
# Edit the new file in migrations/versions/, then:
flask db upgrade
```

## Tests

All tests live under **Backend/tests/** (API, web, news API, config, security). Run from **Backend/**:

```bash
cd Backend
pip install -r requirements-dev.txt
pytest
# or: pytest tests/ -v
# or: pytest tests/test_news_api.py tests/test_api.py -v
```

Default pytest config: `pytest.ini` in Backend (testpaths = tests, coverage on `app`).

## Docker (compose)

From **repo root**:

```bash
docker compose up --build
```

- **Backend** at http://localhost:8000 (Gunicorn in container).
- **Frontend** at http://localhost:5001.
- Frontend env **BACKEND_API_URL=http://localhost:8000** so the browser can call the API. Backend env **CORS_ORIGINS** includes http://localhost:5001 so requests from the frontend origin are allowed.

Database is persisted in `Backend/instance/` (mounted volume). Run migrations inside the backend container if needed:

```bash
docker compose exec backend flask db upgrade
```

## Main env variables

| Variable | Where | Description |
|----------|--------|-------------|
| SECRET_KEY | Backend | Session/CSRF (required unless DEV_SECRETS_OK=1) |
| JWT_SECRET_KEY | Backend | JWT signing (required or fallback to SECRET_KEY) |
| FLASK_APP | Backend | Set to `run:app` |
| PORT | Backend / Frontend | Backend default 5000, Frontend default 5001 |
| BACKEND_API_URL | Frontend | Backend base URL for API and auth links (no trailing slash) |
| CORS_ORIGINS | Backend | Comma-separated origins for API (e.g. frontend URL) |
| FRONTEND_URL | Backend | Optional; redirects GET / and GET /news to frontend |
| DEV_SECRETS_OK | Backend | 1 = dev secrets and seed-dev-user / seed-news allowed |
| DATABASE_URI | Backend | Default SQLite in `Backend/instance/wos.db` |

## Documentation

- **Local development (split):** `docs/development/LocalDevelopment.md` – URLs, startup order, how frontend and backend talk, CORS, seed commands.
- **Architecture:** `docs/architecture/FrontendBackendRestructure.md` – Backend/Frontend responsibilities.
- **Runbook:** `docs/runbook.md` – Example flows.
- **Security:** `docs/security.md` – Auth, CSRF, CORS, cookies.
- **Backend tests:** `Backend/tests/README.md` – Fixtures and test modules.

## API (summary)

- **Health:** `GET /api/v1/health`
- **Auth:** `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- **News (public):** `GET /api/v1/news` (list; query: q, sort, direction, page, limit, category), `GET /api/v1/news/<id>` (detail)
- **News (write):** `POST /api/v1/news`, `PUT /api/v1/news/<id>`, `DELETE /api/v1/news/<id>`, `POST /api/v1/news/<id>/publish`, `POST /api/v1/news/<id>/unpublish` – require JWT and editor/admin role.
