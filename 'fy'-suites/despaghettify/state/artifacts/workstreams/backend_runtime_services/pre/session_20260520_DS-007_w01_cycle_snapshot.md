# DS-007 Pre Snapshot — Backend Import Cycles

## Wave Plan

| Sub-wave | Goal | Primary files / symbols | Gate |
|----------|------|-------------------------|------|
| 1 | Break avoidable static import-cycle back-edges while preserving runtime behavior. | Auth JWT revocation, feature registry compatibility wrappers, API v1 route loading, scene/relationship presenter helper imports, staged runtime helper imports, AI recovery helpers. | `wave-plan-validate`; `ds005_runtime_import_check.py`; `check --with-metrics`; `spaghetti_ast_scan.py` |

## Pre State

- C1 before this wave: **22/393** `backend/app` files in import cycles (**5.598%**, bar **2%**).
- Components present before this wave:
  - Auth JWT/model/extensions component: `extensions.py`, `jwt_revocation.py`, `models/refresh_token.py`, `models/token_blacklist.py`.
  - API v1 self-loop from route side-effect imports in `api/v1/__init__.py`.
  - Feature access resolver/registry cycle.
  - Runtime presenter/relationship/staged-generation helper cycles.
  - AI recovery exhausted/paths cycle.
  - Larger narrative thread and game/governance service cycles remain as potential follow-up if C1 is still above bar.

## Intended Acceptance

The wave is successful if `ds005_runtime_import_check.py` still passes and the refreshed `check --with-metrics` report shows C1 below the 2% bar or materially reduces the cycle set enough to justify narrowing DS-007.
