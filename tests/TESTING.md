# Testing guide — World of Shadows

This document describes how to run the consolidated test suites using the orchestrator [`run_tests.py`](run_tests.py) in this directory. Pytest trees live across multiple repository areas; the runner exposes component suites and root `tests/*` suite groups in one canonical entrypoint.

The root `tests/` folder holds the **orchestrator** (`run_tests.py`), smoke assets (`tests/smoke/`), reports (`tests/reports/`), and this file. It does **not** replace each component’s own `tests/` root.

---

## Quick start

**First-time / fresh clone (installs all Python deps for `--suite all`):** from the repository root, run one of:

- **Linux / macOS / Git Bash:** `./setup-test-environment.sh` or `./scripts/install-full-test-env.sh` (same behavior)
- **Windows (cmd):** `setup-test-environment.bat` or `scripts\install-full-test-env.bat`
- **Windows (PowerShell):** `.\scripts\install-full-test-env.ps1`

That installs `backend/requirements-dev.txt`, `frontend/requirements-dev.txt`, `administration-tool/requirements-dev.txt`, `world-engine/requirements-dev.txt`, plus editable `story_runtime_core` and `ai_stack[test]`, and verifies the LangGraph export surface (`RuntimeTurnGraphExecutor`) expected by the **engine** and **ai_stack** suites. For **ai_stack tests only**, use `scripts/install-ai-stack-test-env.sh` (or `.ps1` / `.bat`) — smaller install.

### Automated setup — security and hygiene

The official setup entry points (`setup-test-environment.*`, `scripts/install-full-test-env.*`) are intended for **trusted checkout trees** and CI:

- **Local requirement files only** — installs use `pip install -r` against paths under this repository (no remote pipe-to-shell installers).
- **`python -m pip`** — reduces accidental use of a different `pip` on `PATH` (see scripts’ comments; G-B-03 asserts this for the shell setup).
- **World Engine pytest** forces a known non-production internal API key in `world-engine/tests/conftest.py` so automated runs do not depend on operator `.env` secrets for internal-route tests (do not reuse that value in production).

From the **repository root** (recommended):

```bash
python tests/run_tests.py
```

Or from `tests/`:

```bash
cd tests
python run_tests.py
```

Cross-platform; use `python3` on Linux/macOS if needed.

---

## Changed-file selector

For day-to-day refactors, use the changed-file selector before reaching for a
full component suite. It maps modified `backend/`, `ai_stack/`, and
`world-engine/` paths to the smallest existing suite or direct pytest target it
knows about.

Dry run from the repository root:

```bash
python scripts/test_changed.py
```

Run the selected tests:

```bash
python scripts/test_changed.py --run
```

You can also pass paths explicitly:

```bash
python scripts/test_changed.py backend/app/services/governance/governance_runtime_service.py
python scripts/test_changed.py ai_stack/story_runtime/semantic_planner/semantic_scene_planner.py
python scripts/test_changed.py world-engine/app/story_runtime/manager/actor_tracking/
```

The selector deliberately keeps the full gates intact. Source changes map to
focused `tests/run_tests.py --suite ... --quick` lanes; changed test files run
directly. Use `--full` when you want the selected suites without `--quick`.

---

## Canonical `--suite` list

| CLI name | Working directory | Pytest path | Notes |
|----------|-------------------|-------------|--------|
| `backend` | `backend/` | `tests` | Collects entire `backend/tests/`, including `writers_room/` and `improvement/` subtrees. |
| `frontend` | `frontend/` | `tests` | Player/public Flask UI tests. |
| `administration` | `administration-tool/` | `tests` | Admin proxy and UI tests. |
| `engine` | `world-engine/` | `tests` | FastAPI runtime, HTTP/WS. |
| `database` | `database/` | `tests` | Schema/migration tests (often import `backend/app` models). |
| `writers_room` | `backend/` | `tests/writers_room` | **Slice** run: Writers-Room tests only (also collected under full `backend`). |
| `improvement` | `backend/` | `tests/improvement` | **Slice** run: improvement-loop tests only. |
| `ai_stack` | **repo root** | `ai_stack/tests` | Requires `PYTHONPATH` including repo root (runner sets this). |
| `story_runtime_core` | **repo root** | `story_runtime_core/tests` | Builtin templates, adapters, delivery. |
| `gates` | **repo root** | `tests/gates` | MVP foundation / architecture enforcement gates. |
| `mvp5` | `frontend/` | `tests` | MVP5 block renderer, typewriter, orchestration (pytest + Jest lane). |
| `root_core` | **repo root** | `tests/test_agency_capability_matrix_truth.py` | Root canonical truth contract test. |
| `root_integration` | **repo root** | `tests/integration` | Root integration checks. |
| `root_branching` | **repo root** | `tests/branching` | Branching behavior checks. |
| `root_smoke` | **repo root** | `tests/smoke` | Repository smoke checks. |
| `root_tools` | **repo root** | `tests/tools` | Tooling tests. |
| `root_requirements_hygiene` | **repo root** | `tests/requirements_hygiene` | Requirements and dependency hygiene checks. |
| `root_e2e_python` | **repo root** | `tests/e2e` | Python end-to-end verification files. |
| `root_experience_scoring` | **repo root** | `tests/experience_scoring_cli` | Experience scoring command tests. |

---

## Focused block suites

The full component suites (`backend`, `engine`, `ai_stack`) remain the canonical gates. The focused block suites below are for faster, systematic diagnosis when one subsystem changes. They run with `--no-cov` under `--quick`, and partial runs do not enforce component-wide coverage thresholds.

Example:

```bash
python tests/run_tests.py --suite engine_runtime --quick
python tests/run_tests.py --suite engine_opening_contracts --quick --stats
python tests/run_tests.py --suite ai_stack_graph ai_stack_goc --quick --continue-on-failure
```

### Backend directory sub-suites

These select **strict subsets** of `backend/tests/` for iteration speed. They use `cwd=backend/` and share [`backend/pytest.ini`](../backend/pytest.ini). **They do not replace** the canonical full gate `python tests/run_tests.py --suite backend` (coverage fail-under is disabled on partial runs — see [`docs/testing/COVERAGE_SEMANTICS.md`](../docs/testing/COVERAGE_SEMANTICS.md)).

| CLI name | Pytest targets (under `backend/`) |
|----------|-------------------------------------|
| `backend_runtime` | `tests/runtime` |
| `backend_observability` | `tests/test_observability`, plus top-level `tests/test_observability.py`, `tests/test_m11_ai_stack_observability.py` |
| `backend_services` | `tests/services` |
| `backend_content` | `tests/content` |
| `backend_routes_core` | `tests/routes`, `tests/web`, `tests/api` |
| `backend_mcp` | `tests/mcp` |
| `backend_play` | Play/session and world-engine bridge files (`test_game_routes.py`, MVP4 playability, world-engine console/control-center contracts, play-service client/control tests). |
| `backend_rest` | `tests` with `--ignore=` for every path covered by the rows above (and `writers_room` / `improvement` trees), so flat files and uncategorized folders remain |

`writers_room` and `improvement` remain dedicated component suites; their tests are also collected under full `backend`.

The split `backend/app/services/` tree also has package-aligned service slices. They overlap with `backend_services`, `writers_room`, `improvement`, and some top-level service tests, but make narrow service work easier to verify:

| CLI name | Focus |
|----------|-------|
| `backend_service_activity` | `app/services/activity/` audit and activity-log service coverage. |
| `backend_service_ai_stack` | `app/services/ai_stack/` closure cockpit, evidence, release-readiness and AI-engineer service tests. |
| `backend_service_analytics` | `app/services/analytics/` analytics and metrics service tests. |
| `backend_service_common` | `app/services/common/` log/search utility tests. |
| `backend_service_content` | `app/services/content/` area, economy, forum, news, slogan and wiki service tests. |
| `backend_service_data` | `app/services/data/` import/export and persistence service tests. |
| `backend_service_game` | `app/services/game/` play-service, game content/profile and game service tests. |
| `backend_service_governance` | `app/services/governance/` narrative, observability, research and operational governance service tests. |
| `backend_service_identity` | `app/services/identity/` user, role, token, mail and encryption service tests. |
| `backend_service_improvement` | `app/services/improvement/` improvement-loop service tests. |
| `backend_service_inspector` | `app/services/inspector/` inspector projection and turn projection service tests. |
| `backend_service_mcp` | `app/services/mcp/` MCP operation service tests. |
| `backend_service_prompts` | `app/services/prompts/` prompt-store service tests. |
| `backend_service_story_runtime` | `app/services/story_runtime/` play-control, operator history and experience service tests. |
| `backend_service_system` | `app/services/system/` system diagnosis service tests. |
| `backend_service_writers_room` | `app/services/writers_room/` pipeline and Writers-Room service tests. |

### World-engine block suites

These select explicit files under `world-engine/tests/`. `engine_rest` runs the remaining world-engine tests after subtracting the focused blocks.

| CLI name | Focus |
|----------|-------|
| `engine_foundation` | Configuration, auth/security guards, bridge contracts, canonical runtime and package policy. |
| `engine_http_ws` | HTTP endpoints, UI proxy/runtime pages, WebSocket session and isolation behavior. |
| `engine_runtime` | Story-runtime internals, runtime manager, turn execution, shell/window projections, RAG/runtime world surfaces. |
| `engine_story_manager_session` | Focused StoryRuntimeManager session package layout, payload round-trip, persistence, runtime projection and W5 player-view checks. |
| `engine_opening_contracts` | MVP1-MVP4 opening, actor-lane, LDSS, GoC greeting/narrator-path and runtime-profile handoff contracts. |
| `engine_persistence` | Stores, tickets, branching, persistence, recovery, JSON/SQLAlchemy storage. |
| `engine_observability` | Langfuse payloads, trace propagation, diagnostics, runtime profiles, narrative governance API, thin-path summaries. |
| `engine_rest` | Remaining `world-engine/tests` files not listed in the focused blocks. |

### AI-stack block suites

These run from the repository root. That is intentional: running from `ai_stack/` can shadow the installed external `langgraph` package with the local `ai_stack/langgraph` directory.

| CLI name | Focus |
|----------|-------|
| `ai_stack_graph` | LangGraph runtime, ADR-0041 sidecar, thin-path graph contracts, graph authority and integration wiring. |
| `ai_stack_goc` | God of Carnage contracts: opening, narrator path, frozen vocab, scene identity, W5 actor situation, visible attribution, actor vitality. |
| `ai_stack_capabilities` | Capability registry, selector, validator, canonical path/prompt/step and player-action resolution. |
| `ai_stack_narrative` | Narrative engines and player-facing runtime surfaces: consequence, dramatic effect, NPC agency, sensory/social/temporal/tonal engines. |
| `ai_stack_retrieval_research` | RAG, semantic embedding, retrieval governance/runtime planner and research golden cases. |
| `ai_stack_quality` | Quality Lab, Langfuse, MCP surface, runtime readiness/aspect/authority and package/config checks. |
| `ai_stack_rest` | Remaining `ai_stack/tests` files not listed in the focused blocks. |

The reorganized `ai_stack/` source tree also has package-aligned slices. These overlap the broader scenario blocks above, but are smaller when you want to validate one package after moving code.

| CLI name | Focus |
|----------|-------|
| `ai_stack_core` | Core package/config/readiness smoke. |
| `ai_stack_actor_tracking` | `actor_tracking/` W5 extraction, projection, validation, diagnostics, and Phase 6B migration safety nets. |
| `ai_stack_contracts` | `contracts/` data and behavioral contract surfaces. |
| `ai_stack_langchain` | `langchain/` bridge and reviver compatibility. |
| `ai_stack_langfuse` | `langfuse/` evaluator catalog and evidence helpers. |
| `ai_stack_langgraph` | `langgraph/` runtime, state, orchestrator and agent nodes. |
| `ai_stack_language_io` | `language_io/` visible attribution and narrative language surfaces. |
| `ai_stack_mcp` | `mcp/` canonical surface, static catalog and agent interface. |
| `ai_stack_prompt_store` | `prompt_store/` canonical prompt catalog. |
| `ai_stack_quality_lab` | `quality_lab/` interpreters, evaluator catalog and production judge. |
| `ai_stack_rag` | `rag/` retrieval, embedding and governance helpers. |
| `ai_stack_research` | `research/` claims, exploration, store and golden cases. |
| `ai_stack_story_runtime_canonical_path` | `story_runtime/canonical_path/` canonical path and LDSS step coverage. |
| `ai_stack_story_runtime_director` | `story_runtime/director/` director/capability/scenedirection slices. |
| `ai_stack_story_runtime_dramatic_effect` | `story_runtime/dramatic_effect/` gates and hold-effect contracts. |
| `ai_stack_story_runtime_god_of_carnage` | `story_runtime/god_of_carnage/` module-specific runtime and roadmap contracts. |
| `ai_stack_story_runtime_narrative` | `story_runtime/narrative/` narrative engine family. |
| `ai_stack_story_runtime_narrator` | `story_runtime/narrator/` narrator path and opening/narrator consequence contracts. |
| `ai_stack_story_runtime_npc_agency` | `story_runtime/npc_agency/` NPC agency, voice, character mind and vitality. |
| `ai_stack_story_runtime_semantic_planner` | `story_runtime/semantic_planner/` semantic scene/move/planner surfaces. |
| `ai_stack_story_runtime_turn` | `story_runtime/turn/` action resolution and validation authority. |
| `ai_stack_telemetry` | `telemetry/` and runtime telemetry/aspect surfaces. |

---

## `--suite all` semantics

`--suite all` (or default `--suite` omitted) runs all Python suite groups in deterministic order:

1. `backend`  
2. `frontend`  
3. `administration`  
4. `engine`  
5. `database`  
6. `ai_stack`  
7. `story_runtime_core`  
8. `gates`  
9. `root_core`  
10. `root_integration`  
11. `root_branching`  
12. `root_smoke`  
13. `root_tools`  
14. `root_requirements_hygiene`  
15. `root_e2e_python`  
16. `root_experience_scoring`  

`writers_room` and `improvement` remain available as dedicated slices for focused execution, but are already covered under full backend collection.

To run **only** Writers-Room or improvement tests (e.g. focused coverage):

```bash
python tests/run_tests.py --suite writers_room
python tests/run_tests.py --suite improvement
```

Example fast lanes:

```bash
python tests/run_tests.py --suite backend_observability --quick
python tests/run_tests.py --suite backend_runtime --quick
python tests/run_tests.py --suite engine_story_manager_session --quick
python tests/run_tests.py --suite backend_service_identity backend_service_content --quick
python tests/run_tests.py --suite engine_runtime --quick
python tests/run_tests.py --suite ai_stack_graph --quick
python tests/run_tests.py --suite ai_stack_langgraph ai_stack_story_runtime_turn --quick
```

---

## `--scope` (pytest marker filter)

`--scope` maps to `pytest -m <marker>` **only** for suites that define the markers in their `pytest.ini` / `pyproject.toml`.

| Suite | `contracts` | `integration` | `e2e` | `security` |
|-------|-------------|-----------------|-------|-------------|
| `backend` | `-m contract` | `-m integration` | `-m e2e` | `-m security` |
| `backend_*` sub-suites | same | same | same | same |
| `writers_room` | same | same | same | same |
| `improvement` | same | same | same | same |
| `administration` | `-m contract` | `-m integration` | **full suite** (no `e2e` marker) | `-m security` |
| `engine` | `-m contract` | `-m integration` | **full suite** (no `e2e` marker) | `-m security` |
| `frontend` | **ignored** — always full suite | | | |
| `database` | **ignored** — always full suite | | | |
| `ai_stack` | **ignored** — always full suite | | | |
| `root_*` suites | **ignored** — always full suite | | | |

When scope is set but not applied, the runner prints an `[INFO]` line (see `run_tests.py`).

---

## `--domain` (backend cross-folder marker filter)

`--domain` applies **only** to suites that use `backend/pytest.ini`: `backend`, every `backend_*` sub-suite, `writers_room`, and `improvement`. It maps to pytest `-m <domain>` using markers registered in [`backend/pytest.ini`](../backend/pytest.ini): `auth`, `observability`, `runtime`, `routes_core`, `content`, `services`, `writers_room`, `improvement`, `mvp_handoff`.

**Combination with `--scope`:** the runner passes a single expression, e.g. `--scope contracts --domain auth` → `-m "contract and auth"`.

Other suites ignore `--domain` (no filter).

---

## `--parallel` (opt-in pytest-xdist)

**Default:** off (sequential pytest).

When set (`--parallel` with no value uses **auto** worker count; `--parallel 4` fixes worker count), the runner runs **pytest-xdist** with `-n …` and **`--dist loadfile`** (tests in one file stay on one worker). Dependency: `pytest-xdist` in [`backend/requirements-test.txt`](../backend/requirements-test.txt).

**Two-pass execution:** tests marked **`@pytest.mark.serial`** run in a **second, sequential** pass (`-m "… and (serial)"`). The first parallel pass uses `-m "… and (not serial)"`. If the serial pass collects zero tests, pytest exit code **5** is treated as success for that pass.

Use **`serial`** for ordering-sensitive work (e.g. migrations touching shared schema, login counter races, strict wall-clock performance assertions).

---

## `--quick`, `--stats`, `--continue-on-failure`

| Flag | Effect |
|------|--------|
| `--quick` | Each suite: `pytest --no-cov -x` (stop on first **test** failure in that suite). **Skips** the pre-run `pytest --collect-only` stats pass (unless `--stats`). **Stops the orchestrator** after the first **suite** that fails (unless `--continue-on-failure`). |
| `--stats` | With `--quick`, still run the collect-only stats pass first. |
| `--continue-on-failure` | With `--quick`, run all selected suites even if one fails. |

Without `--quick`, the runner always runs collect-only first; a non-zero collection exit code **fails the whole run** before pytest executes.

---

## Coverage (`pytest-cov`) per suite

Behavior is implemented in [`run_tests.py`](run_tests.py) (`_cov_sources_for_suite`, `_cov_fail_under_for_suite`, `build_pytest_argv`).

| Suite | `--cov=` roots (each passed as its own flag) | `--cov-fail-under` |
|-------|-----------------------------------------------|---------------------|
| `backend` | `backend/app` | 85 |
| `frontend` | `frontend/app` | 90 |
| `writers_room` | `backend/app` | 50 |
| `improvement` | `backend/app` | 50 |
| `administration` | `--cov=.` + `administration-tool/.coveragerc` (flat tree; tests omitted) | 80 |
| `engine` | `world-engine/app` (path) | 80 |
| `database` | `backend/app` | *(none — instrumentation only; see semantics doc)* |
| `ai_stack` | `ai_stack/` (repo path) | 80 |

- **Default** (no `--coverage`, no `--verbose`): `-v --tb=short`, term-missing report, fail-under as above.  
- **`--coverage`**: adds HTML report and `term-missing:skip-covered`.  
- **`--verbose`**: `-vv --tb=long -s` plus same cov flags as default.  
- **`--quick`**: **no** coverage flags for pytest (`--no-cov`).

**Semantics:** coverage measures **in-process** Python lines touched by tests. It does **not** measure production realism (real network, browser, DB load, or LLM variability). See [`docs/testing/COVERAGE_SEMANTICS.md`](../docs/testing/COVERAGE_SEMANTICS.md).

---

## `run_tests.py` — option summary

| Option | Meaning |
|--------|---------|
| `--suite …` | One or more suite names, or `all` (see above). Includes `backend_*` sub-suites. |
| `--scope …` | Marker filter where supported (see matrix). |
| `--domain …` | Backend domain marker filter; combines with `--scope` via `and`. |
| `--parallel [WORKERS]` | Opt-in xdist parallel run + serial second pass (see above). |
| `--with-playwright` | Add Playwright lane (`tests/e2e`, external toolchain). |
| `--with-compose-smoke` | Add compose-smoke lane (`tests/smoke/compose_smoke`). |
| `--quick` | Fast fail; see table above. |
| `--stats` | Force collect-only with `--quick`. |
| `--continue-on-failure` | Run all suites with `--quick` even after a failure. |
| `--coverage` | HTML + stricter cov reporting. |
| `--verbose` | Verbose pytest + long tracebacks. |

---

## Makefile (optional)

From `tests/`:

| Target | Command |
|--------|---------|
| `make test` | `python3 run_tests.py` |
| `make test-quick` | `python3 run_tests.py --quick` |
| `make test-coverage` | `python3 run_tests.py --coverage` |
| `make test-contracts` | `python3 run_tests.py --suite backend --scope contracts` |
| `make test-integration` | `python3 run_tests.py --suite backend --scope integration` |

---

## JUnit reports

`run_tests.py` writes JUnit XML under `tests/reports/` (`pytest_<suite>_YYYYMMDD_HHMMSS.xml`).

---

## Running pytest manually (single component)

Always set the working directory to the component that owns the code under test:

```bash
cd backend
python -m pytest tests -v
```

---

## Optional: Compose smoke lane

For a **production-narrow** path (real HTTP/WS, services up), see [`smoke/compose_smoke/README.md`](smoke/compose_smoke/README.md).

---

## Optional: Browser E2E (Playwright lane)

Critical UI flows (login, play shell) are scaffolded under [`e2e/`](e2e/README.md) (`@playwright/test`). Use `python tests/run_tests.py --suite all --with-playwright` to include this lane.

---

## CI example

```yaml
- run: pip install -r backend/requirements-dev.txt
- run: python tests/run_tests.py --suite backend --quick
```

Install dependencies per component before `python tests/run_tests.py --suite all`.

---

## Environment preflight

Before running pytest, `run_tests.py` calls `check_environment()` and runs **import probes per selected suite** so automated runs fail fast with install hints instead of mid-suite `ModuleNotFoundError`:

- **backend**, **`backend_*` sub-suites**, **writers_room**, **improvement**, **database** — Flask stack under `backend/` (same imports as `backend/tests/conftest.py`). If `ai_stack.langgraph.langgraph_runtime` is not importable, an **informational** line suggests `pip install -e "./ai_stack[test]"` for tests that touch the graph.
- **frontend** — `flask`, `requests` with `cwd=frontend/` (`frontend/requirements-dev.txt`).
- **administration** — `flask`, `werkzeug` with `cwd=administration-tool/`.
- **engine** — FastAPI / SQLAlchemy / HTTPX for the engine app, then **LangChain / LangGraph** plus `from ai_stack import RuntimeTurnGraphExecutor` with repo root on `PYTHONPATH` (same bar as `.github/workflows/engine-tests.yml`).
- **ai_stack** — editable `story_runtime_core` + `ai_stack` resolvable from repo root, then the **same LangGraph lane** probe as engine (`langchain_core`, `langgraph`, export flag).

For **full** orchestrator parity (including `engine` + `ai_stack` graph lane), use `setup-test-environment.sh` / `setup-test-environment.bat` or `scripts/install-full-test-env.*` (see Quick start above). For AI-stack-only work, use `scripts/install-ai-stack-test-env.sh` (Linux/macOS) or `pip install -r ai_stack/requirements-test.txt` with editable installs per `ai_stack/requirements-test.txt` header comments.

---

## References

- [ADR-0037 — Backend test suite split](../docs/ADR/adr-0037-backend-test-suite-split-runner.md)
- [pytest](https://docs.pytest.org/)
- [Coverage.py](https://coverage.readthedocs.io/)
