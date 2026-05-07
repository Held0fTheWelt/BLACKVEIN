# ADR-0037: Backend test suite split in canonical orchestrator

## Status

Accepted

## Date

2026-05-07

## Intellectual property rights

Repository authorship and licensing: see project **LICENSE**; contact maintainers for clarification.

## Privacy and confidentiality

This ADR contains no personal data. Implementers must follow the repository privacy and confidentiality policies, avoid committing secrets, and document any sensitive data handling in implementation steps.

## Related ADRs *(optional)*

- [ADR-0033](adr-0033-live-runtime-commit-semantics.md) — live gate semantics (tests reference observability fixtures and Langfuse scoring independently of this runner policy).

## Context

The backend pytest tree under `backend/tests/` grew to thousands of tests and long wall-clock times for `python tests/run_tests.py --suite backend`. Developers need **fast, scoped runs** without abandoning the single canonical entrypoint (`tests/run_tests.py` per project discipline). Cross-folder selection for flat top-level test files also required **explicit domain markers** in `backend/pytest.ini`. Optional **pytest-xdist** parallelization must remain **off by default** and must not break ordering-sensitive or timing-sensitive tests.

## Decision

1. **Canonical full gate unchanged:** `python tests/run_tests.py --suite backend` remains the authoritative “run the entire backend pytest tree” command for CI and merge gates.
2. **Directory-based sub-suites** are registered as additional `--suite` choices (`backend_runtime`, `backend_observability`, `backend_services`, `backend_content`, `backend_routes_core`, `backend_mcp`, `backend_rest`). They share `cwd=backend/` and reuse `backend/pytest.ini`. **`backend_rest`** collects `backend/tests` while **ignoring** paths already covered by the other sub-suites (and dedicated `writers_room` / `improvement` slices).
3. **Coverage gates on sub-suites:** orchestrator sets **`supports_coverage=False`** for these sub-suites so partial runs do not enforce the backend-wide `--cov-fail-under` against incomplete execution.
4. **Domain axis:** `--domain <name>` maps to pytest `-m` using markers registered in `backend/pytest.ini` (`auth`, `observability`, `runtime`, `routes_core`, `content`, `services`, `writers_room`, `improvement`, `mvp_handoff`). It **combines with `--scope`** via logical **and** (e.g. `contract and auth`).
5. **`@pytest.mark.serial`:** ordering-sensitive or wall-clock-sensitive tests are tagged `serial`. When `--parallel` is used, the runner executes **two passes**: parallel workers with `-m "… and (not serial)"` plus **`--dist loadfile`**, then a **sequential** pass with `-m "… and (serial)"`. Exit code **5** (no tests collected) on the serial pass is acceptable when no serial tests match the selection.
6. **Dependencies:** `pytest-xdist` is listed in `backend/requirements-test.txt`; parallel execution is opt-in via `--parallel [auto|N]`.

## Consequences

**Positive:** Faster feedback via sub-suites and optional parallel full-backend runs; cross-folder domain filtering for marked modules; CI can stay pinned to `--suite backend`.

**Negative / risks:** Parallel runs can hide shared-state bugs unless tests are isolated or marked `serial`. Domain markers require ongoing hygiene on new top-level test files.

**Follow-ups:** Optional Stage 4 (changed-file / test-impact selection) remains out of scope until explicitly approved.

## Diagrams

None — runner behavior is CLI-documented in [`tests/TESTING.md`](../../tests/TESTING.md).

## Testing

- **Verify:** `python tests/run_tests.py --suite backend --quick` matches prior green counts for the full backend tree.
- **Verify:** `python tests/run_tests.py --suite backend --quick --parallel auto` completes with the same pass/skip totals (two internal passes).
- **Failure modes:** Drift between documented suite keys and `SUITE_CONFIGS` in `tests/run_tests.py`; missing marker registration in `backend/pytest.ini` breaking `--domain`.

## References

- [`tests/run_tests.py`](../../tests/run_tests.py) — `SuiteConfig`, `combined_marker_expression`, parallel two-pass.
- [`tests/TESTING.md`](../../tests/TESTING.md) — operator-facing contracts.
- [`backend/pytest.ini`](../../backend/pytest.ini) — domain and `serial` markers.
