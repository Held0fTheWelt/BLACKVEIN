# Operations Runbook (Local)

This runbook describes the three-service player flow plus separate admin tooling.

## Service URLs (defaults)

| Service | URL | Purpose |
|---|---|---|
| Backend | `http://127.0.0.1:5000` | API/business/auth/policy |
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

### Legacy redirect compatibility
1. Open `http://127.0.0.1:5000/login`
2. Verify backend returns `302` to `http://127.0.0.1:5002/login`
3. Verify no backend-rendered player/public HTML page is served

### Admin flow
1. Open `http://127.0.0.1:5001/manage`
2. Verify management functionality still works independently

## Incident checklist

- If frontend pages fail: check `BACKEND_API_URL` and backend health
- If backend API rejects requests: check JWT/session state and `CORS_ORIGINS`
- If play shell fails to connect: check `PLAY_SERVICE_PUBLIC_URL` and shared secrets
- If legacy paths still render HTML from backend: confirm `backend/app/web/routes.py` is redirect-only compatibility
