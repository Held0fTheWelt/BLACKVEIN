# Server Architecture

## Boundary summary

### Backend (`backend/`)
- Owns REST APIs (`/api/v1/*`)
- Owns authN/authZ, user/account/forum/news/wiki business logic
- Owns persistence and policy enforcement
- Owns play bootstrap and ticket issuance APIs
- Does not own canonical player/public HTML rendering

### Frontend (`frontend/`)
- Owns player/public browser routes:
  - `/`
  - `/login`, `/register`, `/logout`
  - `/dashboard`, `/news`, `/wiki`, `/community`, `/game-menu`
  - `/play`, `/play/<session_id>`, `/play/<session_id>/execute`
- Integrates with backend APIs and play-service websocket bootstrap

### Administration tool (`administration-tool/`)
- Owns admin/management UI routes and workflows
- Calls backend APIs
- Stays separate from `frontend/`

### Play service (`world-engine/`)
- Owns authoritative runtime state and turn execution
- Owns websocket live-state behavior

## Compatibility layer

`backend/app/web/routes.py` is a compatibility redirect layer:
- keeps legacy paths available temporarily
- returns `302` redirects to `FRONTEND_URL`
- does not render canonical player/public HTML

## Operational implications

- Run frontend, backend, and play-service as separate services
- Include both frontend origins (`frontend`, `administration-tool`) in backend `CORS_ORIGINS`
- Keep shared play-service secret aligned across backend and world-engine
