![Logo.png](https://github.com/Held0fTheWelt/BLACKVEIN/blob/master/promo/Logo.png)

# BLACKVEIGN - World of Shadows

Flask server foundation: server-rendered web pages with session auth, and a versioned REST API with JWT auth. No game logic or domain features yet; ready for extension.

## Scope

- **Web:** Home, login, logout, dashboard (protected). Session-based auth; CSRF protection on forms.
- **API:** REST under `/api/v1`: health, auth (register, login, me), and a protected test route. JWT only; no session cookies for API.
- **Database:** SQLite by default; User model only. Tables created via `flask init-db`; no default users created.

## Project structure

```
Backend/            # API, auth, dashboard, DB, tests
  app/              # create_app, config, extensions, models, services, web, api, static
  migrations/       # Flask-Migrate (Alembic)
  tests/
  run.py            # entrypoint: init-db, seed-dev-user
  requirements.txt, requirements-dev.txt, Dockerfile, pytest.ini
Frontend/           # Public website (placeholder)
  frontend_app.py, templates/, static/
README.md, CHANGELOG.md, docker-compose.yml, docs/, .env.example at repo root.
```

## Setup

1. **Prerequisites:** Python 3.10+, pip.
2. **Backend:** From repo root, `cd Backend`. Install: `pip install -r requirements.txt`  
   (Use version ranges as in `requirements.txt`; for reproducible builds use `pip freeze > requirements.lock`.)
3. **Environment:** Copy repo root `.env.example` to `.env` (e.g. in root or Backend) and set at least:
   - `SECRET_KEY` and `JWT_SECRET_KEY` (required; no default secrets in production).
   - For local dev only: `DEV_SECRETS_OK=1` to allow dev fallback secrets and `flask seed-dev-user`.
   - `FLASK_APP=run:app` (so Flask finds the app when running from `Backend/`).
4. **Database:** From `Backend/`: `flask init-db` (creates tables only). Optionally `flask seed-dev-user` when `DEV_SECRETS_OK=1` (supply credentials via env or CLI `--username`/`--password` or `--generate`).
5. **Run backend:** From `Backend/`: `python run.py` or `flask run`. Default port 5000; debug when `FLASK_DEBUG=1`.

## Environment configuration

| Variable | Required | Description |
|----------|----------|-------------|
| SECRET_KEY | Yes (or DEV_SECRETS_OK) | Session and CSRF secret |
| JWT_SECRET_KEY | Yes (or SECRET_KEY) | JWT signing key |
| DATABASE_URI | No | Default: SQLite in `instance/wos.db` |
| CORS_ORIGINS | No | Comma-separated origins for API; empty = same-origin only |
| FLASK_DEBUG | No | 1/true/yes = debug mode |
| PORT | No | Default 5000 |
| PREFER_HTTPS | No | 1/true/yes = secure session cookies |
| DEV_SECRETS_OK | No | 1/true/yes = dev fallback secrets, allows seed-dev-user |

## Web usage

- **Home:** `/` — public.
- **Login:** `/login` — form (username, password). Redirects to dashboard if already logged in.
- **Dashboard:** `/dashboard` — requires login; redirects to `/login` if not.
- **Logout:** POST to `/logout` only (form in header). No GET logout.

## API usage

- **Health:** `GET /api/v1/health` — no auth.
- **Register:** `POST /api/v1/auth/register` — JSON `{"username","password"}`.
- **Login:** `POST /api/v1/auth/login` — JSON `{"username","password"}` → `access_token`, `user`.
- **Me:** `GET /api/v1/auth/me` — header `Authorization: Bearer <token>`.
- **Protected example:** `GET /api/v1/test/protected` — same Bearer token.

Example:

```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123"}'
```

## Known limitations

- Single User model; no roles or permissions.
- SQLite default; switch via `DATABASE_URI` for production.
- CORS must be set explicitly via `CORS_ORIGINS` for a separate frontend.
- No automated migrations; schema changes require manual or custom migration.

## Documentation

- **Runbook:** `docs/runbook.md` — local development workflow and example flows.
- **Security:** `docs/security.md` — auth model, CSRF, CORS, cookies, and dev-only behavior.
