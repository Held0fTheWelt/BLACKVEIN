# Test Suite

Pytest-based tests for the World of Shadows server (web and API v1). Matches current behavior: POST-only logout, protected dashboard, login redirect to dashboard, no default users from init-db.

## Run

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=term-missing

# Only web or API
pytest tests/test_web.py -v
pytest tests/test_api.py -v
```

## Layout

- **conftest.py** – Fixtures: `app` (create_app with TestingConfig), `client`, `runner`, `test_user` (DB user for login), `auth_headers` (JWT for API).
- **test_web.py** – Web: home, health, login (GET/POST, redirect when already logged in), **POST** logout, dashboard (anonymous → redirect to login, logged in → 200), 404.
- **test_api.py** – API v1: health, register, login, me, test/protected; status codes and JSON responses.

## Config

Tests use `TestingConfig` in `app/config.py`: in-memory SQLite, fixed secrets, CSRF disabled, high rate limit. No env secrets required. Users are created by the `test_user` fixture or via API in tests; init-db is not used to seed users.
