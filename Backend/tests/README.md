# Test Suite

Pytest-based tests for the World of Shadows server (web and API v1). Matches current behavior: POST-only logout, protected dashboard, login redirect to dashboard, no default users from init-db.

## Run

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=term-missing

# Only web, API, or news API
pytest tests/test_web.py -v
pytest tests/test_api.py -v
pytest tests/test_news_api.py -v
```

## Layout

- **conftest.py** – Fixtures: `app` (create_app with TestingConfig), `client`, `runner`, `test_user` (DB user, role=user), `auth_headers` (JWT for test_user), `editor_user` (role=editor), `editor_headers` (JWT for editor), `test_user_with_email`, `sample_news` (published + draft news for list/detail/search/sort tests).
- **test_web.py** – Web: home, health, login (GET/POST, redirect when already logged in), **POST** logout, dashboard (anonymous → redirect to login, logged in → 200), 404, register, forgot/reset password.
- **test_api.py** – API v1: health, register, login, me, test/protected; status codes and JSON responses; CORS.
- **test_news_api.py** – News API: list JSON shape, detail JSON, search (q), sort (sort/direction), pagination (page/limit), category filter, published-only visibility (draft not in list, detail 404 for draft); anonymous write 401, user-role write 403, editor write (POST/PUT/publish/delete) 200/201.

## Config

Tests use `TestingConfig` in `app/config.py`: in-memory SQLite, fixed secrets, CSRF disabled, high rate limit. No env secrets required. Users are created by the `test_user` fixture or via API in tests; init-db is not used to seed users.
