"""Import and validation for structured JSON export payloads.

This module focuses on:
- payload structure and metadata validation
- schema/version compatibility checks
- dry-run conflict detection (primary key collisions)
- deterministic import execution (all-or-nothing)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Tuple

from sqlalchemy import and_, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.schema import Column, Table

from app.extensions import db
from app.services.data_export_service import EXPORT_FORMAT_VERSION


@dataclass
class ImportIssue:
    code: str
    message: str
    table: Optional[str] = None


@dataclass
class ImportPreflightResult:
    ok: bool
    issues: List[ImportIssue]
    metadata: Dict[str, Any]


class ImportError(Exception):
    """Raised when an import cannot be completed safely."""


def _get_schema_revision() -> str:
    try:
        result = db.session.execute(text("SELECT version_num FROM alembic_version"))
        row = result.first()
        return row[0] if row else ""
    except SQLAlchemyError:
        return ""


def _get_table(name: str) -> Optional[Table]:
    if name == "alembic_version":
        return None
    return db.metadata.tables.get(name)


def _required_columns(table: Table) -> List[Column]:
    required: List[Column] = []
    for col in table.columns:
        if col.autoincrement:
            continue
        if col in table.primary_key.columns and col.autoincrement:
            continue
        if not col.nullable and col.default is None and col.server_default is None:
            required.append(col)
    return required


def _parse_datetime_if_needed(col: Column, value: Any) -> Any:
    if value is None:
        return None
    if col.type.python_type is datetime and isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return value
    return value


def preflight_validate_payload(payload: Dict[str, Any]) -> ImportPreflightResult:
    """Validate structure and compatibility of a payload without writing to DB."""
    issues: List[ImportIssue] = []

    if not isinstance(payload, dict):
        issues.append(ImportIssue(code="INVALID_PAYLOAD", message="Payload must be a JSON object."))
        return ImportPreflightResult(ok=False, issues=issues, metadata={})

    metadata = payload.get("metadata") or {}
    data = payload.get("data") or {}

    if not isinstance(metadata, dict):
        issues.append(ImportIssue(code="MISSING_METADATA", message="Missing or invalid metadata section."))
        return ImportPreflightResult(ok=False, issues=issues, metadata={})

    # Basic metadata fields
    fmt = metadata.get("format_version")
    if fmt != EXPORT_FORMAT_VERSION:
        issues.append(
            ImportIssue(
                code="UNSUPPORTED_FORMAT_VERSION",
                message=f"Unsupported format_version {fmt!r}; expected {EXPORT_FORMAT_VERSION}.",
            )
        )

    schema_rev = metadata.get("schema_revision")
    current_schema = _get_schema_revision()
    if not schema_rev:
        issues.append(
            ImportIssue(code="MISSING_SCHEMA_REVISION", message="metadata.schema_revision is required.")
        )
    elif schema_rev != current_schema:
        issues.append(
            ImportIssue(
                code="SCHEMA_MISMATCH",
                message=f"Payload schema_revision {schema_rev!r} does not match current schema {current_schema!r}. "
                "Use the data-tool to transform this payload before import.",
            )
        )

    if not isinstance(data, dict) or not isinstance(data.get("tables"), dict):
        issues.append(
            ImportIssue(code="INVALID_DATA_SECTION", message="data.tables must be an object mapping table names.")
        )
        return ImportPreflightResult(ok=False, issues=issues, metadata=metadata)

    tables_data: Dict[str, Any] = data["tables"]

    # Validate tables and columns
    for table_name, rows in tables_data.items():
        table = _get_table(table_name)
        if table is None:
            issues.append(
                ImportIssue(
                    code="UNKNOWN_TABLE",
                    message=f"Payload references unknown or forbidden table {table_name!r}.",
                    table=table_name,
                )
            )
            continue

        if not isinstance(rows, list):
            issues.append(
                ImportIssue(
                    code="INVALID_ROWS",
                    message=f"Rows for table {table_name!r} must be a list.",
                    table=table_name,
                )
            )
            continue

        req_cols = _required_columns(table)
        req_names = {c.name for c in req_cols}

        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                issues.append(
                    ImportIssue(
                        code="INVALID_ROW",
                        message=f"Row {idx} in table {table_name!r} is not an object.",
                        table=table_name,
                    )
                )
                continue

            missing = req_names - set(row.keys())
            if missing:
                issues.append(
                    ImportIssue(
                        code="MISSING_REQUIRED_FIELDS",
                        message=f"Row {idx} in table {table_name!r} is missing required fields: {sorted(missing)}.",
                        table=table_name,
                    )
                )

    # Primary key collision detection
    for table_name, rows in tables_data.items():
        table = _get_table(table_name)
        if table is None or not isinstance(rows, list) or not rows:
            continue

        pk_cols = list(table.primary_key.columns)
        if not pk_cols:
            continue

        # We only support single-column PK collision detection for now
        if len(pk_cols) != 1:
            continue
        pk_col = pk_cols[0]
        incoming_ids = [r.get(pk_col.name) for r in rows if isinstance(r, dict) and pk_col.name in r]
        if not incoming_ids:
            continue

        stmt = select(pk_col).where(pk_col.in_(incoming_ids))
        existing = db.session.execute(stmt).scalars().all()
        if existing:
            issues.append(
                ImportIssue(
                    code="PRIMARY_KEY_CONFLICT",
                    message=f"Table {table_name!r} has {len(existing)} existing rows with primary keys that "
                    "would collide during import. Import policy is 'fail on conflict'.",
                    table=table_name,
                )
            )

    ok = len(issues) == 0
    return ImportPreflightResult(ok=ok, issues=issues, metadata=metadata)


def execute_import(payload: Dict[str, Any]) -> ImportPreflightResult:
    """Validate and, if safe, import the payload in a single transaction.

    Raises ImportError if validation fails or on DB errors; the caller should handle
    this and surface appropriate API responses. On success, returns the same
    structure as preflight, with ok=True and issues possibly containing warnings.
    """
    pre = preflight_validate_payload(payload)
    if not pre.ok:
        raise ImportError("Preflight validation failed; see issues for details.")

    data = payload["data"]
    tables_data: Dict[str, Any] = data["tables"]

    try:
        with db.session.begin():
            for table_name, rows in tables_data.items():
                table = _get_table(table_name)
                if table is None or not isinstance(rows, list) or not rows:
                    continue

                insert_rows: List[Dict[str, Any]] = []
                for row in rows:
                    assert isinstance(row, dict)
                    prepared: Dict[str, Any] = {}
                    for col in table.columns:
                        if col.name in row:
                            prepared[col.name] = _parse_datetime_if_needed(col, row[col.name])
                    insert_rows.append(prepared)

                db.session.execute(table.insert(), insert_rows)
    except SQLAlchemyError as exc:  # pragma: no cover - DB-level errors are rare and environment-specific
        db.session.rollback()
        raise ImportError(f"Database error during import: {exc}") from exc

    return pre

