# World-engine HTTP routes

This package owns the implementation behind `app.api.http`. The root `http.py` module is a compatibility facade for tests, app startup, and existing imports.

- `common.py` contains the shared router, dependency helpers, auth guard, and small runtime helpers.
- `models.py` contains request payload models.
- `play_run_routes.py` covers template, run, ticket, and transcript HTTP endpoints.
- `story_session_routes.py` covers story-session creation, opening generation, and turn execution.
- `story_state_routes.py` covers state, diagnostics, W5, and read-only diagnostic snapshots.
- `branching_routes.py` covers branch tree and branch timeline endpoints.
- `narrative_web_routes.py` covers callback web, consequence cascade, diagnostics envelope, streaming, and narrative governance summary endpoints.
- `narrative_package_routes.py` covers narrative package reload and preview session lifecycle endpoints.
- `narrative_runtime_routes.py` covers narrative runtime state, validator config, health, and validate-and-recover endpoints.
