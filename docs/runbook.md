# Runbook — Local development

**Commands:** For each step, the **short form** (e.g. `flask`) is given first, then the **Python form** (`python -m flask`), so they work in any environment. On **PowerShell**, separate lines with `;` or use one command per line; set environment variables with `$env:NAME = "value"`. On **Bash/Terminal** use `export NAME=value` and for multi-line commands use `\` at end of line.

---

## One-time setup

**Bash / Terminal (e.g. Git Bash, WSL, macOS/Linux):**

```bash
cd Backend
pip install -r requirements.txt
cp ../.env.example ../.env
# Edit .env: set SECRET_KEY and JWT_SECRET_KEY (or DEV_SECRETS_OK=1 for dev fallbacks)
# Add FLASK_APP=run:app to .env or export it
flask init-db
# Or with Python explicitly:
python -m flask init-db
# init-db creates all tables and stamps Alembic at head, so db upgrade is optional (no-op if already at head).

# Apply any new migrations (if you use migrations-only workflow, run this instead of init-db on a fresh DB):
flask db upgrade
# Or:
python -m flask db upgrade
# If you already ran init-db and upgrade fails with "table already exists", run: flask db stamp head

# Optional, only when DEV_SECRETS_OK=1:
flask seed-dev-user --generate
# Or:
python -m flask seed-dev-user --generate
# Or: set SEED_DEV_USERNAME/SEED_DEV_PASSWORD or pass --username/--password
```

**PowerShell (Windows):**

```powershell
cd Backend
pip install -r requirements.txt
Copy-Item ..\.env.example ..\.env
# Edit .env: SECRET_KEY and JWT_SECRET_KEY (or DEV_SECRETS_OK=1)
# Add FLASK_APP=run:app to .env or: $env:FLASK_APP = "run:app"

flask init-db
# Or with Python explicitly:
python -m flask init-db
# init-db creates tables and stamps Alembic at head; db upgrade then does nothing until new migrations exist.

# Apply migrations (or use only "db upgrade" on a fresh DB without init-db):
flask db upgrade
# Or:
python -m flask db upgrade
# If upgrade fails with "table already exists" after init-db, run: flask db stamp head

# Optional (DEV_SECRETS_OK=1):
flask seed-dev-user --generate
# Or:
python -m flask seed-dev-user --generate
```

---

## Start the server

**Bash / Terminal:**

```bash
cd Backend
export FLASK_APP=run:app
export FLASK_DEBUG=1
python run.py
# Or with Flask CLI:
flask run --port 5000
# Or:
python -m flask run --port 5000
```

**PowerShell:**

```powershell
cd Backend
$env:FLASK_APP = "run:app"
$env:FLASK_DEBUG = "1"
python run.py
# Or with Flask CLI:
flask run --port 5000
# Or:
python -m flask run --port 5000
```

Server: http://127.0.0.1:5000

---

## Further useful commands (Backend)

| Action | Short form | With Python |
|--------|------------|-------------|
| Apply migrations | `flask db upgrade` | `python -m flask db upgrade` |
| Create new migration | `flask db revision -m "description"` | `python -m flask db revision -m "description"` |
| Show migration status | `flask db current` | `python -m flask db current` |
| Stamp revision (without running) | `flask db stamp 006_evt` | `python -m flask db stamp 006_evt` |
| Create dev user (moderator) | `flask seed-dev-user --username dev --password Pass1` | `python -m flask seed-dev-user --username dev --password Pass1` |
| Create admin user (testing) | `flask seed-admin-user --username admin --password Admin1` | `python -m flask seed-admin-user --username admin --password Admin1` |
| Seed example news | `flask seed-news` | `python -m flask seed-news` |
| Run tests | `pytest tests` | `python -m pytest tests` |
| Run tests without coverage | `pytest tests --no-cov` | `python -m pytest tests --no-cov` |

**PowerShell:** Run all commands from the Backend directory (`cd Backend`); for multiple commands in one line, separate with `;`, e.g. `cd Backend; python -m flask db upgrade`.

---

## Web flow

1. Open http://127.0.0.1:5000/ in the browser.
2. "Log in" → enter username/password (e.g. from seed-dev-user).
3. After login you are redirected to /dashboard.
4. "Log out" (button in header) → POST to logout.

---

## API flow (example)

**Bash / Terminal:**

```bash
# 1. Register (or use existing user)
curl -X POST http://127.0.0.1:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"Alice123"}'

# 2. Login, get token from response
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"Alice123"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. Call protected route
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/auth/me
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/test/protected
```

**PowerShell:**

```powershell
# 1. Register
curl.exe -X POST http://127.0.0.1:5000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d '{\"username\":\"alice\",\"email\":\"alice@example.com\",\"password\":\"Alice123\"}'

# 2. Login, store token in variable
$response = curl.exe -s -X POST http://127.0.0.1:5000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"username\":\"alice\",\"password\":\"Alice123\"}'
$TOKEN = ( $response | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])" )

# 3. Protected route
curl.exe -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/auth/me
curl.exe -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/test/protected
```

---

## Health checks

- **Web:** `GET /health` → JSON `{"status":"ok"}` (unauthenticated).
- **API:** `GET /api/v1/health` → JSON `{"status":"ok"}` (unauthenticated).

---

## Errors & limits

- **Web routes** (e.g. `/`, `/login`, `/dashboard`): 404/500 as HTML (templates).
- **API routes** (under `/api/`): 404, 429, 500 and JWT 401 as JSON `{"error": "..."}`.
- **Rate limit:** 429 as JSON; default from `RATELIMIT_DEFAULT`.

---

## Troubleshooting

- **SECRET_KEY must be set:** In `.env` set `SECRET_KEY` and `JWT_SECRET_KEY`, or for local dev set `DEV_SECRETS_OK=1`.
- **CSRF invalid on login:** Login form must include CSRF token (already present in templates).
- **CORS errors from frontend:** In `.env` set `CORS_ORIGINS` to the frontend origin (e.g. `http://localhost:3000`).
- **PowerShell: "&&" unknown:** On PowerShell separate commands with `;` (e.g. `cd Backend; python -m flask db upgrade`) or use one command per line.
- **flask: command not found:** Use `python -m flask` instead of `flask` (from the Backend directory).
- **401 Unauthorized on API:** Two cases: (1) **Login** (`POST /auth/login`) returns 401 → wrong username or password. (2) **Other API calls** (e.g. `GET /api/v1/users`) return 401 → missing or invalid JWT: first call `POST /auth/login` with JSON `{"username":"...","password":"..."}`, then send the returned `access_token` in the header `Authorization: Bearer <access_token>`. Note: `seed-dev-user` creates a **moderator** user; for admin-only endpoints use `seed-admin-user` (e.g. `flask seed-admin-user --username admin --password Admin1` with `DEV_SECRETS_OK=1`).
