# Milestone 9 Gate Review

Date: 2026-04-04  
Status: PASS  
Recommendation: Proceed

## Scope delivered

- Added canonical Writers-Room unified-stack architecture document:
  - `docs/architecture/writers_room_on_unified_stack.md`
- Added JWT-protected backend Writers-Room workflow endpoint:
  - `backend/app/api/v1/writers_room_routes.py`
  - route: `POST /api/v1/writers-room/reviews`
- Added unified-stack Writers-Room service implementation:
  - `backend/app/services/writers_room_service.py`
- Updated Writers-Room Flask app to use backend unified workflow as canonical path:
  - `writers-room/app.py`
  - `writers-room/app/templates/index.html`
- Added transitional legacy route markers:
  - `writers-room/app.py` route `/legacy-oracle`
  - template labels legacy mode as transitional only
- Added test coverage for backend workflow + Writers-Room compatibility:
  - `backend/tests/test_writers_room_routes.py`
  - `writers-room/tests/test_writers_room_app.py`

## Prerequisite verification summary

- M8 capability layer and M7 graph seed are active and used by Writers-Room service.
- M6 retrieval is consumed through capability invocation (`wos.context_pack.build`).

## Design decisions

- Canonical Writers-Room operation is now workflow-driven, not direct chat driven.
- Workflow uses shared stack components:
  - retrieval capability (`wos.context_pack.build`, writers_room domain),
  - LangGraph seed graph (`build_seed_writers_room_graph`),
  - shared model routing/adapters with deterministic fallback,
  - guarded bundle generation (`wos.review_bundle.build`).
- Outputs are recommendation-only and explicitly flagged as such for governance.

## Migrations or compatibility shims

- Legacy direct oracle remains available at `/legacy-oracle` but is clearly marked transitional/deprecated.
- Main `/` Writers-Room UI now points to unified backend workflow.

## Tests run

```bash
python -m pytest "backend/tests/test_writers_room_routes.py" -q --tb=short
python -m pytest "writers-room/tests/test_writers_room_app.py" -q --tb=short
```

Result: all commands passed.

## Acceptance criteria status

| Criterion | Status |
|---|---|
| Writers-Room no longer primarily depends on isolated direct chat | Pass |
| Real workflow exists on unified stack | Pass |
| Human review artifacts/surfaces exist | Pass |
| Automated tests prove operational flow | Pass |
| Legacy path not represented as canonical | Pass |

## Required milestone-specific answers

### What exact Writers-Room flow is now canonical?

- JWT-authenticated call to `POST /api/v1/writers-room/reviews`, invoked by Writers-Room `/` UI.

### What shared-stack components does it truly use?

- Retrieval capability: `wos.context_pack.build` (writers_room mode/domain).
- LangGraph seed orchestration: `build_seed_writers_room_graph`.
- Shared model routing/adapters: `story_runtime_core` routing and adapters.
- Guarded capability action: `wos.review_bundle.build`.

### What legacy Writers-Room paths remain and how are they marked?

- `/legacy-oracle` remains for transition; UI and payload metadata mark it as transitional and deprecated.

### What outputs are recommendations only vs actionable artifacts?

- Recommendations/issues are advisory.
- Review bundle metadata is governance input; not a direct publish action.

### What remains deferred before full productization?

- Richer governance UI for bundle triage,
- asynchronous batch review execution,
- deeper dramaturgy evaluation metrics.

## Known limitations

- Current recommendation synthesis uses deterministic heuristics with model fallback, not full scoring/ranking pipelines.

## Risks left open

- Further hardening needed for large-scale review throughput and admin workflow UX.
