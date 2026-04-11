"""Persisted MCP server telemetry (ingested JSON lines) for the operations cockpit."""

from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    return datetime.now(timezone.utc)


class McpOpsTelemetry(db.Model):
    """Append-only row per ingested MCP log record (request / response / tool_call)."""

    __tablename__ = "mcp_ops_telemetry"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, index=True)
    event_ts = db.Column(db.DateTime(timezone=True), nullable=False, index=True)

    record_type = db.Column(db.String(32), nullable=False, index=True)
    trace_id = db.Column(db.String(64), nullable=False, index=True)
    rpc_method = db.Column(db.String(64), nullable=True, index=True)
    tool_name = db.Column(db.String(160), nullable=True, index=True)
    status = db.Column(db.String(16), nullable=False)
    duration_ms = db.Column(db.Float, nullable=True)
    error_code = db.Column(db.String(64), nullable=True, index=True)

    suite_name = db.Column(db.String(40), nullable=False, index=True)
    process_suite_hint = db.Column(db.String(40), nullable=True)
    session_id = db.Column(db.String(128), nullable=True, index=True)

    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    payload_truncated = db.Column(db.Boolean, nullable=False, default=False)
