"""Data-tool CLI for World of Shadows export/import payloads.

Capabilities:
- validate: validate a payload JSON file against basic structure and metadata
- inspect: print metadata summary
- transform: (future) transform old payload versions to current format (currently no-op for supported payloads)

The tool is intentionally backend-agnostic: it does not require a running Flask
app or database. It only operates on JSON files and their metadata.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


SUPPORTED_FORMAT_VERSION = 1


@dataclass
class ToolIssue:
    code: str
    message: str


@dataclass
class ValidationResult:
    ok: bool
    issues: List[ToolIssue]
    metadata: Dict[str, Any]


def load_payload(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"File not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}")


def validate_payload(payload: Dict[str, Any], current_schema: Optional[str] = None) -> ValidationResult:
    issues: List[ToolIssue] = []
    metadata = payload.get("metadata") or {}
    data = payload.get("data") or {}

    if not isinstance(metadata, dict):
        issues.append(ToolIssue(code="MISSING_METADATA", message="Missing or invalid metadata section."))
        return ValidationResult(ok=False, issues=issues, metadata={})

    fmt = metadata.get("format_version")
    if fmt != SUPPORTED_FORMAT_VERSION:
        issues.append(
            ToolIssue(
                code="UNSUPPORTED_FORMAT_VERSION",
                message=f"Unsupported format_version {fmt!r}; expected {SUPPORTED_FORMAT_VERSION}.",
            )
        )

    schema_rev = metadata.get("schema_revision")
    if not schema_rev:
        issues.append(ToolIssue(code="MISSING_SCHEMA_REVISION", message="metadata.schema_revision is required."))
    elif current_schema and schema_rev != current_schema:
        issues.append(
            ToolIssue(
                code="SCHEMA_MISMATCH",
                message=f"Payload schema_revision {schema_rev!r} does not match current schema {current_schema!r}.",
            )
        )

    if not isinstance(data, dict) or not isinstance(data.get("tables"), dict):
        issues.append(
            ToolIssue(code="INVALID_DATA_SECTION", message="data.tables must be an object mapping table names.")
        )

    ok = len(issues) == 0
    return ValidationResult(ok=ok, issues=issues, metadata=metadata)


def cmd_inspect(args: argparse.Namespace) -> None:
    payload = load_payload(Path(args.input))
    result = validate_payload(payload, current_schema=args.current_schema)
    md = result.metadata
    print("Metadata:")
    print(f"  format_version     : {md.get('format_version')}")
    print(f"  application_version: {md.get('application_version')}")
    print(f"  schema_revision    : {md.get('schema_revision')}")
    print(f"  exported_at        : {md.get('exported_at')}")
    scope = md.get("scope") or {}
    print(f"  scope.type         : {scope.get('type')}")
    if scope.get("type") == "table":
        print(f"  scope.table        : {scope.get('table')}")
    if scope.get("type") == "rows":
        print(f"  scope.table        : {scope.get('table')}")
        print(f"  scope.primary_keys : {scope.get('primary_keys')}")
    tables = md.get("tables") or []
    print(f"  tables             : {len(tables)}")
    for t in tables:
        print(f"    - {t.get('name')}: {t.get('row_count')} rows")
    checksum = md.get("checksum") or {}
    if checksum:
        print(f"  checksum           : {checksum.get('algorithm')} {checksum.get('value')}")
    print()
    if result.issues:
        print("Validation issues:")
        for issue in result.issues:
            print(f"  [{issue.code}] {issue.message}")
    else:
        print("Validation: OK")


def cmd_validate(args: argparse.Namespace) -> None:
    payload = load_payload(Path(args.input))
    result = validate_payload(payload, current_schema=args.current_schema)
    if result.issues:
        print("Validation FAILED:")
        for issue in result.issues:
            print(f"  [{issue.code}] {issue.message}")
        sys.exit(1)
    print("Validation OK.")


def cmd_transform(args: argparse.Namespace) -> None:
    payload = load_payload(Path(args.input))
    result = validate_payload(payload, current_schema=args.current_schema)
    if not result.ok:
        print("Cannot transform: validation failed:")
        for issue in result.issues:
            print(f"  [{issue.code}] {issue.message}")
        sys.exit(1)

    md = result.metadata
    fmt = md.get("format_version")
    if fmt != SUPPORTED_FORMAT_VERSION:
        print(
            f"No transformation pipeline is defined for format_version {fmt!r}. "
            f"Supported target format_version is {SUPPORTED_FORMAT_VERSION}."
        )
        sys.exit(1)

    # Currently, there are no historical formats; a supported payload is already in
    # the correct format. We still allow writing it back out as a sanitized copy.
    output_path = Path(args.output)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True, ensure_ascii=False)
    print(f"Payload written without structural changes to {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="World of Shadows data-tool")
    parser.add_argument(
        "--current-schema",
        dest="current_schema",
        metavar="REV",
        help="Optional current schema revision for mismatch detection (e.g. Alembic version_num).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="Inspect metadata and basic validation.")
    p_inspect.add_argument("input", help="Input JSON export file")
    p_inspect.set_defaults(func=cmd_inspect)

    p_validate = sub.add_parser("validate", help="Validate payload only.")
    p_validate.add_argument("input", help="Input JSON export file")
    p_validate.set_defaults(func=cmd_validate)

    p_transform = sub.add_parser("transform", help="Validate and write sanitized/converted payload.")
    p_transform.add_argument("input", help="Input JSON export file")
    p_transform.add_argument("output", help="Output JSON file")
    p_transform.set_defaults(func=cmd_transform)

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

