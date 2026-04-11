"""Operator diagnostic cases for MCP (auto rules + manual)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    return datetime.now(timezone.utc)


class McpDiagnosticCase(db.Model):
    __tablename__ = "mcp_diagnostic_cases"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    public_id = db.Column(db.String(36), nullable=False, unique=True, index=True)
    dedupe_key = db.Column(db.String(192), nullable=True, unique=True, index=True)

    case_type = db.Column(db.String(64), nullable=False, index=True)
    severity = db.Column(db.String(16), nullable=False, default="medium")
    status = db.Column(db.String(16), nullable=False, default="open", index=True)

    suite_name = db.Column(db.String(40), nullable=False, index=True)
    suite_display_override = db.Column(db.String(40), nullable=True)

    summary = db.Column(db.String(512), nullable=False)
    recommended_next_action = db.Column(db.String(512), nullable=True)

    first_seen_at = db.Column(db.DateTime(timezone=True), nullable=False)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False)
    occurrence_count = db.Column(db.Integer, nullable=False, default=1)

    case_origin = db.Column(db.String(16), nullable=False, default="auto_rule")
    trace_id = db.Column(db.String(64), nullable=True, index=True)
    tool_name = db.Column(db.String(160), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)
