#!/usr/bin/env python3
"""
World of Shadows — multi-component test runner.

Orchestrates pytest for **eight** selectable suites: ``backend``, ``frontend``,
``administration``, ``engine``, ``database``, ``writers_room``, ``improvement``,
``ai_stack``. Each suite uses its own working directory (repo root for ``ai_stack``).

``--suite all`` runs six suites in order (**backend**, **frontend**, **administration**,
**engine**, **database**, **ai_stack**). ``writers_room`` and ``improvement`` are **not**
duplicated as extra runs: their tests live under ``backend/tests/`` and are already
collected by the backend suite. Use ``--suite writers_room`` or ``--suite improvement``
for isolated slice runs (e.g. coverage focused on those modules).

Optional ``--scope`` maps to ``pytest -m`` for backend, writers_room, improvement,
administration, and engine (see ``--help``).

**Invocation** (from repository root)::

    python tests/run_tests.py
    python tests/run_tests.py --suite backend --scope contracts
    python tests/run_tests.py --suite all --quick

Or ``cd tests`` then ``python run_tests.py …``. See ``tests/TESTING.md`` for full runner
contracts (``--quick``, ``--scope``, coverage roots, and ``--suite all`` semantics).

**One-shot dependency install (recommended for a fresh clone / CI-like venv):** from the
repository root run ``./setup-test-environment.sh`` (Linux/macOS/Git Bash) or
``setup-test-environment.bat`` (Windows cmd), or the equivalent
``scripts/install-full-test-env.sh`` / ``scripts/install-full-test-env.ps1`` /
``scripts/install-full-test-env.bat``. That installs backend, frontend, administration-tool,
and world-engine dev requirements plus editable ``story_runtime_core`` and ``ai_stack[test]``,
then verifies the LangGraph export surface required by the **engine** and **ai_stack** suites.
Without that closure, :func:`check_environment` fails fast with ``pip`` hints instead of
mid-suite ``ModuleNotFoundError``.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Paths
TESTS_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = TESTS_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
ADMIN_TOOL_DIR = PROJECT_ROOT / "administration-tool"
WORLD_ENGINE_DIR = PROJECT_ROOT / "world-engine"
DATABASE_DIR = PROJECT_ROOT / "database"
REPORTS_DIR = TESTS_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Authoritative pytest-cov roots (single source of truth). Mirrors component ``pytest.ini``
# where noted: ``administration-tool`` uses ``--cov=.`` + ``.coveragerc``; ``world-engine`` and
# ``database`` use explicit ``--cov=`` targets; ``database`` omits ``--cov-fail-under`` (thin slice
# of ``backend/app``). See ``docs/testing/COVERAGE_SEMANTICS.md``.
BACKEND_APP_ROOT = str(BACKEND_DIR / "app")
FRONTEND_APP_ROOT = str(FRONTEND_DIR / "app")
WORLD_ENGINE_APP_ROOT = str(WORLD_ENGINE_DIR / "app")
AI_STACK_ROOT = str(PROJECT_ROOT / "ai_stack")

# Human-readable titles for each component (English)
SUITE_DISPLAY_NAMES: dict[str, str] = {
    "backend": "Backend (Flask API and services)",
    "frontend": "Frontend (player/public UI)",
    "administration": "Administration tool (proxy and UI)",
    "engine": "World engine (runtime and HTTP/WS)",
    "database": "Database (migrations and tooling)",
    "writers_room": "Writers-Room workflow (human-in-the-loop production)",
    "improvement": "Improvement loop (mutation / evaluation / recommendation)",
    "ai_stack": "WOS AI stack (LangGraph runtime, RAG, Writers-Room / improvement seed graphs)",
}

# CLI --scope value -> pytest ``-m`` marker name (must exist in that component's pytest.ini)
SCOPE_TO_PYTEST_MARKER: dict[str, str] = {
    "contracts": "contract",
    "integration": "integration",
    "e2e": "e2e",
    "security": "security",
}


def marker_filter_for_suite(suite_name: str, scope: str) -> str | None:
    """Return the marker expression for ``pytest -m`` if ``--scope`` applies to this suite.

    administration-tool and world-engine register ``contract``, ``integration``, and
    ``security`` but not ``e2e`` (see their ``pytest.ini``). Frontend, database, and
    ai_stack do not use this CLI mapping — returns ``None`` (full suite).
    """
    if scope == "all":
        return None
    marker = SCOPE_TO_PYTEST_MARKER.get(scope)
    if marker is None:
        return None
    if suite_name in ("backend", "writers_room", "improvement"):
        return marker
    if suite_name in ("administration", "engine"):
        if scope == "e2e":
            return None
        return marker
    return None

# Matches backend/pytest.ini coverage gate when running backend tests
BACKEND_COV_FAIL_UNDER = "85"
FRONTEND_COV_FAIL_UNDER = "92"
DEFAULT_COV_FAIL_UNDER = "80"
# writers_room and improvement suites test only their own modules within the larger app package
# Overall app coverage will be low when these suites run alone (expected—untested modules drag average down)
# Instead, we check that the measured coverage (whatever modules ran) meets a minimal gate
WRITERS_ROOM_COV_FAIL_UNDER = "50"  # Realistic: only 3 modules tested out of ~30+ in app
IMPROVEMENT_COV_FAIL_UNDER = "50"   # Realistic: only 3 modules tested out of ~30+ in app

# administration-tool: use ``--cov=.`` + ``administration-tool/.coveragerc`` (single source
# trace) — do not list multiple ``--cov=module`` names; Coverage 7.x warns on import order.

# Suite -> (pytest cwd, path argument to pytest, relative to cwd)
SUITE_PYTEST_TARGETS: dict[str, tuple[Path, str]] = {
    "backend": (BACKEND_DIR, "tests"),
    "frontend": (FRONTEND_DIR, "tests"),
    "administration": (ADMIN_TOOL_DIR, "tests"),
    "engine": (WORLD_ENGINE_DIR, "tests"),
    "database": (DATABASE_DIR, "tests"),
    "writers_room": (BACKEND_DIR, "tests/writers_room"),
    "improvement": (BACKEND_DIR, "tests/improvement"),
    # Writers-Room / improvement seed graphs and runtime turn graph; imports require repo root on PYTHONPATH.
    "ai_stack": (PROJECT_ROOT, "ai_stack/tests"),
}

# Suites run for ``--suite all`` (order preserved). ``writers_room`` / ``improvement`` are
# omitted here because ``backend`` already runs ``pytest tests``, which collects those
# subtrees — separate entries would execute the same tests twice.
ALL_SUITE_SEQUENCE: tuple[str, ...] = (
    "backend",
    "frontend",
    "administration",
    "engine",
    "database",
    "ai_stack",
)


class Colors:
    OKBLUE = "\033[0;34m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    line = "=" * 70
    print(f"{Colors.OKBLUE}{line}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{line}{Colors.ENDC}")


def print_success(text: str) -> None:
    print(f"{Colors.OKGREEN}[OK] {text}{Colors.ENDC}")


def print_error(text: str) -> None:
    print(f"{Colors.FAIL}[FAIL] {text}{Colors.ENDC}")


def print_info(text: str) -> None:
    print(f"{Colors.WARNING}[INFO] {text}{Colors.ENDC}")


def _import_probe(
    *,
    cwd: Path,
    py_code: str,
    env_overrides: dict[str, str] | None = None,
    timeout_s: int = 90,
) -> tuple[bool, str]:
    """Run ``python -c <py_code>`` in ``cwd``; return (ok, stderr_or_stdout_snippet)."""
    env = dict(os.environ)
    if env_overrides:
        env.update(env_overrides)
    try:
        proc = subprocess.run(
            [sys.executable, "-c", py_code],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout_s}s"
    except OSError as exc:
        return False, str(exc)
    if proc.returncode == 0:
        return True, ""
    out = (proc.stderr or "").strip() or (proc.stdout or "").strip()
    return False, out[:1200]


def _probe_ai_stack_langgraph_lane() -> tuple[bool, str]:
    """Same LangChain / LangGraph / export surface as CI (``ai_stack-tests.yml``, engine job)."""
    graph_py = (
        "import langchain_core, langgraph, ai_stack\n"
        "assert ai_stack.LANGGRAPH_RUNTIME_EXPORT_AVAILABLE, "
        "'pip install -e ./story_runtime_core -e \"./ai_stack[test]\" from repo root'\n"
        "from ai_stack import RuntimeTurnGraphExecutor\n"
        "assert RuntimeTurnGraphExecutor is not None\n"
    )
    return _import_probe(
        cwd=PROJECT_ROOT,
        py_code=graph_py,
        env_overrides={"PYTHONPATH": str(PROJECT_ROOT)},
    )


def check_environment(suites: dict[str, tuple[Path, str]]) -> bool:
    """Verify pytest and runtime deps for the **selected** suites.

    The runner's own interpreter only needs ``pytest``. Backend/engine/ai_stack tests
    run with component-local ``cwd`` and ``PYTHONPATH`` like CI; we probe those the
    same way so a missing ``flask`` (etc.) fails here instead of after a misleading OK.
    """
    print_header("Environment check")
    ok = True
    try:
        import pytest

        print_success(f"pytest (runner interpreter): {pytest.__version__}")
    except ImportError:
        print_error("pytest is not installed in the active interpreter. Install test deps (e.g. pip install pytest).")
        return False
    try:
        import coverage

        print_success(f"coverage (runner interpreter): {coverage.__version__}")
    except ImportError:
        print_info("coverage not installed in the active interpreter (optional unless you use --coverage).")

    labels = set(suites.keys())
    if not labels:
        print_info("No suites selected; skipping stack probes.")
        print()
        return True

    # --- Same import surface as backend / database / writers_room / improvement / frontend conftests ---
    needs_backend_stack = bool(
        labels & {"backend", "frontend", "administration", "writers_room", "improvement", "database"}
    )
    if needs_backend_stack:
        print_info("Probing backend Flask stack (cwd=backend, PYTHONPATH=backend) …")
        py = (
            "import flask, flask_sqlalchemy, sqlalchemy, flask_jwt_extended, werkzeug\n"
            "import pydantic\n"
        )
        env_py = os.environ.get("PYTHONPATH", "")
        merged = str(BACKEND_DIR)
        if env_py:
            merged = merged + os.pathsep + env_py
        passed, err = _import_probe(
            cwd=BACKEND_DIR,
            py_code=py,
            env_overrides={"PYTHONPATH": merged},
        )
        if passed:
            print_success(
                "Backend-related suites: Flask, Flask-SQLAlchemy, SQLAlchemy, "
                "Flask-JWT-Extended, Werkzeug, Pydantic importable (see backend/requirements*.txt)."
            )
        else:
            ok = False
            print_error(
                "Backend stack import probe failed. Install backend dependencies, for example: "
                "`cd backend && pip install -r requirements-dev.txt` (or requirements.txt), then retry."
            )
            if err:
                print_info(err)

        opt_passed, opt_err = _import_probe(
            cwd=PROJECT_ROOT,
            py_code="import ai_stack.langgraph_runtime",
            env_overrides={"PYTHONPATH": str(PROJECT_ROOT)},
        )
        if not opt_passed:
            print_info(
                "Optional: some backend tests import ``ai_stack.langgraph_runtime``. "
                "If those fail: ``pip install -e ./story_runtime_core -e \\\"./ai_stack[test]\\\"`` "
                f"from repo root. ({opt_err[:400]})" if opt_err else ""
            )

    if "frontend" in labels:
        print_info("Probing frontend Flask stack (cwd=frontend, PYTHONPATH=frontend) …")
        fe_py = "import flask, requests\n"
        fe_merged = str(FRONTEND_DIR)
        fe_env = os.environ.get("PYTHONPATH", "")
        if fe_env:
            fe_merged = fe_merged + os.pathsep + fe_env
        fe_passed, fe_err = _import_probe(
            cwd=FRONTEND_DIR,
            py_code=fe_py,
            env_overrides={"PYTHONPATH": fe_merged},
        )
        if fe_passed:
            print_success("Frontend suite: Flask and Requests importable (see frontend/pyproject.toml).")
        else:
            ok = False
            print_error(
                "Frontend stack import probe failed. Install frontend deps, for example: "
                "`pip install -r frontend/requirements-dev.txt` or `pip install -e ./frontend[test]`."
            )
            if fe_err:
                print_info(fe_err)

    if "administration" in labels:
        print_info("Probing administration-tool Flask stack …")
        ad_py = "import flask, werkzeug\n"
        ad_merged = str(ADMIN_TOOL_DIR)
        ad_env = os.environ.get("PYTHONPATH", "")
        if ad_env:
            ad_merged = ad_merged + os.pathsep + ad_env
        ad_passed, ad_err = _import_probe(
            cwd=ADMIN_TOOL_DIR,
            py_code=ad_py,
            env_overrides={"PYTHONPATH": ad_merged},
        )
        if ad_passed:
            print_success("Administration suite: Flask and Werkzeug importable (see administration-tool/pyproject.toml).")
        else:
            ok = False
            print_error(
                "Administration-tool stack import probe failed. Install deps, for example: "
                "`pip install -r administration-tool/requirements-dev.txt`."
            )
            if ad_err:
                print_info(ad_err)

    # --- World engine (FastAPI app package ``app`` under world-engine/) ---
    if "engine" in labels:
        print_info("Probing world-engine stack (cwd=world-engine, PYTHONPATH=repo+world-engine) …")
        sep = os.pathsep
        we_py = f"{WORLD_ENGINE_DIR}{sep}{PROJECT_ROOT}"
        py = "import fastapi, sqlalchemy, httpx\n"
        passed, err = _import_probe(
            cwd=WORLD_ENGINE_DIR,
            py_code=py,
            env_overrides={"PYTHONPATH": we_py},
        )
        if passed:
            print_success(
                "World engine suite: FastAPI, SQLAlchemy, HTTPX importable "
                "(see world-engine/requirements.txt and requirements-dev.txt)."
            )
        else:
            ok = False
            print_error(
                "World-engine stack import probe failed. Install engine deps, for example: "
                "`pip install -r world-engine/requirements-dev.txt`, then retry."
            )
            if err:
                print_info(err)

        print_info("Probing ai_stack LangGraph export (StoryRuntimeManager imports RuntimeTurnGraphExecutor) …")
        g_passed, g_err = _probe_ai_stack_langgraph_lane()
        if g_passed:
            print_success("World engine suite: LangChain/LangGraph OK; RuntimeTurnGraphExecutor exported from ai_stack.")
        else:
            ok = False
            print_error(
                "ai_stack LangGraph surface not importable with repo root on PYTHONPATH. "
                "From repo root: `pip install -e ./story_runtime_core` and `pip install -e \"./ai_stack[test]\"`."
            )
            if g_err:
                print_info(g_err)

    # --- ai_stack (repo root on PYTHONPATH; editable installs per CI) ---
    if "ai_stack" in labels:
        print_info("Probing ai_stack (cwd=repo root, PYTHONPATH=repo) …")
        sep = os.pathsep
        root_py = str(PROJECT_ROOT)
        existing = os.environ.get("PYTHONPATH", "")
        if existing:
            root_py = root_py + sep + existing
        py = (
            "import importlib.util\n"
            "for mod in ('story_runtime_core', 'ai_stack'):\n"
            "    assert importlib.util.find_spec(mod), f'missing package: {mod}'\n"
        )
        passed, err = _import_probe(
            cwd=PROJECT_ROOT,
            py_code=py,
            env_overrides={"PYTHONPATH": root_py},
        )
        if passed:
            print_success("ai_stack suite: story_runtime_core and ai_stack importable from repo root.")
        else:
            ok = False
            print_error(
                "ai_stack import probe failed. From repo root run: "
                "`pip install -e ./story_runtime_core -e ./ai_stack[test]` "
                "(same as .github/workflows/ai-stack-tests.yml), then retry."
            )
            if err:
                print_info(err)

        print_info("Probing ai_stack LangChain / LangGraph graph lane (merge bar; same as CI) …")
        g_passed, g_err = _probe_ai_stack_langgraph_lane()
        if g_passed:
            print_success(
                "ai_stack suite: langchain_core, langgraph importable; LANGGRAPH_RUNTIME_EXPORT_AVAILABLE and "
                "RuntimeTurnGraphExecutor OK."
            )
        else:
            ok = False
            print_error(
                "ai_stack graph lane failed (often ModuleNotFoundError: langchain_core). "
                "From repo root: ``pip install -e ./story_runtime_core -e \\\"./ai_stack[test]\\\"`` "
                "or ``pip install -r ai_stack/requirements-test.txt`` plus editable ``ai_stack``."
            )
            if g_err:
                print_info(g_err)

    print()
    return ok


def _subprocess_env_for_suite(suite_name: str) -> dict[str, str] | None:
    """Put repo root on PYTHONPATH for suites that import ``ai_stack`` / ``story_runtime_core`` as siblings."""
    if suite_name not in ("ai_stack", "engine"):
        return None
    env = dict(os.environ)
    root = str(PROJECT_ROOT)
    sep = os.pathsep
    existing = env.get("PYTHONPATH", "")
    parts = [p for p in existing.split(sep) if p]
    if root not in parts:
        parts.insert(0, root)
    env["PYTHONPATH"] = sep.join(parts)
    return env


def show_test_stats(suites: dict[str, tuple[Path, str]], *, scope: str = "all") -> bool:
    """Run collect-only per suite. Returns False if any collection subprocess fails."""
    print_header("Test collection (collect-only)")
    all_ok = True
    for suite_name, (suite_cwd, test_path) in suites.items():
        test_root = suite_cwd / test_path
        if not (test_root.is_dir() or test_root.is_file()):
            print_info(f"{suite_name}: no tests directory or file ({test_root})")
            continue
        collect_argv = ["--collect-only", "-q"]
        m = marker_filter_for_suite(suite_name, scope)
        if m:
            collect_argv.extend(["-m", m])
        collect_argv.append(test_path)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", *collect_argv],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(suite_cwd),
                env=_subprocess_env_for_suite(suite_name) or os.environ,
            )
            out = (result.stdout or "") + (result.stderr or "")
            if result.returncode != 0:
                all_ok = False
                print_error(
                    f"{suite_name}: pytest --collect-only failed (exit {result.returncode})."
                )
                tail = "\n".join((result.stderr or result.stdout or "").strip().split("\n")[-12:])
                if tail.strip():
                    print_info(tail)
                continue
            collected_line = None
            for line in out.split("\n"):
                if "collected" in line.lower() and any(c.isdigit() for c in line):
                    collected_line = line.strip()
                    break
            if collected_line:
                print_info(f"{suite_name}: {collected_line}")
            else:
                all_ok = False
                print_error(f"{suite_name}: could not parse collection output (exit 0).")
        except Exception as exc:
            all_ok = False
            print_error(f"{suite_name}: collect-only failed ({exc})")
    print()
    return all_ok


def get_suite_configs(suite_names: list[str]) -> dict[str, tuple[Path, str]]:
    all_suites = dict(SUITE_PYTEST_TARGETS)
    if "all" in suite_names:
        return {name: all_suites[name] for name in ALL_SUITE_SEQUENCE if name in all_suites}
    result: dict[str, tuple[Path, str]] = {}
    for name in suite_names:
        if name in all_suites:
            result[name] = all_suites[name]
        else:
            print_error(f"Unknown suite: {name}")
    return result if result else dict(all_suites)


def _cov_fail_under_for_suite(suite_name: str) -> str | None:
    if suite_name == "backend":
        return BACKEND_COV_FAIL_UNDER
    if suite_name == "frontend":
        return FRONTEND_COV_FAIL_UNDER
    if suite_name == "writers_room":
        return WRITERS_ROOM_COV_FAIL_UNDER
    if suite_name == "improvement":
        return IMPROVEMENT_COV_FAIL_UNDER
    if suite_name == "database":
        # ``database/tests`` touch a thin slice of ``backend/app``; gating the whole tree is misleading.
        return None
    return DEFAULT_COV_FAIL_UNDER


def _cov_sources_for_suite(suite_name: str) -> list[str]:
    """Return one or more ``pytest-cov`` ``--cov=`` sources (explicit paths or import names).

    Avoids ``--cov=.`` for monorepo components so reports target the real package(s) under test.
    Exception: **administration** uses ``--cov=.`` with a local ``.coveragerc`` (flat layout;
    multiple named modules break Coverage.py tracing). See :func:`_append_cov_flags`.
    ``database`` suite measures ``backend/app`` because schema tests import ORM models there
    (there is no separate ``database/`` Python package — only ``database/tests``).
    """
    if suite_name in ("backend", "writers_room", "improvement", "database"):
        return [BACKEND_APP_ROOT]
    if suite_name == "frontend":
        return [FRONTEND_APP_ROOT]
    if suite_name == "engine":
        return [WORLD_ENGINE_APP_ROOT]
    if suite_name == "administration":
        return []
    if suite_name == "ai_stack":
        return [AI_STACK_ROOT]
    return ["."]


def _append_cov_flags(argv: list[str], suite_name: str) -> None:
    """Append ``--cov=…`` (and administration ``--cov-config``) for the suite."""
    if suite_name == "administration":
        argv.append("--cov=.")
        argv.append(f"--cov-config={ADMIN_TOOL_DIR / '.coveragerc'}")
        return
    for src in _cov_sources_for_suite(suite_name):
        argv.append(f"--cov={src}")


def build_pytest_argv(
    *,
    suite_name: str,
    test_path: str,
    quick: bool,
    coverage_mode: bool,
    verbose: bool,
    scope: str,
) -> list[str]:
    """Build pytest arguments for one component run (cwd = suite working directory)."""
    cov_under = _cov_fail_under_for_suite(suite_name)

    def _append_cov_fail_under(argv_inner: list[str]) -> None:
        if cov_under is not None:
            argv_inner.append(f"--cov-fail-under={cov_under}")

    if quick:
        argv = ["-v", "--tb=short", "--no-cov", "-x"]
        m = marker_filter_for_suite(suite_name, scope)
        if m:
            argv.extend(["-m", m])
        argv.append(test_path)
        return argv

    if coverage_mode:
        argv = ["-v", "--tb=short"]
        _append_cov_flags(argv, suite_name)
        argv.extend(
            [
                "--cov-report=term-missing:skip-covered",
                "--cov-report=html",
            ]
        )
        _append_cov_fail_under(argv)
    elif verbose:
        argv = ["-vv", "--tb=long", "-s"]
        _append_cov_flags(argv, suite_name)
        argv.extend(
            [
                "--cov-report=term-missing",
            ]
        )
        _append_cov_fail_under(argv)
    else:
        argv = ["-v", "--tb=short"]
        _append_cov_flags(argv, suite_name)
        argv.extend(
            [
                "--cov-report=term-missing",
            ]
        )
        _append_cov_fail_under(argv)

    m = marker_filter_for_suite(suite_name, scope)
    if m:
        argv.extend(["-m", m])

    argv.append(test_path)
    return argv


def run_pytest(
    suite_name: str,
    suite_cwd: Path,
    test_path: str,
    pytest_argv: list[str],
    run_title: str,
) -> bool:
    print_header(run_title)
    tests_dir = suite_cwd / test_path
    if not (tests_dir.is_dir() or tests_dir.is_file()):
        print_error(f"Tests directory or file not found: {tests_dir}")
        return False

    junit_report = REPORTS_DIR / f"pytest_{suite_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
    cmd = [sys.executable, "-m", "pytest", *pytest_argv, f"--junit-xml={junit_report}"]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(suite_cwd),
            env=_subprocess_env_for_suite(suite_name) or os.environ,
        )
        return result.returncode == 0
    except OSError as exc:
        print_error(f"Failed to run pytest: {exc}")
        return False


def run_tests_for_suites(
    suites: dict[str, tuple[Path, str]],
    *,
    quick: bool,
    coverage_mode: bool,
    verbose: bool,
    scope: str,
    continue_on_failure: bool,
) -> tuple[bool, dict[str, bool]]:
    all_passed = True
    results: dict[str, bool] = {}

    for suite_name, (suite_cwd, test_path) in suites.items():
        display = SUITE_DISPLAY_NAMES.get(suite_name, suite_name)
        m = marker_filter_for_suite(suite_name, scope)
        if scope != "all" and m is None:
            if suite_name in ("administration", "engine") and scope == "e2e":
                print_info(
                    f"Suite '{suite_name}' has no ``e2e`` marker in pytest.ini; running full tests."
                )
            elif suite_name in ("frontend", "database", "ai_stack"):
                print_info(
                    f"Suite '{suite_name}' does not map --scope '{scope}' to a marker; running full tests."
                )
        if m:
            title = f"{display} — marker '{m}'"
        else:
            title = f"{display} (full)"

        argv = build_pytest_argv(
            suite_name=suite_name,
            test_path=test_path,
            quick=quick,
            coverage_mode=coverage_mode,
            verbose=verbose,
            scope=scope,
        )
        ok = run_pytest(suite_name, suite_cwd, test_path, argv, f"Running: {title}")
        results[suite_name] = ok
        all_passed = all_passed and ok
        if not ok:
            print_error(f"{suite_name} tests failed")
        else:
            print_success(f"{suite_name} tests passed")
        print()

        if not ok and quick and not continue_on_failure:
            print_info(
                "Stopping orchestrator after first failing suite (--quick). "
                "Re-run with --continue-on-failure to execute remaining suites anyway."
            )
            break

    return all_passed, results


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run pytest per component (backend, frontend, administration-tool, world-engine, "
            "database, writers-room, improvement, ai_stack)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Prerequisites (full ``--suite all``): install all component test deps and editable
``story_runtime_core`` + ``ai_stack[test]`` once. From repo root:
  ./setup-test-environment.sh          (Unix / Git Bash)
  setup-test-environment.bat           (Windows cmd)
  ./scripts/install-full-test-env.sh   (wrapper, same as above)
See tests/TESTING.md (Environment preflight).

Examples (from repository root):
  python tests/run_tests.py
  python tests/run_tests.py --suite backend
  python tests/run_tests.py --suite writers_room
  python tests/run_tests.py --suite improvement
  python tests/run_tests.py --suite frontend
  python tests/run_tests.py --suite backend --scope contracts
  python tests/run_tests.py --suite administration --scope security
  python tests/run_tests.py --suite engine --scope integration
  python tests/run_tests.py --suite writers_room improvement --quick
  python tests/run_tests.py --suite ai_stack --quick
  python tests/run_tests.py --suite all --coverage

``--suite all`` runs: backend, frontend, administration, engine, database, ai_stack
(writers_room + improvement are included inside the backend tree; see tests/TESTING.md).
        """,
    )
    parser.add_argument(
        "--suite",
        nargs="+",
        default=["all"],
        choices=["backend", "frontend", "administration", "engine", "database", "writers_room", "improvement", "ai_stack", "all"],
        help=(
            "Component test tree to run (default: all). ``all`` runs six suites without "
            "duplicating writers_room/improvement (they are under backend/tests/)."
        ),
    )
    parser.add_argument(
        "--scope",
        default="all",
        choices=["all", "contracts", "integration", "e2e", "security"],
        help=(
            "Filter by pytest marker where supported: backend, writers_room, improvement "
            "(contract, integration, e2e, security); administration and engine "
            "(contract, integration, security - no e2e marker). "
            "frontend, database, and ai_stack ignore --scope and run the full suite."
        ),
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help=(
            "Per suite: pytest --no-cov -x (stop on first test failure). Orchestrator: skip "
            "pre-run collect-only stats unless --stats; stop after the first failing suite "
            "unless --continue-on-failure."
        ),
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="With --quick, still run collect-only stats before pytest (default: skip when --quick).",
    )
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="With --quick, run every suite even if an earlier suite failed (default: stop early).",
    )
    parser.add_argument("--coverage", action="store_true", help="Coverage with HTML report")
    parser.add_argument("--verbose", action="store_true", help="Verbose pytest and long tracebacks")

    args = parser.parse_args()

    suites = get_suite_configs(args.suite)
    if not suites:
        print_error("No valid suites specified")
        return 1

    if not check_environment(suites):
        return 1

    if args.quick and not args.stats:
        print_info("Skipping pre-run collect-only stats (--quick). Use --stats to force collection.")
    else:
        if not show_test_stats(suites, scope=args.scope):
            print_error("Test collection (collect-only) failed; fix errors above before running tests.")
            return 1

    all_passed, results = run_tests_for_suites(
        suites,
        quick=args.quick,
        coverage_mode=args.coverage,
        verbose=args.verbose,
        scope=args.scope,
        continue_on_failure=args.continue_on_failure,
    )

    print_header("Summary")
    for suite, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        symbol = Colors.OKGREEN if passed else Colors.FAIL
        print(f"{symbol}{status}{Colors.ENDC} - {suite}")

    print()
    if all_passed:
        print_success("All selected suites passed.")
        return 0
    print_error("One or more suites failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
