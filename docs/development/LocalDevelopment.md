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
   - From `administration-tool/`: `python frontend_app.py`.
   - Default port 5001 (override with `PORT`).
   - Set `BACKEND_API_URL=http://127.0.0.1:5000` if the backend is not on that URL (e.g. different host/port). No trailing slash. This value is injected into the page as `window.__FRONTEND_CONFIG__.backendApiUrl` and used by the frontend for all API requests and for login/register/dashboard links.

3. **Optional redirects**
   - Backend: if `FRONTEND_URL=http://127.0.0.1:5001` is set, `GET /` and `GET /news` on the backend redirect to the frontend so the public site is served only by the frontend.

## How Frontend and Backend talk

- **Single source of API base URL:** The frontend gets the backend base URL from the server-rendered config: `BACKEND_API_URL` (env) → Flask `app.config["BACKEND_API_URL"]` → `inject_config()` → `frontend_config.backendApiUrl` → `window.__FRONTEND_CONFIG__`. All API calls use `FrontendConfig.getApiBaseUrl()` (from `main.js`). No hardcoded backend URLs in the frontend.
- **API calls:** The frontend uses `FrontendConfig.apiFetch(path)` (e.g. `apiFetch("/api/v1/news")`) for GET requests. `apiFetch` builds the full URL from `getApiBaseUrl()` + path, sends `Accept: application/json`, and returns a Promise that resolves with the parsed JSON or rejects with an error message string (network error, 4xx/5xx, or invalid JSON).
- **CORS:** When Frontend and Backend run on different origins, the browser sends an `Origin` header. The backend (with `flask-cors`) responds with `Access-Control-Allow-Origin` only if that origin is listed in `CORS_ORIGINS`. If `CORS_ORIGINS` is not set, the browser blocks the response and the frontend shows "Network error". Rules: comma-separated origins, **no spaces** around commas, **no trailing slashes**. Examples:
  - **Frontend lokal, Backend z. B. auf PythonAnywhere:** `CORS_ORIGINS=http://127.0.0.1:5001,http://localhost:5001` (am Backend setzen).
  - **Frontend auf anderer Subdomain (z. B. PythonAnywhere):** `CORS_ORIGINS=https://deine-frontend-app.pythonanywhere.com`. Nach Änderung Backend-Web-App neu laden (z. B. PythonAnywhere Dashboard → Reload).
- **Links to backend:** Login, Register, Dashboard, Wiki, Community links in the frontend point to `{{ backend_api_url }}/login`, etc., so they use the same configured base URL.

## Backend API URL configuration

The frontend defaults to the production backend URL (`https://held0fthewelt.pythonanywhere.com`) to allow live testing and manual verification. This is **intentional**.

### For local development

To test with a local backend:

```bash
# Set the environment variable before starting the Frontend
export BACKEND_API_URL=http://127.0.0.1:5000
python administration-tool/frontend_app.py
```

Or in `.env`:
```
BACKEND_API_URL=http://127.0.0.1:5000
```

Without this, the Frontend will try to reach the production backend.

### For live testing on production

Leave `BACKEND_API_URL` unset or set to the production URL. The Frontend will connect to the live backend.

## News creation workflow

### Required setup

- **Backend:** Running on configured URL
- **Frontend:** Running with correct `BACKEND_API_URL`
- **User:** Must have `moderator` role or higher
- **Auth:** Must be logged into `/manage/` area with valid JWT token

### Testing News creation locally

1. Start backend: `cd Backend && python run.py` (port 5000)
2. Start frontend with local backend: `BACKEND_API_URL=http://127.0.0.1:5000 python administration-tool/frontend_app.py` (port 5001)
3. Open http://127.0.0.1:5001/manage/login
4. Login with test user (e.g., created via `flask seed-dev-user`)
5. Navigate to `/manage/news`
6. Click "New article"
7. Fill form and click Save
8. Check browser console for network errors if submission fails

### Error messages and handling

The News creation form displays error feedback:

- **401 Unauthorized:** Invalid or missing JWT token → User needs to login
- **403 Forbidden:** User lacks moderator/admin role → Admin must grant role
- **400 Bad Request:** Missing required fields (title, slug, content) → Form shows validation hint
- **409 Conflict:** Slug already in use → Try different slug
- **500 Server Error:** Backend issue → Check backend logs

If management UI is visible but user cannot create News (due to role), the form will show "403 Forbidden" on save, making permission requirement explicit.

## Seed data (optional)

- **Dev user:** `flask seed-dev-user` (requires `DEV_SECRETS_OK=1`). Creates a user with moderator role for testing news write API.
- **Example news:** `flask seed-news` (requires `DEV_SECRETS_OK=1`). Creates a small set of example news entries (published and draft) for testing list, search, sort, category filter, and detail views. See CHANGELOG or Backend run.py for details.
