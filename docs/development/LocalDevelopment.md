# Local Development

This project runs with separated services:
- `frontend/` for player/public pages
- `administration-tool/` for admin/management pages
- `backend/` for API/business/auth logic
- `world-engine/` for runtime authority

## Default URLs

| Service | URL |
|---|---|
| Backend | `http://127.0.0.1:5000` |
| Frontend | `http://127.0.0.1:5002` |
| Administration tool | `http://127.0.0.1:5001` |
| Play service | `http://127.0.0.1:8001` |

## Start services

### Backend

```bash
cd backend
pip install -r requirements.txt
flask init-db
flask db upgrade
python run.py
```

### Frontend

```bash
cd frontend
pip install -r requirements.txt
python run.py
```

### Administration tool

```bash
cd administration-tool
pip install -r requirements.txt
python app.py
```

### Play service

```bash
cd world-engine
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8001
```

## Cross-service configuration

### Backend

- `CORS_ORIGINS=http://127.0.0.1:5002,http://127.0.0.1:5001`
- `FRONTEND_URL=http://127.0.0.1:5002` (legacy redirect compatibility)
- `PLAY_SERVICE_PUBLIC_URL=http://127.0.0.1:8001`
- `PLAY_SERVICE_INTERNAL_URL=http://127.0.0.1:8001`
- `PLAY_SERVICE_SHARED_SECRET=<shared secret>`

### Frontend

- `BACKEND_API_URL=http://127.0.0.1:5000`
- `PLAY_SERVICE_PUBLIC_URL=http://127.0.0.1:8001`

### Administration tool

- `BACKEND_API_URL=http://127.0.0.1:5000`

## Notes

- Backend legacy web routes are compatibility redirects only; canonical player/public pages live in `frontend/`.
- The administration tool remains intentionally separate and is not part of `frontend/`.
- Runtime authority remains in `world-engine` (session state, turn execution, websocket live behavior).
