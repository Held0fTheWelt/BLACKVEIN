# Milestone 0 — Gate Review

**Date:** 2026-04-04  
**Status:** **PASS**  
**Recommendation:** **Proceed**

## Scope

- Canonical AI stack architecture baseline (`docs/architecture/ai_stack_in_world_of_shadows.md`).
- Runtime authority decision (`docs/architecture/runtime_authority_decision.md`).
- Documentation drift cleanup for runtime commands and architecture index.
- Hygiene: duplicate session registration, session start path, HTTP error mapping for session creation, JSON body validation.

## Files changed (M0 scope)

| Area | Path |
|------|------|
| Architecture | `docs/architecture/ai_stack_in_world_of_shadows.md` (new) |
| Architecture | `docs/architecture/runtime_authority_decision.md` (new) |
| Architecture | `docs/architecture/README.md` |
| Features | `docs/features/RUNTIME_COMMANDS.md` |
| Runtime | `backend/app/runtime/session_store.py` |
| Runtime | `backend/app/runtime/session_start.py` |
| Services | `backend/app/services/session_service.py` |
| API | `backend/app/api/v1/session_routes.py` (create-session mapping + JSON validation; see note) |
| Tests | `backend/tests/runtime/test_session_store.py` |
| Tests | `backend/tests/test_session_routes.py` (create-session regressions) |

**Note:** `session_routes.py` also carries later-milestone turn-proxy changes in the integrated branch; the M0 acceptance items are the create-session behavior, status codes, and JSON validation.

## Design decisions

- **Session registration:** `session_store.create_session` raises `ValueError` if `session_id` is already registered; `session_service.create_session` loads the module once via `start_session` and registers a single `RuntimeSession`.
- **Session start errors:** `SessionStartError.reason` maps to HTTP status via `SESSION_START_ERROR_STATUS` (`module_not_found` → 404, `module_invalid` / `no_start_scene` → 422, default 422).
- **`short_term_context`:** The previously reported undefined `session` bug is **not present** on the current `master` baseline; `build_short_term_context` uses an explicit `session_state` parameter. No additional change was required for M0.4 on that point.

## Migrations / compatibility

- In-process backend sessions remain **deprecated / non-authoritative**; warnings on create-session responses document this.

## Tests run

```text
cd backend
python -m pytest tests/test_session_routes.py tests/runtime/test_session_store.py -q --tb=short
```

**Result:** Pass (subset covering M0 regressions).

## Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Canonical architecture docs exist and are consistent | **Pass** |
| Runtime authority decision explicit | **Pass** |
| Hygiene bugs (duplicate registration, start path, HTTP mapping) addressed | **Pass** |
| Regression tests exist and pass | **Pass** |
| Doc drift reduced; historical docs labeled | **Pass** |

## Gate review — required extras

### Which docs are canonical after cleanup?

- **Canonical:** `docs/architecture/ai_stack_in_world_of_shadows.md`, `docs/architecture/runtime_authority_decision.md`, and the architecture index in `docs/architecture/README.md` (links).
- **Historical / non-canonical:** `docs/features/RUNTIME_COMMANDS.md` is explicitly marked as historical reference where noted in-file.

### Which docs were downgraded?

- Runtime command documentation that implied a different product or obsolete command-center assumptions was labeled **historical / non-canonical** in `RUNTIME_COMMANDS.md`.

### Authoritative session registration path

1. `session_service.create_session(module_id)` calls `start_session(module_id)` once.
2. It registers via `session_store.create_session(session_id, session_state, module)`.
3. Duplicate `session_id` → `ValueError` from `session_store`.

## Known limitations

- Backend in-process session shell remains for operators/tests.

## Risks

- Volatile in-memory sessions lost on process restart.

## Recommendation

**Proceed** to M1.
