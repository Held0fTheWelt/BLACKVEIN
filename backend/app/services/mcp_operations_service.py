"""MCP operations cockpit: ingest, projections, diagnostic cases, retention."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from flask import Flask
from sqlalchemy import and_, or_

from app.extensions import db
from app.models.mcp_diagnostic_case import McpDiagnosticCase
from app.models.mcp_ops_telemetry import McpOpsTelemetry
from ai_stack.mcp_canonical_surface import (
    build_compact_mcp_operator_truth,
    canonical_mcp_tool_descriptors_by_name,
    verify_catalog_names_alignment,
)
from ai_stack.mcp_static_catalog import mcp_exposure_counts_by_suite, mcp_suite_registry_rows

INGEST_MAX_BODY_BYTES = 65536
ROW_PAYLOAD_MAX_BYTES = 16384
PRUNE_BATCH_SIZE = 2000
DEFAULT_RETENTION_DAYS = 30

ALLOWED_PAYLOAD_KEYS = frozenset(
    {
        "params_keys",
        "tool_name",
        "method",
        "type",
        "status",
        "error_code",
        "tool_class",
        "authority_source",
        "operating_profile",
        "session_id",
        "error_message",
    }
)


def _retention_days() -> int:
    raw = (os.environ.get("WOS_MCP_TELEMETRY_RETENTION_DAYS") or str(DEFAULT_RETENTION_DAYS)).strip()
    try:
        n = int(raw)
        return max(1, min(n, 365))
    except ValueError:
        return DEFAULT_RETENTION_DAYS


def _parse_process_hint(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).strip().lower()
    if s in ("", "all", "*"):
        return "all"
    return s


def resolve_suite_for_record(tool_name: str | None, wos_mcp_suite: str | None) -> tuple[str, str | None]:
    """Return ``(suite_name, process_suite_hint)`` for one telemetry record."""
    hint = _parse_process_hint(wos_mcp_suite)
    process_display = hint if hint else None
    if tool_name:
        desc = canonical_mcp_tool_descriptors_by_name().get(tool_name)
        if desc:
            return desc.mcp_suite.value, process_display
    return "unknown", process_display


def _truncate_json_payload(data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Keep only allowed keys; enforce max serialized size."""
    slim: dict[str, Any] = {}
    for k, v in data.items():
        if k not in ALLOWED_PAYLOAD_KEYS:
            continue
        if k == "params_keys" and isinstance(v, list):
            slim[k] = [str(x)[:128] for x in v[:50]]
        elif k == "error_message" and v is not None:
            slim[k] = str(v)[:500]
        elif k == "session_id" and v is not None:
            slim[k] = str(v)[:128]
        else:
            slim[k] = v
    raw = json.dumps(slim, default=str)
    if len(raw.encode("utf-8")) <= ROW_PAYLOAD_MAX_BYTES:
        return slim, False
    # Hard truncate
    slim["truncated_note"] = "payload trimmed to size cap"
    while len(json.dumps(slim, default=str).encode("utf-8")) > ROW_PAYLOAD_MAX_BYTES and slim:
        keys = list(slim.keys())
        if not keys:
            break
        del slim[keys[-1]]
    return slim, True


def _parse_event_ts(rec: dict[str, Any]) -> datetime:
    ts = rec.get("timestamp")
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(float(ts), tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            pass
    return datetime.now(timezone.utc)


def _mcp_record_identity_ok(rec: dict[str, Any]) -> tuple[str, str] | None:
    """Return (record_type, trace_id) or None if the record cannot be ingested."""
    rtype = (rec.get("type") or "").strip()
    if rtype not in ("request", "response", "tool_call"):
        return None
    trace_id = (rec.get("trace_id") or "").strip()
    if not trace_id or len(trace_id) > 64:
        return None
    return rtype, trace_id


def _coerce_mcp_record_scalar_fields(
    rec: dict[str, Any], rtype: str, trace_id: str
) -> dict[str, Any | None]:
    """Normalize tool/method/status/duration/error fields (no DB row yet)."""
    wos_suite = rec.get("wos_mcp_suite")
    if wos_suite is not None:
        wos_suite = str(wos_suite).strip()[:40] or None

    tool_name = rec.get("tool_name")
    if tool_name is not None:
        tool_name = str(tool_name).strip()[:160] or None

    method = rec.get("method")
    if method is not None:
        method = str(method).strip()[:64] or None

    status = (rec.get("status") or "").strip()
    if status not in ("success", "error"):
        status = "error" if rec.get("error_code") else "success"

    duration = rec.get("duration_ms")
    try:
        duration_ms = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration_ms = None

    error_code = rec.get("error_code")
    if error_code is not None:
        error_code = str(error_code).strip()[:64] or None

    if rtype == "tool_call" and not tool_name:
        tool_name = None

    suite_name, process_hint = resolve_suite_for_record(tool_name, wos_suite)

    payload_src = {k: rec.get(k) for k in ALLOWED_PAYLOAD_KEYS if k in rec}
    if "params_keys" not in payload_src and rtype == "request":
        pk = rec.get("params_keys")
        if isinstance(pk, list):
            payload_src["params_keys"] = pk
    payload_json, truncated = _truncate_json_payload(payload_src)

    sid = rec.get("session_id")
    if sid is not None:
        sid = str(sid).strip()[:128] or None

    return {
        "event_ts": _parse_event_ts(rec),
        "record_type": rtype,
        "trace_id": trace_id,
        "rpc_method": method,
        "tool_name": tool_name,
        "status": status,
        "duration_ms": duration_ms,
        "error_code": error_code,
        "suite_name": suite_name,
        "process_suite_hint": process_hint,
        "session_id": sid,
        "payload_json": payload_json,
        "payload_truncated": truncated,
    }


def _normalize_record(rec: dict[str, Any]) -> dict[str, Any] | None:
    """Map stderr-shaped record to row fields. Returns None if invalid."""
    ident = _mcp_record_identity_ok(rec)
    if ident is None:
        return None
    rtype, trace_id = ident
    return _coerce_mcp_record_scalar_fields(rec, rtype, trace_id)


def _prune_old_telemetry() -> int:
    """Delete up to PRUNE_BATCH_SIZE rows older than retention. Returns rows deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=_retention_days())
    ids = [
        r[0]
        for r in db.session.query(McpOpsTelemetry.id)
        .filter(McpOpsTelemetry.created_at < cutoff)
        .order_by(McpOpsTelemetry.id.asc())
        .limit(PRUNE_BATCH_SIZE)
        .all()
    ]
    if not ids:
        return 0
    res = McpOpsTelemetry.query.filter(McpOpsTelemetry.id.in_(ids)).delete(synchronize_session=False)
    return int(res or 0)


def _materialize_rules_for_row(row: McpOpsTelemetry) -> None:
    """Synchronous auto-rules (upsert by dedupe_key)."""
    now = datetime.now(timezone.utc)
    if row.record_type == "tool_call" and row.status == "error":
        dedupe = f"failed_tool_call|{row.trace_id}|{row.tool_name or 'none'}"
        summary = f"Tool call failed: {row.tool_name or 'unknown'}"
        rec = "Inspect stderr or Logs for this trace_id; retry after fixing backend or inputs."
        _upsert_auto_case(
            dedupe_key=dedupe,
            case_type="failed_tool_call",
            severity="high",
            suite_name=row.suite_name,
            summary=summary[:512],
            recommended_next_action=rec[:512],
            trace_id=row.trace_id,
            tool_name=row.tool_name,
            now=now,
        )
    if (
        row.record_type == "response"
        and row.status == "error"
        and (row.error_code or "") == "PERMISSION_DENIED"
        and (row.rpc_method or "") == "tools/call"
    ):
        dedupe = f"policy_rejection|{row.trace_id}"
        summary = "tools/call rejected (permission / operating profile)."
        rec = "Check WOS_MCP_OPERATING_PROFILE and tool_class; use a suite-filtered MCP server if intentional."
        _upsert_auto_case(
            dedupe_key=dedupe,
            case_type="policy_rejection",
            severity="medium",
            suite_name=row.suite_name,
            summary=summary[:512],
            recommended_next_action=rec[:512],
            trace_id=row.trace_id,
            tool_name=row.tool_name,
            now=now,
        )


def _upsert_auto_case(
    *,
    dedupe_key: str,
    case_type: str,
    severity: str,
    suite_name: str,
    summary: str,
    recommended_next_action: str,
    trace_id: str | None,
    tool_name: str | None,
    now: datetime,
) -> None:
    existing = McpDiagnosticCase.query.filter_by(dedupe_key=dedupe_key).first()
    if existing:
        existing.last_seen_at = now
        existing.occurrence_count = int(existing.occurrence_count or 1) + 1
        return
    c = McpDiagnosticCase(
        public_id=str(uuid.uuid4()),
        dedupe_key=dedupe_key,
        case_type=case_type,
        severity=severity,
        status="open",
        suite_name=suite_name,
        summary=summary,
        recommended_next_action=recommended_next_action,
        first_seen_at=now,
        last_seen_at=now,
        occurrence_count=1,
        case_origin="auto_rule",
        trace_id=trace_id,
        tool_name=tool_name,
    )
    db.session.add(c)


def ingest_telemetry_batch(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Persist normalized records and run auto-rules. Caller must commit or use this inside a transaction.
    """
    accepted = 0
    errors: list[str] = []
    _prune_old_telemetry()
    for raw in records:
        if not isinstance(raw, dict):
            errors.append("non-object record skipped")
            continue
        norm = _normalize_record(raw)
        if not norm:
            errors.append("invalid record skipped")
            continue
        row = McpOpsTelemetry(**norm)
        db.session.add(row)
        db.session.flush()
        _materialize_rules_for_row(row)
        accepted += 1
    return {"accepted": accepted, "errors": errors}


def rebuild_automatic_cases(*, since_days: int = 30) -> dict[str, Any]:
    """Delete auto_rule cases and re-materialize from telemetry window."""
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(since_days, 90)))
    McpDiagnosticCase.query.filter(McpDiagnosticCase.case_origin == "auto_rule").delete(
        synchronize_session=False
    )
    rows = (
        McpOpsTelemetry.query.filter(McpOpsTelemetry.event_ts >= since)
        .order_by(McpOpsTelemetry.id.asc())
        .all()
    )
    for row in rows:
        _materialize_rules_for_row(row)
    return {"deleted_auto_cases": True, "rows_scanned": len(rows), "since_days": since_days}


def _log_level(row: McpOpsTelemetry) -> str:
    if row.status == "error" or row.error_code:
        return "error"
    return "info"


def case_to_dict(c: McpDiagnosticCase) -> dict[str, Any]:
    eff_suite = c.suite_display_override or c.suite_name
    return {
        "case_id": c.public_id,
        "case_type": c.case_type,
        "severity": c.severity,
        "status": c.status,
        "suite_name": c.suite_name,
        "suite_display": eff_suite,
        "suite_display_override": c.suite_display_override,
        "summary": c.summary,
        "recommended_next_action": c.recommended_next_action,
        "first_seen_at": c.first_seen_at.isoformat() if c.first_seen_at else None,
        "last_seen_at": c.last_seen_at.isoformat() if c.last_seen_at else None,
        "occurrence_count": c.occurrence_count,
        "case_origin": c.case_origin,
        "trace_id": c.trace_id,
        "tool_name": c.tool_name,
    }


def activity_row_dict(row: McpOpsTelemetry) -> dict[str, Any]:
    err_msg = ""
    if isinstance(row.payload_json, dict):
        err_msg = str(row.payload_json.get("error_message") or "")[:200]
    return {
        "timestamp": row.event_ts.isoformat() if row.event_ts else None,
        "suite_name": row.suite_name,
        "process_suite_hint": row.process_suite_hint,
        "actor_type": "mcp_client",
        "actor_id": None,
        "operation_type": "tools/call",
        "target_type": "tool",
        "target_name": row.tool_name,
        "correlation_id": row.trace_id,
        "session_id": (row.payload_json or {}).get("session_id") if isinstance(row.payload_json, dict) else None,
        "duration_ms": row.duration_ms,
        "outcome_status": "ok" if row.status == "success" else "error",
        "error_code": row.error_code,
        "error_message": err_msg,
        "telemetry_id": row.id,
    }


def log_row_dict(row: McpOpsTelemetry) -> dict[str, Any]:
    return {
        "id": row.id,
        "timestamp": row.event_ts.isoformat() if row.event_ts else None,
        "log_level": _log_level(row),
        "record_type": row.record_type,
        "method": row.rpc_method,
        "trace_id": row.trace_id,
        "tool_name": row.tool_name,
        "suite_name": row.suite_name,
        "process_suite_hint": row.process_suite_hint,
        "status": row.status,
        "duration_ms": row.duration_ms,
        "error_code": row.error_code,
        "payload_truncated": row.payload_truncated,
        "payload": row.payload_json or {},
    }


def query_activity(
    *,
    page: int,
    limit: int,
    suite: str | None,
    trace_id: str | None,
    errors_only: bool,
) -> tuple[list[dict[str, Any]], int]:
    q = McpOpsTelemetry.query.filter(McpOpsTelemetry.record_type == "tool_call")
    if suite:
        q = q.filter(McpOpsTelemetry.suite_name == suite)
    if trace_id:
        q = q.filter(McpOpsTelemetry.trace_id == trace_id)
    if errors_only:
        q = q.filter(or_(McpOpsTelemetry.status == "error", McpOpsTelemetry.error_code.isnot(None)))
    total = q.count()
    rows = (
        q.order_by(McpOpsTelemetry.event_ts.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return [activity_row_dict(r) for r in rows], total


def query_logs(
    *,
    page: int,
    limit: int,
    log_level: str | None,
    suite: str | None,
    trace_id: str | None,
    session_id: str | None,
    errors_only: bool,
    date_from: str | None,
    date_to: str | None,
) -> tuple[list[dict[str, Any]], int]:
    q = McpOpsTelemetry.query
    if suite:
        q = q.filter(McpOpsTelemetry.suite_name == suite)
    if trace_id:
        q = q.filter(McpOpsTelemetry.trace_id == trace_id)
    if session_id:
        q = q.filter(McpOpsTelemetry.session_id == session_id)
    if errors_only:
        q = q.filter(or_(McpOpsTelemetry.status == "error", McpOpsTelemetry.error_code.isnot(None)))
    if log_level == "error":
        q = q.filter(or_(McpOpsTelemetry.status == "error", McpOpsTelemetry.error_code.isnot(None)))
    elif log_level == "info":
        q = q.filter(
            and_(McpOpsTelemetry.status == "success", McpOpsTelemetry.error_code.is_(None))
        )
    if date_from:
        try:
            df = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            q = q.filter(McpOpsTelemetry.event_ts >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            q = q.filter(McpOpsTelemetry.event_ts <= dt)
        except ValueError:
            pass
    total = q.count()
    rows = (
        q.order_by(McpOpsTelemetry.event_ts.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return [log_row_dict(r) for r in rows], total


def query_diagnostics(*, page: int, limit: int, status: str | None) -> tuple[list[dict[str, Any]], int]:
    q = McpDiagnosticCase.query
    if status:
        q = q.filter(McpDiagnosticCase.status == status)
    total = q.count()
    rows = q.order_by(McpDiagnosticCase.last_seen_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return [case_to_dict(r) for r in rows], total


def get_overview(app: Flask) -> dict[str, Any]:
    registry = mcp_suite_registry_rows()
    exposure = mcp_exposure_counts_by_suite()
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    recent_n = McpOpsTelemetry.query.filter(McpOpsTelemetry.event_ts >= since).count()
    err_n = McpOpsTelemetry.query.filter(
        and_(McpOpsTelemetry.event_ts >= since, or_(McpOpsTelemetry.status == "error", McpOpsTelemetry.error_code.isnot(None)))
    ).count()
    open_cases = McpDiagnosticCase.query.filter(McpDiagnosticCase.status == "open").count()
    last_tools = (
        McpOpsTelemetry.query.filter(McpOpsTelemetry.record_type == "tool_call")
        .order_by(McpOpsTelemetry.event_ts.desc())
        .limit(8)
        .all()
    )
    return {
        "suites": registry,
        "exposure_counts_by_suite": exposure,
        "last_24h": {"telemetry_rows": recent_n, "error_or_code_rows": err_n},
        "open_diagnostic_cases": open_cases,
        "recent_tool_activity": [activity_row_dict(r) for r in last_tools],
        "running_operations": [],
        "retention_days": _retention_days(),
    }


def get_suites_detail() -> dict[str, Any]:
    rows = mcp_suite_registry_rows()
    counts = mcp_exposure_counts_by_suite()
    return {"suites": rows, "counts_by_suite": counts}


def probe_backend_reachable(app: Flask) -> bool | None:
    base = (os.environ.get("BACKEND_PUBLIC_URL") or "").strip().rstrip("/")
    if not base:
        try:
            base = app.config.get("SERVER_NAME")
            # not a URL — skip
        except Exception:
            pass
    if not base or not base.startswith("http"):
        # Try request context self URL not available — default None
        return None
    try:
        r = requests.get(f"{base}/api/v1/health", timeout=2)
        return r.status_code == 200
    except requests.RequestException:
        return False


def action_refresh_catalog(app: Flask) -> dict[str, Any]:
    """Refresh catalog alignment/operator truth projection for cockpit actions."""
    backend_ok = probe_backend_reachable(app)
    align = verify_catalog_names_alignment()
    registry_names = list(canonical_mcp_tool_descriptors_by_name().keys())
    operator_truth = build_compact_mcp_operator_truth(
        backend_reachable=backend_ok,
        catalog_alignment_ok=bool(align.get("aligned")),
        registry_tool_names=registry_names,
    )
    return {
        "catalog_alignment": align,
        "operator_truth": operator_truth,
        "backend_reachable": backend_ok
    }


def action_audit_bundle(*, limit_events: int = 500) -> dict[str, Any]:
    rows = McpOpsTelemetry.query.order_by(McpOpsTelemetry.id.desc()).limit(limit_events).all()
    cases = McpDiagnosticCase.query.order_by(McpDiagnosticCase.id.desc()).limit(200).all()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "telemetry": [log_row_dict(r) for r in reversed(rows)],
        "diagnostic_cases": [case_to_dict(c) for c in cases],
        "suite_registry": mcp_suite_registry_rows(),
    }


def create_manual_case(
    *,
    case_type: str,
    summary: str,
    suite_name: str = "unknown",
    severity: str = "medium",
    recommended_next_action: str | None = None,
) -> McpDiagnosticCase:
    now = datetime.now(timezone.utc)
    c = McpDiagnosticCase(
        public_id=str(uuid.uuid4()),
        dedupe_key=None,
        case_type=case_type[:64],
        severity=severity[:16],
        status="open",
        suite_name=suite_name[:40],
        summary=summary[:512],
        recommended_next_action=(recommended_next_action or "")[:512] or None,
        first_seen_at=now,
        last_seen_at=now,
        occurrence_count=1,
        case_origin="manual",
        trace_id=None,
        tool_name=None,
    )
    db.session.add(c)
    return c


def reclassify_case(
    *,
    public_id: str,
    case_type: str | None = None,
    status: str | None = None,
    suite_display_override: str | None = None,
) -> McpDiagnosticCase | None:
    c = McpDiagnosticCase.query.filter_by(public_id=public_id).first()
    if not c:
        return None
    if case_type is not None:
        t = str(case_type).strip()
        if t:
            c.case_type = t[:64]
    if status is not None:
        st = str(status).strip()
        if st:
            c.status = st[:16]
    if suite_display_override is not None:
        s = suite_display_override.strip()[:40]
        c.suite_display_override = s or None
    c.case_origin = "mixed" if c.case_origin == "auto_rule" else c.case_origin
    c.updated_at = datetime.now(timezone.utc)
    return c
