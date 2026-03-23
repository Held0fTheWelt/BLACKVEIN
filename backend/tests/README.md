# Test Suite

Pytest-based tests for the World of Shadows backend (web and API v1). Matches current behavior: POST-only logout, protected dashboard, login redirect to dashboard, no default users from init-db.

**Run all commands from the repository `backend/` directory** (e.g. `cd backend` then `pytest`).

## Run

```bash
# From backend/
# All tests (with coverage; 85% gate in pytest.ini)
pytest

# Full suite without coverage
pytest --no-cov

# With explicit coverage options
pytest --cov=app --cov-report=term-missing

# Targeted modules
pytest tests/test_web.py -v
pytest tests/test_api.py -v
pytest tests/test_news_api.py -v
pytest tests/test_forum_api.py -v
pytest tests/test_wiki_public.py -v
pytest tests/test_data_api.py -v
pytest tests/test_users_api.py -v
pytest tests/test_roles.py -v
pytest tests/test_admin_logs.py -v
```

See **docs/VERIFICATION.md** for what each command verifies, expected success, and coverage gate details.

## Layout

- **conftest.py** – Fixtures: `app`, `client`, `runner`, `test_user` (role=user), `auth_headers`, `moderator_user`, `moderator_headers`, `admin_user`, `admin_headers`, `test_user_with_email`, `sample_news`, area/forum fixtures.
- **test_api.py** – API v1: health, register, login, me, test/protected; status codes, JSON, CORS.
- **test_news_api.py** – News CRUD: list/detail (public + moderator drafts), search/sort/pagination/category; write 401/403/201/200; publish/unpublish/delete.
- **test_forum_api.py** – Forum: categories, threads, posts, likes, reports, subscriptions, notifications, permissions, moderation, search.
- **test_wiki_public.py** – Public wiki API and discussion link behaviour.
- **test_data_api.py** – Data export/import API: auth, metadata, validation, SuperAdmin requirement.
- **test_users_api.py** – Users CRUD: list (admin 200, non-admin 403), get (self/admin/other), update (self/admin/403), delete (admin/403/404); 401 without token.
- **test_roles.py** – Roles CRUD: list/get/create/update/delete (admin only); 403/401/404/400/409 as applicable.
- **test_admin_logs.py** – Admin logs API (401/403/200), filters, dashboard logs, CSV export; role helpers; activity log on login.
- **test_areas_api.py** – Areas and feature-areas API; user areas.
- **test_slogans.py** – Slogans API and site slogans/settings.
- **test_metrics_dashboard.py** – Dashboard metrics API.
- **test_security_and_correctness.py** – Wiki sanitization, password change, security headers, CSV formula injection, etc.
- **test_wiki_api.py** – Wiki admin/editorial API.
- **test_web.py** – Web: home, health, wiki, login, logout, dashboard, register, forgot/reset password, activation, CSRF.
- **test_web_open_redirect.py** – Open redirect safety (login `next`).
- **test_config.py** – App config (secret key, testing config).

## Config

Tests use `TestingConfig` in `app/config.py`: in-memory SQLite, fixed secrets, CSRF disabled, high rate limit. No env secrets required. Users are created by the `test_user` fixture or via API in tests; init-db is not used to seed users.
