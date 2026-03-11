# Changelog

All notable changes to the World of Shadows project are documented in this file.

---

## [Unreleased]

### Added
- **Phase 3 (authorization helpers and guards):** Centralized role constants (`ALLOWED_ROLES`) and permission helpers in `app.auth.permissions`: `current_user_has_role`, `current_user_has_any_role`, `current_user_is_moderator_or_admin`, `current_user_is_banned`; admin and write-news checks now treat banned users as not privileged. Decorators `@require_jwt_admin` and `@require_jwt_moderator_or_admin` for API routes (include JWT + role check). Role and admin routes use `@require_jwt_admin`; news write routes use `@require_jwt_moderator_or_admin`. Web: `require_web_login` and `require_web_admin` redirect banned users to `/blocked`; web login redirects banned users to blocked page and logs `login_blocked_banned`. New route `GET /blocked` and template `blocked.html` for restricted-access message.
- **Phase 2 (roles and ban model):** Replaced editor role with moderator everywhere. Roles are now user, moderator, admin. Migration 009: added user fields `is_banned`, `banned_at`, `ban_reason`; data migration maps existing editor→moderator. Role seed and `ensure_roles_seeded()` only create user, moderator, admin. User model: `can_write_news()` uses moderator or admin; `to_dict(include_ban=...)` for ban fields. New users default to role=user. run.py seed-dev-user and seed-news use moderator; conftest and tests use `moderator_user`/`moderator_headers`; test_news_api and test_admin_logs updated; README and news_routes comments updated.
- **Phase 1 audit (roles and access control):** Documented current state for role and access-control upgrade: User model (role_id, no ban fields), Role model (user, moderator, editor, admin), auth/session/JWT flow, permission helpers (current_user_is_admin, current_user_can_write_news using editor/admin), news write protection (editor-or-admin), user API and admin/dashboard protections, absence of banned-user handling and blocked-user view, Postman collection (editor references, no ban/assign-role). Audit file: `docs/audit-phase1-roles-access-control.md`. Lists all editor references to replace with moderator, migration path for editor→moderator, and gaps (ban state, blocked-user UX, admin-only role/ban API). No behavior changes.
- **Admin logs & roles audit:** Recorded current state of the dashboard logs area (log rows come from a hardcoded DEMO_ROWS array in dashboard.js; no API), user model and role column (user/editor/admin only; migration 004 uses server_default editor), auth and session/JWT flow, existing role checks (API only; dashboard has none), logger usage (technical logs only; no persisted activity/audit log), CSV export (client-side from demo data only), and test coverage for dashboard/auth/admin. No code or behavior change; audit only.
- **Role foundation:** Role model and `roles` table with seeded names: user, moderator, editor, admin. User model has `role_id` FK to Role; `role` property returns role name. New users get default role user. Centralized helpers: `user.has_role(name)`, `user.has_any_role(names)`, `user.is_admin`, `user.is_moderator_or_admin`; API permissions use `user.is_admin`; web guard `require_web_admin`. Migration 007: create roles, backfill from `users.role`, drop string column. `ensure_roles_seeded()` on init-db and in tests.
- **ActivityLog and migration:** Persistent `activity_logs` table (id, created_at, actor_user_id, actor_username_snapshot, actor_role_snapshot, category, action, status, message, route, method, tags, meta, target_type, target_id). Migration 008.
- **Centralized activity log service:** `log_activity(...)` in `app.services.activity_log_service`; `list_activity_logs(...)` for filtering and pagination. All activity logging goes through this service.
- **Auth and account instrumentation:** Activity logs for web and API login (success, failure, blocked unverified), logout, registration, verification email sent, email verification success/failure, resend verification, password reset requested/completed.
- **News and admin instrumentation:** Activity logs for news created/updated/deleted/published/unpublished, user updated, user role changed, user deleted.
- **Admin-only logs API:** `GET /api/v1/admin/logs` (JWT, admin only) with filters q, category, status, date_from, date_to, page, limit; response items, total, page, limit. `GET /api/v1/admin/logs/export` returns CSV (admin only). Session-authenticated `GET /dashboard/api/logs` and `GET /dashboard/api/logs/export` for the dashboard (require_web_admin).
- **Dashboard logs from real API:** Removed DEMO_ROWS; dashboard Logs tab fetches from `/dashboard/api/logs` with loading, empty, and error states; filters and count reflect real data. CSV export uses server-side `/dashboard/api/logs/export`.
- **Admin-only dashboard UI:** Overview, Metrics, and Logs sections visible only to admin users; User Settings visible to all. Non-admin users get 403 on dashboard logs API.
- **Tests:** `test_admin_logs.py` for default role on registration, role helpers, admin logs API 401/403/200, filters, activity log on login, dashboard logs API access, CSV export.
- **Role CRUD API:** Full CRUD for roles at `/api/v1/roles`: `GET /api/v1/roles` (list, admin only, paginated with `page`, `limit`, `q`), `GET /api/v1/roles/<id>` (single role, admin only), `POST /api/v1/roles` (create, admin only; body: `name`), `PUT /api/v1/roles/<id>` (update name, admin only), `DELETE /api/v1/roles/<id>` (admin only; 400 if users have this role). Role names: lowercase, digits, underscore; 1–20 chars; validated and normalized in `role_service`. `BackendApi.md` section **5. Roles (CRUD)**; Admin Logs renumbered to section 6.
- **User update:** Accepts any role that exists in the database (no fixed enum); validated via role lookup.
- **Postman:** "Roles" folder: List, Get, Create, Update, Delete (admin token); collection variable `role_id`; README updated.
- **Tests:** `test_roles.py` (16 tests) for list/get/create/update/delete as admin, 403 as non-admin, 401 unauthenticated, 404/400/409 where applicable, delete blocked when users have the role.
- **News CRUD (API):** Full CRUD for news was already in place; extended for editors: **List** with optional JWT and `published_only=0` or `include_drafts=1` returns all articles including drafts. **Detail** with editor/admin JWT returns draft articles (so editors can read/edit drafts). List and detail use optional JWT; unauthenticated behavior unchanged (published only). `BackendApi.md` section **3. News (CRUD)** updated with new query params and behavior.
- **Postman:** News folder extended with News List (editor, include drafts), News Create, News Update, News Publish, News Unpublish, News Delete (all use editor/admin token and `news_id`).
- **Tests:** `test_news_api.py` +3 tests: editor list with `published_only=0` includes drafts, list without param still published-only, editor GET draft by id returns 200.
- **Postman suite and unit tests:** Collection covers Auth, System, News (CRUD + publish/unpublish), Users (CRUD), Roles (CRUD), Admin Logs (list + export); all requests have test scripts (status and body assertions). `postman/README.md` documents env vars including `role_id` and flow. **test_users_api.py** added (16 tests): Users list/get/update/delete aligned with Postman (401/403/404, admin vs non-admin, self vs other). Backend **tests/README.md** updated with full layout (test_api, test_news_api, test_users_api, test_roles, test_admin_logs, test_web, test_web_open_redirect, test_config). Total **116** backend tests.

### Changed
- **ActivityLog model:** Column `metadata` renamed to `meta` (SQLAlchemy reserved name).
- **Email registration optional:** New config `REGISTRATION_REQUIRE_EMAIL` (default **False**): when False, registration does not require email (API and web). Users without email can log in immediately; verification email is only sent when an email is provided. Set `REGISTRATION_REQUIRE_EMAIL=1` to restore the previous behaviour (email required, verify before login). `create_user()` accepts optional email; API register and web register only require and send verification when config is True or when email is given. Template `register.html` shows "Email (optional)" and drops the required attribute when email is not required. Tests updated (register without email returns 201 / redirects to login when optional; 400 / error when required).

---

## [0.0.9] - 2026-03-11

### Added

- **Wiki page:** Dedicated view at `/wiki`, reachable via the "Wiki" button in the header. Content is loaded from the Markdown file `Backend/content/wiki.md` and rendered to HTML with the Python `markdown` library (extension "extra"); if the file is missing, "Coming soon" is shown. New stylesheet `app/static/wiki.css` for wiki prose; template `wiki.html` extends `base.html`. Dependency `markdown>=3.5,<4` in `requirements.txt`. Test: `test_wiki_returns_200` in `test_web.py`.
- **Startup mode log:** On backend startup, a single line is always logged indicating the current mode: `Running BLACKVEIN Backend [mode: TESTING]`, `[mode: NORMAL (MAIL_ENABLED=1)]`, or `[mode: DEV (MAIL_ENABLED=0)]` (`app/__init__.py`).

### Changed

- **Email verification (dev):** When `MAIL_ENABLED=0` or `TESTING=True`, the activation link is logged at WARNING level on register/resend ("DEV email verification mode (...). Activation URL for 'user': ...") so it appears in the same terminal as HTTP logs (`app/services/mail_service.py`).

---

## [0.0.8] - 2025-03-10

### Added

- **User CRUD API:** Full CRUD for users at `/api/v1/users`: `GET /api/v1/users` (list, admin only, paginated with `page`, `limit`, `q`), `GET /api/v1/users/<id>` (single user, admin or self), `PUT /api/v1/users/<id>` (update, admin or self; body: optional `username`, `email`, `password`, `current_password`, `role` admin only), `DELETE /api/v1/users/<id>` (admin only). Service layer: `get_user_by_id`, `list_users`, `update_user`, `delete_user` in `user_service.py`; permissions `get_current_user()` and `current_user_is_admin()` in `app.auth.permissions`. On delete: user's news keep `author_id=None`; reset and verification tokens are removed.
- **User model:** `to_dict(include_email=False)` extended; auth responses (login, me) include `email` for the current user when requested.
- **BackendApi.md:** Section **4. Users (CRUD)** with all endpoints, query/body parameters and response formats; section 5 (General) renumbered.
- **Postman:** "Users" folder in the collection: Users List (admin), Users Get (self), Users Update (self), Users Get (404), Users Delete (admin, uses `target_user_id`). Variable `target_user_id` in collection and environments; Users List sets it to another user for Delete. `postman/README.md` and collection description updated for users and admin usage.
- **Runbook:** All commands documented in **two forms** (short `flask` / Python form `python -m flask`) and for **PowerShell** as well as **Bash/Terminal**. Table "Further useful commands" (migrations, stamp, seed-dev-user, seed-news, pytest). API flow with curl examples for Bash and PowerShell. Troubleshooting: `&&` in PowerShell, `flask` not found ? `python -m flask`.

### Changed

- **Config:** `MAIL_USE_TLS` default changed from `True` to `False` (local SMTP without TLS).
- **Auth API:** Login and Me responses include `email` for the logged-in user.

---

## [0.0.7] - 2025-03-10

### Added

- **Email verification on registration:** New users must verify their email before they can log in (web session and API JWT). After registration (web and API), a time-limited activation token is created and a verification email is sent (or only logged in dev when MAIL_ENABLED is off). Activation URL: `/activate/<token>`; validity configurable via `EMAIL_VERIFICATION_TTL_HOURS` (default 24).
- **User model:** Column `email_verified_at` (nullable DateTime); migration `005_add_email_verified_at`.
- **EmailVerificationToken:** New model and table `email_verification_tokens` (token_hash, user_id, created_at, expires_at, used_at, invalidated_at, purpose, sent_to_email); migration `006_email_verification_tokens`. Token creation as with password reset (secrets.token_urlsafe(32), SHA-256 hash).
- **Service layer:** `create_email_verification_token`, `invalidate_existing_verification_tokens`, `get_valid_verification_token`, `verify_email_with_token` in `user_service.py`. `send_verification_email` in `mail_service.py` (uses `APP_PUBLIC_BASE_URL` or url_for for activation link; when MAIL_ENABLED=False or TESTING, only logs).
- **Web registration:** After successful registration, redirect to `/register/pending` with instructions to check email; token is created and verification email sent.
- **New web routes:** `GET /register/pending`, `GET /activate/<token>`, `GET/POST /resend-verification` (generic success message, no user enumeration; existing tokens invalidated). Templates: `register_pending.html`, `resend_verification.html`.
- **Login enforcement:** Web login and `require_web_login`: users with email but no `email_verified_at` cannot log in (session not set or cleared, flash message). API `POST /auth/login`: for unverified email returns 403 with `{"error": "Email not verified."}`.
- **Config:** `MAIL_ENABLED`, `MAIL_USE_SSL`, `APP_PUBLIC_BASE_URL`, `EMAIL_VERIFICATION_TTL_HOURS` in `app/config.py`. Existing mail config (MAIL_SERVER, MAIL_PORT, etc.) unchanged.
- **Tests:** `test_register_post_success_redirects_to_pending`, `test_register_pending_get_returns_200`, `test_activate_valid_token_redirects_to_login`, `test_login_blocked_for_unverified_user`, `test_resend_verification_get_returns_200`, `test_login_unverified_email_returns_403`. Fixture `test_user_with_email` sets `email_verified_at` so reset/login tests keep working. Audit doc `Backend/docs/PHASE1_AUDIT_0.0.7.md`.
- **Postman:** Full test environment and test suite: two environments ("World of Shadows ? Local", "World of Shadows ? Test") with `baseUrl`, `apiPath`, `username`, `password`, `email`, `access_token`, `user_id`, `news_id`, `register_username`, `register_email`, `register_password`. Collection with test scripts for all requests: Auth (Register, Login, Login invalid, Me, Me no token), System (Health, Test Protected), News (List, Detail, Detail 404). Assertions for status codes and response body; Login sets token and `user_id`, News List sets `news_id`. `postman/README.md` with instructions (import, variables, Collection Runner).

### Changed

- **Registration (web):** Redirect after success changed from login to `/register/pending`.
- **Registration (API):** After `create_user`, verification tokens are created and email sent; login remains blocked with 403 until verification.

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
