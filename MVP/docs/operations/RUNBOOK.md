# Operations Runbook (Local)

This runbook describes the three-service player flow plus separate admin tooling.

## Service URLs (defaults)

| Service | URL | Purpose |
|---|---|---|
| Backend | `http://127.0.0.1:5000` | API/business/auth/policy + technical pages at `/backend/*` |
| Frontend | `http://127.0.0.1:5002` | Player/public web UI |
| Administration Tool | `http://127.0.0.1:5001` | Admin/management UI |
| Play Service | `http://127.0.0.1:8001` | Authoritative runtime |

## Startup order

1. Start backend
2. Start play-service
3. Start frontend
4. Start administration-tool (if needed)

## Backend setup

```bash
cd backend
pip install -r requirements.txt
flask init-db
flask db upgrade
python run.py
```

Required env (minimum):
- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `CORS_ORIGINS=http://127.0.0.1:5002,http://127.0.0.1:5001`
- `FRONTEND_URL=http://127.0.0.1:5002` (legacy redirect compatibility)
- `PLAY_SERVICE_PUBLIC_URL=http://127.0.0.1:8001`
- `PLAY_SERVICE_INTERNAL_URL=http://127.0.0.1:8001`
- `PLAY_SERVICE_SHARED_SECRET=<same as play-service>`

## Frontend setup

```bash
cd frontend
pip install -r requirements.txt
python run.py
```

Required env:
- `FRONTEND_SECRET_KEY`
- `BACKEND_API_URL=http://127.0.0.1:5000`
- `PLAY_SERVICE_PUBLIC_URL=http://127.0.0.1:8001`

## Administration tool setup

```bash
cd administration-tool
pip install -r requirements.txt
python app.py
```

Required env:
- `BACKEND_API_URL=http://127.0.0.1:5000`

## Play service setup

```bash
cd world-engine
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8001
```

Required env:
- `PLAY_SERVICE_SECRET` (must match backend shared secret)
- `PLAY_SERVICE_INTERNAL_API_KEY` (if internal endpoints are protected)

## Browser flow checks

### Player/public flow
1. Open `http://127.0.0.1:5002/`
2. Register/login on frontend
3. Access dashboard/news/wiki/community/game menu
4. Start a run via `/play`, open play shell `/play/<session_id>`

### Backend entry (technical)
1. Open `http://127.0.0.1:5000/` — expect `302` to `http://127.0.0.1:5000/backend/` (system/developer info, not player UI).

### Legacy redirect compatibility
1. Open `http://127.0.0.1:5000/login`
2. Verify backend returns `302` to `http://127.0.0.1:5002/login`
3. Verify no backend-rendered player/public HTML page is served (only `/backend/*` technical templates)

### Admin flow
1. Open `http://127.0.0.1:5001/manage`
2. Verify management functionality still works independently
3. Optional: open `http://127.0.0.1:5001/manage/diagnosis` (requires JWT and feature `manage.system_diagnosis`) for aggregated system health from `GET /api/v1/admin/system-diagnosis`
4. Optional: open `http://127.0.0.1:5001/manage/play-service-control` (requires JWT and feature `manage.play_service_control`, **admin only**) to edit **desired** Play-Service posture, run **test**/**apply** in-process (`/api/v1/admin/play-service-control*`). This is **not** host orchestration; **diagnosis** remains the read-only aggregated **observed** view. Operator labels vs. transport, timeout semantics, and new-session gating scope: see **Play-Service control: known implementation limits** in `docs/technical/operations/observability-and-governance.md`.

## Docker Compose (host ports)

Root `docker compose up --build` maps **backend :8000**, **frontend :5002**, **administration-tool :5001**, **play-service :8001** (play-service container listens on 8000 internally). This differs from bare-metal backend **5000**; set `BACKEND_API_URL` in `frontend` / `administration-tool` to `http://backend:8000` for container-to-backend calls.

**Windows / IDE shells:** If `docker` is not found, prepend `C:\Program Files\Docker\Docker\resources\bin` to `PATH`, or invoke that `docker.exe` directly. If image pulls fail with `docker-credential-desktop` missing, use the same `bin` directory on `PATH`, or set `DOCKER_CONFIG` to a directory whose `config.json` is `{"auths":{}}` (UTF-8 **without** BOM) so public pulls do not use `credsStore`.

**Host port 8000:** If `http://127.0.0.1:8000/health` fails on the host while containers are up, another process may already bind `127.0.0.1:8000` (check `netstat`). The backend container is still healthy on the Docker network: e.g. `docker exec worldofshadows-frontend-1 python -c "import urllib.request; print(urllib.request.urlopen('http://backend:8000/health').read())"`.

### Backend container: seed users (Docker Exec)

Do **not** run `seed-dev-user` as a shell command; it is not on `PATH`. Use the Flask CLI with application **`run:app`** (module `run.py`, object `app`). Wrong values such as `app.run` cause import errors and missing commands.

**Always** either set `FLASK_APP=run:app` or pass `--app run:app`. Working directory must be **`backend/`** on the host or **`/app`** in the container (where `run.py` lives).

`seed-dev-user` and `seed-admin-user` require **`DEV_SECRETS_OK=1`** (local dev only).

```bash
# Inside backend container (Exec tab) — explicit --app avoids wrong FLASK_APP
cd /app
python -m flask --app run:app ensure-superadmin --username admin
```

```bash
# Seed (new user only), inside container
cd /app
DEV_SECRETS_OK=1 python -m flask --app run:app seed-dev-user --username admin --password Admin123 --superadmin
```

From the **host** (project root):

```bash
docker compose exec backend python -m flask --app run:app ensure-superadmin --username admin
```

```bash
docker compose exec -e DEV_SECRETS_OK=1 backend python -m flask --app run:app seed-dev-user --username admin --password Admin123 --superadmin
```

Alternative: `DEV_SECRETS_OK=1 python -m flask --app run:app seed-admin-user --username admin --password Admin123` (creates admin with role_level 100).

**User already exists:** Do not re-run seed; use **`ensure-superadmin`** (see first container example above). Password is unchanged.

**Windows PowerShell** (bare metal, from `backend\`):

```powershell
cd C:\path\to\WorldOfShadows\backend
$env:FLASK_APP = "run:app"
flask ensure-superadmin --username admin
```

To only raise `role_level` (user is already admin): `flask set-user-role-level --username admin --role-level 100`.

## Incident checklist

- If frontend pages fail: check `BACKEND_API_URL` and backend health
- If backend API rejects requests: check JWT/session state and `CORS_ORIGINS`
- If play shell fails to connect: check `PLAY_SERVICE_PUBLIC_URL` and shared secrets
- If legacy paths still render HTML from backend: confirm `backend/app/web/routes.py` is redirect-only compatibility
