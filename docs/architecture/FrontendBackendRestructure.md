# Frontend/Backend Restructure – Implementation Note

This document defines the target structure for splitting World of Shadows into separate **Backend/** and **Frontend/** folders. MasterBlogAPI is used only as an architectural reference (frontend/backend separation, API-first content delivery, thin frontend consuming backend JSON). World of Shadows branding, auth patterns, and existing behaviour are preserved.

---

## 1. Reference: MasterBlogAPI (Summary)

- **Backend:** Single Flask app (Port 5002); REST API under `/api/v1` (JSON); JWT auth; SQLite + SQLAlchemy (Post, User); Swagger at `/api/docs`; CORS & rate limiting.
- **Frontend:** Separate Flask app (Port 5001); serves only HTML/CSS/JS; no DB; all data via `fetch()` to backend API (API-first, JSON).
- **Content:** Blog posts (CRUD), categories, tags, comments; all delivered as JSON to the frontend.

---

## 2. Current World of Shadows (Pre-Restructure)

| Area | Location | Notes |
|------|----------|--------|
| Flask app | `app/__init__.py` | `create_app()`, single process, template_folder in `app/web/templates`, static_folder in `app/static` |
| Config | `app/config.py` | Base/Development/Testing; DB path `instance/wos.db` (relative to project root) |
| Web routes | `app/web/routes.py` | Home, login, logout, register, forgot/reset password, news, wiki, community, game-menu, dashboard |
| API routes | `app/api/v1/` | `/api/v1`: health, auth (register, login, me), test/protected |
| Auth | Session (web) + JWT (API) | `app/web/auth.py`: `require_web_login`, `is_safe_redirect`; CSRF for web, API exempt |
| Templates | `app/web/templates/` | base, home, login, register, dashboard, news, wiki, community, game_menu, forgot/reset_password, 404, 500 |
| Static | `app/static/` | style.css, landing.js, dashboard.js |
| Models | `app/models/` | User, PasswordResetToken |
| Services | `app/services/` | user_service, mail_service |
| Tests | `tests/` | conftest, test_web, test_api, test_config, test_web_open_redirect |
| Migrations | `migrations/` | Flask-Migrate (Alembic) |
| Entrypoint | `run.py` | CLI: init-db, seed-dev-user |
| Instance | Project root `instance/` | Created by config when DATABASE_URI unset; contains `wos.db` |

Today: one process serves both HTML pages and API; “frontend” is server-rendered templates + static assets.

---

## 3. Target Architecture

### 3.1 Backend/ (Data, API, Auth, Dashboard, Persistence, Tests)

Backend owns all data, API, authentication, dashboard (admin/authenticated UI), persistence, and tests.

| Belongs in Backend/ | Current location / notes |
|---------------------|---------------------------|
| `app/` | Move from repo root; keep `config.py`, `extensions.py`, `models/`, `services/`, `api/`. |
| `instance/` | Move under Backend/; DB path becomes `Backend/instance/wos.db` (or configurable). |
| `migrations/` | Move under Backend/; Alembic env/cwd relative to Backend. |
| `tests/` | Move under Backend/; test backend API, auth, services, DB. |
| `run.py` | Move to Backend/; entrypoint for backend app (or `backend_app.py` if preferred). |
| Requirements | Backend `requirements.txt` (and optional `requirements-dev.txt`) in Backend/. |
| Auth | Session + JWT stay in backend; dashboard and any admin UI remain backend-served (session). |
| API | All `/api/v1` routes; add **news API** (list, detail, optional CRUD with JWT) for frontend consumption. |
| Dashboard / protected web | Login, logout, register, forgot-password, reset-password, dashboard, game-menu: **remain in backend** (session-based, server-rendered). |

Backend does **not** serve the public marketing/news pages; those move to the frontend.

### 3.2 Frontend/ (Public Website, Public News, Static Assets, API Consumption)

Frontend is the public face: home, news list, news detail, and any other public pages. It consumes backend via JSON API only.

| Belongs in Frontend/ | Purpose |
|----------------------|---------|
| `frontend_app.py` | Minimal Flask (or similar) server: serves HTML and static assets only; no DB, no business logic. |
| `templates/` | Public pages only: base, home, news (list), news detail, optionally wiki/community placeholders. |
| `static/` | CSS, JS (e.g. style.css, landing.js; news page can load data via API). |
| Public pages | Home, News (list), News (detail); thin rendering, data from Backend API (e.g. `GET /api/v1/news`, `GET /api/v1/news/<id>`). |

Frontend does **not** implement login/register/dashboard/game-menu; those stay in the backend. Links to “Log in” or “Dashboard” can point to the backend URL (same-origin or configured backend origin).

### 3.3 What Stays Backend-Only (No Move to Frontend)

- Login, logout, register, forgot-password, reset-password (session + CSRF).
- Dashboard and game-menu (protected, session).
- All API definitions and JWT/session auth logic.
- User/PasswordResetToken models, user_service, mail_service.
- Migrations, instance, run.py, backend tests.

### 3.4 What Becomes Frontend (Public Pages)

- **Home** (landing): move to Frontend; can stay server-rendered with static assets, or fetch minimal data from API if needed.
- **News list** and **news detail**: move to Frontend; implement a **real news system** in Backend (model + API), frontend consumes JSON (API-first principle from MasterBlogAPI).
- Optionally: wiki/community placeholders in Frontend (or keep as redirects to backend until they are implemented).

### 3.5 News System (Principle from MasterBlogAPI)

- **Backend:** New model (e.g. `News` or `Post`): id, title, slug or id, content/summary, author, published_at, status; CRUD API under e.g. `/api/v1/news` (list, get by id/slug). List/detail public; create/update/delete with JWT (and optionally role checks).
- **Frontend:** News list page: fetch `GET /api/v1/news` (or with query params), render list. News detail page: fetch `GET /api/v1/news/<id>`, render article. No direct DB access; thin frontend.

---

## 4. Target Directory Layout (After Restructure)

```
WorldOfShadows/
├── Backend/
│   ├── app/
│   │   ├── __init__.py          # create_app (no public home/news templates here)
│   │   ├── config.py
│   │   ├── extensions.py
│   │   ├── models/              # User, PasswordResetToken, News (new)
│   │   ├── services/
│   │   ├── api/v1/              # auth, system, news (new)
│   │   ├── web/                 # auth routes + dashboard/game-menu templates only
│   │   │   ├── routes.py        # login, logout, register, forgot/reset, dashboard, game-menu
│   │   │   ├── auth.py
│   │   │   └── templates/       # login, register, dashboard, game_menu, forgot/reset, 404, 500
│   │   └── static/              # backend-only assets if any (e.g. dashboard.js)
│   ├── instance/
│   ├── migrations/
│   ├── tests/
│   ├── run.py
│   ├── requirements.txt
│   └── requirements-dev.txt
├── Frontend/
│   ├── frontend_app.py
│   ├── templates/               # base, home, news (list), news (detail), optional wiki/community
│   └── static/                  # style.css, landing.js, optional news.js
├── docs/
├── CHANGELOG.md
├── README.md
└── ... (repo-level files; docker/compose can be updated to run Backend + Frontend)
```

---

## 5. Decisions and Conventions

- **No blind copy of MasterBlogAPI:** Only structure (Backend vs Frontend) and pattern (API-first, thin frontend) are adopted; domain is World of Shadows (news, not blog posts; existing auth and branding preserved).
- **Reuse existing auth:** Session + JWT and `require_web_login` / `is_safe_redirect` stay in Backend; Frontend does not duplicate auth logic.
- **Avoid unnecessary rewrites:** Move and adapt; keep existing code readable and production-oriented. Update imports and paths (e.g. `instance/`, `template_folder`) in the same step as the move.
- **Responsibilities:**
  - **Backend** = data, API, auth, dashboard, persistence, tests.
  - **Frontend** = public website, public news pages, static assets, API consumption only.

---

## 6. Next Steps (Not Done in This Audit)

1. Create `Backend/` and `Frontend/` and move/restructure files as per above.
2. Implement news model and `/api/v1/news` in Backend.
3. Add `frontend_app.py` and move public templates/static into Frontend; wire frontend to backend API URL.
4. Update run scripts, docker-compose, and docs (e.g. ServerArchitecture.md, README) to describe two processes (Backend + Frontend) and the API boundary.

This document is the result of an audit of the current repository and the MasterBlogAPI reference; no file moves were performed in this step.

---

## 7. Routing responsibility split (implemented)

| Responsibility | Backend (port 5000) | Frontend (port 5001) |
|----------------|--------------------|----------------------|
| **Public home** | When `FRONTEND_URL` is set: redirect `GET /` → frontend. Else: serve legacy `home.html`. | `GET /` – public landing (hero, links to backend login/register). |
| **Public news** | When `FRONTEND_URL` is set: redirect `GET /news` → frontend. Else: serve legacy `news.html`. | `GET /news` (list), `GET /news/<id>` (detail); data via JS from backend API. |
| **Auth & internal** | `GET/POST /login`, `POST /logout`, `GET/POST /register`, `GET/POST /forgot-password`, `GET/POST /reset-password/<token>`, `GET /dashboard` (protected), `GET /game-menu` (protected). All session-rendered. | No auth; “Log in” / “Get started” link to backend URL. |
| **Placeholders** | `GET /wiki`, `GET /community` – backend placeholders (frontend header links to backend for these). | — |
| **API** | All `GET/POST ... /api/v1/*` (health, auth, future news). | Consumes API only via JS; no server-side API. |

**Config:** Backend `FRONTEND_URL` (no trailing slash). When set, logout also redirects to `FRONTEND_URL/`. No duplicate public news: backend does not serve a competing news page when frontend is in use.
