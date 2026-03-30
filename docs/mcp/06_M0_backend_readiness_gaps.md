# Backend Readiness & Gaps (M0)

Diese Datei listet auf, was für Phase A (und später B/C) **bereits vorhanden** ist und wo **Gaps** bestehen.

## Bereits vorhanden (Repo evidence)
- Web health:
  - `GET /health` (backend/app/web/routes.py)
- Session REST API v1:
  - `POST /api/v1/sessions`
  - `GET /api/v1/sessions/<id>`
  - `POST /api/v1/sessions/<id>/turns`
  - `GET /api/v1/sessions/<id>/logs`
  - `GET /api/v1/sessions/<id>/state`
  - (backend/app/api/v1/session_routes.py)

## Gaps (für saubere MCP Nutzung)
### GAP-1: Module/Content Read API (optional)
- Für remote-only Operator (ohne lokales Repo) wäre sinnvoll:
  - `GET /api/v1/story/modules`
  - `GET /api/v1/story/modules/<module_id>`
  - `GET /api/v1/story/modules/<module_id>/scenes/<scene_id>`
Status: **nicht belegt** im Ist-Stand → optionaler Ausbau.

### GAP-2: Guard Preview Endpoints
- Für `wos.guard.preview_delta` und `wos.guard.preview_transition`:
  - `POST /api/v1/guard/preview-delta`
  - `POST /api/v1/guard/preview-transition`
Status: **nicht belegt** → geplant für B3.

### GAP-3: AuthZ/Service Token für Session API
- Session API ist im aktuellen Code nicht sichtbar geschützt (keine Decorators im file).
- Für MCP Operator-Tools sollte ein Service/AuthZ Layer vorgesehen werden.
Status: **prüfen** (M0 Gate).

### GAP-4: Story Persistenz (W3.2)
- Session-State ist in-memory; Backend erwähnt W3.2.
Status: außerhalb von MCP-A1; relevant für robuste Operator-Flows.

