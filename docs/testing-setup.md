# Testing Setup and Reproducible Validation Guide

This document explains how to install test dependencies, run tests, understand test profiles, and validate the repository in clean environments.

## Environment parity (CI, Dev Container, local)

**Why results can differ:** A laptop may use Python 3.11–3.13 while CI and the default Dev Container use **Python 3.10**. Pip/setuptools versions also differ unless pinned. That alone can change editable-install and test outcomes.

**What we treat as the merge bar:** GitHub Actions workflows under `.github/workflows/` (notably **backend** and **ai-stack** jobs) run on **ubuntu-latest** with **`python-version: '3.10'`**. That is the closest definition of “green in CI” for this repo.

**Aligned local / container installs** — use **one** of these so dependency sets match the documented path:

1. **Repository root** — `./setup-test-environment.sh` or `setup-test-environment.bat`  
   Installs `backend/requirements-test.txt`, then **editable** `story_runtime_core`, then **editable** `ai_stack[test]`. Fails the script if an editable install errors (no silent success).
2. **Dev Container** — `.devcontainer/devcontainer.json`  
   Uses the same **Python 3.10** image and runs the same pip sequence as (1), then adds `world-engine/requirements-dev.txt` so **world-engine** tests work in-container. `PYTHONPATH` includes the repo root (and `world-engine` for engine imports).
3. **Manual / CI-style** — For `ai_stack` tests only, mirror `.github/workflows/ai-stack-tests.yml`:  
   `pip install -e ./story_runtime_core` and `pip install -e "./ai_stack[test]"` with `PYTHONPATH` set to the repository root.
4. **Minimal CI-parity one-shot** — `scripts/install-ai-stack-test-env.sh` or `scripts/install-ai-stack-test-env.ps1` / `.bat` (same pip lines as the workflow). **Docker:** `docker build -f docker/Dockerfile.ai-stack-test -t wos-ai-stack-test .` then `docker run --rm wos-ai-stack-test`.

**Merge bar (explicit):** Any claim that the full `pytest ai_stack/tests` run is merge-ready **must** assume the workflow install sequence above. Environments that only set `PYTHONPATH` without `ai_stack[test]` may see **skipped** GoC/LangGraph tests (`pytest.importorskip`); that is **not** CI parity.

**If the container and your host disagree:** Inside the container, run `python --version` and `pip list | head` (or equivalent), then run `./setup-test-environment.sh` from the mounted workspace to reconcile. Rebuild the Dev Container after `postCreateCommand` changes.

### PYTHONPATH alone is not enough (LangGraph / GoC)

Setting `PYTHONPATH` to the repo root only makes **source packages importable**; it does **not** install **PyPI** dependencies such as `langchain-core` or `langgraph`. Without those, `ai_stack.langgraph_runtime` cannot load and the GoC / LangGraph tests are **skipped** (by design).

**Platform-neutral, CI-identical minimal install** (only `story_runtime_core` + `ai_stack[test]`, same commands as `.github/workflows/ai-stack-tests.yml`):

```bash
python -m pip install --upgrade pip
python -m pip install -e "./story_runtime_core"
python -m pip install -e "./ai_stack[test]"
export PYTHONPATH="$(pwd)"   # Linux / macOS
```

Windows (PowerShell): `.\scripts\install-ai-stack-test-env.ps1`  
Windows (cmd) / double-click path: `scripts\install-ai-stack-test-env.bat`  
macOS / Linux: `./scripts/install-ai-stack-test-env.sh`

**Docker (same stack, any host with Docker):** from repo root:

```bash
docker build -f docker/Dockerfile.ai-stack-test -t wos-ai-stack-test .
docker run --rm wos-ai-stack-test
```

After a successful install, `python -c "import langchain_core, langgraph; import ai_stack.langgraph_runtime"` must exit 0.

## Quick Start

### CRITICAL: Install Dependencies First

**Tests CANNOT run without installing dependencies.** This is the mandatory first step.

**Common pitfall (backend pytest):** A repository-root virtualenv (for example `.venv`) used only for
`ai_stack` is **not** sufficient to run `pytest` from `backend/tests/`. Backend tests import Flask and
the full app stack. Install backend test deps explicitly:

```bash
python -m pip install -r backend/requirements-test.txt
```

(or run `./setup-test-environment.sh` / `setup-test-environment.bat` from the repo root, which includes that step).

#### Automatic Setup (Recommended)

Run the setup script to install all dependencies automatically:

```bash
# macOS / Linux
./setup-test-environment.sh

# Windows
setup-test-environment.bat
```

This script will:
1. Run `python -m pip install -r backend/requirements-test.txt` from `backend/` (that file starts with `-r requirements.txt`, so **production + test** deps install together)
2. Install **editable** `story_runtime_core` and **editable** `ai_stack[test]` from the repository root (required for LangGraph / GoC tests; failures abort the script)
3. Verify that critical packages (flask, sqlalchemy, pytest, langchain_core, langgraph, etc.) are installed
4. Exit with an error if any verification import fails

#### Manual Setup

If you prefer to install manually, run **one** of:

```bash
python -m pip install -r backend/requirements-test.txt
```

```bash
cd backend && python -m pip install -r requirements-test.txt
```

Or, for development (includes testing plus optional dev tools):

```bash
cd backend
pip install -r requirements-dev.txt
```

#### Verify Installation

To verify dependencies are installed:

```bash
python -c "import flask, sqlalchemy, flask_sqlalchemy, flask_migrate, flask_limiter, pytest, pytest_asyncio; print('All dependencies installed')"
```

If you see `ModuleNotFoundError`, dependencies are **not installed**. Re-run the setup script.

### Run Canonical Smoke Suite

To run a quick validation of core repository health:

```bash
# From repository root
python -m pytest tests/smoke/ -v --tb=short
```

Expected result: ~140 tests pass in <15 seconds.

### Run Backend Unit Tests

To run all backend tests with coverage:

```bash
cd backend
python -m pytest tests/ -v
```

### Writers' Room — Gate G7 operating contract (`backend/tests/writers_room`)

Local verification (matches `docs/GoC_Gate_Baseline_Audit_Plan.md` G7 command intent; use `--no-cov` because `backend/pytest.ini` adds coverage by default):

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest tests/writers_room/ -q --tb=short --no-cov
```

**CI:** `.github/workflows/backend-tests.yml` includes a dedicated job **`writers-room-g7-contract-tests`** that runs exactly `python -m pytest tests/writers_room/ -q --tb=short --no-cov` from `backend/` after `pip install -r backend/requirements-dev.txt`. The **`backend-fast-tests`** job also runs `pytest tests/ -m "not slow"` (which collects `tests/writers_room/`). The explicit job proves the Writers' Room path executes on every workflow run that reaches it.

### Improvement Path — Gate G8 operating contract (`backend/tests/improvement`)

Local verification (matches `docs/audit/gate_G8_improvement_operating_baseline.md` command intent; use `--no-cov` because `backend/pytest.ini` adds coverage by default):

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest tests/improvement/ -q --tb=short --no-cov
```

**CI:** `.github/workflows/backend-tests.yml` includes a dedicated job **`improvement-g8-contract-tests`** that runs exactly `python -m pytest tests/improvement/ -q --tb=short --no-cov` from `backend/` after `pip install -r backend/requirements-dev.txt`. The **`backend-coverage-tests`** job **depends on** this job (and on `writers-room-g7-contract-tests`), so the coverage gate does not run without the explicit Improvement suite passing.

### G9 / G9B evidence scaffolding + G10 backend E2E audit path

**Human evidence (G9 / G9B):** Score-sheet templates, JSON schemas, and the §6.9 threshold helper live under `docs/goc_evidence_templates/` and `scripts/g9_threshold_validator.py`. Filling templates does not constitute gate closure; see `docs/goc_evidence_templates/README.md`.

**Validator CLI tests** (repository root; only `pytest` required — no Flask):

```bash
python -m pytest tests/experience_scoring_cli/ -q --tb=short
```

**Automated scenario bundle** aligned with roadmap §6.9 (from repository root, with `story_runtime_core` + `ai_stack[test]` installed and `PYTHONPATH` set to the repo root as for the ai_stack suite):

```bash
python -m pytest ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py ai_stack/tests/test_goc_multi_turn_experience_quality.py ai_stack/tests/test_goc_mvp_breadth_playability_regression.py ai_stack/tests/test_goc_retrieval_heavy_scenario.py -q --tb=short
```

**G10 audit-plan backend trio** (requires backend dependencies — same failure mode as the baseline audit if you only installed ai_stack into `.venv`):

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest tests/test_e2e_god_of_carnage_full_lifecycle.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_runtime_validation_commands_orchestration.py -q --tb=short --no-cov
```

If you see `ModuleNotFoundError` for parent-repo packages (e.g. `ai_stack`), set `PYTHONPATH` to the **repository root** (parent of `backend/`) and retry:

```bash
cd backend
python -m pip install -r requirements-dev.txt
# PowerShell: $env:PYTHONPATH = "<repo-root>"
# bash: export PYTHONPATH="$(cd .. && pwd)"
python -m pytest tests/test_e2e_god_of_carnage_full_lifecycle.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_runtime_validation_commands_orchestration.py -q --tb=short --no-cov
```

**Archived witness (example):** `tests/reports/evidence/g10_backend_e2e_20260409/pytest_g10_backend_trio.txt` (15 passed, `exit_code: 0`) with `run_metadata.json`.

**CI interpretation:** A green `g10-backend-e2e-evidence-path` job proves the trio command is runnable in CI. **Program / roadmap closure** is not implied: step 11 must still be grounded in the **authoritative** G9/G9B evidence bundle (`g9_level_a_fullsix_20260410` — see `docs/audit/gate_G9_experience_acceptance_baseline.md`), and `docs/audit/gate_G10_end_to_end_closure_baseline.md` governs integrative structural vs `closure_level_status` (§7A prerequisite health).

**CI:** `.github/workflows/backend-tests.yml` runs **`g10-backend-e2e-evidence-path`** with exactly the trio command above after `pip install -r backend/requirements-dev.txt`. The **`requirements-test-hygiene`** job also runs `python -m pytest tests/experience_scoring_cli/ -q --tb=short` from the repository root.

### AI stack / LangGraph tests (`ai_stack/tests`)

**Why `from ai_stack import RuntimeTurnGraphExecutor` can fail:** `ai_stack/__init__.py` imports RAG and LangGraph modules inside `try` / `except ModuleNotFoundError` so lightweight consumers (for example MCP catalog checks) do not require **langchain-core** or **langgraph**. If those packages are missing, the import is skipped and `RuntimeTurnGraphExecutor` is **not** re-exported at package top level — this is intentional, not a broken install.

**Reproducible full `ai_stack` test run** (from repository root):

```bash
python -m pip install -e "./story_runtime_core"
python -m pip install -e "./ai_stack[test]"
export PYTHONPATH="$(pwd)"   # Linux / macOS; Windows: set PYTHONPATH=%CD%
python -m pytest ai_stack/tests -q --tb=short
```

Or use the pinned file (same intent as `[test]` extras):

```bash
python -m pip install -r ai_stack/requirements-test.txt
python -m pip install -e "./story_runtime_core"
python -m pip install -e "./ai_stack"
python -m pytest ai_stack/tests -q --tb=short
```

After a correct install, `import ai_stack; assert ai_stack.LANGGRAPH_RUNTIME_EXPORT_AVAILABLE` should be **True**, and `RuntimeTurnGraphExecutor` appears in `ai_stack.__all__`.

**Roadmap S4 (misinterpretation / correction)** — canonical chain in `ai_stack/goc_s4_misinterpretation_scenario.py`; pytest node is collected by the full ai_stack suite:

```bash
python -m pytest ai_stack/tests/test_goc_roadmap_s4_misinterpretation_correction.py -q --tb=short
```

**G9 Level-A capture with partial-run metadata:** the same script can still emit all scenario JSON files (S1–S6). For bundles whose audit purpose is **S4 closure only**, pass `--evidence-run-scope s4_closure_partial` so `run_metadata.json` carries `evidence_run_scope` / `evidence_run_note` and is not mistaken for a full six-scenario G9 matrix or threshold run:

```bash
python scripts/g9_level_a_evidence_capture.py tests/reports/evidence/<audit_run_id> --audit-run-id <audit_run_id> --evidence-run-scope s4_closure_partial
```

See `docs/audit/gate_G9_experience_acceptance_baseline.md` (`g9_s4_closure_20260409`).

**G9 Level-A S5-targeted partial capture:** writes only S5 scenario JSON, `run_metadata.json`, and `pytest_s5_anchor.txt` (script runs the S5 pytest node). Not a full six-scenario matrix.

```bash
python -m pytest ai_stack/tests/test_goc_multi_turn_experience_quality.py::test_experience_multiturn_primary_failure_fallback_and_degraded_explained -q --tb=short
python scripts/g9_level_a_evidence_capture.py tests/reports/evidence/<audit_run_id> --audit-run-id <audit_run_id> --evidence-run-scope s5_targeted_partial
```

Example bundle: `tests/reports/evidence/g9_s5_targeted_20260409/`. The S5 node is collected whenever `python -m pytest ai_stack/tests` runs (same as CI `ai-stack-tests.yml`).

**G9 Level-A full six-scenario rerun (pytest + capture + threshold helper):** from repo root with `PYTHONPATH` set to the repository root and `story_runtime_core` + `ai_stack[test]` installed, run the six fixed nodes in one session (log path is an example — use a new `audit_run_id` folder per run):

```bash
python -m pytest \
  ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py::test_scenario_standard_escalation_non_preview \
  ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py::test_scenario_thin_edge_silence_non_preview \
  ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py::test_scenario_multi_pressure_non_preview \
  ai_stack/tests/test_goc_roadmap_s4_misinterpretation_correction.py::test_roadmap_s4_misinterpretation_correction_chain \
  ai_stack/tests/test_goc_multi_turn_experience_quality.py::test_experience_multiturn_primary_failure_fallback_and_degraded_explained \
  ai_stack/tests/test_goc_retrieval_heavy_scenario.py::test_roadmap_scenario_retrieval_heavy_governance_visible \
  -v 2>&1 | tee tests/reports/evidence/<audit_run_id>/pytest_g9_roadmap_bundle.txt

python scripts/g9_level_a_evidence_capture.py tests/reports/evidence/<audit_run_id> --audit-run-id <audit_run_id>
# After filling g9_experience_score_matrix.json in that directory:
python scripts/g9_threshold_validator.py tests/reports/evidence/<audit_run_id>/g9_experience_score_matrix.json
```

Authoritative example bundle: `tests/reports/evidence/g9_level_a_fullsix_20260410/` (see `docs/audit/gate_G9_experience_acceptance_baseline.md`). Earlier bundles (e.g. `g9_level_a_fullsix_20260409`) are historical context only for the §6.9 threshold story.

**Evidence preservation rule (closure runs):** Do not regenerate G9/G9B/G10 evidence just for freshness. Preserve existing authoritative bundles unless a newly rerun canonical path contradicts them, they are stale against current repo truth, or regeneration is required for internal consistency. Example closure-validation bundle: `tests/reports/evidence/all_gates_closure_20260409/` (rerun transcripts + validator/delta checks while preserving authoritative `g9_level_a_fullsix_20260410` and `g10_backend_e2e_20260409`).

**G9B (second evaluator, same `audit_run_id`):** freeze a **separate** full 6×5 matrix file (e.g. `g9_experience_score_matrix_evaluator_b.json`) grounded in the **same** scenario JSONs in that bundle; add matching `g9b_raw_score_sheet_evaluator_b.json`. Populate `g9b_score_delta_record.json` (`not_applicable_level_a: false`) by running `python scripts/g9b_compute_score_delta.py <matrix_a> <matrix_b> -o <bundle>/g9b_score_delta_record.json --raw-sheet-a-ref <bundle>/g9b_raw_score_sheet.json --raw-sheet-b-ref <bundle>/g9b_raw_score_sheet_evaluator_b.json` (authoritative per-cell deltas from the frozen files; do not hand-invent). Update `g9b_evaluator_record.json`, `g9b_level_b_attempt_record.json`, and the independence declaration per `docs/audit/gate_G9B_evaluator_independence_baseline.md`. Optional: run `scripts/g9_threshold_validator.py` on Evaluator B’s matrix for transparency only — §6.9 pass for the gate remains tied to the authoritative Evaluator A matrix. Do not commit invented scores; see `docs/goc_evidence_templates/README.md`.

**GoC structural gate smoke (G1–G4 contract closure):** from repo root with `PYTHONPATH` set to the repository root, run:

```bash
python -m pytest ai_stack/tests/test_goc_frozen_vocab.py ai_stack/tests/test_goc_roadmap_semantic_surface.py ai_stack/tests/test_scene_direction_subdecision_matrix.py ai_stack/tests/test_goc_field_initialization_envelope.py ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py -q --tb=short
python -m pytest story_runtime_core/tests/test_model_registry.py -q --tb=short
```

Backend parity (semantic registry vs enums + routing evidence): from `backend/` with `PYTHONPATH` including the repo root,

```bash
python -m pytest tests/test_goc_semantic_parity.py tests/runtime/test_model_routing_evidence.py tests/runtime/test_decision_policy.py -q --tb=short --no-cov
```

**G5 / G6 (retrieval governance summary + admin semantic boundary):** from repo root with `story_runtime_core` and `ai_stack[test]` installed as for the ai_stack suite above,

```bash
python -m pytest ai_stack/tests/test_retrieval_governance_summary.py ai_stack/tests/test_capabilities.py ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py ai_stack/tests/test_goc_retrieval_heavy_scenario.py -q --tb=short
```

From `backend/` (repo root still on `PYTHONPATH` via `pytest.ini`):

```bash
python -m pytest tests/test_goc_admin_semantic_boundary.py tests/test_goc_evidence_retrieval_governance.py -q --tb=short --no-cov
```

**CI alignment:** `.github/workflows/ai-stack-tests.yml` runs `python -m pytest ai_stack/tests -q --tb=short` with `PYTHONPATH` set to the workspace (entire `ai_stack/tests` tree collected — **no file allowlist**), so new modules such as `test_goc_roadmap_s4_misinterpretation_correction.py` run automatically when workflow triggers apply. `.github/workflows/backend-tests.yml` runs `pytest tests/` for the full `backend/tests` tree when `backend/**`, `ai_stack/**`, or `story_runtime_core/**` changes — so backend tests that import `ai_stack` (including `test_goc_evidence_retrieval_governance.py`) still run on pure stack PRs, not only when `backend/` files change. The same workflow runs explicit **`writers-room-g7-contract-tests`** (`tests/writers_room/`), **`improvement-g8-contract-tests`** (`tests/improvement/`), **`g10-backend-e2e-evidence-path`** (G10 audit trio), and root **`tests/experience_scoring_cli/`** inside **`requirements-test-hygiene`**; **`backend-coverage-tests`** waits on the fast suite, both contract jobs, and the G10 trio job (see sections above).

The root **`setup-test-environment.sh`** / **`setup-test-environment.bat`** scripts also install **`story_runtime_core`** and **`ai_stack[test]`** in editable mode after backend dependencies.

## Test Profiles: What They Mean

The repository supports three explicit test execution profiles:

### 1. **testing_isolated** (Default Backend Tests)

**What it is:** Tests run against `TestingConfig` with an **in-memory SQLite database**, **no routing bootstrap**, and **CSRF disabled by default**.

**When to use:**
- Running unit tests for rapid development feedback
- Testing business logic in isolation
- CI/CD pipelines where database state must not leak between tests

**Configuration:**
- `SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"`
- `ROUTING_REGISTRY_BOOTSTRAP = False` (prevents process-global router contamination)
- `WTF_CSRF_ENABLED = False` (enabled separately for CSRF-specific tests)
- Fixed secrets (safe for CI)

**How to select:**
```bash
cd backend
pytest tests/ -v
```

**Fixtures available:**
- `app` — Flask app with in-memory DB, ready for testing
- `client` — Test client for the app
- `test_user` — Pre-created regular user (username: testuser, password: Testpass1)
- `auth_headers` — JWT headers for test_user
- `moderator_user`, `moderator_headers` — Moderator role
- `admin_user`, `admin_headers` — Admin role
- `super_admin_user`, `super_admin_headers` — Admin with level 100
- `runner` — Flask CLI runner for command testing

**Example test:**
```python
def test_example(app, test_user, auth_headers):
    with app.app_context():
        # Your test code
        pass
```

---

### 2. **testing_bootstrap_on** (Production-like Routing Tests)

**What it is:** Tests run with `ROUTING_REGISTRY_BOOTSTRAP = True`, simulating production-like routing initialization. Uses the same in-memory database and test fixtures, but enables routing registry bootstrap.

**When to use:**
- Validating Area 2 convergence and final closure gates
- Testing HTTP proofs that depend on routing initialization
- Verifying production-like configuration behavior

**Configuration:**
- `SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"`
- `ROUTING_REGISTRY_BOOTSTRAP = True` (enables routing initialization)
- `WTF_CSRF_ENABLED = False`
- Fixed secrets

**How to select:**
```python
# In your test, inject the bootstrap-on fixtures instead of regular ones:

def test_with_bootstrap(app_bootstrap_on, client_bootstrap_on, auth_headers_bootstrap_on):
    # Tests run with routing bootstrap enabled
    response = client_bootstrap_on.get("/api/v1/areas/convergence")
    assert response.status_code == 200
```

**Bootstrap-specific fixtures:**
- `app_bootstrap_on` — App with `ROUTING_REGISTRY_BOOTSTRAP = True`
- `client_bootstrap_on` — Client for bootstrap-on app
- `test_user_bootstrap` — Test user in bootstrap-on app's DB
- `auth_headers_bootstrap_on` — JWT for bootstrap-on test user

**Note:** Bootstrap-on tests have their own isolated database lifecycle, separate from regular `app` tests. Do not mix fixtures.

---

### 3. **testing_isolated_production_like** (Smoke Tests)

**What it is:** Production-like configuration (database file, bootstrap enabled, full initialization) for validation tests that simulate real deployment startup behavior.

**When to use:**
- Smoke testing: rapid checks that core services initialize
- Validating production configuration defaults
- Testing real database file operations (not in-memory)

**Configuration:**
- Uses production `Config` class (not `TestingConfig`)
- `ROUTING_REGISTRY_BOOTSTRAP = True` (default)
- Real database file (not in-memory)
- Fixtures from backend test suite imported

**How to select:**
```bash
# From repository root
python -m pytest tests/smoke/ -v
```

**Fixtures available:** All backend fixtures (test_user, auth_headers, etc.) are available via pytest plugin loading.

---

## Canonical Smoke Suite

A lightweight validation to catch major breakage quickly:

```bash
python -m pytest tests/smoke/ -v --tb=short
```

This runs ~140 tests covering:
- **Backend startup:** App creation, config, database connection
- **Engine startup:** World Engine dependencies and initialization
- **Content modules:** W0 and W1 contract validation, YAML structure

**Expected result:** All pass in ~10–15 seconds.

**What it validates:**
- Core Flask app starts without errors
- Database is connectable and has required tables
- Runtime routing bootstrap works (smoke profile)
- Content module YAML is valid and internally consistent
- Core API endpoints respond

**Not covered by smoke:** Area 2 dual-workstream closure gates (**G-A-01** … **G-A-07**, **G-B-01** … **G-B-07**) and the full `backend/tests/runtime` convergence suites — run those explicitly from `backend/` (see below).

---

## Area 2 dual-workstream validation (canonical)

Focused regression for **Workstream A** (practical convergence) and **Workstream B** (reproducibility). Gate tables: [`docs/archive/architecture-legacy/area2_workstream_a_gates.md`](archive/architecture-legacy/area2_workstream_a_gates.md), [`docs/archive/architecture-legacy/area2_workstream_b_gates.md`](archive/architecture-legacy/area2_workstream_b_gates.md). Combined report: [`docs/archive/architecture-legacy/area2_dual_workstream_closure_report.md`](archive/architecture-legacy/area2_dual_workstream_closure_report.md).

**Command surface (code):** [`backend/app/runtime/area2_validation_commands.py`](../backend/app/runtime/area2_validation_commands.py) — `AREA2_DUAL_CLOSURE_PYTEST_MODULES`, `area2_dual_closure_pytest_invocation()`.

**Prerequisites:** Install dependencies (`./setup-test-environment.sh`, `setup-test-environment.bat`, or `python -m pip install -r backend/requirements-test.txt`).

**Run from `backend/`** (required so `backend/pytest.ini` sets `pythonpath` and `testpaths`). Pass **`--no-cov`** because `pytest.ini` defaults include coverage `addopts`:

```bash
cd backend
python -m pytest tests/runtime/test_runtime_routing_registry_composed_proofs.py tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py tests/runtime/test_runtime_startup_profiles_operator_truth.py tests/runtime/test_cross_surface_operator_audit_contract.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_model_inventory_bootstrap.py -q --tb=short --no-cov
```

**G-A-01 … G-A-07** (Workstream A) are enforced in `backend/tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py`. **G-B-01** startup profile determinism, **G-B-02** bootstrap reproducibility, **G-B-03** clean-environment validation, **G-B-04** dependency/setup explicitness, **G-B-05** test-profile stability, **G-B-06** validation-command reality, and **G-B-07** documentation truth are enforced in `backend/tests/runtime/test_runtime_startup_profiles_operator_truth.py`.

---

## Area 2 Task 4 full closure validation (canonical)

**Gates:** **G-T4-01** (E2E truth, three surfaces), **G-T4-02** (bootstrap validation), **G-T4-03** (cross-surface contract), **G-T4-04** (negative/degraded honesty), **G-T4-05** (drift resistance), **G-T4-06** (validation-command reality), **G-T4-07** (required proof-suite stability via subprocess), **G-T4-08** (documentation truth). Gate table: [`docs/archive/architecture-legacy/area2_task4_closure_gates.md`](archive/architecture-legacy/area2_task4_closure_gates.md). Closure report: [`docs/archive/architecture-legacy/area2_validation_hardening_closure_report.md`](archive/architecture-legacy/area2_validation_hardening_closure_report.md).

**Command surface (code):** [`backend/app/runtime/area2_validation_commands.py`](../backend/app/runtime/area2_validation_commands.py) — `AREA2_TASK4_FULL_CLOSURE_PYTEST_MODULES`, `area2_task4_full_closure_pytest_invocation()`.

**Working directory:** `backend/` (same as dual-workstream: `pytest.ini` `pythonpath` and `testpaths`).

**Module list (must match code, in order):** `tests/runtime/test_runtime_routing_registry_composed_proofs.py`, `tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py`, `tests/runtime/test_runtime_startup_profiles_operator_truth.py`, `tests/runtime/test_cross_surface_operator_audit_contract.py`, `tests/test_bootstrap_staged_runtime_integration.py`, `tests/runtime/test_model_inventory_bootstrap.py`, `tests/runtime/test_runtime_operator_comparison_cross_surface.py`, `tests/runtime/test_runtime_ai_turn_degraded_paths_tool_loop.py`, `tests/runtime/test_runtime_drift_resistance.py`, `tests/runtime/test_runtime_staged_orchestration.py`, `tests/runtime/test_runtime_model_ranking_synthesis_contracts.py`, `tests/improvement/test_improvement_model_routing_denied.py`, `tests/runtime/test_ai_turn_executor.py::test_agent_orchestration_executes_real_separate_subagents_and_logs_trace`, `tests/runtime/test_runtime_validation_commands_orchestration.py`.

```bash
cd backend
python -m pytest tests/runtime/test_runtime_routing_registry_composed_proofs.py tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py tests/runtime/test_runtime_startup_profiles_operator_truth.py tests/runtime/test_cross_surface_operator_audit_contract.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_model_inventory_bootstrap.py tests/runtime/test_runtime_operator_comparison_cross_surface.py tests/runtime/test_runtime_ai_turn_degraded_paths_tool_loop.py tests/runtime/test_runtime_drift_resistance.py tests/runtime/test_runtime_staged_orchestration.py tests/runtime/test_runtime_model_ranking_synthesis_contracts.py tests/improvement/test_improvement_model_routing_denied.py tests/runtime/test_ai_turn_executor.py::test_agent_orchestration_executes_real_separate_subagents_and_logs_trace tests/runtime/test_runtime_validation_commands_orchestration.py -q --tb=short --no-cov
```

---

## Running Broader Test Subsets

### All Backend Tests (with coverage)

```bash
cd backend
python -m pytest tests/ -v --cov=app --cov-report=html
```

This covers:
- Unit tests (fast, no external deps)
- Integration tests (DB, auth, API)
- Security tests (OWASP, input validation, authZ)
- Contract tests (API stability)
- E2E tests (full workflows)

### Fast Mode: Only Unit Tests

```bash
cd backend
python -m pytest tests/ -m unit -v
```

Skips integration and slow tests.

### Security-Specific Tests

```bash
cd backend
python -m pytest tests/ -m security -v
```

### Content Module Tests

```bash
python -m pytest tests/smoke/test_smoke_contracts.py tests/smoke/test_goc_module_structure_smoke.py -v
```

---

## Pytest Configuration Files

The repository uses pytest configuration in two places for consistency:

### `backend/pytest.ini`

Classic pytest INI format. Defines:
- `pythonpath`: Includes `.` and `..` for flexible import paths
- `testpaths`: `tests/` directory
- `markers`: Unit, integration, security, contract, e2e, persistence, slow
- `asyncio_mode`: strict (required for async test determinism)
- `addopts`: Verbose output, coverage, short tracebacks

### `backend/pyproject.toml`

Duplicate configuration in TOML format (for tools that prefer TOML). Includes pytest, coverage, and path settings.

Both files must stay in sync. If you modify one, update the other.

---

## Test Dependency Declarations

### `backend/requirements.txt`

Production dependencies only. Used by:
- Production deployments
- Test environments (as a base)
- Any environment that needs the app to run

### `backend/requirements-test.txt`

**Test dependencies explicitly declared** (first directive is `-r requirements.txt` in the same directory, so production deps install in one step).

Used for clean-environment testing (pick one):

```bash
# From repository root (recommended in CI and fresh clones)
python -m pip install -r backend/requirements-test.txt

# From backend/
cd backend && python -m pip install -r requirements-test.txt
```

You do **not** need a separate `pip install -r requirements.txt` when using `requirements-test.txt` — the file already includes it.

**Portable checks** (no Flask/app imports; only pytest required):

```bash
python -m pip install 'pytest>=7,<9'
python -m pytest tests/requirements_hygiene/ -q
```

Includes (among others):
- `flask>=3.0.6,<4` — explicit anchor for the Flask app under test (also in `requirements.txt` via `-r`)
- `pytest>=7.0,<9` — test runner
- `pytest-asyncio>=0.21,<1` — async test support (import-time requirement)
- `pytest-cov>=4.0,<6` — coverage measurement
- `pytest-timeout>=2.1` — timeout enforcement
- `anyio` — explicit async primitives for consistent clean installs
- `exceptiongroup` — Python 3.10 compatibility for pytest/async (environment marker)

**Does NOT include** dev-only tools like formatters, linters, type checkers.

### `backend/requirements-dev.txt`

Development dependencies (super-set of test requirements).

Used by developers:
```bash
pip install -r requirements-dev.txt
```

Includes:
- All of requirements.txt
- All test requirements (via requirements-test.txt)
- Optional dev tools (commented, can be uncommented)

---

## Environment-Sensitive Behavior

The following aspects may vary between environments and are **intentionally left configurable**:

### Database URI
- **Default:** SQLite file at `backend/instance/wos.db`
- **Override:** Set `DATABASE_URI` environment variable
- **Testing:** In-memory SQLite (set automatically by TestingConfig)

### Secrets (Development Only)
- **Production:** Requires `SECRET_KEY` and `JWT_SECRET_KEY` environment variables
- **Development:** Set `DEV_SECRETS_OK=1` to enable fallback secrets (NEVER in production)
- **Testing:** Fixed secrets in TestingConfig (safe for CI)

### CORS Origins
- **Default:** None (same-origin only)
- **Override:** Set `CORS_ORIGINS=http://localhost:3000,https://example.com`

### Email Configuration
- **Default:** Disabled (`MAIL_ENABLED=0`)
- **Override:** Set `MAIL_ENABLED=1`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`

### Routing Bootstrap
- **Production:** Enabled by default (`ROUTING_REGISTRY_BOOTSTRAP=True` in Config)
- **Unit tests:** Disabled (`ROUTING_REGISTRY_BOOTSTRAP=False` in TestingConfig) to avoid cross-test contamination
- **Smoke tests:** Enabled (production-like behavior)
- **Bootstrap tests:** Use `app_bootstrap_on` fixture to override

---

## Clean-Environment Validation (for CI/CD)

To validate that the repository can be tested in a fresh environment:

1. **Install dependencies:**
   ```bash
   python -m pip install --no-cache-dir -r backend/requirements-test.txt
   ```

2. **Run canonical smoke suite:**
   ```bash
   python -m pytest tests/smoke/ -v --tb=short
   ```

3. **Run broader test suite:**
   ```bash
   cd backend
   python -m pytest tests/ -v --tb=short
   ```

For Area 2 operational closure, also run the **Area 2 dual-workstream** command from the [`Area 2 dual-workstream validation (canonical)`](#area-2-dual-workstream-validation-canonical) section (same install prerequisites; **`cd backend`** and **`--no-cov`**).

If smoke and backend suites pass, the environment is valid for those scopes. If tests fail, check:
- All required packages are in requirements files
- PYTHONPATH is correctly set (`backend/pytest.ini` handles this when cwd is `backend/`)
- Database is readable/writable (if using file-based SQLite)
- No local environment assumptions are leaked

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'app.database'"
- This is a fixed import error in the repository. Use `from app.extensions import db` instead.
- Smoke tests have been updated to use the correct import.

### "fixture 'auth_headers' not found"
- Ensure pytest loads plugins correctly. Smoke tests import backend fixtures via `pytest_plugins`.
- If running a custom test outside smoke/backend, add this to your conftest:
  ```python
  pytest_plugins = ['backend.tests.conftest']
  ```

### "ROUTING_REGISTRY_BOOTSTRAP is not set" or "RuntimeError: working outside of application context"
- Use the correct fixture for your profile:
  - `app` for isolated tests
  - `app_bootstrap_on` for bootstrap tests
  - Ensure you're inside the app context when accessing app globals

### Tests run slowly
- Run only unit tests: `pytest tests/ -m unit`
- Skip slow tests: `pytest tests/ -m "not slow"`
- Use pytest-xvs for early exit on failure: `pytest tests/ -xvs`

### Database errors or "table does not exist"
- The test fixtures automatically create all tables. If you see this:
  1. Ensure the `app` fixture is used (it calls `db.create_all()`)
  2. Check that migrations are properly applied (if using a real DB)
  3. Verify `SQLALCHEMY_DATABASE_URI` is set correctly in TestingConfig

---

## Glossary

**testing_isolated:** Default profile; uses in-memory DB, no routing bootstrap, CSRF disabled. For unit tests.

**testing_bootstrap_on:** Production-like routing with in-memory DB and test fixtures. For area-specific tests.

**testing_isolated_production_like:** Full production config (real DB file, bootstrap, etc.). For smoke tests.

**ROUTING_REGISTRY_BOOTSTRAP:** When true, initializes the global routing registry at startup. Must be false in isolated unit tests to prevent cross-test contamination.

**Smoke test:** Lightweight, quick test of core functionality (not heavy integration testing). Validates startup, basic health, and key paths.

**Fixture:** Pytest fixture; a reusable test setup (e.g., `app`, `test_user`, `auth_headers`). Defined in conftest.py.

**Profile:** A named test configuration (e.g., testing_isolated, testing_bootstrap_on). Determines what config class is used and what fixtures are available.

