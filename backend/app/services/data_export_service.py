"""Structured JSON export of application data with versioned metadata.

This module provides foundation helpers for:
- full database export
- single-table export
- row-level export for a single table

It deliberately does NOT deal with HTTP, files, or permissions. That is handled
by API routes. All functions here return plain Python dicts ready to be dumped
as JSON.
"""
from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Tuple

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import RowMapping
from sqlalchemy.sql.schema import Table

from app.extensions import db

try:
    from app.version import APP_VERSION
except Exception:  # pragma: no cover - fallback if version module missing
    APP_VERSION = "0.0.0"


EXPORT_FORMAT_VERSION = 1


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_schema_revision() -> str:
    """Return current Alembic schema revision (version_num from alembic_version)."""
    try:
        result = db.session.execute(text("SELECT version_num FROM alembic_version"))
        row = result.first()
        return row[0] if row else ""
    except SQLAlchemyError:
        # Tests use db.create_all() without Alembic; in that case, omit schema revision.
        return ""


def _iter_exportable_tables() -> Iterable[Table]:
    """Yield all application tables that should be part of a full export.

    Excludes Alembic's own version table.
    """
    metadata = db.metadata
    for name, table in metadata.tables.items():
        if name == "alembic_version":
            continue
        yield table


def _get_table_by_name(table_name: str) -> Table:
    table = db.metadata.tables.get(table_name)
    if table is None:
        raise ValueError(f"Unknown table: {table_name}")
    if table.name == "alembic_version":
        raise ValueError("Table 'alembic_version' cannot be exported")
    return table


def _serialize_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Convert a SQLAlchemy row mapping into a JSON-serializable dict."""
    out: Dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def _collect_rows(table: Table, where_ids: Iterable[Any] | None = None) -> List[Dict[str, Any]]:
    """Return list of serialized rows for table, optionally filtered by primary key values."""
    stmt = select(table)
    pk_cols = list(table.primary_key.columns)
    if where_ids is not None:
        ids = list(where_ids)
        if len(pk_cols) != 1:
            raise ValueError(f"Row-level export currently supports only single-column PK tables (table={table.name})")
        if not ids:
            return []
        stmt = stmt.where(pk_cols[0].in_(ids))
    result = db.session.execute(stmt)
    rows: List[Dict[str, Any]] = []
    for row in result.mappings():  # type: RowMapping
        rows.append(_serialize_row(row))
    return rows


def _build_metadata(
    scope: Dict[str, Any],
    tables_info: List[Dict[str, Any]],
    data_section: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the metadata section for an export payload."""
    exported_at = _utc_now().isoformat()
    schema_rev = _get_schema_revision()
    host = socket.gethostname() or "unknown"

    # Compute checksum over the data section only, stable JSON encoding
    data_json = json.dumps(data_section, sort_keys=True, separators=(",", ":")).encode("utf-8")
    import hashlib

    checksum = hashlib.sha256(data_json).hexdigest()

    return {
        "format_version": EXPORT_FORMAT_VERSION,
        "application_version": APP_VERSION,
        "schema_revision": schema_rev,
        "exported_at": exported_at,
        "scope": scope,
        "tables": tables_info,
        "generator": {
            "name": "WorldOfShadows Backend",
            "host": host,
        },
        "checksum": {
            "algorithm": "sha256",
            "value": checksum,
        },
    }


def export_full() -> Dict[str, Any]:
    """Export all application tables (excluding alembic_version)."""
    data_tables: Dict[str, List[Dict[str, Any]]] = {}
    tables_meta: List[Dict[str, Any]] = []

    for table in _iter_exportable_tables():
        rows = _collect_rows(table)
        data_tables[table.name] = rows
        tables_meta.append({"name": table.name, "row_count": len(rows)})

    data_section = {"tables": data_tables}
    scope = {"type": "full"}
    metadata = _build_metadata(scope=scope, tables_info=tables_meta, data_section=data_section)
    return {"metadata": metadata, "data": data_section}


def export_table(table_name: str) -> Dict[str, Any]:
    """Export all rows from a single table."""
    table = _get_table_by_name(table_name)
    rows = _collect_rows(table)
    data_tables = {table.name: rows}
    tables_meta = [{"name": table.name, "row_count": len(rows)}]
    data_section = {"tables": data_tables}
    scope = {"type": "table", "table": table.name}
    metadata = _build_metadata(scope=scope, tables_info=tables_meta, data_section=data_section)
    return {"metadata": metadata, "data": data_section}


def export_table_rows(table_name: str, primary_keys: Iterable[Any]) -> Dict[str, Any]:
    """Export selected rows from a single table by primary key values."""
    table = _get_table_by_name(table_name)
    ids = list(primary_keys)
    rows = _collect_rows(table, where_ids=ids)
    data_tables = {table.name: rows}
    tables_meta = [{"name": table.name, "row_count": len(rows)}]
    data_section = {"tables": data_tables}
    scope = {"type": "rows", "table": table.name, "primary_keys": ids}
    metadata = _build_metadata(scope=scope, tables_info=tables_meta, data_section=data_section)
    return {"metadata": metadata, "data": data_section}


def list_exportable_tables() -> List[str]:
    """Return a sorted list of exportable table names for UI/API purposes."""
    names = [t.name for t in _iter_exportable_tables()]
    return sorted(names)

