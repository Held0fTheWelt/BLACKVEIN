# Changelog

All notable changes to the World of Shadows project are documented in this file.

---

## [Unreleased]

_(No changes yet.)_

---

## [0.0.6] - 2025-03-10

### Added

- **Developer workflow and documentation:** `docker-compose.yml` updated for the Frontend/Backend split: two services, `backend` (build from Backend/, port 8000, Gunicorn) and `frontend` (build from Frontend/, port 5001). Backend sets `CORS_ORIGINS=http://localhost:5001,http://127.0.0.1:5001`; frontend sets `BACKEND_API_URL=http://localhost:8000` so the browser can call the API. `Frontend/requirements.txt` (Flask) and `Frontend/Dockerfile` added for the compose build. `README.md` rewritten: repository structure (Backend + Frontend), prerequisites, env vars (with table), **run workflow** (backend: `cd Backend`, `pip install -r requirements.txt`, `flask init-db`, `flask db upgrade`, optional `flask seed-dev-user` / `flask seed-news`, `python run.py` or `flask run`; frontend: `cd Frontend`, `pip install -r requirements.txt`, `python frontend_app.py`), **migrations** (`flask db upgrade` / `flask db revision` from Backend/), **tests** (`pytest` from Backend/), **Docker** (`docker compose up --build`, backend 8000, frontend 5001), and links to `docs/development/LocalDevelopment.md`, architecture, runbook, security, Backend tests README. No vague docs; commands and structure match the current repo.

- **Backend tests for news API and split:** New `Backend/tests/test_news_api.py` (19 tests): news list JSON shape and item fields; news detail JSON and 404 for missing/draft; search (q), sort (sort/direction), pagination (page/limit), category filter; published-only visibility (list excludes drafts, detail returns 404 for draft); anonymous write (POST/PUT/DELETE without token ? 401); authenticated user with role=user (POST/PUT ? 403); editor (role=editor) write (POST 201, PUT 200, publish 200, DELETE 200). Fixtures in `conftest.py`: `editor_user`, `editor_headers`, `sample_news` (two published, one draft). `Backend/tests/README.md` updated. News detail route fixed to handle timezone-naive `published_at` from SQLite (compare with UTC when needed). All 64 Backend tests pass; test paths remain under `Backend/tests/`.

- **Frontend?backend connectivity:** Backend API base URL is centralized: Frontend reads it only from `BACKEND_API_URL` (env) ? Flask `inject_config()` ? `window.__FRONTEND_CONFIG__.backendApiUrl`. `main.js` is loaded in `base.html` and exposes `FrontendConfig.getApiBaseUrl()` and `FrontendConfig.apiFetch(pathOrUrl, opts)`. `apiFetch` builds the full URL from the base + path, sends `Accept: application/json`, and returns a Promise that resolves with parsed JSON or rejects with an error message string (network, 4xx/5xx, or invalid JSON). News list and detail use `FrontendConfig` and `apiFetch` for all backend calls. CORS: when Frontend and Backend run on different origins (e.g. Frontend :5001, Backend :5000), set `CORS_ORIGINS=http://127.0.0.1:5001,http://localhost:5001` so the browser allows API requests; documented in `.env.example`. `docs/development/LocalDevelopment.md` describes default URLs (Backend 5000, Frontend 5001), startup flow, how Frontend and Backend talk (single API URL source, apiFetch, CORS), and optional seed commands.

- **Seed/example news:** `flask seed-news` (requires `DEV_SECRETS_OK=1`) creates a small set of example news entries for development and validation. Themes: project announcement, backend/frontend split (development), news system live (features), World of Blackveign (lore), API and CORS setup (technical), and one draft (Upcoming Events). Categories: Announcements, Development, Features, Lore, Technical. Five published and one draft so list/detail, search, sort, and category filter can be tested. Author is set from the first user if any. Skips slugs that already exist. Data is loaded by running the CLI once after `flask init-db` (and optionally `flask seed-dev-user`).

- **Frontend news detail page:** `Frontend/templates/news_detail.html` and `Frontend/static/news.js` (loadDetail) implement the public article view. Page is directly addressable at `/news/<id>`; JS fetches `GET /api/v1/news/<id>` and renders title, date (published_at/created_at), summary (if present), full content, author and category in meta line, and back link to news list. No placeholder content; loading and error states only. Document title updates to "Article title ? World of Shadows" when the article loads. Styling: `.news-detail-content .summary`, `.back-link-top`/`.back-link-bottom`, focus-visible on back link.

- **Frontend news list page:** `Frontend/templates/news.html` and `Frontend/static/news.js` implement the public news list with backend API consumption only (no DB). List shows title, summary, published date, category, and link to detail. Controls: search (q), sort (published_at, created_at, updated_at, title), direction (asc/desc), category filter, Apply button; Enter in search/category triggers apply. Pagination: Previous/Next and "Page X of Y (total)"; hidden when a single page. States: loading, empty ("No news yet"), error. Styling in `styles.css`: `.news-controls`, `.news-input`, `.news-select`, `.news-item-summary`, `.news-item-meta`, `.news-pagination`; WoS design tokens. Entry point: `NewsApp.initList()`.

- **Public frontend base and homepage:** `Frontend/templates/base.html` is the common public layout with semantic header (nav: News, Wiki, Community, Log in, Register, Dashboard), skip-link for accessibility, main content area, and footer. `Frontend/templates/index.html` is the public homepage with hero (Blackveign tagline, Get started / Sign in / News CTAs) and an "Explore" card grid linking to News, Log in, Register, and Dashboard. All auth/dashboard links point to the backend (`BACKEND_API_URL`). `Frontend/static/styles.css` includes World of Shadows design tokens (void/violet, Inter, JetBrains Mono), header/nav/footer styles, hero and card grid, focus-visible for keyboard users, and styles shared with news pages. `Frontend/static/main.js` exposes `FrontendConfig.getApiBaseUrl()` for API consumption. No server-side DB; frontend is static/JS-driven and production-oriented.

- **Permission groundwork for news write:** User model has a `role` column (`user`, `editor`, `admin`). Only `editor` and `admin` may call the protected news write API (POST/PUT/DELETE/publish/unpublish); others receive 403 Forbidden. Helper `current_user_can_write_news()` in `app.auth.permissions` and `User.can_write_news()` centralise the check; news write routes use the helper after `@jwt_required()`. Migration `004_add_user_role` adds `role` with server default `editor` for existing users; new registrations get `user`; `flask seed-dev-user` creates users with `editor` so dev can write news.

- **News service layer:** `Backend/app/services/news_service.py` with `list_news` (published_only, search, sort, order, page, per_page, category), `get_news_by_id`, `get_news_by_slug`, `create_news`, `update_news`, `delete_news`, `publish_news`, `unpublish_news`. Filtering, sorting, pagination, and slug validation live in the service; route handlers stay thin. Exported from `app.services`.
- **Public news API:** `GET /api/v1/news` (list) and `GET /api/v1/news/<id>` (detail). List supports query params: `q` (search), `sort`, `direction`, `page`, `limit`, `category`. Only published news is returned; drafts/unpublished return 404 on detail. Response: list `{ "items", "total", "page", "per_page" }`, detail single news object. Uses news service; rate limit 60/min.
- **Protected news write API:** `POST /api/v1/news`, `PUT /api/v1/news/<id>`, `DELETE /api/v1/news/<id>`, `POST /api/v1/news/<id>/publish`, `POST /api/v1/news/<id>/unpublish`. All require `Authorization: Bearer <JWT>` and editor/admin role; 401 without or invalid token, 403 for forbidden. Author for create set from JWT identity. Handlers delegate to news_service; rate limit 30/min per write endpoint.

---

## [0.0.5] - 2025-03-10

### Added

- **Architecture audit:** Implementation note `docs/architecture/FrontendBackendRestructure.md` defining the target Backend/Frontend split. World of Shadows is to be restructured into `Backend/` (app, instance, migrations, tests, run.py, API, auth, dashboard) and `Frontend/` (frontend_app.py, public templates, static, API consumption). MasterBlogAPI used only as reference for separation and API-first content delivery; existing auth and branding preserved. Real news system will be implemented in Backend (model + API) with frontend consuming JSON; no file moves in this audit step.
- **Backend/Frontend restructure:** Repository split into `Backend/` and `Frontend/`. Backend now contains `app/`, `migrations/`, `tests/`, `run.py`, `requirements.txt`, `requirements-dev.txt`, `Dockerfile`, `pytest.ini`, `.dockerignore`; run and test from `Backend/` with `FLASK_APP=run:app`. New `Frontend/` has `frontend_app.py`, `templates/`, `static/` (placeholder only). Root keeps `README.md`, `CHANGELOG.md`, `docker-compose.yml`, `docs/`, `.env.example`. Docker build context is `Backend/`; compose mounts `Backend/instance`. No news system yet; structure only.
- **Frontend application:** Lightweight Flask public frontend in `Frontend/`: `frontend_app.py` with home (`/`), news list (`/news`), news detail (`/news/<id>`); templates `base.html`, `index.html`, `news.html`, `news_detail.html`; static `styles.css`, `main.js`, `news.js`. Config via `BACKEND_API_URL` (default `http://127.0.0.1:5000`) for login/wiki/community links and for JS to call backend API. No database; news data will be loaded by JS from backend API (graceful empty/404 until news API exists). Styling aligned with World of Shadows (void/violet, Inter, JetBrains Mono). Run from `Frontend/` with `python frontend_app.py` (port 5001).
- **News model:** `Backend/app/models/news.py` with id, title, slug (unique), summary, content, author_id (FK users), is_published, published_at, created_at, updated_at, cover_image, category; migration `003_news` adds `news` table.

### Changed

- **Routing responsibility split:** Backend serves only auth and internal flows (login, register, forgot/reset-password, dashboard, game-menu, wiki/community placeholders). When `FRONTEND_URL` is set, backend redirects `GET /` and `GET /news` to the frontend so the public home and news are served only by the frontend; logout redirects to frontend home. Backend keeps legacy `home.html`/`news.html` when `FRONTEND_URL` is unset (e.g. tests, backend-only deployment). No duplicate public news; config documented in `.env.example` and `docs/architecture/FrontendBackendRestructure.md`.
- **Backend stabilization (post-move):** When running from `Backend/`, config now also loads `.env` from repo root so a single `.env` at project root works. Documented that the database instance path is `Backend/instance` when run from Backend. Imports, migration path, pytest discovery, and Docker/startup unchanged and verified; all 45 tests pass from `Backend/`.
- **Config:** Single `TestingConfig`; removed duplicate. `FRONTEND_URL` (optional) for redirecting public home/news to frontend.

### Security

- **Open redirect:** Login no longer redirects to external URLs. `is_safe_redirect()` in `app/web/auth.py` allows only path-only URLs (no scheme, no netloc). `next` query param is ignored when unsafe; fallback to dashboard.

---

## [0.0.4] - 2025-03-10

### Added

- **Landing page:** Aetheris-style hero (eyebrow, title, subtitle, CTAs), benefits grid, scrolling ticker, features section, void footer, fixed command dock. Design tokens (void, violet, mono/display fonts, transitions) and Google Fonts (Inter, JetBrains Mono). `landing.js`: hero cursor shear, feature reveal on scroll, benefit counters, smooth scroll for dock links, preload with IntersectionObserver; reduced-motion respected.
- **Dashboard:** Two-column layout (sidebar left, content right). Sidebar sections: User (User Settings), Admin (Overview, Metrics, Logs). User Settings: form for name and email with "Save Changes" (client-side confirmation). Metrics view: metric cards, revenue/user charts (Chart.js), threshold config with localStorage and breach alerts. Logs view: filterable activity table, CSV export. Overview: short description of sections. Content area fills available height with internal scroll.
- **Header navigation:** "Log in" removed. New nav links: News, Wiki, Community (each with placeholder page). When logged in: "Enter Game" between News and Wiki, linking to protected `/game-menu` (Game Menu placeholder page).
- **Base template:** Optional blocks for layout variants: `html_class`, `body_class`, `extra_head`, `site_header`, `site_main`, `flash_messages`, `content`, `site_footer`, `extra_scripts`. Header and footer kept by default; landing overrides only `site_main`.

### Changed

- **Config / styles:** Extended `:root` with violet/void tokens and font variables. Landing and dashboard CSS appended; responsive breakpoints for hero, benefits, features, dock and dashboard grid.

---

## [0.0.3] - 2025-03-10

### Security

- **Secrets:** Removed hardcoded fallback secrets from production config. `SECRET_KEY` and `JWT_SECRET_KEY` must be set in the environment. App raises at startup if `SECRET_KEY` is missing (unless testing or `DEV_SECRETS_OK=1`).
- **Dev-only fallback:** Added `DevelopmentConfig` and `DEV_SECRETS_OK` env var. When set, dev fallback secrets are used and `flask seed-dev-user` is allowed. Not for production.
- **Default user seeding removed:** `flask init-db` only creates tables; it no longer creates an admin/admin user. Use `flask seed-dev-user` with `DEV_SECRETS_OK=1` for local dev only.
- **Logout:** Web logout is POST only. Logout link replaced with a form and CSRF token to reduce abuse.
- **CSRF:** Web forms (login, logout) protected with CSRF. API blueprint exempt; API remains JWT-based.
- **CORS:** Origins are configurable via `CORS_ORIGINS` (comma-separated). No CORS when unset (same-origin only).
- **Session cookies:** `SESSION_COOKIE_HTTPONLY` and `SESSION_COOKIE_SAMESITE` set explicitly; `SESSION_COOKIE_SECURE` when `PREFER_HTTPS=1`.

### Added

- **Web auth:** Protected route `/dashboard`; central `require_web_login` decorator in `app/web/auth.py`. Anonymous access to `/dashboard` redirects to `/login`.
- **Login flow:** If already logged in, GET `/login` redirects to dashboard. Optional `next` query param for redirect-after-login.
- **Dashboard template:** `app/web/templates/dashboard.html`.
- **CLI:** `flask seed-dev-user` to create a default admin user when `DEV_SECRETS_OK=1`.
- **Documentation:** `README.md` (purpose, structure, setup, env, web/API usage). `docs/runbook.md` (local workflow, example API flow). `docs/security.md` (auth model, CSRF, CORS, cookies, dev-only behavior).

### Changed

- **Config:** `SECRET_KEY`, `JWT_SECRET_KEY` from env only in base config. Added `CORS_ORIGINS`, explicit session cookie settings. `DevelopmentConfig` and `TestingConfig` separated.
- **Startup:** Debug mode driven by `FLASK_DEBUG` instead of `FLASK_ENV`.
- **API:** User lookup uses `db.session.get(User, id)` (SQLAlchemy 2.x) instead of `User.query.get(id)`.
- **Web health:** Docstring aligned: returns JSON status.
- **.env.example:** Updated with required vars, `CORS_ORIGINS`, `FLASK_DEBUG`, `DEV_SECRETS_OK`.

### Removed

- **Default admin from init-db:** No automatic admin/admin creation.
- **Empty layer:** Removed unused `app/repositories/` package.

### Documentation

- README.md: project purpose, scope, structure, setup, environment table, web/API usage, limitations, links to runbook and security.
- docs/runbook.md: one-time setup, start server, web flow, API curl examples, health checks, troubleshooting.
- docs/security.md: session vs JWT auth, CSRF scope, secrets and dev fallback, default users, CORS, session cookies, rate limiting.

---

## [0.0.2] - 2025-03-10

### Added

- **Test suite:** Pytest tests for web and API (19 tests), in-memory DB config, pytest.ini, pytest and pytest-cov in requirements.
- **Planning docs:** Milestone list and execution prompts for staged rebuild (no code changes).
- Test suite: Pytest tests for web and API, in-memory DB config, pytest.ini, pytest and pytest-cov in requirements.
- Planning docs: Milestone list and execution prompts for staged rebuild (no code changes).

---

## [0.0.1] - 2025-03-10

### Added

- **Server foundation**
  - Flask application factory (`app/__init__.py`) with config loading from environment.
  - Central config (`app/config.py`) for `SECRET_KEY`, database URI, JWT, session cookies, and rate limiting.
  - Extensions module (`app/extensions.py`): SQLAlchemy, Flask-JWT-Extended, Flask-Limiter, Flask-CORS.
  - Single entrypoint `run.py`; no separate backend/frontend apps.

- **Database**
  - SQLite as default database (configurable via `DATABASE_URI`).
  - User model (`app/models/user.py`): `id`, `username`, `password_hash`.
  - CLI command `flask init-db` to create tables and optionally seed a default admin user.

- **Web (server-rendered)**
  - Blueprint `web`: routes for `/`, `/health`, `/login`, `/logout`.
  - Session-based authentication for browser users.
  - Templates: `base.html`, `home.html`, `login.html`, `404.html`, `500.html`.
  - Static assets: `app/static/style.css` (World of Shadows theme).

- **API (REST v1)**
  - Versioned API under `/api/v1`.
  - **Auth:** `POST /api/v1/auth/register`, `POST /api/v1/auth/login` (returns JWT), `GET /api/v1/auth/me` (protected).
  - **System:** `GET /api/v1/health`, `GET /api/v1/test/protected` (protected).
  - JWT authentication for API; CORS and rate limiting enabled.
  - Consistent JSON error responses for 401 and 429.

- **Tooling and docs:** requirements.txt, .env.example, Postman collection for API testing.

### Technical notes

- No movie or blog domain logic; foundation only.
- Code and identifiers in English.
- `.gitignore` updated (instance/, *.db, .env, __pycache__, etc.).
- Server foundation: Flask app factory, config, extensions (db, jwt, limiter, CORS), single entrypoint run.py.
- Database: SQLite default, User model, flask init-db.
- Web: Blueprint with home, health, login, logout; session auth; templates and static.
- API: /api/v1 health, auth (register, login, me), protected test route; JWT and rate limiting.
- Tooling and docs: requirements.txt, .env.example, Postman collection for API testing.
