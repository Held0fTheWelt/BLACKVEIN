# Delagecy Removal Reclassification Audit

Date: 2026-05-20

## Rule Applied

Legacy is not active compatibility.

If a finding names behavior that is still required by the current system, the
behavior must stay intact. The work item is then a canonicalization task:
rename the field, helper, diagnostic, or documentation so the active contract no
longer describes itself as legacy. It is not counted as removal by renaming
alone.

If the behavior is truly obsolete, remove the implementation and every surface
that exposes it: UI, route, API alias, test expectation, generated output,
diagnostic field, docs, and config fallback.

If the classification is unclear or removal could break an active workflow,
stop and discuss before continuing.

## Rechecked Changes

| Area | Classification | Audit result |
| --- | --- | --- |
| Backend web redirect routes | True legacy removal | Removed routes remain removed. No active app code may point at deleted `web.*` endpoints. |
| `backend/app/web/auth.py` | Active helper with broken references | Corrected during audit: redirects now target the canonical browser surface through `FRONTEND_URL` or local browser paths. |
| Site settings API aliases | True legacy API residue | Old request/response aliases were removed; DB setting names remain because they are active storage keys. |
| `PLAY_SERVICE_SECRET` backend fallback | True backend config residue | Backend now requires `PLAY_SERVICE_SHARED_SECRET`; world-engine keeps its own `PLAY_SERVICE_SECRET` contract. |
| ADR-0041 readiness consumer | Active behavior with outdated naming | Behavior preserved; names and reason strings were canonicalized from `legacy_*` to `base_*`. |
| W5 current room fallback | Active fallback behavior | Behavior preserved; diagnostics now call it `fallback_current_room` rather than `legacy_current_room`. |
| Langfuse evaluator alternate trace names | Active evaluator tooling | Behavior preserved; catalog, generated transfer JSON, and MCP tools now use `alternate_trace_names*`. |
| Frontend large session-key eviction | Active cleanup behavior | Behavior preserved; stale-cookie cleanup now uses `stale` terminology. |
| Admin/backend visible UI residue | True UI residue | Legacy labels, hidden blocks, and obsolete Inspector UI panels were removed or renamed to neutral active UI names. |

## Integrity Corrections Made During Recheck

- `backend/app/web/auth.py` no longer calls removed endpoints such as
  `web.login`, `web.blocked`, or `web.dashboard`.
- `tools/mcp_server/tools_registry_handlers_langfuse_verify.py` no longer imports
  or reads removed Langfuse `legacy_trace_names*` symbols.
- `tools/mcp_server/tests/test_evaluator_catalog_tools.py` now verifies the
  canonical `alternate_trace_names` surface.
- `delagecy` policy docs, generated tracker wording, registry policy flags, and
  ADR-0029 now explicitly state that active behavior must be preserved and
  canonicalized rather than deleted as legacy.

## Still Blocked / Do Not Auto-Remove

These clusters still contain `legacy*` wording, but they are active runtime
contracts or broad data-shape surfaces. They must be registered, reported, and
discussed before removal or canonicalization:

- dramatic-effect gate fields such as `legacy_fallback_used`;
- LangChain bridge aliases such as `narrative_response` and responder aliases;
- world-engine manager `_legacy_loader` / `_legacy_sources` remnants from the
  monolith split;
- model-routing registry/report terminology such as legacy adapter maps;
- persisted/generated historical scan reports and registry rows.

## Verification

Targeted verification after the recheck:

- `backend`: `tests/web/test_auth.py`, `tests/test_web.py`,
  `tests/test_backend_info_routes.py`, `tests/test_mail_service.py`
- `ai_stack`: `tests/test_langfuse_evaluator_catalog.py`,
  `tests/test_runtime_readiness_consumer.py`
- `world-engine`: `tests/test_story_runtime_w5_player_view.py`
- `tools`: `tools/mcp_server/tests/test_evaluator_catalog_tools.py`
- `delagecy`: `delagecy/tools/tests`
