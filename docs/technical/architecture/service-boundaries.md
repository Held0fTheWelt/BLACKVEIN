# Service boundaries

Concrete **ownership** of each deployable application and how browser clients reach them. For containers and Compose defaults, see [`docs/admin/setup-and-first-run.md`](../../admin/setup-and-first-run.md) and [`docs/start-here/system-map-services-and-data-stores.md`](../../start-here/system-map-services-and-data-stores.md).

## Backend (`backend/`)

- Owns REST APIs under `/api/v1/*`.
- Owns authentication, authorization, accounts, forum, news, wiki, and related persistence.
- Owns play **bootstrap** and ticket-style integration with the play service (see code and deployment env vars).
- Does **not** own canonical player marketing HTML; see compatibility redirects below.
- Exposes a small **technical** surface at `/backend/*` (architecture/API/ops links). A direct visit to backend `/` redirects to `/backend` — this is **not** the player game UI.

## Frontend (`frontend/`)

- Owns player-facing routes (home, login/register, dashboard, news, wiki, community, game menu, play routes).
- Calls backend APIs and uses the **browser-reachable** play URL for WebSocket/runtime bootstrap.

## Administration tool (`administration-tool/`)

- Owns admin UI routes and workflows.
- Calls backend APIs only; stays separate from `frontend/`.

## Play service (`world-engine/`)

- Owns **authoritative** narrative session state and **turn execution** for live play.
- Owns WebSocket live-state behavior for sessions.

## Compatibility redirect layer (`backend`)

`backend/app/web/routes.py` implements legacy redirects: `GET /` goes to `/backend` (technical backend home), not the player frontend. Other legacy paths may `302` to `FRONTEND_URL` when configured, else return `410` JSON. Canonical public HTML for players is on the **frontend** service.

## Operational rule

Run **frontend**, **backend**, **administration-tool**, and **play-service** as separate processes or containers. Include both frontend origins in backend `CORS_ORIGINS`. Keep **shared secrets** (`PLAY_SERVICE_*`) aligned between backend and world-engine.

## Classification of backend runtime code

Some backend packages mix **API orchestration**, **transitional shims**, and **tooling**. See [`backend-runtime-classification.md`](backend-runtime-classification.md) for the breakdown (referenced from backend source comments; path: `docs/technical/architecture/backend-runtime-classification.md`).
