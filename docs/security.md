# Security assumptions and configuration

## Authentication

- **Web (browser):** Session-based. Login form sets `session["user_id"]` and `session["username"]`. Protected routes use a central `require_web_login` decorator; unauthenticated users are redirected to `/login`. Logout is **POST only** to reduce link-follow and CSRF abuse.
- **API:** JWT only. No session cookies. Clients send `Authorization: Bearer <token>`. Token obtained via `POST /api/v1/auth/login` with JSON body. No CSRF applied to API routes.

## CSRF

- **Scope:** Server-rendered web forms only (login, logout). All web POST forms include a CSRF token.
- **API:** Exempt from CSRF. API auth is token-based and not cookie-based for the API context.

## Secrets

- **Production:** No hardcoded secrets. `SECRET_KEY` and `JWT_SECRET_KEY` must be set in the environment. The app refuses to start without `SECRET_KEY` unless in testing or dev mode.
- **Dev fallback:** When `DEV_SECRETS_OK=1`, a development config provides fallback secrets and allows the `flask seed-dev-user` command. Do not use in production.

## Default users

- **Normal init:** `flask init-db` only creates tables. It does **not** create any user.
- **Dev seed:** `flask seed-dev-user` is for local development only when `DEV_SECRETS_OK=1`. It does **not** use fixed credentials. You must supply credentials in one of these ways: set `SEED_DEV_USERNAME` and `SEED_DEV_PASSWORD` in the environment; pass `--username` and `--password` (or get a password prompt); or use `--generate` to create a user with a random password that is printed once. Do not use in production.

## CORS

- **Configurable:** Allowed origins come from `CORS_ORIGINS` (comma-separated). If unset or empty, no CORS headers are sent (same-origin only); the browser then blocks cross-origin API calls and the frontend may show "Network error". Set to your frontend origin(s) when using a separate frontend. Rules: no spaces around commas, no trailing slashes (e.g. `http://127.0.0.1:5001,http://localhost:5001` or `https://deine-frontend-app.pythonanywhere.com`).

## Session cookies

- **HttpOnly:** Enabled by default.
- **SameSite:** Lax.
- **Secure:** Set when `PREFER_HTTPS=1` (for production over HTTPS).

## Rate limiting

- Applied to API routes (per-route limits). Web routes use the default limit from config. Storage is in-memory by default; set `RATELIMIT_STORAGE_URI` for a persistent backend if needed.
