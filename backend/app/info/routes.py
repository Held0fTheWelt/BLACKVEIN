"""Technical HTML pages for the Flask backend (operators / developers only)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from flask import Blueprint, abort, current_app, g, jsonify, render_template, send_file, url_for

from ai_stack.quality_lab.limit_inventory import (
    build_mcp_tool_limit_inventory,
    mcp_dispatch_rate_limit_metadata,
    rate_limit_production_tuning_metadata,
    summarize_route_limit_inventory,
)
from app.info.api_catalog import build_api_catalog

info_bp = Blueprint(
    "info",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="static",
)

_REL_OPENAPI = Path("docs") / "api" / "openapi.yaml"
_TEXT_FILE_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
_TEXT_FILE_NAMES = {
    ".env.example",
    "Dockerfile",
    "Makefile",
    "mkdocs.yml",
    "setup-test-environment.sh",
}
_PROJECT_SCAN_SKIP_DIRS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".worktrees",
    "__pycache__",
    "backend/instance",
    "backend/var",
    "dist",
    "htmlcov",
    "node_modules",
}
_PROJECT_SECTIONS = [
    {
        "key": "backend",
        "label": "Backend API & Runtime",
        "prefixes": ("backend",),
        "description": "Flask-API, Auth, Runtime-Bridges, Persistenz und diese Info-Oberflächen.",
    },
    {
        "key": "world_engine",
        "label": "World-Engine / Play-Service",
        "prefixes": ("world-engine",),
        "description": "Autoritative Story-Session, Turn-Lifecycle, WebSocket- und Commit-Semantik.",
    },
    {
        "key": "ai_runtime",
        "label": "AI, RAG & LangGraph",
        "prefixes": ("ai_stack", "story_runtime_core", "content"),
        "description": "Capability-Auswahl, Retrieval, Evaluatoren, LangGraph- und Runtime-Bausteine.",
    },
    {
        "key": "frontend",
        "label": "Player-Frontend",
        "prefixes": ("frontend",),
        "description": "Spieler-UI, Play-Shell, lokale Browser-Projektion und Public-Routen.",
    },
    {
        "key": "admin",
        "label": "Administration-Tool",
        "prefixes": ("administration-tool",),
        "description": "Operator-/Redaktionsoberfläche, Governance, MCP, Diagnose und Settings.",
    },
    {
        "key": "mcp_tools",
        "label": "MCP & Tooling",
        "prefixes": ("tools", "postman"),
        "description": "MCP-Server, Tool-Kataloge, Operator-Interfaces und API-Artefakte.",
    },
    {
        "key": "database",
        "label": "Datenbank & Migrationen",
        "prefixes": ("database", "schemas"),
        "description": "Schema-Verträge, Migrationen und Datenbank-Testhilfen.",
    },
    {
        "key": "docs",
        "label": "Docs & ADR Runtime Store",
        "prefixes": ("docs", "mkdocs.yml"),
        "description": "Architekturentscheidungen, Runbooks, API-Referenz und Evidence-Regeln.",
    },
    {
        "key": "root_tests",
        "label": "Root Gates & Smoke Tests",
        "prefixes": ("tests", "test_langfuse_e2e.py", "test_trace_from_backend.py", "test_trace_simple.py", "test_trace_verify.py"),
        "description": "Repo-weite Gates, Smoke-Tests und Integrationsprüfungen.",
    },
    {
        "key": "bootstrap",
        "label": "Docker, Bootstrap & CI",
        "prefixes": (
            ".github",
            ".env.example",
            "docker",
            "docker-compose.langfuse.yml",
            "docker-compose.yml",
            "docker-up.py",
            "scripts",
            "setup-test-environment.sh",
        ),
        "description": "Run-once-Stack, Compose, Secret-Generierung, lokale Start- und Build-Pfade.",
    },
    {
        "key": "governance_suites",
        "label": "FY Testify / Governance Suites",
        "prefixes": ("'fy'-suites", "writers-room"),
        "description": "Zusätzliche Governance-, Writer- und Nachweis-Suiten außerhalb der Kernservices.",
    },
]
_TEST_SUITE_PREFIXES = [
    ("backend/tests", "Backend tests"),
    ("world-engine/tests", "World-Engine tests"),
    ("administration-tool/tests", "Administration-Tool tests"),
    ("frontend/tests", "Frontend tests"),
    ("ai_stack/tests", "AI/RAG/LangGraph tests"),
    ("tools/mcp_server/tests", "MCP server tests"),
    ("database/tests", "Database tests"),
    ("writers-room/tests", "Writers-Room tests"),
    ("tests", "Root gates & smoke tests"),
    ("'fy'-suites", "FY Testify/Governance tests"),
]
_KEY_ADR_SUMMARIES = [
    {
        "adr": "ADR-0030",
        "path": "docs/ADR/adr-0030-docker-up-complete-bootstrap.md",
        "topic": "Run-once Docker-Bootstrap",
        "explains": "Warum `docker-up.py up` Env-Erzeugung, Compose, Health, Admin-Bootstrap und Gate als einen lokalen Startpfad bündelt.",
    },
    {
        "adr": "ADR-0031",
        "path": "docs/ADR/adr-0031-env-configuration-governance.md",
        "topic": "Env- und Secret-Grenzen",
        "explains": "Welche Werte automatisch generiert werden, welche Provider-Keys manuell bleiben und warum Langfuse in Backend-Governance überführt wird.",
    },
    {
        "adr": "ADR-0037",
        "path": "docs/ADR/adr-0037-backend-test-suite-split-runner.md",
        "topic": "Testsuite-Schnitt",
        "explains": "Wie große Testbereiche in sinnvolle Runner/Gates aufgeteilt werden, damit Feedback schnell und nachvollziehbar bleibt.",
    },
    {
        "adr": "ADR-0039",
        "path": "docs/ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md",
        "topic": "Keine Scheinbeweise",
        "explains": "Warum Tests, MCP-Resultate und Langfuse-Scores echte Vertragsfelder prüfen müssen und keine Labels als Beweis ausreichen.",
    },
    {
        "adr": "ADR-0041",
        "path": "docs/ADR/adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md",
        "topic": "Runtime Capability Authority",
        "explains": "Wie Capabilities semantisch ausgewählt, budgetiert und als Co-Authority-Evidence dokumentiert werden.",
    },
]
_SUMMARY_EXAMPLES = [
    {
        "label": "Health",
        "method": "GET",
        "path": "/api/v1/health",
        "note": "Schneller API-Check ohne Fachlogik; gut für Monitoring und Rauchtests.",
    },
    {
        "label": "Login",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "note": "Gibt Access/Refresh-Tokens für Browser-, Admin- und Tooling-Clients aus.",
    },
    {
        "label": "Spielstart",
        "method": "GET",
        "path": "/api/v1/game/bootstrap",
        "note": "Liefert den Bootstrap-Kontext, bevor ein Run im Play-Service beginnt.",
    },
    {
        "label": "Player-Session",
        "method": "POST",
        "path": "/api/v1/game/player-sessions",
        "note": "Erstellt die Backend-Seite einer Spielsitzung und bindet den World-Engine-Pfad an.",
    },
]


def _resolve_repo_root() -> Path:
    cfg = (current_app.config.get("WOS_REPO_ROOT") or "").strip()
    if cfg:
        candidate = Path(cfg)
        if candidate.exists():
            return candidate.resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "docker-compose.yml").is_file() or (parent / "docs").is_dir():
            return parent
    return here.parents[3]


def _resolve_openapi_yaml_path() -> Path | None:
    """Locate openapi.yaml for monorepo checkout and Docker /app layout (see backend/Dockerfile)."""
    cfg = (current_app.config.get("OPENAPI_SPEC_PATH") or "").strip()
    if cfg:
        p = Path(cfg)
        if p.is_file():
            return p
    here = Path(__file__).resolve()
    # .../repo/backend/app/info/routes.py -> parents[3] == repo root
    # .../app/app/info/routes.py (Docker) -> parents[2] == /app with docs/ copied under /app/docs
    for depth in (3, 2):
        if depth < len(here.parents):
            candidate = here.parents[depth] / _REL_OPENAPI
            if candidate.is_file():
                return candidate
    return None


def _is_relative_to(rel: Path, prefix: str) -> bool:
    rel_posix = rel.as_posix()
    normalized = prefix.strip("/")
    return rel_posix == normalized or rel_posix.startswith(f"{normalized}/")


def _scan_skip_parts(rel_dir: Path) -> bool:
    if not rel_dir.parts:
        return False
    rel_posix = rel_dir.as_posix()
    for skipped in _PROJECT_SCAN_SKIP_DIRS:
        if rel_posix == skipped or rel_posix.startswith(f"{skipped}/"):
            return True
    return any(part in _PROJECT_SCAN_SKIP_DIRS for part in rel_dir.parts)


def _is_countable_text_file(path: Path) -> bool:
    return path.name in _TEXT_FILE_NAMES or path.suffix.lower() in _TEXT_FILE_EXTENSIONS


def _is_visible_project_file(rel: Path) -> bool:
    rel_posix = rel.as_posix()
    for skipped in _PROJECT_SCAN_SKIP_DIRS:
        if "/" in skipped and (rel_posix == skipped or rel_posix.startswith(f"{skipped}/")):
            return False
    if any(part in _PROJECT_SCAN_SKIP_DIRS for part in rel.parts):
        return False
    if any(part.startswith(".") and part != ".github" for part in rel.parts[:-1]):
        return False
    return True


def _project_section_for(rel: Path) -> str:
    for section in _PROJECT_SECTIONS:
        if any(_is_relative_to(rel, prefix) for prefix in section["prefixes"]):
            return section["key"]
    return "other"


def _test_suite_for(rel: Path) -> str:
    for prefix, label in _TEST_SUITE_PREFIXES:
        if _is_relative_to(rel, prefix):
            return label
    return "Weitere Testdateien"


def _file_size_kib(path: Path) -> int:
    try:
        size = path.stat().st_size
    except OSError:
        return 0
    if size <= 0:
        return 0
    return max(1, (size + 1023) // 1024)


def _iter_git_project_text_files(root: Path) -> list[tuple[Path, Path]] | None:
    commands = (
        ["git", "-C", str(root), "ls-files", "-z"],
        ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "-z"],
    )
    entries: list[tuple[Path, Path]] = []
    seen: set[str] = set()
    git_available = False
    for command in commands:
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                timeout=3,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if completed.returncode != 0:
            continue
        git_available = True
        for raw in completed.stdout.split(b"\0"):
            if not raw:
                continue
            rel_text = raw.decode("utf-8", errors="ignore")
            if not rel_text or rel_text in seen:
                continue
            seen.add(rel_text)
            rel = Path(rel_text)
            path = root / rel
            if not path.is_file() or not _is_visible_project_file(rel) or not _is_countable_text_file(path):
                continue
            entries.append((rel, path))
    return entries if git_available else None


def _iter_project_text_files(root: Path):
    git_entries = _iter_git_project_text_files(root)
    if git_entries is not None:
        yield from git_entries
        return

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        try:
            rel_dir = current.relative_to(root)
        except ValueError:
            continue
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not _scan_skip_parts(rel_dir / dirname)
            and dirname not in _PROJECT_SCAN_SKIP_DIRS
            and not (dirname.startswith(".") and dirname not in {".github"})
        ]
        for filename in filenames:
            path = current / filename
            if not _is_countable_text_file(path):
                continue
            try:
                rel = path.relative_to(root)
            except ValueError:
                continue
            if not _is_visible_project_file(rel):
                continue
            yield rel, path


def _extract_compose_services(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    services: list[str] = []
    in_services = False
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line == "services:":
            in_services = True
            continue
        if in_services and line and not line.startswith(" ") and re.match(r"^[A-Za-z0-9_-]+:", line):
            break
        if in_services:
            match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
            if match:
                services.append(match.group(1))
    return services


def _build_project_management_overview() -> dict[str, Any]:
    cache = current_app.extensions.setdefault("backend_info_project_management", {})
    cached = cache.get("overview")
    if cached:
        return cached

    root = _resolve_repo_root()
    section_rows = {
        section["key"]: {
            "key": section["key"],
            "label": section["label"],
            "description": section["description"],
            "files": 0,
            "size_kib": 0,
        }
        for section in _PROJECT_SECTIONS
    }
    section_rows["other"] = {
        "key": "other",
        "label": "Weitere Repo-Bereiche",
        "description": "Kleinere Hilfsdateien, lokale Projektkonfiguration und nicht klassifizierte Artefakte.",
        "files": 0,
        "size_kib": 0,
    }
    test_suite_rows: dict[str, dict[str, Any]] = {}

    total_files = 0
    total_size_kib = 0
    test_files = 0
    test_size_kib = 0
    for rel, path in _iter_project_text_files(root):
        size_kib = _file_size_kib(path)
        section = section_rows[_project_section_for(rel)]
        section["files"] += 1
        section["size_kib"] += size_kib
        total_files += 1
        total_size_kib += size_kib

        is_test_file = path.name.startswith("test_") or path.name.endswith("_test.py")
        if is_test_file:
            suite_label = _test_suite_for(rel)
            suite = test_suite_rows.setdefault(
                suite_label,
                {"label": suite_label, "files": 0, "size_kib": 0},
            )
            suite["files"] += 1
            suite["size_kib"] += size_kib
            test_files += 1
            test_size_kib += size_kib

    for row in section_rows.values():
        row["share"] = round((row["size_kib"] / total_size_kib * 100), 1) if total_size_kib else 0.0
    sections = sorted(section_rows.values(), key=lambda row: row["size_kib"], reverse=True)
    test_suites = sorted(test_suite_rows.values(), key=lambda row: row["files"], reverse=True)

    adr_dir = root / "docs" / "ADR"
    adr_files = sorted(adr_dir.rglob("*.md")) if adr_dir.is_dir() else []
    compose_files = [root / "docker-compose.yml", root / "docker-compose.langfuse.yml"]
    compose_services = {
        compose.name: _extract_compose_services(compose)
        for compose in compose_files
        if compose.is_file()
    }
    overview = {
        "root": str(root),
        "totals": {
            "files": total_files,
            "size_kib": total_size_kib,
            "test_files": test_files,
            "test_size_kib": test_size_kib,
            "adr_files": len(adr_files),
            "compose_services": sum(len(items) for items in compose_services.values()),
        },
        "sections": sections,
        "test_suites": test_suites,
        "compose_services": compose_services,
        "key_adrs": [
            {
                **adr,
                "exists": (root / adr["path"]).is_file(),
            }
            for adr in _KEY_ADR_SUMMARIES
        ],
    }
    cache["overview"] = overview
    return overview


def _build_info_api_catalog() -> dict[str, Any] | None:
    """Build the shared API catalog once per request for the informational pages."""
    if hasattr(g, "_backend_info_api_catalog"):
        return g._backend_info_api_catalog
    path = _resolve_openapi_yaml_path()
    if path is None:
        g._backend_info_api_catalog = None
        return None
    rules = tuple(current_app.url_map.iter_rules())
    cache_key = (
        str(path),
        path.stat().st_mtime_ns,
        len(rules),
        len(current_app.view_functions),
        current_app.config.get("RATELIMIT_DEFAULT", "100 per minute"),
    )
    cache = current_app.extensions.setdefault("backend_info_api_catalog", {})
    cached = cache.get("entry")
    if cached and cached.get("key") == cache_key:
        g._backend_info_api_catalog = cached.get("catalog")
        return g._backend_info_api_catalog
    try:
        catalog = build_api_catalog(
            path,
            rules,
            current_app.view_functions,
            default_rate_limit=current_app.config.get("RATELIMIT_DEFAULT", "100 per minute"),
        )
    except Exception as exc:  # pragma: no cover - defensive; drift tests cover the spec itself.
        current_app.logger.warning("Backend info API catalog unavailable: %s", exc)
        catalog = None
    cache["entry"] = {"key": cache_key, "catalog": catalog}
    g._backend_info_api_catalog = catalog
    return catalog


def _catalog_stats_summary(catalog: dict[str, Any] | None) -> dict[str, Any]:
    stats = catalog.get("stats", {}) if catalog else {}
    method_counts = stats.get("methods") if isinstance(stats.get("methods"), dict) else {}
    method_order = ("GET", "POST", "PUT", "PATCH", "DELETE")
    methods = [
        {"method": method, "count": int(method_counts.get(method, 0))}
        for method in method_order
        if method_counts.get(method, 0)
    ]
    tags = catalog.get("tags", []) if catalog else []
    top_tags = sorted(
        [tag for tag in tags if isinstance(tag, dict)],
        key=lambda tag: int(tag.get("count") or 0),
        reverse=True,
    )[:6]
    return {
        "available": bool(catalog),
        "stats": {
            "endpoints": int(stats.get("endpoints") or 0),
            "implemented": int(stats.get("implemented") or 0),
            "tags": int(stats.get("tags") or 0),
            "public": int(stats.get("public") or 0),
            "protected": int(stats.get("protected") or 0),
        },
        "methods": methods,
        "top_tags": top_tags,
        "examples": _SUMMARY_EXAMPLES,
    }


def _build_limit_inventory_snapshot() -> dict[str, Any]:
    catalog = _build_info_api_catalog()
    route_summary = summarize_route_limit_inventory(catalog.get("endpoints", []) if catalog else [])
    from ai_stack.mcp.mcp_canonical_surface import CANONICAL_MCP_TOOL_DESCRIPTORS

    mcp_tools = build_mcp_tool_limit_inventory(CANONICAL_MCP_TOOL_DESCRIPTORS)
    suite_counts: dict[str, int] = {}
    for tool in mcp_tools:
        suite = tool.get("suite") or "unknown"
        suite_counts[suite] = suite_counts.get(suite, 0) + 1
    mcp_stats = {
        "tools": len(mcp_tools),
        "suites": suite_counts,
    }
    return {
        **route_summary,
        "mcp_dispatch": mcp_dispatch_rate_limit_metadata(),
        "mcp_tools": mcp_tools,
        "mcp_stats": mcp_stats,
        "production_tuning": rate_limit_production_tuning_metadata(
            route_summary.get("route_stats"),
            mcp_stats,
        ),
    }


class BackendLimitInventory:
    """Lazy view model for route/tool rate-limit inventory snippets."""

    def _snapshot(self) -> dict[str, Any]:
        if hasattr(g, "_backend_limit_inventory_snapshot"):
            return g._backend_limit_inventory_snapshot
        g._backend_limit_inventory_snapshot = _build_limit_inventory_snapshot()
        return g._backend_limit_inventory_snapshot

    @property
    def route_stats(self) -> dict[str, Any]:
        return self._snapshot()["route_stats"]

    @property
    def top_limits(self) -> list[dict[str, Any]]:
        return self._snapshot()["top_limits"]

    @property
    def route_examples(self) -> list[dict[str, Any]]:
        return self._snapshot()["route_examples"]

    @property
    def auth_routes(self) -> list[dict[str, Any]]:
        return self._snapshot()["auth_routes"]

    @property
    def mcp_dispatch(self) -> dict[str, Any]:
        return self._snapshot()["mcp_dispatch"]

    @property
    def mcp_tools(self) -> list[dict[str, Any]]:
        return self._snapshot()["mcp_tools"]

    @property
    def mcp_stats(self) -> dict[str, Any]:
        return self._snapshot()["mcp_stats"]

    @property
    def production_tuning(self) -> dict[str, Any]:
        return self._snapshot()["production_tuning"]


class BackendInfoSummary:
    """Lazy view model for shared backend info snippets."""

    @property
    def examples(self) -> list[dict[str, str]]:
        return _SUMMARY_EXAMPLES

    def _snapshot(self) -> dict[str, Any]:
        if hasattr(g, "_backend_info_summary_snapshot"):
            return g._backend_info_summary_snapshot
        g._backend_info_summary_snapshot = _catalog_stats_summary(_build_info_api_catalog())
        return g._backend_info_summary_snapshot

    @property
    def available(self) -> bool:
        return bool(self._snapshot()["available"])

    @property
    def stats(self) -> dict[str, int]:
        return self._snapshot()["stats"]

    @property
    def methods(self) -> list[dict[str, int]]:
        return self._snapshot()["methods"]

    @property
    def top_tags(self) -> list[dict[str, Any]]:
        return self._snapshot()["top_tags"]


@info_bp.context_processor
def _info_context():
    cfg = current_app.config
    frontend = (cfg.get("FRONTEND_URL") or "").strip().rstrip("/") or None
    configured_admin_tool = (cfg.get("ADMINISTRATION_TOOL_URL") or "").strip().rstrip("/") or None
    admin_tool = configured_admin_tool or "http://localhost:5001"
    play_public = (cfg.get("PLAY_SERVICE_PUBLIC_URL") or "").strip().rstrip("/") or None
    play_internal = (cfg.get("PLAY_SERVICE_INTERNAL_URL") or "").strip().rstrip("/") or None
    configured_langfuse_ui = (
        os.environ.get("LANGFUSE_UI_URL")
        or os.environ.get("LANGFUSE_MCP_BASE_URL")
        or os.environ.get("NEXTAUTH_URL")
        or ""
    ).strip().rstrip("/")
    langfuse_web_port = (os.environ.get("LANGFUSE_WEB_PORT") or "3000").strip() or "3000"
    langfuse_ui = configured_langfuse_ui or f"http://localhost:{langfuse_web_port}"
    docs = (cfg.get("DOCS_SITE_URL") or "").strip().rstrip("/") or None
    return {
        "frontend_url": frontend,
        "admin_tool_url": admin_tool,
        "admin_tool_configured": bool(configured_admin_tool),
        "langfuse_ui_url": langfuse_ui,
        "langfuse_ui_configured": bool(configured_langfuse_ui),
        "play_service_public_url": play_public,
        "play_service_internal_url": play_internal,
        "docs_site_url": docs,
        "backend_info_summary": BackendInfoSummary(),
        "backend_limit_inventory": BackendLimitInventory(),
        "nav_items": [
            (url_for("info.backend_home"), "Home"),
            (url_for("info.api_overview"), "API"),
            (url_for("info.api_explorer"), "API Explorer"),
            (url_for("info.project_management"), "Projekt"),
            (url_for("info.data_model"), "Datenmodell"),
            (url_for("info.runtime_algorithms"), "Algorithmen"),
            (url_for("info.runtime_path"), "Runtime"),
            (url_for("info.engine_integration"), "Engine"),
            (url_for("info.ai_integration"), "AI"),
            (url_for("info.observability_evidence"), "Observability"),
            (url_for("info.mcp_integration"), "MCP"),
            (url_for("info.security_features"), "Security"),
            (url_for("info.auth_security"), "Auth"),
            (url_for("info.operations_health"), "Ops"),
        ],
    }


@info_bp.route("/", strict_slashes=False)
def backend_home():
    return render_template("home.html")


@info_bp.route("/api", strict_slashes=False)
def api_overview():
    return render_template("api.html")


@info_bp.route("/openapi.yaml", strict_slashes=False)
def openapi_spec():
    """Serve the repo OpenAPI document (same inventory as drift-checked spec)."""
    path = _resolve_openapi_yaml_path()
    if path is None:
        abort(404)
    return send_file(path, mimetype="application/yaml")


@info_bp.route("/api-explorer", strict_slashes=False)
def api_explorer():
    catalog = _build_info_api_catalog()
    return render_template("api_explorer.html", catalog=catalog)


@info_bp.route("/api-explorer/catalog.json", strict_slashes=False)
def api_explorer_catalog():
    path = _resolve_openapi_yaml_path()
    if path is None:
        abort(404)
    catalog = build_api_catalog(
        path,
        current_app.url_map.iter_rules(),
        current_app.view_functions,
        default_rate_limit=current_app.config.get("RATELIMIT_DEFAULT", "100 per minute"),
    )
    return jsonify(catalog)


@info_bp.route("/project-management", strict_slashes=False)
def project_management():
    return render_template(
        "project_management.html",
        project_overview=_build_project_management_overview(),
    )


@info_bp.route("/data-model", strict_slashes=False)
def data_model():
    return render_template("data_model.html")


@info_bp.route("/algorithms", strict_slashes=False)
def runtime_algorithms():
    return render_template("algorithms.html")


@info_bp.route("/engine", strict_slashes=False)
def engine_integration():
    return render_template("engine.html")


@info_bp.route("/runtime", strict_slashes=False)
def runtime_path():
    return render_template("runtime.html")


@info_bp.route("/ai", strict_slashes=False)
def ai_integration():
    return render_template("ai.html")


@info_bp.route("/observability", strict_slashes=False)
def observability_evidence():
    return render_template("observability.html")


@info_bp.route("/mcp", strict_slashes=False)
def mcp_integration():
    return render_template("mcp.html")


@info_bp.route("/security-features", strict_slashes=False)
def security_features():
    return render_template("security_features.html")


@info_bp.route("/auth", strict_slashes=False)
def auth_security():
    return render_template("auth.html")


@info_bp.route("/ops", strict_slashes=False)
def operations_health():
    return render_template("ops.html")
