"""MCP operations cockpit telemetry and diagnostic cases

Revision ID: 041
Revises: 040
Create Date: 2026-04-10

"""
from alembic import op
import sqlalchemy as sa


revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mcp_ops_telemetry",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("record_type", sa.String(length=32), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("rpc_method", sa.String(length=64), nullable=True),
        sa.Column("tool_name", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("suite_name", sa.String(length=40), nullable=False),
        sa.Column("process_suite_hint", sa.String(length=40), nullable=True),
        sa.Column("session_id", sa.String(length=128), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("payload_truncated", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mcp_ops_telemetry_created_at", "mcp_ops_telemetry", ["created_at"])
    op.create_index("ix_mcp_ops_telemetry_event_ts", "mcp_ops_telemetry", ["event_ts"])
    op.create_index("ix_mcp_ops_telemetry_record_type", "mcp_ops_telemetry", ["record_type"])
    op.create_index("ix_mcp_ops_telemetry_trace_id", "mcp_ops_telemetry", ["trace_id"])
    op.create_index("ix_mcp_ops_telemetry_rpc_method", "mcp_ops_telemetry", ["rpc_method"])
    op.create_index("ix_mcp_ops_telemetry_tool_name", "mcp_ops_telemetry", ["tool_name"])
    op.create_index("ix_mcp_ops_telemetry_error_code", "mcp_ops_telemetry", ["error_code"])
    op.create_index("ix_mcp_ops_telemetry_suite_name", "mcp_ops_telemetry", ["suite_name"])
    op.create_index("ix_mcp_ops_telemetry_session_id", "mcp_ops_telemetry", ["session_id"])

    op.create_table(
        "mcp_diagnostic_cases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("dedupe_key", sa.String(length=192), nullable=True),
        sa.Column("case_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("suite_name", sa.String(length=40), nullable=False),
        sa.Column("suite_display_override", sa.String(length=40), nullable=True),
        sa.Column("summary", sa.String(length=512), nullable=False),
        sa.Column("recommended_next_action", sa.String(length=512), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("case_origin", sa.String(length=16), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("tool_name", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index("ix_mcp_diagnostic_cases_public_id", "mcp_diagnostic_cases", ["public_id"])
    op.create_index("ix_mcp_diagnostic_cases_dedupe_key", "mcp_diagnostic_cases", ["dedupe_key"])
    op.create_index("ix_mcp_diagnostic_cases_case_type", "mcp_diagnostic_cases", ["case_type"])
    op.create_index("ix_mcp_diagnostic_cases_status", "mcp_diagnostic_cases", ["status"])
    op.create_index("ix_mcp_diagnostic_cases_suite_name", "mcp_diagnostic_cases", ["suite_name"])
    op.create_index("ix_mcp_diagnostic_cases_trace_id", "mcp_diagnostic_cases", ["trace_id"])


def downgrade():
    op.drop_index("ix_mcp_diagnostic_cases_trace_id", table_name="mcp_diagnostic_cases")
    op.drop_index("ix_mcp_diagnostic_cases_suite_name", table_name="mcp_diagnostic_cases")
    op.drop_index("ix_mcp_diagnostic_cases_status", table_name="mcp_diagnostic_cases")
    op.drop_index("ix_mcp_diagnostic_cases_case_type", table_name="mcp_diagnostic_cases")
    op.drop_index("ix_mcp_diagnostic_cases_dedupe_key", table_name="mcp_diagnostic_cases")
    op.drop_index("ix_mcp_diagnostic_cases_public_id", table_name="mcp_diagnostic_cases")
    op.drop_table("mcp_diagnostic_cases")

    op.drop_index("ix_mcp_ops_telemetry_session_id", table_name="mcp_ops_telemetry")
    op.drop_index("ix_mcp_ops_telemetry_suite_name", table_name="mcp_ops_telemetry")
    op.drop_index("ix_mcp_ops_telemetry_error_code", table_name="mcp_ops_telemetry")
    op.drop_index("ix_mcp_ops_telemetry_tool_name", table_name="mcp_ops_telemetry")
    op.drop_index("ix_mcp_ops_telemetry_rpc_method", table_name="mcp_ops_telemetry")
    op.drop_index("ix_mcp_ops_telemetry_trace_id", table_name="mcp_ops_telemetry")
    op.drop_index("ix_mcp_ops_telemetry_record_type", table_name="mcp_ops_telemetry")
    op.drop_index("ix_mcp_ops_telemetry_event_ts", table_name="mcp_ops_telemetry")
    op.drop_index("ix_mcp_ops_telemetry_created_at", table_name="mcp_ops_telemetry")
    op.drop_table("mcp_ops_telemetry")
