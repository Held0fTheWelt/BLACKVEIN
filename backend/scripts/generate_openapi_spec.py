#!/usr/bin/env python3
"""Generate OpenAPI YAML from registered Flask /api/v1 routes.

Writes:
  - docs/api/openapi.yaml (canonical)
  - docs/backend/openapi.yaml (identical copy for MkDocs static URL /backend/openapi.yaml)

Run from repo root or backend/:
  python backend/scripts/generate_openapi_spec.py --write
  python backend/scripts/generate_openapi_spec.py --check

Requires backend dependencies (Flask app import).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
OUTPUT_PATHS: list[Path] = [
    REPO_ROOT / "docs" / "api" / "openapi.yaml",
    REPO_ROOT / "docs" / "backend" / "openapi.yaml",
]

# Longest prefix wins (specific before general).
_TAG_PREFIXES: list[tuple[str, str]] = [
    ("/api/v1/admin/bootstrap", "OperationalGovernance"),
    ("/api/v1/admin/ai", "OperationalGovernance"),
    ("/api/v1/admin/runtime", "OperationalGovernance"),
    ("/api/v1/admin/settings", "OperationalGovernance"),
    ("/api/v1/admin/costs", "OperationalGovernance"),
    ("/api/v1/admin/audit/governance", "OperationalGovernance"),
    ("/api/v1/admin/ai-stack", "AIStackGovernance"),
    ("/api/v1/admin/mcp", "MCP"),
    ("/api/v1/admin/analytics", "Analytics"),
    ("/api/v1/admin/play-service-control", "GameBootstrap"),
    ("/api/v1/admin/world-engine", "WorldEngineConsole"),
    ("/api/v1/admin/system-diagnosis", "System"),
    ("/api/v1/admin", "Admin"),
    ("/api/v1/auth", "Auth"),
    ("/api/v1/data", "Admin"),
    ("/api/v1/feature-areas", "Areas"),
    ("/api/v1/areas", "Areas"),
    ("/api/v1/forum", "Forum"),
    ("/api/v1/notifications", "Forum"),
    ("/api/v1/game-admin", "GameAdmin"),
    ("/api/v1/game-content", "GameBootstrap"),
    ("/api/v1/game", "GameBootstrap"),
    ("/api/v1/improvement", "Improvement"),
    ("/api/v1/languages", "SiteContent"),
    ("/api/v1/news", "SiteContent"),
    ("/api/v1/operator/mcp-telemetry", "MCP"),
    ("/api/v1/player", "GameBootstrap"),
    ("/api/v1/roles", "Roles"),
    ("/api/v1/sessions", "SessionsBridge"),
    ("/api/v1/site", "SiteContent"),
    ("/api/v1/slogans", "SiteContent"),
    ("/api/v1/users", "Users"),
    ("/api/v1/wiki-admin", "SiteContent"),
    ("/api/v1/wiki", "SiteContent"),
    ("/api/v1/writers-room", "WritersRoom"),
    ("/api/v1/health", "System"),
    ("/api/v1/test", "System"),
    ("/api/v1/bootstrap/public-status", "OperationalGovernance"),
    ("/api/v1/internal/runtime-config", "OperationalGovernance"),
    ("/api/v1/internal/provider-credential", "OperationalGovernance"),
]

_TAG_DESCRIPTIONS: dict[str, str] = {
    "Auth": "JWT issuance, registration, password flows.",
    "Users": "User profiles, preferences, bans, bookmarks.",
    "Roles": "Role CRUD for authorized admin clients.",
    "Forum": "Categories, threads, posts, moderation, search, tags, notifications.",
    "SiteContent": "News, wiki, site settings, slogans, languages.",
    "GameBootstrap": "Characters, runs, tickets, save slots, templates, play-service bridge.",
    "GameAdmin": "Published experiences governance and runtime admin views.",
    "SessionsBridge": "In-process session bridge for operators/tests; not authoritative live play.",
    "WritersRoom": "Writers-room review workflow API.",
    "Improvement": "Improvement experiments, recommendations, variants.",
    "Admin": "Admin logs, metrics, moderator assignments, exports/imports.",
    "Analytics": "Admin analytics aggregates and timelines.",
    "AIStackGovernance": "AI stack inspector, evidence, release readiness.",
    "MCP": "MCP operations UI support and operator telemetry ingest.",
    "System": "Health, system diagnosis, internal probes.",
    "WorldEngineConsole": "Admin proxy to the play service: readiness, runs, story sessions, diagnostics.",
    "Areas": "Feature areas and navigational areas CRUD.",
    "OperationalGovernance": "Bootstrap, provider/model/route governance, runtime modes, settings, and cost control plane.",
}

_FLASK_VAR = re.compile(r"^<(?:(\w+):)?([\w_]+)>$")


def _tag_for_path(path: str) -> str:
    for prefix, tag in sorted(_TAG_PREFIXES, key=lambda x: -len(x[0])):
        if path == prefix or path.startswith(prefix + "/"):
            return tag
    raise ValueError(f"No OpenAPI tag mapping for path: {path}")


def flask_rule_to_openapi_path(rule: str) -> tuple[str, list[dict]]:
    """Return OpenAPI path template and path parameters."""
    segments: list[str] = []
    params: list[dict] = []
    parts = [p for p in rule.split("/") if p]
    for part in parts:
        m = _FLASK_VAR.match(part)
        if not m:
            segments.append(part)
            continue
        conv, name = m.group(1) or "string", m.group(2)
        segments.append("{" + name + "}")
        if conv in ("int", "integer"):
            schema: dict = {"type": "integer"}
        else:
            schema = {"type": "string"}
        params.append(
            {
                "name": name,
                "in": "path",
                "required": True,
                "schema": schema,
            }
        )
    return "/" + "/".join(segments), params


def _summary_for(method: str, path: str) -> str:
    tail = path.split("/api/v1/", 1)[-1] if "/api/v1/" in path else path
    return f"{method.upper()} /{tail}"


def _operation_id(method: str, path: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_]+", "_", f"{method}_{path}")
    safe = re.sub(r"_+", "_", safe).strip("_")
    if safe[0].isdigit():
        safe = "op_" + safe
    return safe[:120]


def _security_for(method: str, path: str) -> list | None:
    """Return None for default (global bearer), [] for explicitly public."""
    if path == "/api/v1/health" and method == "get":
        return []
    public_post = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
    }
    if method == "post" and path in public_post:
        return []
    return None


def collect_route_operations():
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))

    from app import create_app
    from app.config import TestingConfig

    app = create_app(TestingConfig)
    # (openapi_path, method_lower) -> merged entry
    operations: dict[tuple[str, str], dict] = {}
    path_params: dict[str, list[dict]] = {}

    for rule in app.url_map.iter_rules():
        rule_str = rule.rule
        if not rule_str.startswith("/api/v1"):
            continue
        methods = {m.lower() for m in (rule.methods or set()) if m not in ("HEAD", "OPTIONS")}
        if not methods:
            continue
        oa_path, params = flask_rule_to_openapi_path(rule_str)
        if oa_path not in path_params:
            path_params[oa_path] = params
        elif params and len(params) > len(path_params[oa_path]):
            path_params[oa_path] = params

        tag = _tag_for_path(rule_str)
        for method in sorted(methods):
            key = (oa_path, method)
            if key in operations:
                raise RuntimeError(f"Duplicate OpenAPI operation: {method.upper()} {oa_path}")
            op: dict = {
                "tags": [tag],
                "summary": _summary_for(method, oa_path),
                "operationId": _operation_id(method, oa_path),
                "responses": {
                    "200": {"description": "Success (see docs/api/REFERENCE.md for response shapes)."},
                    "401": {"description": "Unauthorized — missing or invalid JWT where required."},
                    "403": {"description": "Forbidden — policy or role."},
                    "404": {"description": "Not found."},
                    "429": {"description": "Rate limited."},
                    "500": {"description": "Server error."},
                },
            }
            sec = _security_for(method, oa_path)
            if sec is not None:
                op["security"] = sec
            operations[key] = op

    return operations, path_params


def build_spec() -> dict:
    operations, path_params = collect_route_operations()
    paths: dict = {}
    for (oa_path, method), op in sorted(operations.items(), key=lambda x: (x[0][0], x[0][1])):
        if oa_path not in paths:
            paths[oa_path] = {}
        entry = dict(op)
        params = path_params.get(oa_path) or []
        if params:
            entry["parameters"] = list(params)
        paths[oa_path][method] = entry

    tags = [{"name": name, "description": desc} for name, desc in sorted(_TAG_DESCRIPTIONS.items())]

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "World of Shadows — Backend API",
            "version": "1.0.0",
            "description": (
                "Machine-readable inventory of Flask `/api/v1` routes. "
                "Human-readable request/response examples: `docs/api/REFERENCE.md`. "
                "Tag taxonomy: `docs/api/openapi-taxonomy.md`."
            ),
        },
        "servers": [{"url": "/", "description": "Same origin as backend (set base URL in your client)."}],
        "tags": tags,
        "paths": paths,
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Flask-JWT-Extended access token from `POST /api/v1/auth/login`.",
                }
            }
        },
        "security": [{"BearerAuth": []}],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write docs/api/openapi.yaml")
    parser.add_argument("--check", action="store_true", help="Fail if file differs from generated")
    args = parser.parse_args()
    spec = build_spec()
    text = yaml.dump(
        spec,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    if args.write:
        for out in OUTPUT_PATHS:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            print(f"Wrote {out}")
        return 0
    if args.check:
        for out in OUTPUT_PATHS:
            if not out.is_file():
                print(f"Missing {out}", file=sys.stderr)
                return 1
            existing = out.read_text(encoding="utf-8").replace("\r\n", "\n")
            if existing.rstrip() != text.rstrip():
                print(
                    f"{out} is out of date; run: python backend/scripts/generate_openapi_spec.py --write",
                    file=sys.stderr,
                )
                return 1
        print("openapi.yaml matches Flask routes.")
        return 0
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
