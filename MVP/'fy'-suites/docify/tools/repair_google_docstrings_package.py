#!/usr/bin/env python3
"""Reflow module/class docstrings and add missing Google ``Args:`` / ``Returns:`` sections.

Mirrors ``python_documentation_audit.py`` width (72) and section header rules. Skips
nested functions inside other function bodies. Excludes ``tests/`` under the
package root by default (same layout as ``bulk_google_docstrings_package.py``).

Run from the repository root::

    python "./'fy'-suites/docify/tools/repair_google_docstrings_package.py" --package-root ai_stack

"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
_REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[3]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import python_docstring_synthesize as pds  # noqa: E402


def _iter_py_files(package_root: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(package_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            rel = path.relative_to(package_root)
        except ValueError:
            continue
        if rel.parts and rel.parts[0] == "tests":
            continue
        out.append(path)
    return out


def _all_callables(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every function/async node (including nested helpers) for Google repair passes."""
    return [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def _one_repair_pass(source: str, tree: ast.Module) -> tuple[str, int, str | None]:
    """Return (new_source, edit_count_in_pass, error)."""
    edits = 0
    s = source
    pds._attach_parents(tree)

    new_s, err = pds.repair_module_docstring_in_source(s, tree)
    if err:
        return s, edits, err
    if new_s != s:
        edits += 1
        s = new_s
        try:
            tree = ast.parse(s)
        except SyntaxError as exc:
            return s, edits, f"re-parse after module repair: {exc}"
        pds._attach_parents(tree)

    classes = sorted(
        (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)),
        key=lambda n: -(n.lineno or 0),
    )
    for cls in classes:
        new_s, err = pds.repair_class_docstring_in_source(s, cls)
        if err:
            return s, edits, err
        if new_s != s:
            edits += 1
            s = new_s
            try:
                tree = ast.parse(s)
            except SyntaxError as exc:
                return s, edits, f"re-parse after class repair: {exc}"
            pds._attach_parents(tree)

    funcs = sorted(_all_callables(tree), key=lambda n: -(n.lineno or 0))
    for fn in funcs:
        new_s, err = pds.repair_function_google_docstring_in_source(s, fn)
        if err:
            return s, edits, err
        if new_s != s:
            edits += 1
            s = new_s
            try:
                tree = ast.parse(s)
            except SyntaxError as exc:
                return s, edits, f"re-parse after function repair: {exc}"
            pds._attach_parents(tree)

    return s, edits, None


def process_file(path: Path, *, dry_run: bool) -> tuple[int, str | None]:
    try:
        initial = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return 0, f"read: {exc}"

    source = initial
    total = 0
    for _ in range(50):
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return total, f"parse: {exc}"
        new_source, n, err = _one_repair_pass(source, tree)
        if err:
            return total, err
        total += n
        if new_source == source:
            break
        source = new_source

    if not dry_run and source != initial:
        path.write_text(source, encoding="utf-8", newline="\n")

    return total, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=Path("ai_stack"))
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    repo_root = (args.repo_root or _REPO_ROOT_DEFAULT).resolve()
    pkg = (repo_root / args.package_root).resolve()
    if not pkg.is_dir():
        print(f"package root not found: {pkg}", file=sys.stderr)
        return 2

    paths = _iter_py_files(pkg)
    errors: list[tuple[str, str]] = []
    grand = 0
    for i, path in enumerate(paths):
        n, err = process_file(path, dry_run=args.dry_run)
        grand += n
        if err:
            errors.append((str(path.relative_to(repo_root)), err))
        if (i + 1) % 25 == 0:
            print(f"... {i + 1}/{len(paths)} files", file=sys.stderr)

    print(f"files: {len(paths)}  repair_edits: {grand}  dry_run: {args.dry_run}")
    for rel, msg in errors[:40]:
        print(f"ERROR {rel}: {msg}", file=sys.stderr)
    if len(errors) > 40:
        print(f"... {len(errors) - 40} more errors", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
