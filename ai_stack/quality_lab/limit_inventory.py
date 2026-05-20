"""Central rate-limit inventory helpers for HTTP routes and MCP tools."""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Any, Iterable

API_DEFAULT_RATE_LIMIT = "100 per minute"
API_RATE_LIMIT_KEY_DESCRIPTION = "JWT identity when available; otherwise remote address"
API_CUSTOM_KEY_DESCRIPTION = "custom route key_func"
MCP_RATE_LIMIT_MAX_CALLS = 30
MCP_RATE_LIMIT_WINDOW_SECONDS = 60
MCP_RATE_LIMIT_PERIOD = "minute"
MCP_RATE_LIMIT_LABEL = f"{MCP_RATE_LIMIT_MAX_CALLS} per {MCP_RATE_LIMIT_PERIOD}"
MCP_RATE_LIMIT_KEY_DESCRIPTION = "hashed bearer/service token, or stdio:local when no token is configured"
MCP_RATE_LIMIT_ADR = "ADR-0028"
RATE_LIMIT_TELEMETRY_STATUS = "inventory_only"
RATE_LIMIT_TELEMETRY_STATUS_LABEL = (
    "Route/tool coverage is visible; production 429/MCP hit telemetry is not claimed yet."
)

RATE_LIMIT_PRODUCTION_TELEMETRY_SIGNALS = (
    {
        "metric": "rate_limit_requests_total",
        "source": "HTTP route and MCP dispatch observations",
        "purpose": "Baseline request/tool-call volume before changing quotas.",
        "privacy": "Route, method, auth kind, and tool labels only.",
    },
    {
        "metric": "rate_limit_hits_total",
        "source": "HTTP 429 handler and MCP RateLimitedError",
        "purpose": "Count blocked calls by route/tool, limit source, and environment.",
        "privacy": "Use hashed limiter key buckets; never raw tokens or cookies.",
    },
    {
        "metric": "rate_limit_quota_utilization_ratio",
        "source": "Limiter backend or edge/gateway counters",
        "purpose": "Find hot routes before users hit hard blocks.",
        "privacy": "Aggregate by route/tool class and deployment tier.",
    },
    {
        "metric": "rate_limit_retry_after_seconds",
        "source": "HTTP response headers and MCP error metadata",
        "purpose": "Tune client backoff and operator alerts.",
        "privacy": "No request body, prompt, email address, or bearer value.",
    },
    {
        "metric": "edge_throttle_events_total",
        "source": "CDN/WAF/API gateway",
        "purpose": "Separate app limiter pressure from perimeter throttling.",
        "privacy": "Provider event id plus coarse rule/category labels.",
    },
)

RATE_LIMIT_PRODUCTION_TUNING_WORKFLOW = (
    {
        "step": "Baseline",
        "description": "Collect at least 7 days of production or staging traffic before changing route/tool limits.",
    },
    {
        "step": "Segment",
        "description": "Separate public reads, auth flows, admin writes, service-token traffic, and MCP tool calls.",
    },
    {
        "step": "Shadow-Tuning",
        "description": "Evaluate proposed limits against telemetry without blocking additional traffic first.",
    },
    {
        "step": "Canary",
        "description": "Roll out stricter or looser limits to one tier/tenant/client class before global enforcement.",
    },
    {
        "step": "Review",
        "description": "Update the inventory, ADR notes, alerts, and rollback threshold with every production tuning change.",
    },
)

RATE_LIMIT_TELEMETRY_PRIVACY_RULES = (
    "Store only hashed limiter key values; never raw bearer tokens, cookies, IP addresses, or email addresses.",
    "Do not record request bodies, prompts, passwords, reset tokens, or provider credentials in rate-limit events.",
    "Keep local/dev telemetry labeled as local evidence; do not use it as production tuning proof.",
    "Treat CDN/WAF counters as perimeter evidence and app/MCP counters as application evidence.",
)

_LIMIT_LITERAL_RE = re.compile(r"(?P<count>\d+)\s*(?:per|/)\s*(?P<period>[A-Za-z]+)s?")
_LIMITER_LITERAL_RE = re.compile(r"@limiter\.limit\(\s*(?P<quote>[\"'])(?P<limit>.+?)(?P=quote)")
_ADMIN_SECURITY_LIMIT_RE = re.compile(r"rate_limit\s*=\s*(?P<quote>[\"'])(?P<limit>.+?)(?P=quote)")
_PERIOD_SECONDS = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
}


@dataclass(frozen=True)
class LimitLayer:
    """One rate-limit layer discovered for a route or tool."""

    limit: str
    source: str
    key: str
    max_calls: int | None = None
    period: str | None = None
    window_seconds: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "limit": self.limit,
            "source": self.source,
            "key": self.key,
            "max_calls": self.max_calls,
            "period": self.period,
            "window_seconds": self.window_seconds,
        }


def normalize_rate_limit_label(raw: str | None) -> str:
    """Normalize common Flask-Limiter/admin-security limit spellings."""
    text = (raw or "").strip()
    if not text:
        return ""
    match = _LIMIT_LITERAL_RE.search(text)
    if not match:
        return text
    count = match.group("count")
    period = match.group("period").lower().rstrip("s")
    return f"{count} per {period}"


def parse_rate_limit_label(raw: str | None) -> dict[str, Any]:
    """Return structured fields for a rate-limit label when it is parseable."""
    label = normalize_rate_limit_label(raw)
    match = _LIMIT_LITERAL_RE.search(label)
    if not match:
        return {"limit": label, "max_calls": None, "period": None, "window_seconds": None}
    count = int(match.group("count"))
    period = match.group("period").lower().rstrip("s")
    return {
        "limit": f"{count} per {period}",
        "max_calls": count,
        "period": period,
        "window_seconds": _PERIOD_SECONDS.get(period),
    }


def _view_source(view: Any) -> str:
    if view is None:
        return ""
    try:
        target = inspect.unwrap(view)
        lines, _start = inspect.getsourcelines(target)
    except (OSError, TypeError):
        return ""
    return "".join(lines)


def _decorator_calls(source: str, prefix: str) -> Iterable[str]:
    lines = source.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith(prefix):
            continue
        call_lines = [stripped]
        balance = stripped.count("(") - stripped.count(")")
        cursor = index + 1
        while balance > 0 and cursor < len(lines):
            chunk = lines[cursor].strip()
            call_lines.append(chunk)
            balance += chunk.count("(") - chunk.count(")")
            cursor += 1
        yield " ".join(call_lines)


def extract_route_limit_layers(view: Any) -> list[LimitLayer]:
    """Extract explicit route limiter and admin-security limit decorators."""
    source = _view_source(view)
    layers: list[LimitLayer] = []
    for call in _decorator_calls(source, "@limiter.limit"):
        match = _LIMITER_LITERAL_RE.search(call)
        if not match:
            continue
        parsed = parse_rate_limit_label(match.group("limit"))
        layers.append(
            LimitLayer(
                limit=parsed["limit"],
                source="route_decorator",
                key=API_CUSTOM_KEY_DESCRIPTION if "key_func" in call else API_RATE_LIMIT_KEY_DESCRIPTION,
                max_calls=parsed["max_calls"],
                period=parsed["period"],
                window_seconds=parsed["window_seconds"],
            )
        )
    for call in _decorator_calls(source, "@admin_security"):
        match = _ADMIN_SECURITY_LIMIT_RE.search(call)
        if not match:
            continue
        parsed = parse_rate_limit_label(match.group("limit"))
        layers.append(
            LimitLayer(
                limit=parsed["limit"],
                source="admin_security_policy",
                key="admin action user id",
                max_calls=parsed["max_calls"],
                period=parsed["period"],
                window_seconds=parsed["window_seconds"],
            )
        )
    return layers


def route_rate_limit_metadata(view: Any, default_limit: str | None = None) -> dict[str, Any]:
    """Build the public rate-limit metadata for one Flask route view."""
    default = normalize_rate_limit_label(default_limit or API_DEFAULT_RATE_LIMIT)
    layers = extract_route_limit_layers(view)
    primary = layers[0] if layers else None
    if primary is None:
        parsed = parse_rate_limit_label(default)
        primary = LimitLayer(
            limit=parsed["limit"],
            source="configured_default",
            key=API_RATE_LIMIT_KEY_DESCRIPTION,
            max_calls=parsed["max_calls"],
            period=parsed["period"],
            window_seconds=parsed["window_seconds"],
        )

    return {
        "limit": primary.limit,
        "source": primary.source,
        "key": primary.key,
        "max_calls": primary.max_calls,
        "period": primary.period,
        "window_seconds": primary.window_seconds,
        "enforced": bool(primary.limit),
        "scope": "http_route",
        "layers": [layer.to_dict() for layer in layers] or [primary.to_dict()],
        "additional_policy_limits": [layer.to_dict() for layer in layers[1:]],
    }


def mcp_dispatch_rate_limit_metadata() -> dict[str, Any]:
    """Return the MCP JSON-RPC dispatch limiter used by every tool call."""
    return {
        "limit": MCP_RATE_LIMIT_LABEL,
        "source": "mcp_json_rpc_dispatch",
        "key": MCP_RATE_LIMIT_KEY_DESCRIPTION,
        "max_calls": MCP_RATE_LIMIT_MAX_CALLS,
        "period": MCP_RATE_LIMIT_PERIOD,
        "window_seconds": MCP_RATE_LIMIT_WINDOW_SECONDS,
        "enforced": True,
        "scope": "mcp_json_rpc_dispatch",
        "adr": MCP_RATE_LIMIT_ADR,
        "applies_to": "all MCP JSON-RPC requests, including tools/list and tools/call",
    }


def mcp_tool_rate_limit_metadata(tool_name: str) -> dict[str, Any]:
    """Return per-tool rate-limit metadata inherited from MCP dispatch."""
    metadata = mcp_dispatch_rate_limit_metadata()
    metadata.update(
        {
            "tool": tool_name,
            "scope": "mcp_tool_via_json_rpc_dispatch",
            "applies_to": f"tools/call for {tool_name}; quota is shared with other MCP requests",
        }
    )
    return metadata


def _value_from_row(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def build_mcp_tool_limit_inventory(tool_rows: Iterable[Any]) -> list[dict[str, Any]]:
    """Attach the central MCP dispatch limiter to every tool row/descriptor."""
    inventory: list[dict[str, Any]] = []
    for row in tool_rows:
        name = str(_value_from_row(row, "name", ""))
        if not name:
            continue
        inventory.append(
            {
                "name": name,
                "suite": str(_value_from_row(row, "mcp_suite", "")),
                "tool_class": str(_value_from_row(row, "tool_class", "")),
                "rate_limit": mcp_tool_rate_limit_metadata(name),
            }
        )
    return inventory


def rate_limit_production_tuning_metadata(
    route_stats: dict[str, Any] | None = None,
    mcp_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the production tuning and telemetry contract for info views."""
    route_stats = route_stats or {}
    mcp_stats = mcp_stats or {}
    return {
        "status": RATE_LIMIT_TELEMETRY_STATUS,
        "status_label": RATE_LIMIT_TELEMETRY_STATUS_LABEL,
        "routes": int(route_stats.get("routes") or 0),
        "tools": int(mcp_stats.get("tools") or 0),
        "signals": [dict(signal) for signal in RATE_LIMIT_PRODUCTION_TELEMETRY_SIGNALS],
        "workflow": [dict(step) for step in RATE_LIMIT_PRODUCTION_TUNING_WORKFLOW],
        "privacy": list(RATE_LIMIT_TELEMETRY_PRIVACY_RULES),
        "readiness_levels": [
            {
                "level": "inventory_only",
                "claim": "API/Auth/MCP limits are visible in catalog and info surfaces.",
                "gate": "Current repository evidence.",
            },
            {
                "level": "instrumented",
                "claim": "429, MCP blocked-call, and edge throttle events are emitted with safe labels.",
                "gate": "Production or staging collector evidence.",
            },
            {
                "level": "tuned",
                "claim": "Limits have been adjusted from observed traffic and false-positive review.",
                "gate": "Baseline, shadow run, canary result, and rollback threshold.",
            },
        ],
    }


def summarize_route_limit_inventory(endpoints: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Summarize route-level limits for backend info pages and tests."""
    rows = list(endpoints)
    source_counts: dict[str, int] = {}
    limit_counts: dict[str, int] = {}
    explicit_route_count = 0
    admin_policy_count = 0
    for endpoint in rows:
        limit = endpoint.get("rate_limit") if isinstance(endpoint.get("rate_limit"), dict) else {}
        source = str(limit.get("source") or "unknown")
        label = str(limit.get("limit") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
        limit_counts[label] = limit_counts.get(label, 0) + 1
        layers = limit.get("layers") if isinstance(limit.get("layers"), list) else []
        if any(isinstance(layer, dict) and layer.get("source") == "route_decorator" for layer in layers):
            explicit_route_count += 1
        if any(isinstance(layer, dict) and layer.get("source") == "admin_security_policy" for layer in layers):
            admin_policy_count += 1

    def sort_key(endpoint: dict[str, Any]) -> tuple[str, str, str]:
        return (str(endpoint.get("tag") or ""), str(endpoint.get("path") or ""), str(endpoint.get("method") or ""))

    auth_routes = sorted(
        [endpoint for endpoint in rows if endpoint.get("tag") == "Auth"],
        key=sort_key,
    )
    preferred_tags = {"Auth", "MCP", "System", "GameBootstrap"}
    route_examples = sorted(
        [endpoint for endpoint in rows if endpoint.get("tag") in preferred_tags],
        key=sort_key,
    )[:12]
    top_limits = sorted(limit_counts.items(), key=lambda item: (-item[1], item[0]))[:8]

    return {
        "route_stats": {
            "routes": len(rows),
            "explicit": explicit_route_count,
            "default": source_counts.get("configured_default", 0),
            "admin_policy": admin_policy_count,
            "sources": source_counts,
        },
        "top_limits": [{"limit": limit, "count": count} for limit, count in top_limits],
        "route_examples": route_examples,
        "auth_routes": auth_routes,
    }
