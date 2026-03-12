# World of Shadows (Blackveign)

Flask-based backend (API, auth, dashboard, news, DB) and a separate Flask frontend (public site, news pages). The frontend consumes the backend API only; no database in the frontend.

## Repository structure

```
backend/                  # API, auth, dashboard, DB, migrations, tests
  app/                    # create_app, config, models, services, api, web, auth
  migrations/             # Flask-Migrate (Alembic)
  tests/                  # pytest (test_api, test_web, test_news_api, …)
  run.py                  # entrypoint; CLI: init-db, seed-dev-user, seed-news
  requirements.txt, requirements-dev.txt, Dockerfile, pytest.ini
administration-tool/      # Public website + management area
  frontend_app.py         # Flask app: /, /news, /forum, /manage, …
  templates/, static/
  requirements.txt, Dockerfile
README.md, CHANGELOG.md, docker-compose.yml, docs/, .env.example at repo root.
```

## Prerequisites

- Python 3.10+ (3.13 recommended)
- pip

## Environment

Copy `.env.example` to `.env` at the **repo root**. Backend and administration-tool both read from the root `.env` when run locally. Set at least:

- **SECRET_KEY**, **JWT_SECRET_KEY** (required in production; or set **DEV_SECRETS_OK=1** for local dev fallbacks).
- **FLASK_APP=run:app** (so Flask finds the app when running from `backend/`).

Optional for local dev:

- **PORT** – Backend default 5000; administration-tool (frontend) default 5001.
- **BACKEND_API_URL** – Administration tool: backend base URL for API and auth (no trailing slash). Default in code is the remote PythonAnywhere backend for initial testing; for local troubleshooting set e.g. `BACKEND_API_URL=http://127.0.0.1:5000`.
- **CORS_ORIGINS** – Backend: comma-separated origins allowed to call the API (e.g. `http://127.0.0.1:5001,http://localhost:5001`). Required when the frontend runs on another port.
- **FRONTEND_URL** – Backend: when set, `GET /` and `GET /news` redirect to this URL (e.g. `http://127.0.0.1:5001`).
- **DEV_SECRETS_OK=1** – Enables dev fallback secrets and CLI commands `flask seed-dev-user`, `flask seed-news`.
- **MAIL_ENABLED** – Set to `1` to send verification and password-reset emails; `0` or unset = log URLs only (dev).
- **APP_PUBLIC_BASE_URL** – Base URL for activation links (e.g. `https://your-domain.com`). Optional; see `.env.example`.
- **EMAIL_VERIFICATION_TTL_HOURS** – Validity of activation links in hours (default 24).

## Run workflow (local)

### 1. Backend

```bash
cd backend
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
# From backend/
export FLASK_APP=run:app   # or set in .env
python run.py
# or: flask run
```

Default: **http://127.0.0.1:5000**. Health: `GET /api/v1/health`.

### 2. Frontend

```bash
cd administration-tool
pip install -r requirements.txt
python frontend_app.py
```

Default: **http://127.0.0.1:5001**. Open in browser; login/register/dashboard links point to the backend (using **BACKEND_API_URL**). News list and detail load data from `GET /api/v1/news` and `GET /api/v1/news/<id>`. **Management area:** `/manage` (staff login at `/manage/login`); JWT in sessionStorage; news, user admin (admin only), wiki, forum. See `docs/runbook.md` for management and wiki API.

### 3. CORS (when backend and administration-tool run on different ports)

Set in `.env` (or backend environment):

```bash
CORS_ORIGINS=http://127.0.0.1:5001,http://localhost:5001
```

Otherwise the browser blocks frontend requests to the backend API.

## Migrations

From **backend/**:

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

All tests live under **backend/tests/** (API, web, news API, config, security). Run from **backend/**:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
# or: pytest tests/ -v
# or: pytest tests/test_news_api.py tests/test_api.py -v
```

Default pytest config: `pytest.ini` in backend (testpaths = tests, coverage on `app`).

## Docker (compose)

From **repo root**:

```bash
docker compose up --build
```

- **backend** service at http://localhost:8000 (Gunicorn in container).
- **frontend** (administration-tool) service at http://localhost:5001.
- Frontend env **BACKEND_API_URL=http://localhost:8000** so the browser can call the API when using Docker. Backend env **CORS_ORIGINS** includes http://localhost:5001 so requests from the frontend origin are allowed.

Database is persisted in `backend/instance/` (mounted volume). Run migrations inside the backend container if needed:

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
| BACKEND_API_URL | Administration tool | Backend base URL for API and auth (no trailing slash); default in code is remote PythonAnywhere for initial testing |
| CORS_ORIGINS | Backend | Comma-separated origins for API (e.g. frontend URL) |
| FRONTEND_URL | Backend | Optional; redirects GET / and GET /news to frontend |
| DEV_SECRETS_OK | Backend | 1 = dev secrets and seed-dev-user / seed-news allowed |
| DATABASE_URI | Backend | Default SQLite in `backend/instance/wos.db` |

## Documentation

- **Local development (split):** `docs/development/LocalDevelopment.md` – URLs, startup order, how frontend and backend talk, CORS, seed commands.
- **Architecture:** `docs/architecture/FrontendBackendRestructure.md` – backend/administration-tool responsibilities.
- **Runbook:** `docs/runbook.md` – Example flows.
- **Security:** `docs/security.md` – Auth, CSRF, CORS, cookies.
- **Backend tests:** `backend/tests/README.md` – Fixtures and test modules.

## API (summary)

- **Health:** `GET /api/v1/health`
- **Auth:** `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- **News (CRUD):** `GET /api/v1/news` (list; query: q, sort, direction, page, limit, category; with editor JWT: `published_only=0` for drafts), `GET /api/v1/news/<id>` (detail; with editor JWT returns drafts), `POST /api/v1/news`, `PUT /api/v1/news/<id>`, `DELETE /api/v1/news/<id>`, `POST /api/v1/news/<id>/publish`, `POST /api/v1/news/<id>/unpublish` – write/publish require JWT and editor/admin role.
- **Users (CRUD):** `GET /api/v1/users` (admin only), `GET /api/v1/users/<id>`, `PUT /api/v1/users/<id>`, `DELETE /api/v1/users/<id>` (admin only for list/delete).
- **Roles (CRUD):** `GET /api/v1/roles` (admin only; query: page, limit, q), `GET /api/v1/roles/<id>`, `POST /api/v1/roles`, `PUT /api/v1/roles/<id>`, `DELETE /api/v1/roles/<id>` (admin only).
- **Admin logs:** `GET /api/v1/admin/logs` (admin only; query: q, category, status, date_from, date_to, page, limit), `GET /api/v1/admin/logs/export` (admin only; CSV). Dashboard uses session-authenticated `/dashboard/api/logs` and `/dashboard/api/logs/export` (admin only).

**Roles:** Default roles are user, moderator, editor, admin; admins can manage roles via the Roles CRUD API. New registrations get role **user**. Editor and admin can write news; only **admin** can access user list, user delete, roles CRUD, and activity logs API. Role checks are centralized (`user.is_admin`, `user.has_role(...)`, `require_web_admin`). Activity logging is done via `log_activity(...)`; auth, account, news, and admin actions produce structured entries visible in the admin dashboard Logs tab.
