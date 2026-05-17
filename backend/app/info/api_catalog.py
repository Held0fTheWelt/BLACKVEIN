"""Build a searchable catalog for the backend API explorer."""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any, Iterable

import yaml

from ai_stack.limit_inventory import API_DEFAULT_RATE_LIMIT, route_rate_limit_metadata

_HTTP_METHODS = ("get", "post", "put", "patch", "delete")
_METHOD_ORDER = {method.upper(): idx for idx, method in enumerate(_HTTP_METHODS)}
_FLASK_VAR = re.compile(r"^<(?:(\w+):)?([\w_]+)>$")


def flask_rule_to_openapi_path(rule: str) -> str:
    """Convert a Flask rule to an OpenAPI path template."""
    segments: list[str] = []
    for part in [p for p in rule.split("/") if p]:
        match = _FLASK_VAR.match(part)
        if not match:
            segments.append(part)
            continue
        segments.append("{" + match.group(2) + "}")
    return "/" + "/".join(segments)


def _repo_relative_path(path: str | None) -> str | None:
    if not path:
        return None
    source = Path(path).resolve()
    here = Path(__file__).resolve()
    for root in (here.parents[3], here.parents[2]):
        try:
            return source.relative_to(root).as_posix()
        except ValueError:
            continue
    return source.name


def _first_doc_paragraph(view: Any) -> str:
    doc = inspect.getdoc(view) or ""
    if not doc:
        return ""
    paragraph = doc.split("\n\n", 1)[0]
    paragraph = re.sub(r"\s+", " ", paragraph).strip()
    if len(paragraph) > 280:
        return paragraph[:277].rstrip() + "..."
    return paragraph


def _handler_info(view: Any, flask_endpoint: str, default_rate_limit: str) -> dict[str, Any]:
    handler = flask_endpoint
    source_path = None
    source_line = None
    doc = ""
    if view is not None:
        handler = f"{view.__module__}.{getattr(view, '__name__', flask_endpoint)}"
        source_path = _repo_relative_path(inspect.getsourcefile(view))
        try:
            source_line = inspect.getsourcelines(view)[1]
        except (OSError, TypeError):
            source_line = None
        doc = _first_doc_paragraph(view)
    return {
        "flask_endpoint": flask_endpoint,
        "handler": handler,
        "source_path": source_path,
        "source_line": source_line,
        "doc": doc,
        "rate_limit": route_rate_limit_metadata(view, default_rate_limit),
    }


def _implementation_index(
    url_rules: Iterable[Any],
    view_functions: dict[str, Any],
    default_rate_limit: str,
) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for rule in url_rules:
        rule_str = str(getattr(rule, "rule", ""))
        if not rule_str.startswith("/api/v1"):
            continue
        oa_path = flask_rule_to_openapi_path(rule_str)
        methods = {
            method.upper()
            for method in (getattr(rule, "methods", None) or set())
            if method not in {"HEAD", "OPTIONS"}
        }
        info = _handler_info(view_functions.get(rule.endpoint), str(rule.endpoint), default_rate_limit)
        info["flask_rule"] = rule_str
        for method in methods:
            index[(oa_path, method)] = dict(info)
    return index


def _parameter_type(parameter: dict[str, Any]) -> str:
    schema = parameter.get("schema") if isinstance(parameter.get("schema"), dict) else {}
    return str(schema.get("type") or "value")


def _parameters_for(path_item: dict[str, Any], operation: dict[str, Any]) -> list[dict[str, Any]]:
    merged = []
    for parameter in [*(path_item.get("parameters") or []), *(operation.get("parameters") or [])]:
        if not isinstance(parameter, dict):
            continue
        merged.append(
            {
                "name": str(parameter.get("name") or ""),
                "in": str(parameter.get("in") or ""),
                "required": bool(parameter.get("required")),
                "type": _parameter_type(parameter),
            }
        )
    return merged


def _auth_for(operation: dict[str, Any], default_security: Any) -> dict[str, str]:
    security = operation.get("security", default_security)
    if security == []:
        return {"kind": "public", "label": "Public"}
    return {"kind": "bearer", "label": "Bearer JWT"}


def _curl_example(method: str, path: str, auth_kind: str, has_body: bool) -> str:
    lines = [f'curl -X {method} "http://localhost:5000{path}"', '  -H "Accept: application/json"']
    if auth_kind != "public":
        lines.append('  -H "Authorization: Bearer <access_token>"')
    if has_body or method in {"POST", "PUT", "PATCH"}:
        lines.append('  -H "Content-Type: application/json"')
        lines.append("  -d '{...}'")
    return " \\\n".join(lines)


def _method_label(method: str) -> str:
    return {
        "GET": "Read/List",
        "POST": "Create/Action",
        "PUT": "Replace/Update",
        "PATCH": "Patch",
        "DELETE": "Delete",
    }.get(method, method)


def _search_text(endpoint: dict[str, Any]) -> str:
    parts = [
        endpoint["method"],
        endpoint["path"],
        endpoint["summary"],
        endpoint["tag"],
        endpoint.get("tag_description") or "",
        endpoint.get("handler") or "",
        endpoint.get("flask_endpoint") or "",
        endpoint.get("doc") or "",
        endpoint.get("operation_id") or "",
        endpoint.get("auth", ""),
    ]
    rate_limit = endpoint.get("rate_limit") if isinstance(endpoint.get("rate_limit"), dict) else {}
    parts.extend(
        [
            str(rate_limit.get("limit") or ""),
            str(rate_limit.get("source") or ""),
            str(rate_limit.get("key") or ""),
        ]
    )
    for parameter in endpoint.get("parameters", []):
        parts.extend([parameter.get("name") or "", parameter.get("in") or "", parameter.get("type") or ""])
    return " ".join(parts).lower()


def build_api_catalog(
    openapi_path: Path,
    url_rules: Iterable[Any],
    view_functions: dict[str, Any],
    *,
    default_rate_limit: str = API_DEFAULT_RATE_LIMIT,
) -> dict[str, Any]:
    """Return a JSON-serializable catalog for the implemented Flask API."""
    spec = yaml.safe_load(openapi_path.read_text(encoding="utf-8")) or {}
    tags = spec.get("tags") or []
    tag_descriptions = {
        str(tag.get("name")): str(tag.get("description") or "")
        for tag in tags
        if isinstance(tag, dict) and tag.get("name")
    }
    tag_order = {name: idx for idx, name in enumerate(tag_descriptions)}
    impl_index = _implementation_index(url_rules, view_functions, default_rate_limit)

    endpoints: list[dict[str, Any]] = []
    paths = spec.get("paths") or {}
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method_lower in _HTTP_METHODS:
            operation = path_item.get(method_lower)
            if not isinstance(operation, dict):
                continue
            method = method_lower.upper()
            impl = impl_index.get((path, method), {})
            tag = str((operation.get("tags") or ["Other"])[0])
            parameters = _parameters_for(path_item, operation)
            auth = _auth_for(operation, spec.get("security"))
            responses = operation.get("responses") if isinstance(operation.get("responses"), dict) else {}
            has_body = bool(operation.get("requestBody"))
            endpoint = {
                "id": str(operation.get("operationId") or f"{method.lower()}_{path}"),
                "method": method,
                "method_label": _method_label(method),
                "path": str(path),
                "summary": str(operation.get("summary") or f"{method} {path}"),
                "description": str(operation.get("description") or ""),
                "operation_id": str(operation.get("operationId") or ""),
                "tag": tag,
                "tag_description": tag_descriptions.get(tag, ""),
                "auth": auth["label"],
                "auth_kind": auth["kind"],
                "parameters": parameters,
                "path_parameters": [p for p in parameters if p["in"] == "path"],
                "query_parameters": [p for p in parameters if p["in"] == "query"],
                "responses": sorted(str(code) for code in responses),
                "has_request_body": has_body,
                "request_body_required": bool(
                    isinstance(operation.get("requestBody"), dict)
                    and operation.get("requestBody", {}).get("required")
                ),
                "curl": _curl_example(method, str(path), auth["kind"], has_body),
                "implemented": bool(impl),
                **impl,
            }
            endpoint["search"] = _search_text(endpoint)
            endpoints.append(endpoint)

    endpoints.sort(
        key=lambda item: (
            tag_order.get(item["tag"], 999),
            item["path"],
            _METHOD_ORDER.get(item["method"], 99),
        )
    )

    tag_counts: dict[str, int] = {}
    method_counts: dict[str, int] = {}
    rate_limit_source_counts: dict[str, int] = {}
    public_count = 0
    implemented_count = 0
    for endpoint in endpoints:
        tag_counts[endpoint["tag"]] = tag_counts.get(endpoint["tag"], 0) + 1
        method_counts[endpoint["method"]] = method_counts.get(endpoint["method"], 0) + 1
        rate_limit = endpoint.get("rate_limit") if isinstance(endpoint.get("rate_limit"), dict) else {}
        source = str(rate_limit.get("source") or "unknown")
        rate_limit_source_counts[source] = rate_limit_source_counts.get(source, 0) + 1
        if endpoint["auth_kind"] == "public":
            public_count += 1
        if endpoint["implemented"]:
            implemented_count += 1

    tags_payload = [
        {
            "name": name,
            "description": tag_descriptions.get(name, ""),
            "count": tag_counts.get(name, 0),
        }
        for name in tag_descriptions
        if tag_counts.get(name, 0)
    ]
    for name in sorted(set(tag_counts) - set(tag_descriptions)):
        tags_payload.append({"name": name, "description": "", "count": tag_counts[name]})

    return {
        "openapi": spec.get("openapi"),
        "title": (spec.get("info") or {}).get("title"),
        "version": (spec.get("info") or {}).get("version"),
        "stats": {
            "endpoints": len(endpoints),
            "implemented": implemented_count,
            "tags": len(tags_payload),
            "public": public_count,
            "protected": len(endpoints) - public_count,
            "methods": method_counts,
            "rate_limit_sources": rate_limit_source_counts,
        },
        "tags": tags_payload,
        "endpoints": endpoints,
    }
