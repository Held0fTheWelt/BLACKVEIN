# Local development – Frontend and Backend

This document describes how to run World of Shadows with the Frontend and Backend on separate processes and how they communicate.

## URLs (default)

| Service   | URL                     | Purpose                    |
|-----------|-------------------------|----------------------------|
| Backend   | http://127.0.0.1:5000   | API, auth, dashboard, DB   |
| Frontend  | http://127.0.0.1:5001   | Public site, news pages   |

The frontend fetches data from the backend over HTTP (e.g. `GET /api/v1/news`). Because the origins differ (port 5000 vs 5001), the browser enforces CORS: the backend must allow the frontend origin.

## Startup flow

1. **Backend**
   - From repo root or `Backend/`: set `FLASK_APP=run:app`, then `flask run` or `python run.py`.
   - Default port 5000 (override with `PORT`).
   - Ensure `.env` or environment has at least `SECRET_KEY` and `JWT_SECRET_KEY` (or use `DEV_SECRETS_OK=1` for dev fallbacks).
   - For local dev with Frontend on another port, set `CORS_ORIGINS=http://127.0.0.1:5001,http://localhost:5001` (comma-separated, no spaces).

2. **Frontend**
   - From `Frontend/`: `python frontend_app.py`.
   - Default port 5001 (override with `PORT`).
   - Set `BACKEND_API_URL=http://127.0.0.1:5000` if the backend is not on that URL (e.g. different host/port). No trailing slash. This value is injected into the page as `window.__FRONTEND_CONFIG__.backendApiUrl` and used by the frontend for all API requests and for login/register/dashboard links.

3. **Optional redirects**
   - Backend: if `FRONTEND_URL=http://127.0.0.1:5001` is set, `GET /` and `GET /news` on the backend redirect to the frontend so the public site is served only by the frontend.

## How Frontend and Backend talk

- **Single source of API base URL:** The frontend gets the backend base URL from the server-rendered config: `BACKEND_API_URL` (env) → Flask `app.config["BACKEND_API_URL"]` → `inject_config()` → `frontend_config.backendApiUrl` → `window.__FRONTEND_CONFIG__`. All API calls use `FrontendConfig.getApiBaseUrl()` (from `main.js`). No hardcoded backend URLs in the frontend.
- **API calls:** The frontend uses `FrontendConfig.apiFetch(path)` (e.g. `apiFetch("/api/v1/news")`) for GET requests. `apiFetch` builds the full URL from `getApiBaseUrl()` + path, sends `Accept: application/json`, and returns a Promise that resolves with the parsed JSON or rejects with an error message string (network error, 4xx/5xx, or invalid JSON).
- **CORS:** When Frontend (e.g. 5001) and Backend (5000) run on different origins, the browser sends an `Origin` header. The backend (with `flask-cors`) responds with `Access-Control-Allow-Origin: <allowed origin>` only if that origin is listed in `CORS_ORIGINS`. If `CORS_ORIGINS` is not set, the browser blocks the response and the frontend sees a network/CORS error. So for local dev with split Frontend/Backend, set `CORS_ORIGINS` as above.
- **Links to backend:** Login, Register, Dashboard, Wiki, Community links in the frontend point to `{{ backend_api_url }}/login`, etc., so they use the same configured base URL.

## Seed data (optional)

- **Dev user:** `flask seed-dev-user` (requires `DEV_SECRETS_OK=1`). Creates a user with editor role for testing news write API.
- **Example news:** `flask seed-news` (requires `DEV_SECRETS_OK=1`). Creates a small set of example news entries (published and draft) for testing list, search, sort, category filter, and detail views. See CHANGELOG or Backend run.py for details.
