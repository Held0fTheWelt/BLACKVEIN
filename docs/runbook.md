# Runbook — Local development

## One-time setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set SECRET_KEY and JWT_SECRET_KEY (or set DEV_SECRETS_OK=1 for dev fallbacks)
flask init-db
# Optional, only when DEV_SECRETS_OK=1:
flask seed-dev-user
```

## Start the server

```bash
export FLASK_APP=run.py
export FLASK_DEBUG=1
python run.py
# Or: flask run --port 5000
```

Server: http://127.0.0.1:5000

## Web flow

1. Open http://127.0.0.1:5000/
2. Click "Log in" → enter username/password (e.g. admin/admin if you ran seed-dev-user with DEV_SECRETS_OK=1).
3. After login you are redirected to /dashboard.
4. Use "Log out" (button in header) to logout; it sends a POST.

## API flow (example)

```bash
# 1. Register a user (or use existing)
curl -X POST http://127.0.0.1:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"alice123"}'

# 2. Login and get token
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"alice123"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. Call protected route
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/auth/me
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/test/protected
```

## Health checks

- Web: `GET /health` → `{"status":"ok"}`
- API: `GET /api/v1/health` → `{"status":"ok"}`

## Troubleshooting

- **SECRET_KEY must be set:** Set `SECRET_KEY` and `JWT_SECRET_KEY` in `.env`, or set `DEV_SECRETS_OK=1` for local dev.
- **CSRF invalid on login:** Ensure the login form includes the CSRF token (already in templates).
- **CORS errors from a frontend:** Set `CORS_ORIGINS` in `.env` to your frontend origin (e.g. `http://localhost:3000`).
