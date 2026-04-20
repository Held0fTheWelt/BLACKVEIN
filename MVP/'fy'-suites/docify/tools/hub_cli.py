"""Docify hub CLI — audit, drift hints, and backlog helpers.

After ``pip install -e .`` from the repository root, use the ``docify`` console script, or:

  python -m docify.tools audit --json --exit-zero
  python -m docify.tools drift --json

Script path (repo-relative):

  python "./'fy'-suites/docify/tools/hub_cli.py" drift

See ``'fy'-suites/docify/README.md`` and ``documentation-check-task.md`` for governance flows.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Sequence

from docify.tools.repo_paths import docify_hub_dir, repo_root

INPUT_LIST_NAME = "documentation_implementation_input.md"
OPEN_DOC_ROW = re.compile(r"^\|\s*\*\*(DOC-\d+)\*\*\s*\|")


def parse_open_doc_ids(markdown: str) -> list[str]:
    """Return sorted open **DOC-*** ids from backlog table rows (no filesystem access)."""
    seen: set[str] = set()
    for line in markdown.splitlines():
        m = OPEN_DOC_ROW.match(line)
        if m:
            seen.add(m.group(1))
    return sorted(seen, key=lambda s: int(s.split("-")[1]))


def _print_global_help() -> None:
    print(
        "Docify hub CLI\n\n"
        "Commands:\n"
        "  audit …          Python AST docstring audit (pass-through; same flags as legacy script).\n"
        "  drift …          Heuristic documentation follow-up hints from git-changed paths.\n"
        "  open-doc         Print open DOC-* backlog IDs from documentation_implementation_input.md.\n\n"
        "Examples:\n"
        "  docify audit --json --exit-zero --out 'fy'-suites/docify/reports/doc_audit.json\n"
        "  docify drift --json --out 'fy'-suites/docify/reports/doc_drift.json\n"
    )


def cmd_open_doc(args: argparse.Namespace) -> int:
    """Print open DOC-* IDs (Markdown table rows using | **DOC-nnn** |)."""
    if args.input is not None:
        path = Path(args.input).expanduser().resolve()
        if not path.is_file():
            print(f"Missing backlog file: {path}", file=sys.stderr)
            return 3
    else:
        root = repo_root()
        hub = docify_hub_dir(root)
        path = hub / INPUT_LIST_NAME
        if not path.is_file():
            print(f"Missing {path.relative_to(root)}", file=sys.stderr)
            return 3
    text = path.read_text(encoding="utf-8", errors="replace")
    for item in parse_open_doc_ids(text):
        print(item)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch ``docify`` subcommands."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        _print_global_help()
        return 0
    if argv[0].startswith("-") and argv[0] not in ("-h", "--help"):
        print(f"Unknown flag: {argv[0]}", file=sys.stderr)
        _print_global_help()
        return 2

    cmd = argv[0]
    tail = argv[1:]

    if cmd == "audit":
        from docify.tools.python_documentation_audit import main as audit_main

        return int(audit_main(tail))

    if cmd == "drift":
        from docify.tools.documentation_drift import drift_cli_main

        return int(drift_cli_main(tail))

    if cmd == "open-doc":
        parser = argparse.ArgumentParser(description="List open DOC-* backlog rows.")
        parser.add_argument(
            "--input",
            type=Path,
            default=None,
            help=(
                "Path to documentation_implementation_input.md "
                "(default: resolve hub file via repo_root())."
            ),
        )
        ns = parser.parse_args(tail)
        return cmd_open_doc(ns)

    print(f"Unknown command: {cmd}", file=sys.stderr)
    _print_global_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
