# Server Architecture

## Boundary summary

### Backend (`backend/`)
- Owns REST APIs (`/api/v1/*`)
- Owns authN/authZ, user/account/forum/news/wiki business logic
- Owns persistence and policy enforcement
- Owns play bootstrap and ticket issuance APIs
- Does not own canonical player/public HTML rendering
- Exposes a small **technical information surface** at `/backend/*` (system/developer-facing pages only: architecture, API overview, ops links). Direct browser visits to the backend root `/` redirect to `/backend`. This is not a player or admin UI.

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
- **`GET /`** redirects to **`/backend`** (technical backend home), not to the player frontend
- other legacy paths (`/login`, `/play`, …) return `302` redirects to `FRONTEND_URL` when set, else JSON **410**
- does not render canonical player/public HTML

Technical pages live under **`backend/app/info/`** (blueprint registered in `create_app()`).

## Operational implications

- Run frontend, backend, and play-service as separate services
- Include both frontend origins (`frontend`, `administration-tool`) in backend `CORS_ORIGINS`
- Keep shared play-service secret aligned across backend and world-engine
