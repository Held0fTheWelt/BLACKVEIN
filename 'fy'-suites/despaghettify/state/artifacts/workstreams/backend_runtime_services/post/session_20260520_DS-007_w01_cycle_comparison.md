# DS-007 Post Snapshot — Backend Import Cycles

## Result

DS-007 reduced the static `backend/app` import-cycle share below the C1 bar:

| Metric | Before | After |
|--------|--------|-------|
| files in import cycles | 22 / 393 | 6 / 395 |
| C1 Anteil | 5.598% | 1.519% |

The wave broke avoidable back-edges in:

- JWT revocation: callback queries no longer import token model classes.
- Feature registry compatibility wrappers: resolver access no longer creates a static import edge.
- API v1 route registration: side-effect route imports no longer self-loop on `app.api.v1`.
- Scene presenter conflict outputs: shared output models moved to `scene_presenter_conflict_models.py`.
- Relationship context and runtime staged generation helpers: parent-module callbacks no longer appear as static graph back-edges.
- AI turn recovery state writes: degraded-marker and decision-log writes moved to `ai_turn_recovery_state.py`.

Two larger components remain as advisory non-firing C1 debt: narrative thread update helpers and game/governance service coupling. They do not keep C1 above the bar after this wave.

## Gates

- `wave-plan-validate --check-primary-paths` — pass
- `ds005_runtime_import_check.py` — pass
- `check --with-metrics` — pass, `C1=1.519%`
- `spaghetti_ast_scan.py` — pass
- `pytest backend/tests/test_feature_access_resolver.py backend/tests/runtime/test_scene_presenter.py backend/tests/runtime/test_relationship_context.py backend/tests/runtime/test_runtime_ai_stages_contracts.py -q --tb=short` — **73 passed**
