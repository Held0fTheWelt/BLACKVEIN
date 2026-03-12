# Test Suite

Pytest-based tests for the World of Shadows server (web and API v1). Matches current behavior: POST-only logout, protected dashboard, login redirect to dashboard, no default users from init-db.

## Run

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=term-missing

# Only web, API, or specific API module
pytest tests/test_web.py -v
pytest tests/test_api.py -v
pytest tests/test_news_api.py -v
pytest tests/test_users_api.py -v
pytest tests/test_roles.py -v
pytest tests/test_admin_logs.py -v
```

## Layout

- **conftest.py** – Fixtures: `app`, `client`, `runner`, `test_user` (role=user), `auth_headers`, `moderator_user`, `moderator_headers`, `admin_user`, `admin_headers`, `test_user_with_email`, `sample_news`.
- **test_api.py** – API v1: health, register, login, me, test/protected; status codes, JSON, CORS.
- **test_news_api.py** – News CRUD: list/detail (public + moderator drafts), search/sort/pagination/category; write 401/403/201/200; publish/unpublish/delete.
- **test_users_api.py** – Users CRUD: list (admin 200, non-admin 403), get (self/admin/other), update (self/admin/403), delete (admin/403/404); 401 without token. Aligned with Postman Users folder.
- **test_roles.py** – Roles CRUD: list/get/create/update/delete (admin only); 403/401/404/400/409 as applicable.
- **test_admin_logs.py** – Admin logs API (401/403/200), filters, dashboard logs, CSV export; role helpers; activity log on login.
- **test_web.py** – Web: home, health, wiki, login, logout, dashboard, register, forgot/reset password, activation, CSRF.
- **test_web_open_redirect.py** – Open redirect safety (login `next`).
- **test_config.py** – App config (secret key, testing config).

## Config

Tests use `TestingConfig` in `app/config.py`: in-memory SQLite, fixed secrets, CSRF disabled, high rate limit. No env secrets required. Users are created by the `test_user` fixture or via API in tests; init-db is not used to seed users.
