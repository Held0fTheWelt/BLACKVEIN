"""CLI dispatcher for ``python -m tools.mcp_server.diagnostics``.

Subcommands:

* ``opening-quality`` — run the opening-quality probe end-to-end against the
  local launcher; emits classified rows to stdout and a structured JSON
  report under ``tests/reports/MCP_OPENING_QUALITY_PROBE.json``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.mcp_server.diagnostics.opening_quality import (
    DEFAULT_REPORT_PATH,
    Classification,
    OpeningQualityReport,
    run_opening_quality_probe,
)


def _print_human(report: OpeningQualityReport, report_path: Path | None) -> int:
    if not report.rows:
        print("FAIL: no trace_ids selected; nothing to classify.", file=sys.stderr)
        if report_path is not None:
            print(f"(report written to {report_path})", file=sys.stderr)
        return 2

    print(f"selected trace_ids: {report.selected_trace_ids}")
    print(f"generated_at      : {report.generated_at}")
    print()
    print("=== CLASSIFIED ROWS ===")
    overall_ok = True
    for row in report.rows:
        origin_bits = []
        if row.trace_origin:
            origin_bits.append(f"origin={row.trace_origin}")
        if row.execution_tier:
            origin_bits.append(f"tier={row.execution_tier}")
        if row.final_adapter:
            origin_bits.append(f"final_adapter={row.final_adapter}")
        suffix = f" ({', '.join(origin_bits)})" if origin_bits else ""
        print(
            f"- {row.trace_id} [{row.trace_name}] -> {row.classification.value}"
            f" (is_opening={row.is_opening_trace}){suffix}"
        )
        if row.fallback_reason:
            print(f"    fallback_reason   : {row.fallback_reason}")
        if row.degradation_chain:
            print(f"    degradation_chain : {row.degradation_chain}")
        for note in row.notes:
            print(f"    note              : {note}")
        if row.classification is Classification.UNCLASSIFIED:
            overall_ok = False

    print()
    if overall_ok:
        print("overall: OK (no UNCLASSIFIED rows)")
    else:
        print("overall: WARN (UNCLASSIFIED rows present; inspect notes above)")

    if report_path is not None:
        print(f"\nfull structured report: {report_path}")
    return 0 if overall_ok else 3


def _cmd_opening_quality(args: argparse.Namespace) -> int:
    report_path: Path | None = None if args.no_report else Path(args.report)
    report = run_opening_quality_probe(
        matrix_limit=args.matrix_limit,
        judge_limit_per_role=args.judge_limit,
        with_turn_execute=args.with_turn_execute,
        trace_id_overrides=args.trace_id or None,
        report_path=report_path,
    )
    return _print_human(report, report_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.mcp_server.diagnostics",
        description="Operational diagnostics for the wos-mcp server.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    oq = sub.add_parser(
        "opening-quality",
        help="Probe opening-quality contracts via local MCP launcher.",
    )
    oq.add_argument("--matrix-limit", type=int, default=15)
    oq.add_argument("--judge-limit", type=int, default=5)
    oq.add_argument(
        "--with-turn-execute",
        action="store_true",
        help="Also pick a recent turn.execute trace and classify it (NON_OPENING_OK).",
    )
    oq.add_argument(
        "--trace-id",
        action="append",
        default=[],
        help="Override trace selection (may be repeated, max 2).",
    )
    oq.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help="Path for the structured JSON report.",
    )
    oq.add_argument(
        "--no-report",
        action="store_true",
        help="Skip writing the structured JSON report.",
    )
    oq.set_defaults(func=_cmd_opening_quality)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
