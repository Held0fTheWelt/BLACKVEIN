#!/usr/bin/env python3
"""Docify hub CLI — PEP 8 inline ``#`` comments or a Google-style function docstring.

Two modes:

1. **Block comments** — for a 1-based line range (or ``--function`` body span),
   insert indented ``#`` lines above intersecting statements. Prose wraps to
   **72** columns after ``# `` (common PEP 8 style), English only.

2. **Google docstring** — with ``--emit-google-docstring`` and ``--function``,
   emit a draft docstring: summary, optional paragraph, ``Args:`` (when
   parameters exist), and ``Returns:`` with a ``TypeName:`` line plus an
   indented narrative when the signature has a non-``None`` return annotation.
   Docstring **flow lines** are wrapped so the dedented body stays within
   **72** characters per line (PEP 257-style readability).

Use ``python_documentation_audit.py`` (same suite path) for tree-wide backlog; pass
``--google-docstring-audit`` there to validate layout on symbols that already
have docstrings.

Examples:

    python "./'fy'-suites/docify/tools/python_docstring_synthesize.py" \\
        --file path/to/your_module.py \\
        --start-line 50 --end-line 85

    python "./'fy'-suites/docify/tools/python_docstring_synthesize.py" \\
        --file path/to/your_module.py \\
        --function your_callable --apply

    python "./'fy'-suites/docify/tools/python_docstring_synthesize.py" \\
        --file path/to/your_module.py \\
        --function your_callable --emit-google-docstring --apply-docstring
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import textwrap
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

# PEP 8: prefer 79-char lines for code; block comments often use a shorter flow
# width for readability (matching common docstring guidance).
_COMMENT_FLOW_WIDTH = 72
# Docstring narrative width (PEP 257 recommends wrapping long docstring lines).
_DOCSTRING_FLOW_WIDTH = 72
# Matches ``python_documentation_audit.py`` Google docstring width checks.
_GOOGLE_DOCSTRING_MAX_LINE = 72


def reflow_plain_docstring_paragraphs(doc: str, *, width: int = _GOOGLE_DOCSTRING_MAX_LINE) -> str:
    """Reflow *doc* paragraphs so soft-wrapped lines stay within *width* (best effort)."""
    doc = doc.strip()
    if not doc:
        return doc
    paras = doc.split("\n\n")
    new_paras: list[str] = []
    for raw in paras:
        lines = [ln.rstrip() for ln in raw.splitlines()]
        nonempty = [ln for ln in lines if ln.strip()]
        if not nonempty:
            continue
        if all(len(ln) <= width for ln in lines):
            new_paras.append("\n".join(lines).strip())
            continue
        flat = " ".join(ln.strip() for ln in nonempty)
        wrapped = textwrap.wrap(
            flat,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        new_paras.append("\n".join(wrapped) if wrapped else flat)
    return "\n\n".join(new_paras)


def _google_audit_missing_args_section(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    doc: str,
) -> bool:
    if re.search(r"(?m)^\s*Args:\s*$", doc):
        return False
    args = [*node.args.posonlyargs, *node.args.args]
    if _callable_kind(node) == "method" and args and args[0].arg in ("self", "cls"):
        args = args[1:]
    return bool(args or node.args.vararg or node.args.kwonlyargs or node.args.kwarg)


def _google_audit_missing_returns_section(node: ast.FunctionDef | ast.AsyncFunctionDef, doc: str) -> bool:
    ret = node.returns
    needs = ret is not None and not (isinstance(ret, ast.Constant) and ret.value is None)
    if not needs:
        return False
    return not re.search(r"(?m)^\s*Returns:\s*$", doc)


def _google_returns_type_line_invalid(node: ast.FunctionDef | ast.AsyncFunctionDef, doc: str) -> bool:
    """True when ``Returns:`` exists but the first non-empty tail line fails the audit regex."""
    if not _needs_returns_section(node.returns):
        return False
    if not re.search(r"(?m)^\s*Returns:\s*$", doc):
        return False
    after = re.split(r"(?m)^\s*Returns:\s*$", doc, maxsplit=1)[-1]
    tail_lines = [ln for ln in after.splitlines() if ln.strip()]
    type_line = tail_lines[0] if tail_lines else ""
    return not bool(re.match(r"^\s*[A-Za-z_][\w\[\].<> ,|]*:\s*$", type_line))


def _google_audit_doc_has_long_line(doc: str, *, width: int = _GOOGLE_DOCSTRING_MAX_LINE) -> bool:
    return any(len(line) > width for line in doc.splitlines())


def _first_summary_paragraph_for_reuse(doc_clean: str) -> str | None:
    head = re.split(r"(?m)^Args:\s*$", doc_clean, maxsplit=1)[0].strip()
    head = re.split(r"(?m)^Returns:\s*$", head, maxsplit=1)[0].strip()
    if not head:
        return None
    first = head.split("\n\n")[0].strip()
    return first or None


def format_function_docstring_from_dedented_body(
    dedent_body: str,
    content_indent: str,
) -> str:
    """Build a triple-quoted function docstring statement from already-dedented body text."""
    lines = dedent_body.rstrip().split("\n")
    if not lines:
        inner_prefixed = [content_indent]
    else:
        inner_prefixed = [f"{content_indent}{ln}" for ln in lines]
    first_text = inner_prefixed[0][len(content_indent) :]
    parts: list[str] = [f'{content_indent}"""{first_text}']
    for ln in inner_prefixed[1:]:
        parts.append("\n" + ln)
    parts.append(f'\n{content_indent}"""\n')
    return "".join(parts)


def format_top_module_docstring_block(inner: str) -> str:
    """Format a module-level docstring (column 0) with lines wrapped inside the literal."""
    inner = inner.rstrip("\n")
    lines = inner.splitlines() or [""]
    if len(lines) == 1 and len(lines[0]) + 3 <= _GOOGLE_DOCSTRING_MAX_LINE:
        return f'"""{lines[0]}\n\n"""\n'
    parts = ['"""\n']
    for ln in lines:
        parts.append(ln + "\n")
    parts.append('"""\n')
    return "".join(parts)


def _stmt_span(node: ast.stmt) -> tuple[int, int]:
    """Return (lineno, end_lineno) with sensible fallbacks."""
    start = getattr(node, "lineno", 1) or 1
    end = getattr(node, "end_lineno", None) or start
    return start, end


def _intersects(line_start: int, line_end: int, sel_start: int, sel_end: int) -> bool:
    return not (line_end < sel_start or line_start > sel_end)


def _function_spanning_range(
    tree: ast.Module,
    start: int,
    end: int,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Return the innermost function whose body span contains [start, end]."""
    candidates: list[tuple[int, ast.FunctionDef | ast.AsyncFunctionDef]] = []

    class V(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
            self._maybe_add(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
            self._maybe_add(node)

        def _maybe_add(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            s, e = _stmt_span(node)
            if s <= start and e >= end:
                span = e - s
                candidates.append((span, node))
            self.generic_visit(node)

    V().visit(tree)
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _indent_for_line(lines: list[str], lineno: int) -> str:
    idx = lineno - 1
    if 0 <= idx < len(lines):
        raw = lines[idx]
        return raw[: len(raw) - len(raw.lstrip())]
    return ""


def _attach_parents(node: ast.AST) -> None:
    """Populate ``parent`` links for AST nodes (``ast`` does not set them)."""
    for child in ast.iter_child_nodes(node):
        setattr(child, "parent", node)  # noqa: B010
        _attach_parents(child)


def _find_function(
    tree: ast.Module,
    name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Return the first ``FunctionDef`` / ``AsyncFunctionDef`` with *name*."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _callable_kind(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    parent = getattr(node, "parent", None)
    return "method" if isinstance(parent, ast.ClassDef) else "function"


def _unparse(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except AttributeError:
        return None


def _return_type_label(returns: ast.expr | None) -> str:
    """Short display label for ``Returns`` narrative (not necessarily one line)."""
    if returns is None:
        return "None"
    if isinstance(returns, ast.Constant) and returns.value is None:
        return "None"
    label = (_unparse(returns) or "Any").replace("\n", " ").strip().strip("'\"")
    if len(label) > 64:
        label = label[:61] + "..."
    return label


def _return_type_line_for_google_block(returns: ast.expr | None, *, content_indent: str) -> str:
    """Single-line ``TypeName:`` tail for Google ``Returns:`` (audit regex + max 72 chars)."""
    leader = f"{content_indent}    "
    raw = (_unparse(returns) or "Any").replace("\n", " ").strip().strip("'\"")
    # ``leader + type + ':'`` must stay within the audit width (small margin).
    max_t = max(8, _GOOGLE_DOCSTRING_MAX_LINE - len(leader) - 2)
    if len(raw) > max_t:
        raw = raw[: max_t - 3] + "..."
    return raw


def _needs_returns_section(returns: ast.expr | None) -> bool:
    if returns is None:
        return False
    if isinstance(returns, ast.Constant) and returns.value is None:
        return False
    return True


def _iter_params_for_doc(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[str, ast.expr | None]]:
    out: list[tuple[str, ast.expr | None]] = []
    for a in (*node.args.posonlyargs, *node.args.args):
        out.append((a.arg, a.annotation))
    if node.args.vararg:
        va = node.args.vararg
        out.append((f"*{va.arg}", va.annotation))
    for a in node.args.kwonlyargs:
        out.append((a.arg, a.annotation))
    if node.args.kwarg:
        ka = node.args.kwarg
        out.append((f"**{ka.arg}", ka.annotation))
    return out


def _params_for_google_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[str, ast.expr | None]]:
    params = _iter_params_for_doc(node)
    if _callable_kind(node) == "method" and params and params[0][0] in ("self", "cls"):
        return params[1:]
    return params


def _wrap_to_width(text: str, *, width: int, initial: str, subsequent: str) -> list[str]:
    if width < 12:
        width = 12
    wrapped = textwrap.wrap(
        text.strip(),
        width=width,
        initial_indent=initial,
        subsequent_indent=subsequent,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return wrapped or [initial.rstrip()]


def build_google_docstring_lines(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    content_indent: str,
    summary_override: str | None = None,
) -> list[str]:
    """Build docstring **inner** lines (no opening/closing ``\"\"\"``).

    Each line is prefixed with *content_indent* (the function body's leading
    whitespace). Wrapped segments stay within ``_DOCSTRING_FLOW_WIDTH`` for
    the full line length.
    """
    ci = content_indent
    kind = _callable_kind(node)
    name = node.name
    lines_out: list[str] = []

    if summary_override and summary_override.strip():
        summary = " ".join(summary_override.split())
        lines_out.extend(_wrap_to_width(summary, width=_DOCSTRING_FLOW_WIDTH, initial=ci, subsequent=ci))
    else:
        summary = (
            f"Describe what ``{name}`` does in one line (verb-led summary for this {kind})."
        )
        lines_out.extend(_wrap_to_width(summary, width=_DOCSTRING_FLOW_WIDTH, initial=ci, subsequent=ci))
    lines_out.append("")

    detail = (
        f"Behaviour, edge cases, and invariants should be inferred from the "
        f"implementation and public contract of this {kind}."
    )
    lines_out.extend(
        _wrap_to_width(
            detail,
            width=_DOCSTRING_FLOW_WIDTH,
            initial=ci,
            subsequent=ci,
        )
    )

    params = _params_for_google_args(node)
    if params:
        lines_out.append("")
        lines_out.append(f"{ci}Args:")
        arg_prefix = f"{ci}    "
        for pname, ann in params:
            ann_s = _unparse(ann)
            type_hint = f" ({ann_s})" if ann_s else ""
            desc = f"``{pname}``{type_hint}; meaning follows the type and call sites."
            leader = f"{arg_prefix}{pname}: "
            cont = f"{arg_prefix}    "
            wrapped = textwrap.wrap(
                desc.strip(),
                width=_DOCSTRING_FLOW_WIDTH,
                initial_indent=leader,
                subsequent_indent=cont,
                break_long_words=False,
                break_on_hyphens=False,
            )
            lines_out.extend(wrapped if wrapped else [leader.rstrip()])

    if _needs_returns_section(node.returns):
        lines_out.append("")
        lines_out.append(f"{ci}Returns:")
        type_line = _return_type_line_for_google_block(node.returns, content_indent=ci)
        lines_out.append(f"{ci}    {type_line}:")
        type_name = _return_type_label(node.returns)
        body = (
            f"Returns a value of type ``{type_name}``; see the function body for "
            f"structure, error paths, and sentinels."
        )
        narr_prefix = f"{ci}        "
        fill_w = _DOCSTRING_FLOW_WIDTH - len(narr_prefix)
        lines_out.extend(
            _wrap_to_width(
                body,
                width=max(16, fill_w),
                initial=narr_prefix,
                subsequent=narr_prefix,
            )
        )

    while lines_out and lines_out[-1].strip() == "":
        lines_out.pop()
    return lines_out


def _apply_google_docstring_same_line_function_body(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    stmt0: ast.stmt,
    raw_lines: list[str],
    plain: list[str],
) -> tuple[str | None, str | None]:
    """Handle ``def foo(...): <suite>`` when *suite* starts on the same line as ``def``."""
    if stmt0.col_offset is None:
        return None, "single-line function body missing col_offset (cannot splice docstring)"
    idx = (func.lineno or 1) - 1
    if not (0 <= idx < len(raw_lines)):
        return None, "function lineno out of range"
    line = raw_lines[idx]
    cut = stmt0.col_offset
    if cut > len(line):
        return None, "col_offset past line end"
    head = line[:cut]
    tail = line[cut:].lstrip()
    def_indent = _indent_for_line(plain, func.lineno or 1)
    content_indent = f"{def_indent}    "
    new_stmt = format_function_docstring_block(func, content_indent=content_indent)
    merged = f"{head.rstrip()}\n{new_stmt}{content_indent}{tail}"
    out_lines = raw_lines[:idx] + [merged] + raw_lines[idx + 1 :]
    new_source = "".join(out_lines)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def format_function_docstring_block(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    content_indent: str,
    summary_override: str | None = None,
) -> str:
    """Return a full triple-quoted docstring assignment (first body statement)."""
    inner_lines = build_google_docstring_lines(
        node,
        content_indent=content_indent,
        summary_override=summary_override,
    )
    if not inner_lines:
        inner_lines = [f"{content_indent}Empty docstring."]
    first_line = inner_lines[0]
    if not first_line.startswith(content_indent):
        first_line = f"{content_indent}{first_line.lstrip()}"
    first_text = first_line[len(content_indent) :]
    parts: list[str] = [f'{content_indent}"""{first_text}']
    for ln in inner_lines[1:]:
        parts.append("\n" + ln)
    parts.append(f'\n{content_indent}"""\n')
    return "".join(parts)


def apply_google_docstring_to_function_node(
    source: str,
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str | None, str | None]:
    """Insert or replace the docstring on a concrete function or method *func*."""
    if not func.body:
        return None, f"function {func.name!r} has no body"

    raw_lines = source.splitlines(keepends=True)
    plain = [ln.rstrip("\n") for ln in raw_lines]
    stmt0 = func.body[0]
    end_ln = getattr(stmt0, "end_lineno", None) or stmt0.lineno or 1
    if (
        func.lineno == stmt0.lineno == end_ln
        and getattr(stmt0, "col_offset", None) is not None
        and not (
            isinstance(stmt0, ast.Expr)
            and isinstance(stmt0.value, ast.Constant)
            and isinstance(stmt0.value.value, str)
        )
    ):
        return _apply_google_docstring_same_line_function_body(func, stmt0, raw_lines, plain)

    content_indent = _indent_for_line(plain, stmt0.lineno)
    new_stmt = format_function_docstring_block(func, content_indent=content_indent)
    new_stmt_lines = new_stmt.splitlines(keepends=True)

    start_idx = stmt0.lineno - 1
    if isinstance(stmt0, ast.Expr) and isinstance(stmt0.value, ast.Constant) and isinstance(
        stmt0.value.value, str
    ):
        end_idx = (stmt0.end_lineno or stmt0.lineno) - 1
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[end_idx + 1 :]
    else:
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[start_idx:]

    new_source = "".join(out_lines)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def format_class_docstring_block(node: ast.ClassDef, *, content_indent: str) -> str:
    """Return a minimal triple-quoted class docstring (first body statement)."""
    text = (
        f"``{node.name}`` groups related behaviour; callers should read members "
        f"for contracts and threading assumptions."
    )
    inner = reflow_plain_docstring_paragraphs(text)
    return format_function_docstring_from_dedented_body(inner, content_indent)


def apply_google_docstring_to_class_node(source: str, node: ast.ClassDef) -> tuple[str | None, str | None]:
    """Insert or replace the docstring on a concrete *ClassDef*."""
    if not node.body:
        return None, f"class {node.name!r} has no body"

    raw_lines = source.splitlines(keepends=True)
    plain = [ln.rstrip("\n") for ln in raw_lines]
    content_indent = _indent_for_line(plain, node.body[0].lineno)
    new_stmt = format_class_docstring_block(node, content_indent=content_indent)
    new_stmt_lines = new_stmt.splitlines(keepends=True)

    stmt0 = node.body[0]
    start_idx = stmt0.lineno - 1
    if isinstance(stmt0, ast.Expr) and isinstance(stmt0.value, ast.Constant) and isinstance(
        stmt0.value.value, str
    ):
        end_idx = (stmt0.end_lineno or stmt0.lineno) - 1
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[end_idx + 1 :]
    else:
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[start_idx:]

    new_source = "".join(out_lines)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def _header_insert_line_index(lines: list[str]) -> int:
    """Return 0-based index where a new module docstring line block should be inserted."""
    i = 0
    if lines and lines[0].startswith("#!"):
        i = 1
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped == "":
            i += 1
            continue
        if stripped.startswith("#") and ("coding:" in stripped or "coding=" in stripped):
            i += 1
            continue
        break
    return i


def apply_module_google_docstring(source: str, *, rel_posix: str) -> tuple[str | None, str | None]:
    """Insert or replace a file-level module docstring (PEP 257, before ``from __future__``)."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return None, f"parse error: {exc}"

    doc = ast.get_docstring(tree, clean=False)
    if doc is not None and doc.strip():
        return source, None

    summary_raw = (
        f"``{rel_posix}`` — module entrypoints and invariants belong in this "
        f"docstring as they are stabilised."
    )
    summary_inner = reflow_plain_docstring_paragraphs(summary_raw)
    raw_lines = source.splitlines(keepends=True)
    plain = [ln.rstrip("\n") for ln in raw_lines]

    if tree.body:
        first = tree.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(
            first.value.value, str
        ):
            if not first.value.value.strip():
                content_indent = _indent_for_line(plain, first.lineno)
                if content_indent.strip():
                    new_stmt = format_function_docstring_from_dedented_body(summary_inner, content_indent)
                else:
                    new_stmt = format_top_module_docstring_block(summary_inner)
                new_stmt_lines = new_stmt.splitlines(keepends=True)
                start_idx = first.lineno - 1
                end_idx = (first.end_lineno or first.lineno) - 1
                out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[end_idx + 1 :]
                new_source = "".join(out_lines)
                try:
                    ast.parse(new_source)
                except SyntaxError as exc:
                    return None, f"post-edit parse error: {exc}"
                return new_source, None

    insert_at = _header_insert_line_index(raw_lines)
    block = format_top_module_docstring_block(summary_inner)
    out_lines = raw_lines[:insert_at] + [block] + raw_lines[insert_at:]
    new_source = "".join(out_lines)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def repair_module_docstring_in_source(source: str, tree: ast.Module) -> tuple[str | None, str | None]:
    """Reflow an existing module docstring when any line exceeds the audit width."""
    doc = ast.get_docstring(tree, clean=False) or ""
    if not doc.strip():
        return source, None
    if not _google_audit_doc_has_long_line(doc):
        return source, None
    new_inner = reflow_plain_docstring_paragraphs(doc)
    if new_inner.strip() == doc.strip():
        return source, None
    if not tree.body:
        return None, "empty module"
    first = tree.body[0]
    if not (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return None, "module docstring is not a leading string literal"
    new_block = format_top_module_docstring_block(new_inner)
    new_stmt_lines = new_block.splitlines(keepends=True)
    raw_lines = source.splitlines(keepends=True)
    start_idx = first.lineno - 1
    end_idx = (first.end_lineno or first.lineno) - 1
    new_source = "".join(raw_lines[:start_idx] + new_stmt_lines + raw_lines[end_idx + 1 :])
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def repair_class_docstring_in_source(source: str, node: ast.ClassDef) -> tuple[str | None, str | None]:
    """Reflow an existing class docstring when any line exceeds the audit width."""
    doc = ast.get_docstring(node, clean=False) or ""
    if not doc.strip():
        return source, None
    if not _google_audit_doc_has_long_line(doc):
        return source, None
    new_inner = reflow_plain_docstring_paragraphs(doc)
    if new_inner.strip() == doc.strip():
        return source, None
    if not node.body:
        return None, f"class {node.name!r} has no body"
    stmt0 = node.body[0]
    raw_lines = source.splitlines(keepends=True)
    plain = [ln.rstrip("\n") for ln in raw_lines]
    content_indent = _indent_for_line(plain, stmt0.lineno)
    new_stmt = format_function_docstring_from_dedented_body(new_inner, content_indent)
    new_stmt_lines = new_stmt.splitlines(keepends=True)
    start_idx = stmt0.lineno - 1
    if isinstance(stmt0, ast.Expr) and isinstance(stmt0.value, ast.Constant) and isinstance(
        stmt0.value.value, str
    ):
        end_idx = (stmt0.end_lineno or stmt0.lineno) - 1
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[end_idx + 1 :]
    else:
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[start_idx:]
    new_source = "".join(out_lines)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def repair_function_google_docstring_in_source(
    source: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str | None, str | None]:
    """Align function/method docstrings with Google audit (width, ``Args:``, ``Returns:``)."""
    if not node.body:
        return source, None

    doc = ast.get_docstring(node, clean=False) or ""
    doc_clean = ast.get_docstring(node, clean=True) or ""
    if not doc.strip():
        return source, None

    stmt0 = node.body[0]
    end_ln = getattr(stmt0, "end_lineno", None) or stmt0.lineno or 1
    if (
        node.lineno == stmt0.lineno == end_ln
        and getattr(stmt0, "col_offset", None) is not None
        and isinstance(stmt0, ast.Expr)
        and isinstance(stmt0.value, ast.Constant)
        and isinstance(stmt0.value.value, str)
    ):
        return apply_google_docstring_to_function_node(source, node)

    missing_a = _google_audit_missing_args_section(node, doc)
    missing_r = _google_audit_missing_returns_section(node, doc)
    long_l = _google_audit_doc_has_long_line(doc)
    bad_ret = _google_returns_type_line_invalid(node, doc)
    if not (missing_a or missing_r or long_l or bad_ret):
        return source, None

    raw_lines = source.splitlines(keepends=True)
    plain = [ln.rstrip("\n") for ln in raw_lines]
    content_indent = _indent_for_line(plain, stmt0.lineno)

    summary = _first_summary_paragraph_for_reuse(doc_clean)
    new_stmt = format_function_docstring_block(
        node,
        content_indent=content_indent,
        summary_override=summary,
    )

    new_stmt_lines = new_stmt.splitlines(keepends=True)
    start_idx = stmt0.lineno - 1
    if isinstance(stmt0, ast.Expr) and isinstance(stmt0.value, ast.Constant) and isinstance(
        stmt0.value.value, str
    ):
        end_idx = (stmt0.end_lineno or stmt0.lineno) - 1
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[end_idx + 1 :]
    else:
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[start_idx:]

    new_source = "".join(out_lines)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def apply_function_google_docstring(source: str, func_name: str) -> tuple[str | None, str | None]:
    """Parse *source*, replace or insert a Google-style docstring for *func_name*."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return None, f"parse error: {exc}"

    _attach_parents(tree)
    func = _find_function(tree, func_name)
    if func is None:
        return None, f"no function named {func_name!r}"
    return apply_google_docstring_to_function_node(source, func)


def _format_block_comment(indent: str, prose: str) -> list[str]:
    """Turn *prose* into PEP 8 style ``#`` lines at *indent*."""
    available = max(20, _COMMENT_FLOW_WIDTH - len(indent) - 2)
    wrapped = textwrap.wrap(
        prose.strip(),
        width=available,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if not wrapped:
        return [f"{indent}#"]
    out: list[str] = []
    for i, seg in enumerate(wrapped):
        out.append(f"{indent}# {seg}" if seg else f"{indent}#")
    return out


def _describe_statement(stmt: ast.stmt) -> str:
    """English explanation from AST shape; two short sentences where helpful."""
    if isinstance(stmt, ast.If):
        try:
            cond = ast.unparse(stmt.test)
        except AttributeError:
            cond = "the condition"
        if len(cond) > 65:
            cond = cond[:62] + "..."
        orelse = stmt.orelse
        extra = ""
        if orelse and not (len(orelse) == 1 and isinstance(orelse[0], ast.If)):
            extra = " The else branch covers the complementary case."
        elif orelse:
            extra = " elif/else ladders chain further decisions below."
        return (
            f"Branch when {cond}. Readers should compare both arms for data flow and invariants."
            + extra
        )
    if isinstance(stmt, ast.Assign):
        if (
            len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and isinstance(stmt.value, ast.Constant)
            and stmt.value.value is None
        ):
            return (
                f"Reset ``{stmt.targets[0].id}`` to a known baseline before conditional updates. "
                f"That keeps later branches from reusing stale values when the guard skips them."
            )
        targets = [ast.unparse(t) for t in stmt.targets]
        try:
            rhs = ast.unparse(stmt.value)
        except AttributeError:
            rhs = "the right-hand expression"
        if len(rhs) > 45:
            rhs = rhs[:42] + "..."
        return (
            f"Bind {' , '.join(targets)} to {rhs}. "
            f"Names introduced here should stay consistent for the rest of the block."
        )
    if isinstance(stmt, ast.AnnAssign):
        try:
            ann = ast.unparse(stmt.annotation)
        except AttributeError:
            ann = "annotation"
        return (
            f"Declare or narrow a typed slot using {ann}. "
            f"Callers and type checkers both rely on this shape staying truthful."
        )
    if isinstance(stmt, ast.Return):
        if isinstance(stmt.value, ast.Call):
            func = stmt.value.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name:
                return (
                    f"Produce the final ``{name}(...)`` value for this path. "
                    f"Keyword arguments encode the payload; adjust them when the dataclass or API evolves."
                )
        try:
            val = ast.unparse(stmt.value) if stmt.value else "nothing"
        except AttributeError:
            val = "a value"
        if len(val) > 55:
            val = "a structured value"
        return f"Exit with {val}. Ensure this matches the function's advertised contract to callers."
    if isinstance(stmt, ast.For):
        return (
            "Iterate with a clear loop variable and predictable side effects. "
            "Prefer extracting non-trivial body logic so reviewers can follow each pass."
        )
    if isinstance(stmt, ast.While):
        return (
            "Repeat until the guard becomes false; watch for infinite loops when external state stalls. "
            "Document any intentional busy-wait or polling behaviour in adjacent comments."
        )
    if isinstance(stmt, ast.With):
        return (
            "Acquire managed resources for the nested suite and release them on exit. "
            "Exceptions should still leave the context protocol in a valid teardown path."
        )
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        try:
            call = ast.unparse(stmt.value)
        except AttributeError:
            call = "a call"
        if len(call) > 50:
            call = call[:47] + "..."
        return (
            f"Evaluate ``{call}`` for its side effect (return value discarded). "
            f"State touched here should be obvious from the callee name or nearby assignments."
        )
    return (
        "Logical step in the surrounding control flow. "
        "Tie it back to the function docstring or module overview when behaviour is non-obvious."
    )


def plan_block_comments(
    source: str,
    *,
    start_line: int,
    end_line: int,
    function_name: str | None,
) -> tuple[list[tuple[int, list[str]]], str | None]:
    """
    Return (insertions, error) where each insertion is (1-based line before which
    to insert, list of new comment lines).
    """
    lines = source.splitlines()
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [], f"parse error: {exc}"

    if function_name:
        fn: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                fn = node
                break
        if fn is None:
            return [], f"no function named {function_name!r}"
        if not fn.body:
            return [], f"function {function_name!r} has no body"
        first = _stmt_span(fn.body[0])[0]
        last = max(_stmt_span(st)[1] for st in fn.body)
        start_line, end_line = first, last

    target_fn = _function_spanning_range(tree, start_line, end_line)
    body: Sequence[ast.stmt]
    if target_fn is not None:
        body = target_fn.body
    else:
        body = tree.body

    inserts: list[tuple[int, list[str]]] = []
    for stmt in body:
        sl, el = _stmt_span(stmt)
        if not _intersects(sl, el, start_line, end_line):
            continue
        indent = _indent_for_line(lines, sl)
        prose = _describe_statement(stmt)
        block = _format_block_comment(indent, prose)
        if not block:
            continue
        inserts.append((sl, block))

    inserts.sort(key=lambda x: x[0], reverse=True)
    return inserts, None


def apply_planned_comments(path: Path, inserts: list[tuple[int, list[str]]]) -> None:
    raw = path.read_text(encoding="utf-8-sig")
    lines = raw.splitlines()
    for lineno, block in inserts:
        idx = lineno - 1
        for i, comment_line in enumerate(block):
            lines.insert(idx + i, comment_line)
    out = "\n".join(lines) + ("\n" if raw.endswith("\n") else "")
    path.write_text(out, encoding="utf-8", newline="\n")


@dataclass
class BlockInsert:
    """One planned comment insertion."""

    before_line: int
    lines: list[str]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--file", type=Path, required=True, help="Python file to edit (repo-relative or absolute).")
    parser.add_argument("--start-line", type=int, default=None)
    parser.add_argument("--end-line", type=int, default=None)
    parser.add_argument(
        "--function",
        type=str,
        default=None,
        help="Use this function's full body span (comments) or target name (Google docstring mode).",
    )
    parser.add_argument("--apply", action="store_true", help="Write comment insertions to the file (comments mode).")
    parser.add_argument(
        "--emit-google-docstring",
        action="store_true",
        help="Emit a Google-style docstring draft for ``--function`` instead of ``#`` comments.",
    )
    parser.add_argument(
        "--apply-docstring",
        action="store_true",
        help="Write ``--emit-google-docstring`` output to the file (implies review in git diff).",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.emit_google_docstring:
        if not args.function:
            parser.error("--emit-google-docstring requires --function NAME")
        if args.start_line is not None or args.end_line is not None:
            parser.error("--emit-google-docstring does not use --start-line / --end-line")
        if args.apply and args.apply_docstring:
            parser.error("use either --apply (comments) or --apply-docstring (docstring), not both")
        if args.apply:
            parser.error("with --emit-google-docstring use --apply-docstring to write the file, not --apply")
    elif args.apply_docstring:
        parser.error("--apply-docstring requires --emit-google-docstring")
    elif args.function:
        if args.start_line is not None or args.end_line is not None:
            parser.error("with --function, omit --start-line and --end-line (body span is derived from AST).")
    elif args.start_line is None or args.end_line is None:
        parser.error("pass --start-line and --end-line, or pass --function alone, or use --emit-google-docstring.")

    repo_root = (args.repo_root or Path(__file__).resolve().parents[3]).resolve()
    target = args.file
    path = target.resolve() if target.is_absolute() else (repo_root / target).resolve()
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 2

    source = path.read_text(encoding="utf-8-sig")
    rel = path.relative_to(repo_root).as_posix()

    if args.emit_google_docstring:
        new_src, err = apply_function_google_docstring(source, args.function)
        if err or new_src is None:
            print(err or "unknown error", file=sys.stderr)
            return 2
        tree2 = ast.parse(source)
        _attach_parents(tree2)
        fn2 = _find_function(tree2, args.function)
        if fn2 is None or not fn2.body:
            print("internal error: function missing after successful transform preview", file=sys.stderr)
            return 2
        ci = _indent_for_line(source.splitlines(), fn2.body[0].lineno)
        preview = format_function_docstring_block(fn2, content_indent=ci)
        payload: dict[str, object] = {
            "repo_root": str(repo_root),
            "file": rel,
            "mode": "google_docstring",
            "function": args.function,
            "dry_run": not args.apply_docstring,
            "docstring_block": preview,
        }
        if args.json or args.out:
            text = json.dumps(payload, indent=2) + "\n"
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(text, encoding="utf-8")
            else:
                sys.stdout.write(text)
        else:
            print(payload["docstring_block"], end="")

        if args.apply_docstring:
            path.write_text(new_src, encoding="utf-8", newline="\n")
        return 0

    start_line = args.start_line if args.start_line is not None else 1
    end_line = args.end_line if args.end_line is not None else 10**9
    inserts, err = plan_block_comments(
        source,
        start_line=int(start_line),
        end_line=int(end_line),
        function_name=args.function,
    )
    if err:
        print(err, file=sys.stderr)
        return 2

    payload = {
        "repo_root": str(repo_root),
        "file": rel,
        "mode": "block_comments",
        "dry_run": not args.apply,
        "insertions": [asdict(BlockInsert(before_line=a, lines=b)) for a, b in inserts],
    }

    if args.json or args.out:
        text = json.dumps(payload, indent=2) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
    else:
        print(f"Planned insertions before lines: {[i for i, _ in inserts]}")
        for before, block in inserts:
            print(f"\n--- before line {before} ---")
            print("\n".join(block))

    if args.apply and inserts:
        apply_planned_comments(path, inserts)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
