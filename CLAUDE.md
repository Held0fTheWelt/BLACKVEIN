# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**World of Shadows (Blackveign)** is a Flask-based application with two separate deployable units:

1. **Backend** (`backend/`): REST API, database, auth, admin dashboard
2. **Administration-tool** (`administration-tool/`): Public website + staff management interface; no database, consumes the backend API only

Both are Flask apps. The frontend uses vanilla JavaScript + Jinja2 templates (no React/Vue/SPA framework).


## Using ClaudeClockwork Agents

This project uses the ClaudeClockwork autonomous agent framework.

**Important**: Framework management files have been moved to ClaudeClockwork.
This repo contains only WorldOfShadows project files.

For agent patterns, framework documentation, and agent catalog:
→ See: `/mnt/d/ClaudeClockwork/KNOWLEDGE/`
→ See: `/mnt/d/ClaudeClockwork/AGENTS_CATALOG.md`

For project-specific guidelines, continue reading this file.

---


## Repository Structure

```
backend/                     # REST API server (WSGI app, SQLAlchemy, JWT, migrations)
  app/
    __init__.py             # create_app() factory
    config.py               # Config classes: DevelopmentConfig, TestingConfig, ProductionConfig
    extensions.py           # db, jwt, limiter, mail initialization
    models/                 # SQLAlchemy models: User, Role, News, Forum, Wiki, Area, ActivityLog, etc.
    services/               # Business logic: user_service, forum_service, news_service, activity_log_service, etc.
    api/v1/                 # REST blueprints: auth_routes, news_routes, forum_routes, wiki_routes, admin_routes, etc.
    web/                    # Web blueprints: login, register, dashboard, wiki rendering
    auth/                   # JWT/session utilities, permissions, feature_registry
    static/                 # CSS, JavaScript (admin dashboard)
  migrations/               # Alembic (Flask-Migrate) versions; numbered sequentially (001, 002, ..., 028+)
  tests/                    # pytest suite; conftest.py fixtures, test modules by feature
  run.py                    # CLI: entrypoint with commands (init-db, seed-dev-user, seed-news, etc.)
  pytest.ini                # Coverage gate: 85% fail-under
  requirements.txt          # Dependencies: Flask, SQLAlchemy, JWT, Jinja2, etc.
  requirements-dev.txt      # pytest, coverage, factories

administration-tool/        # Public website + /manage dashboard
  frontend_app.py           # Flask app; routes: /, /news, /forum, /wiki, /manage, etc.
  templates/                # Jinja2 templates for public site and management UI
  static/                   # JavaScript (manage_*.js files), CSS
  requirements.txt          # Flask, requests (for API calls to backend)

docs/                       # Architecture, security, deployment, runbook, forum feature docs
.env.example                # Template for .env (repo root); both backend and frontend read from root .env
docker-compose.yml          # Services: backend (Gunicorn), frontend, PostgreSQL (in production)
```

## Key Architecture Concepts

### Backend: Application Factory + Blueprints

- **`create_app(config_object)`** in `backend/app/__init__.py` initializes Flask, extensions, blueprints, error handlers, and security headers.
- **Config classes** in `backend/app/config.py`:
  - `DevelopmentConfig`: Debug mode, SQLite, dev secrets allowed.
  - `TestingConfig`: In-memory SQLite, CSRF disabled, high rate limits.
  - `ProductionConfig`: PostgreSQL (via DATABASE_URI env var), strict secrets.
- **Extensions** in `backend/app/extensions.py`: SQLAlchemy (db), Flask-JWT-Extended (jwt), Flask-Limiter (limiter), Flask-Mail (mail).
- **Blueprints** registered in `backend/app/api/__init__.py`:
  - **API v1** (`api_v1_bp`): Mounted at `/api/v1/`; routes: auth, news, forum, wiki, users, roles, admin logs, data, areas, etc.
  - **Web** (`web_bp`): Mounted at `/`; routes: home, wiki, login, register, dashboard, etc.

### Database + Migrations

- **ORM**: SQLAlchemy with Flask-SQLAlchemy.
- **Migrations**: Alembic via `flask db upgrade` / `flask db revision`.
- **Models** in `backend/app/models/`:
  - `User`: username, password_hash, email, role_id, created_at.
  - `Role`: name, permissions; seeded on app startup via `ensure_roles_seeded()`.
  - `News`: title, content, category, published, author, created_at.
  - `Forum`: Category, Thread, Post, ForumReport, ForumTag, ForumBookmark, ForumNotification, ForumSubscription.
  - `Wiki`: Article, Discussion (related forum threads).
  - `ActivityLog`: user, action, target_type, target_id, message, meta (before/after), created_at.
  - `Area`, `FeatureArea`: For feature gating.

### Authentication & Authorization

- **API routes**: JWT Bearer token in `Authorization` header.
  - `@jwt_required()`: Requires valid token; sets `current_user` via `get_jwt_identity()`.
  - `@jwt_required(optional=True)`: Token optional; used for public endpoints that have different behavior for logged-in users.
- **Web routes**: Flask session cookies; `require_web_admin()` or role checks via `current_user.is_admin`, `current_user.has_role()`.
- **Roles**: Default roles are `user`, `moderator`, `editor`, `admin`. Registered users get role `user` by default. Admin-only endpoints check `current_user.is_admin` or `user.has_role("admin")`.

### Activity Logging

- **`log_activity(user, action, target_type, target_id, message, meta={})`** in `backend/app/services/activity_log_service.py` records admin/moderation actions to the ActivityLog table.
- **`meta` dict**: Typically contains `{"before": {...}, "after": {...}}` for before/after state tracking (used in moderation: thread lock/unlock, post hide/unhide, report resolution, etc.).
- **Visible in**: Admin dashboard → Activity Logs tab; also available via `GET /api/v1/admin/logs`.

### Service Layer

- **`backend/app/services/`** contains business logic (not directly in routes):
  - `user_service`: user creation, password reset, role assignment.
  - `news_service`: article CRUD, publish/unpublish, filtering.
  - `forum_service`: categories, threads, posts, bookmarks, tags, reports, moderation.
  - `activity_log_service`: logging admin/mod actions.
  - `wiki_service`: article CRUD, discussion links.
  - `data_export_service`, `data_import_service`: GDPR export/import.
  - Services are imported by routes and called to avoid repeating logic.

### Frontend: Vanilla JS + Jinja2

- **No build step**; JavaScript is not bundled.
- **`FrontendConfig.apiFetch(path, options)`** in `administration-tool/static/manage_*.js`: Wrapper for `fetch()` that handles JWT auth (reads token from `sessionStorage`), CORS, and error handling.
- **XSS protection**: `escapeHtml(s)` utility in `manage_forum.js` (and imported/used in other manage modules) sanitizes user-controlled strings before `innerHTML`.
- **Forum admin**: `manage_forum.js` includes tag management, moderation reports, bulk actions, moderation log.
- **News admin**: `manage_news.js` — article CRUD with related forum threads linking.
- **Wiki admin**: `manage_wiki.js` — article CRUD with related forum threads linking.

### Tests

- **Location**: `backend/tests/`.
- **Fixtures** in `conftest.py`:
  - `app`: Flask app with TestingConfig (in-memory SQLite).
  - `client`: Test client for making requests.
  - `test_user`, `moderator_user`, `admin_user`: Pre-seeded test users with roles.
  - `auth_headers`, `moderator_headers`, `admin_headers`: JWT headers for API requests.
  - `sample_news`: Test news article.
- **Coverage gate**: `pytest.ini` sets `--cov-fail-under=85`; tests must maintain 85% coverage.
- **Test modules** (run individually or all together):
  - `test_api.py`: Auth (register, login), health endpoint.
  - `test_news_api.py`: News CRUD, publish, search, pagination.
  - `test_forum_api.py`: Forum categories, threads, posts, bookmarks, tags, reports, moderation, notifications.
  - `test_wiki_public.py` / `test_wiki_api.py`: Wiki articles and discussion links.
  - `test_web.py`: Web routes: login, register, dashboard, password reset.
  - `test_users_api.py`, `test_roles.py`, `test_admin_logs.py`: Admin APIs.
  - `test_data_api.py`: Data export/import (GDPR).
  - `test_security_and_correctness.py`: Security headers, CSRF, sanitization, formula injection prevention.

## Common Development Commands

### Backend Setup & Run

```bash
cd backend

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing

# Database setup (one-time)
export FLASK_APP=run:app  # or add to .env
flask init-db              # Create tables (optional; migrations do this)
flask db upgrade           # Apply Alembic migrations

# Seed development data (requires DEV_SECRETS_OK=1 in .env)
flask seed-dev-user --username dev --password YourPassword1
flask seed-news

# Run backend server
python run.py              # Reads FLASK_APP=run:app from .env or export
# or: flask run

# Backend at http://127.0.0.1:5000
```

### Database Migrations

```bash
cd backend
export FLASK_APP=run:app

# Apply pending migrations
flask db upgrade

# Create a new migration after model changes
flask db revision -m "add_user_bio_column"
# Edit migrations/versions/NNN_add_user_bio_column.py then:
flask db upgrade

# Rollback one migration
flask db downgrade
```

### Frontend (Administration-tool)

```bash
cd administration-tool

# Install dependencies
pip install -r requirements.txt

# Run frontend server
python frontend_app.py

# Frontend at http://127.0.0.1:5001
# Management console: http://127.0.0.1:5001/manage (staff login required)
```

### Testing

```bash
cd backend

# Run all tests with coverage
pytest

# Run tests from one file
pytest tests/test_forum_api.py -v

# Run a single test
pytest tests/test_forum_api.py::test_forum_categories -v

# Run without coverage (faster)
pytest --no-cov

# Run with coverage report (missing lines)
pytest --cov=app --cov-report=term-missing

# Show coverage percentage
pytest --cov=app
```

### Environment & Configuration

- **`.env` file**: Placed at **repo root** (not in backend/); both backend and frontend read from it.
- **Key variables**:
  - `SECRET_KEY`: For session/CSRF (required in production or set `DEV_SECRETS_OK=1`).
  - `JWT_SECRET_KEY`: For JWT signing (fallback to `SECRET_KEY` if not set).
  - `FLASK_APP`: Set to `run:app` (backend).
  - `PORT`: Backend default 5000; frontend default 5001.
  - `BACKEND_API_URL`: Frontend uses this to call the API (e.g., `http://127.0.0.1:5000`).
  - `CORS_ORIGINS`: Backend — comma-separated origins allowed to call the API (include frontend URL if on different port).
  - `DEV_SECRETS_OK=1`: Allows dev fallback secrets and seed commands.
  - `MAIL_ENABLED`: `1` = send real emails; `0` or unset = log URLs only (dev).
  - `DATABASE_URI`: Default SQLite (`sqlite:///instance/wos.db`); set for PostgreSQL in production.

## Code Style & Patterns

### Routes & API Endpoints

- **Routes organized by feature**: `api/v1/forum_routes.py`, `api/v1/news_routes.py`, etc. (not by HTTP method).
- **Status codes**:
  - `200 OK`: GET successful, POST/PUT with success.
  - `201 Created`: POST creates new resource.
  - `204 No Content`: DELETE successful.
  - `400 Bad Request`: Validation error (e.g., missing required field).
  - `401 Unauthorized`: Missing or invalid JWT.
  - `403 Forbidden`: Authenticated but lacks permission (role, ownership, etc.).
  - `404 Not Found`: Resource not found.
  - `409 Conflict`: Duplicate key, state conflict (e.g., trying to delete tag still in use).
  - `429 Too Many Requests`: Rate limit exceeded (flask-limiter).
- **API response format**: JSON object with data or error key (e.g., `{"data": {...}}` or `{"error": "message"}`).

### Database Queries & Performance

- **Visibility filtering** (forum threads, posts):
  - Non-moderators: `status.notin_(("deleted", "hidden", "archived"))`.
  - Moderators: Can see `deleted` and `hidden`; `archived` is staff-only.
  - Use `include_hidden=False` (default) in service methods to exclude `hidden` and `archived` for non-mods.
- **N+1 prevention**:
  - Use `batch_tag_thread_counts(tag_ids)` instead of looping `tag_thread_count(tag)`.
  - Use `list_tags_for_threads(thread_ids)` for batch tag queries.
  - Join-load relationships in SQLAlchemy: `.outerjoin(Author).options(contains_eager(Thread.posts))`.
- **Pagination**: Use `page` and `limit` (not `THREAD_FETCH_CAP` Python-side limit); SQL WHERE filters visibility.

### Security

- **XSS**: Use `escapeHtml()` before setting `innerHTML` in JavaScript. Backend HTML output via Jinja2 is auto-escaped.
- **CSRF**: Flask-WTF form CSRF tokens in web routes; API routes exempt via `csrf.exempt(api_v1_bp)`.
- **SQL injection**: SQLAlchemy parameterized queries (never string concatenation).
- **Rate limiting**: Applied via `@limiter.limit("N per minute")` on routes; default 100 per minute.
- **Security headers**: Added in `backend/app/__init__.py` `after_request` handler: CSP, X-Frame-Options, X-Content-Type-Options, etc.

### Moderation & Activity Logging

- **All moderation actions** (lock/unlock thread, hide/unhide post, resolve report, delete tag, etc.) **must call `log_activity()`** with:
  - `user`: The admin/moderator performing the action.
  - `action`: String describing the action (e.g., "thread_locked", "post_hidden").
  - `target_type`: "thread", "post", "report", etc.
  - `target_id`: ID of the thread/post/report.
  - `message`: Human-readable summary.
  - `meta`: `{"before": {...state before action...}, "after": {...state after action...}}` for audit trail.
- **Example**: Locking a thread:
  ```python
  thread.locked = True
  db.session.commit()
  log_activity(current_user, "thread_locked", "thread", thread.id, f"Locked thread '{thread.title}'", meta={"before": {"locked": False}, "after": {"locked": True}})
  ```

### Testing Patterns

- **Use fixtures**: Avoid creating duplicate fixtures; use `test_user`, `auth_headers`, etc. from `conftest.py`.
- **Test isolation**: Each test runs with a fresh in-memory SQLite database; no test data leakage.
- **JWT testing**: Use `auth_headers` fixture to make authenticated API requests.
- **Error assertions**: Check both status code and error message: `assert response.status_code == 403; assert "admin" in response.get_json()["error"]`.
- **Coverage**: All new logic must be tested; aim for 85% coverage (gate in `pytest.ini`).

## Key Files to Know

| File | Purpose |
|------|---------|
| `backend/app/__init__.py` | App factory, blueprint registration, error handlers, security headers. |
| `backend/app/config.py` | Config classes (Dev, Testing, Prod). |
| `backend/app/extensions.py` | SQLAlchemy, JWT, limiter, mail init. |
| `backend/app/models/*.py` | SQLAlchemy models: User, Role, News, Forum entities, Wiki, ActivityLog, etc. |
| `backend/app/services/*.py` | Business logic: user_service, forum_service, news_service, activity_log_service, etc. |
| `backend/app/api/v1/*.py` | REST routes grouped by feature. |
| `backend/app/auth/permissions.py` | Role/permission checks, decorators. |
| `backend/tests/conftest.py` | Pytest fixtures: app, client, test users, auth headers. |
| `backend/run.py` | CLI entrypoint; imports `create_app()` and Flask CLI commands. |
| `backend/pytest.ini` | Pytest config: coverage gate (85%), test discovery. |
| `administration-tool/frontend_app.py` | Frontend Flask app; routes and templates. |
| `administration-tool/static/manage_*.js` | Admin UI JavaScript; FrontendConfig.apiFetch() for API calls. |
| `.env.example` | Template for environment variables. |
| `docs/runbook.md` | Example API flows. |
| `docs/security.md` | Auth, CSRF, CORS, security headers. |

## Recent Work (Forum Expansion Wave v0.0.30-0.0.32)

The codebase has recently completed a comprehensive five-phase forum expansion wave:

### Phase 1 (v0.0.27-0.0.28): Community Foundation
- Bookmarks and saved threads page
- Thread tags with normalization and editing UI
- Full-text forum search with filters

### Phase 2 (v0.0.30): Forum ↔ News/Wiki Integration
- Discussion thread linking (primary 1:1 relationship)
- Related threads management (many-to-many)
- Auto-suggest related content based on tags and categories

### Phase 3 (v0.0.30): Moderation Professionalization
- Escalation queue for high-priority reports
- Review queue for moderator intake
- Report assignment and bulk status updates
- Resolution notes on all reports
- Activity logging for all moderation actions

### Phase 4 (v0.0.31): Community Profiles & Social Depth
- User profile pages with activity summary
- Popular tags discovery
- Tag detail pages with thread listings
- User bookmarks endpoint

### Phase 5 (v0.0.32): Performance & Regression Testing
- Eager loading of author relationships (prevents N+1 queries)
- Batch tag operations (`batch_tag_thread_counts()`)
- Comprehensive regression test suite (92+ forum tests)
- 85% code coverage maintained throughout

### Key Patterns (Consistent Across All Phases)

- **`FrontendConfig.apiFetch(path, options)`**: All frontend API calls use this wrapper (reads JWT from sessionStorage).
- **`escapeHtml(s)` utility** in manage_forum.js: XSS protection for user-controlled strings in innerHTML.
- **Batch operations** in forum_service: `batch_tag_thread_counts()`, `list_tags_for_threads()` to avoid N+1 queries.
- **Eager loading**: SQLAlchemy `.options(joinedload())` in critical query paths (thread lists, post lists, bookmarks).
- **SQL-level visibility filtering**: `include_hidden=False` in service methods; non-mods see only public threads, mods see hidden/archived/deleted.
- **Moderation logging**: All moderation actions (lock, hide, resolve, delete, assign) call `log_activity()` with before/after metadata.
- **Pagination enforcement**: All list endpoints use `page` and `limit` (1-100) with SQL-level filtering.
- **Test coverage**: 85% gate enforced; 92+ forum tests covering all features and edge cases.

### New Documentation
- `docs/PHASE_SUMMARY.md` — Comprehensive summary of all phases with endpoint reference
- `docs/API_REFERENCE.md` — Complete API documentation with examples
- `CHANGELOG.md` — Updated with all phase changes (v0.0.30-0.0.32)
- Postman collection — Updated with all new endpoints from Phases 2-4

When adding new forum features, follow these patterns for consistency.

## Integration with Git Worktrees (for Feature Branches)

When implementing features requiring isolation:

```bash
# Create a worktree for a feature branch
git worktree add ~/.config/superpowers/worktrees/WorldOfShadows/feature-my-feature feature-my-feature

# Work in the worktree; commit, push, create PR
# (Worktree is independent copy of the repo with its own working directory)

# Clean up when done
git worktree remove ~/.config/superpowers/worktrees/WorldOfShadows/feature-my-feature
```

(See `superpowers:using-git-worktrees` skill for more details.)
