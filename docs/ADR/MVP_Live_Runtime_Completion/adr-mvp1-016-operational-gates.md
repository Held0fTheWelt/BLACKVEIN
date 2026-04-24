# ADR-MVP1-016: Operational Test and Startup Gates

**Status**: Accepted
**MVP**: 1 — Experience Identity and Session Start (and all MVPs)
**Date**: 2026-04-24

## Context

The MVP_Live_Runtime_Completion guide requires that every MVP prove its implementation through operational gates: docker-up.py, run-test.py (tests/run_tests.py), GitHub workflows, and TOML/tooling. Without these gates, documentation and test results in isolation cannot prove the live path works.

## Decision

The following operational gate requirements apply to MVP1 and all subsequent MVPs:

1. **`docker-up.py`**: Must exist and start backend, frontend, play-service. Must report failed services and exit nonzero. MVP1 does not modify docker-up.py but confirms it exists.

2. **`tests/run_tests.py`** (equivalent of guide's `run-test.py`): Must include MVP1 tests in the engine and backend suites. MVP1 tests are placed in `world-engine/tests/` and `backend/tests/` which are covered by `--suite engine` and `--suite backend`.

3. **GitHub workflows**: Must include MVP1 tests or equivalent suites:
   - `.github/workflows/engine-tests.yml` — covers `world-engine/tests/` (includes `test_mvp1_experience_identity.py`)
   - `.github/workflows/backend-tests.yml` — covers `backend/tests/` (includes `test_mvp1_session_identity.py`)

4. **TOML/tooling**: `pyproject.toml` and service TOMLs must not exclude MVP1 test paths.

5. **Operational evidence artifact**: Must be written to `tests/reports/MVP_Live_Runtime_Completion/MVP<N>_OPERATIONAL_EVIDENCE.md`.

6. **Source locator artifact**: Must be written to `tests/reports/MVP_Live_Runtime_Completion/MVP<N>_SOURCE_LOCATOR.md` before any code patching.

## Affected Services/Files

- `docker-up.py` (confirmed valid, not modified)
- `tests/run_tests.py` (confirmed valid, engine/backend suites cover MVP1 tests)
- `.github/workflows/engine-tests.yml` (confirmed covers world-engine/tests/)
- `.github/workflows/backend-tests.yml` (confirmed covers backend/tests/)
- `tests/reports/MVP_Live_Runtime_Completion/MVP1_OPERATIONAL_EVIDENCE.md` (NEW)
- `tests/reports/MVP_Live_Runtime_Completion/MVP1_SOURCE_LOCATOR.md` (NEW)

## Consequences

- No MVP is closed without an operational evidence artifact
- No MVP patches code before completing the source locator artifact
- Pre-existing test failures that are unrelated to the MVP must be documented and explained in the operational evidence artifact

## Error Codes

- `source_locator_artifact_missing`
- `source_locator_unresolved`
- `operational_evidence_artifact_missing`
- `operational_suite_evidence_missing`
- `docker_up_false_success`
- `run_test_false_success`
- `github_workflow_missing_mvp_suite`

## Validation Evidence

- `test_source_locator_artifact_exists_for_mvp` — PASS
- `test_source_locator_matrix_has_no_placeholders_before_patch` — PASS
- `test_run_test_equivalent_is_documented_and_functional` — PASS
- `test_operational_evidence_artifact_exists_for_mvp` — PASS (after artifact creation)
- `test_operational_report_lists_mvp_specific_suites` — PASS (after artifact creation)

## Operational Gate Impact

This ADR IS the operational gate definition.
