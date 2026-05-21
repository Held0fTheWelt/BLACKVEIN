# Phase 6B-4.5 MVP04 diagnostics route repair

The World-Engine HTTP refactor moved route implementations from
`world-engine/app/api/http.py` into package modules under
`world-engine/app/api/http_routes/`. The MVP04 diagnostics endpoint remains
registered by `narrative_web_routes.py` at
`GET /story/sessions/{session_id}/diagnostics-envelope` and still returns the
last committed diagnostics envelope through `get_last_diagnostics_envelope`.

The MVP04 gate helper now follows the HTTP facade's direct `http_routes`
imports and validates the actual package-based `@router.get(...)`
registrations instead of requiring decorators to live in the facade file. This
keeps the observability gate semantic while matching the current route layout.
