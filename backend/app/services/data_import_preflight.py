"""Preflight validation phases for structured JSON import payloads (DS-019).

Named steps (:func:`_append_format_and_schema_issues`, table/row checks, PK conflicts) live here;
``data_import_service.preflight_validate_payload`` injects schema/table helpers to avoid cycles.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Type

from sqlalchemy import select
from sqlalchemy.sql.schema import Column, Table

from app.extensions import db
from app.services.data_export_service import EXPORT_FORMAT_VERSION


def _append_format_and_schema_issues(
    issues: List[Any],
    metadata: Dict[str, Any],
    import_issue_cls: Type[Any],
    get_schema_revision: Callable[[], str],
) -> None:
    fmt = metadata.get("format_version")
    if fmt != EXPORT_FORMAT_VERSION:
        issues.append(
            import_issue_cls(
                code="UNSUPPORTED_FORMAT_VERSION",
                message=f"Unsupported format_version {fmt!r}; expected {EXPORT_FORMAT_VERSION}.",
            )
        )

    schema_rev = metadata.get("schema_revision")
    current_schema = get_schema_revision()
    if not schema_rev:
        issues.append(
            import_issue_cls(code="MISSING_SCHEMA_REVISION", message="metadata.schema_revision is required.")
        )
    elif schema_rev != current_schema:
        issues.append(
            import_issue_cls(
                code="SCHEMA_MISMATCH",
                message=f"Payload schema_revision {schema_rev!r} does not match current schema {current_schema!r}. "
                "Use the data-tool to transform this payload before import.",
            )
        )


def _validate_data_tables_section(
    issues: List[Any],
    data: Any,
    metadata: Dict[str, Any],
    import_issue_cls: Type[Any],
    import_preflight_result_cls: Type[Any],
) -> tuple[Optional[Dict[str, Any]], Optional[Any]]:
    """Return ``(tables_data, early_exit)``; ``early_exit`` set when ``data.tables`` is invalid."""
    if not isinstance(data, dict) or not isinstance(data.get("tables"), dict):
        issues.append(
            import_issue_cls(code="INVALID_DATA_SECTION", message="data.tables must be an object mapping table names.")
        )
        return None, import_preflight_result_cls(ok=False, issues=issues, metadata=metadata)
    return data["tables"], None


def _append_table_and_row_issues(
    issues: List[Any],
    tables_data: Dict[str, Any],
    import_issue_cls: Type[Any],
    get_table: Callable[[str], Optional[Table]],
    required_columns: Callable[[Table], List[Column]],
) -> None:
    for table_name, rows in tables_data.items():
        table = get_table(table_name)
        if table is None:
            issues.append(
                import_issue_cls(
                    code="UNKNOWN_TABLE",
                    message=f"Payload references unknown or forbidden table {table_name!r}.",
                    table=table_name,
                )
            )
            continue

        if not isinstance(rows, list):
            issues.append(
                import_issue_cls(
                    code="INVALID_ROWS",
                    message=f"Rows for table {table_name!r} must be a list.",
                    table=table_name,
                )
            )
            continue

        req_cols = required_columns(table)
        req_names = {c.name for c in req_cols}

        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                issues.append(
                    import_issue_cls(
                        code="INVALID_ROW",
                        message=f"Row {idx} in table {table_name!r} is not an object.",
                        table=table_name,
                    )
                )
                continue

            missing = req_names - set(row.keys())
            if missing:
                issues.append(
                    import_issue_cls(
                        code="MISSING_REQUIRED_FIELDS",
                        message=f"Row {idx} in table {table_name!r} is missing required fields: {sorted(missing)}.",
                        table=table_name,
                    )
                )


def _append_primary_key_conflict_issues(
    issues: List[Any],
    tables_data: Dict[str, Any],
    import_issue_cls: Type[Any],
    get_table: Callable[[str], Optional[Table]],
) -> None:
    for table_name, rows in tables_data.items():
        table = get_table(table_name)
        if table is None or not isinstance(rows, list) or not rows:
            continue

        pk_cols = list(table.primary_key.columns)
        if not pk_cols:
            continue

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
                import_issue_cls(
                    code="PRIMARY_KEY_CONFLICT",
                    message=f"Table {table_name!r} has {len(existing)} existing rows with primary keys that "
                    "would collide during import. Import policy is 'fail on conflict'.",
                    table=table_name,
                )
            )


def run_preflight_validate_payload(
    payload: Dict[str, Any],
    *,
    get_schema_revision: Callable[[], str],
    get_table: Callable[[str], Optional[Table]],
    required_columns: Callable[[Table], List[Column]],
) -> Any:
    """Validate structure and compatibility of a payload without writing to DB (implementation)."""
    from app.services.data_import_types import ImportIssue, ImportPreflightResult

    issues: List[Any] = []

    if not isinstance(payload, dict):
        issues.append(ImportIssue(code="INVALID_PAYLOAD", message="Payload must be a JSON object."))
        return ImportPreflightResult(ok=False, issues=issues, metadata={})

    metadata = payload.get("metadata") or {}
    data = payload.get("data") or {}

    if not isinstance(metadata, dict):
        issues.append(ImportIssue(code="MISSING_METADATA", message="Missing or invalid metadata section."))
        return ImportPreflightResult(ok=False, issues=issues, metadata={})

    _append_format_and_schema_issues(issues, metadata, ImportIssue, get_schema_revision)

    tables_data, early = _validate_data_tables_section(issues, data, metadata, ImportIssue, ImportPreflightResult)
    if early is not None:
        return early
    assert tables_data is not None

    _append_table_and_row_issues(issues, tables_data, ImportIssue, get_table, required_columns)
    _append_primary_key_conflict_issues(issues, tables_data, ImportIssue, get_table)

    ok = len(issues) == 0
    return ImportPreflightResult(ok=ok, issues=issues, metadata=metadata)
