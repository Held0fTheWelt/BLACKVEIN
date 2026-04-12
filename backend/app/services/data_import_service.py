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

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError, InvalidRequestError
from sqlalchemy.sql.schema import Column, Table

from app.extensions import db
from app.services.data_import_types import ImportIssue, ImportPreflightResult  # noqa: F401
from app.services.data_import_preflight import run_preflight_validate_payload as _run_preflight_validate_payload_impl


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
        # Skip columns that are explicitly autoincrement (not 'auto' string value)
        if col.autoincrement is True:
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
            # Invalid datetime string: return None to avoid DB errors
            # This allows import to proceed with NULL for invalid dates
            return None
    return value


def preflight_validate_payload(payload: Dict[str, Any]) -> ImportPreflightResult:
    """Validate structure and compatibility of a payload without writing to DB."""
    return _run_preflight_validate_payload_impl(
        payload,
        get_schema_revision=_get_schema_revision,
        get_table=_get_table,
        required_columns=_required_columns,
    )


def _prepare_insert_rows(table: Table, rows: List[Any]) -> List[Dict[str, Any]]:
    insert_rows: List[Dict[str, Any]] = []
    for row in rows:
        assert isinstance(row, dict)
        prepared: Dict[str, Any] = {}
        for col in table.columns:
            if col.name in row:
                prepared[col.name] = _parse_datetime_if_needed(col, row[col.name])
        insert_rows.append(prepared)
    return insert_rows


def _execute_inserts_for_all_tables(tables_data: Dict[str, Any]) -> None:
    for table_name, rows in tables_data.items():
        table = _get_table(table_name)
        if table is None or not isinstance(rows, list) or not rows:
            continue
        db.session.execute(table.insert(), _prepare_insert_rows(table, rows))


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
        try:
            with db.session.begin():
                _execute_inserts_for_all_tables(tables_data)
        except InvalidRequestError as e:
            if "transaction is already begun" in str(e).lower():
                savepoint = db.session.begin_nested()
                try:
                    _execute_inserts_for_all_tables(tables_data)
                    savepoint.commit()
                except Exception:
                    savepoint.rollback()
                    raise
            else:
                raise
    except SQLAlchemyError as exc:  # pragma: no cover - DB-level errors are rare and environment-specific
        db.session.rollback()
        raise ImportError(f"Database error during import: {exc}") from exc

    return pre

