#!/usr/bin/env python3
"""Generate or extract wave_plan.json from Markdown (single source helpers).

- **json2md:** emit a GFM wave-plan table (+ optional fenced JSON) from valid `wave_plan.json`.
- **md2json:** extract ` ```json ` block (`--embed`, default) or parse the generated wave table (`--from-wave-table`).

Run from repository root. Does not modify the canonical DS input list.

Examples:

  python "./'fy'-suites/despaghettify/tools/wave_plan_emit.py" json2md \\
    --json "'fy'-suites/despaghettify/tools/fixtures/despag_wave_plan_example_valid.json" \\
    --out /tmp/wave_plan.md

  python "./'fy'-suites/despaghettify/tools/wave_plan_emit.py" md2json --embed \\
    --md "'fy'-suites/despaghettify/tools/fixtures/wave_plan_embed_example.md" \\
    --out /tmp/wave_plan.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_tools = Path(__file__).resolve().parent
_hub = _tools.parent
_grand = _hub.parent
_ins = str(_grand if _grand.name == "'fy'-suites" else _hub.parent)
if _ins not in sys.path:
    sys.path.insert(0, _ins)

from despaghettify.tools.repo_paths import repo_root

try:
    ROOT = repo_root()
except RuntimeError:
    ROOT = Path.cwd()

JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.I)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def json_to_markdown(data: dict, *, include_fence: bool = True) -> str:
    """Build human-editable Markdown: fenced JSON (source of truth) + summary table."""
    waves = data.get("sub_waves")
    if not isinstance(waves, list):
        raise ValueError("sub_waves must be an array")
    chunks: list[str] = []
    if include_fence:
        chunks.append("<!-- despag:wave-plan-json -->\n```json\n")
        chunks.append(json.dumps(data, indent=2))
        chunks.append("\n```\n<!-- /despag:wave-plan-json -->\n\n")
    chunks.append("## Wave plan (generated table)\n\n")
    chunks.append("| Sub-wave | Goal | Primary files / symbols | Gate |\n")
    chunks.append("|----------|------|---------------------------|------|\n")
    for w in waves:
        if not isinstance(w, dict):
            continue
        idx = w.get("index", "")
        goal = str(w.get("goal", "")).replace("|", "\\|").replace("\n", " ")
        paths = w.get("primary_paths") or []
        path_s = ", ".join(str(p) for p in paths).replace("|", "\\|")
        gates = w.get("gate_commands") or []
        gate_cell = "<br>".join(str(g).replace("|", "\\|") for g in gates)
        chunks.append(f"| {idx} | {goal} | `{path_s}` | {gate_cell} |\n")
    return "".join(chunks)


def extract_json_from_embed(md: str) -> dict:
    """
    Implement ``extract_json_from_embed`` for the surrounding module workflow.

    Module context: ``'fy'-suites/despaghettify/tools/wave_plan_emit.py`` — keep this
    routine aligned with sibling helpers in the same package.

    Args:
        md: Md for this call. Declared type: ``str``. (positional or keyword)

    Returns:
        Mapping typed as ``dict``; keys and values follow caller contracts.

    """
    m = JSON_FENCE.search(md)
    if not m:
        raise ValueError("no ```json ... ``` block found (use markers or a fenced JSON block)")
    return json.loads(m.group(1).strip())


def _split_gate_cell(cell: str) -> list[str]:
    cell = cell.strip()
    if not cell:
        return []
    parts = re.split(r"<br\s*/?>", cell, flags=re.I)
    out: list[str] = []
    for p in parts:
        for q in re.split(r"\s*;\s*", p):
            q = q.strip()
            if q:
                out.append(q)
    return out


def wave_table_to_json(md: str, *, ds_id: str, slug: str = "", session_date: str = "") -> dict:
    """Parse table rows | n | goal | paths | gates | after a header line containing 'Sub-wave' and 'Goal'."""
    lines = md.splitlines()
    sub_waves: list[dict] = []
    in_body = False
    for line in lines:
        if "Sub-wave" in line and "Goal" in line and "|" in line:
            in_body = True
            continue
        if in_body and re.match(r"^\|\s*-+", line):
            continue
        if in_body and line.strip().startswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) < 4:
                continue
            sw, goal, path_cell, gate_cell = cells[0], cells[1], cells[2], cells[3]
            if not sw.isdigit():
                if sub_waves:
                    break
                continue
            paths: list[str] = []
            for m in re.finditer(r"`([^`]+)`", path_cell):
                for piece in re.split(r",\s*", m.group(1).strip()):
                    if piece.strip():
                        paths.append(piece.strip())
            if not paths:
                pc = path_cell.strip().strip("`").strip()
                if pc:
                    paths = [pc]
            gates = _split_gate_cell(gate_cell)
            if not gates:
                raise ValueError(f"row {sw}: no gate commands parsed")
            wid = f"w{int(sw):02d}"
            sub_waves.append(
                {
                    "index": int(sw),
                    "id": wid,
                    "goal": goal.strip(),
                    "primary_paths": paths,
                    "gate_commands": gates,
                }
            )
        elif in_body and sub_waves and line.strip() and not line.strip().startswith("|"):
            break
    if not sub_waves:
        raise ValueError("no wave table rows parsed (expected | n | goal | paths | gate |)")
    out: dict = {"schema_version": "1", "ds_id": ds_id, "sub_waves": sub_waves}
    if slug.strip():
        out["slug"] = slug.strip()
    if session_date.strip():
        out["session_date"] = session_date.strip()
    return out


def cmd_json2md(args: argparse.Namespace) -> int:
    """
    Implement ``cmd_json2md`` for the surrounding module workflow.

    Module context: ``'fy'-suites/despaghettify/tools/wave_plan_emit.py`` — keep this
    routine aligned with sibling helpers in the same package.

    Args:
        args:
            Positional values forwarded to the implementation, typed as
            ``argparse.Namespace``. (positional or keyword)

    Returns:
        Value typed as ``int`` for downstream use.

    """
    inp = Path(args.json)
    if not inp.is_absolute():
        inp = ROOT / inp
    data = _load_json(inp)
    text = json_to_markdown(data, include_fence=not args.table_only)
    out_s = (args.out or "").strip()
    out = Path(out_s) if out_s else None
    if out and not out.is_absolute():
        out = ROOT / out
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(out.relative_to(ROOT).as_posix())
    else:
        sys.stdout.write(text)
    return 0


def cmd_md2json(args: argparse.Namespace) -> int:
    """
    Implement ``cmd_md2json`` for the surrounding module workflow.

    Module context: ``'fy'-suites/despaghettify/tools/wave_plan_emit.py`` — keep this
    routine aligned with sibling helpers in the same package.

    Args:
        args:
            Positional values forwarded to the implementation, typed as
            ``argparse.Namespace``. (positional or keyword)

    Returns:
        Value typed as ``int`` for downstream use.

    """
    inp = Path(args.md)
    if not inp.is_absolute():
        inp = ROOT / inp
    md = inp.read_text(encoding="utf-8", errors="replace")
    if args.from_wave_table:
        data = wave_table_to_json(
            md,
            ds_id=args.ds_id,
            slug=args.slug or "",
            session_date=args.session_date or "",
        )
    else:
        data = extract_json_from_embed(md)
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(out.relative_to(ROOT).as_posix())
    return 0


def main() -> int:
    """
    Implement ``main`` for the surrounding module workflow.

    Module context: ``'fy'-suites/despaghettify/tools/wave_plan_emit.py`` — keep this
    routine aligned with sibling helpers in the same package.

    Returns:
        Value typed as ``int`` for downstream use.

    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_jm = sub.add_parser("json2md", help="Write Markdown (fenced JSON + table) from wave_plan.json")
    p_jm.add_argument("--json", required=True)
    p_jm.add_argument("--out", default="", help="output .md path (repo-relative); default stdout table+fence to stdout if empty")
    p_jm.add_argument("--table-only", action="store_true", help="omit fenced JSON block")
    p_jm.set_defaults(func=cmd_json2md)

    p_mj = sub.add_parser("md2json", help="Extract JSON from fenced block or parse wave table")
    p_mj.add_argument("--md", required=True)
    p_mj.add_argument("--out", required=True)
    p_mj.add_argument("--from-wave-table", action="store_true", help="parse generated wave table instead of ```json fence")
    p_mj.add_argument("--ds-id", default="DS-000", help="required for --from-wave-table")
    p_mj.add_argument("--slug", default="")
    p_mj.add_argument("--session-date", default="")
    p_mj.set_defaults(func=cmd_md2json)

    args = ap.parse_args()
    if args.cmd == "md2json" and args.from_wave_table:
        if not re.fullmatch(r"(?i)DS-\d+", args.ds_id.strip()):
            print("--ds-id must be DS-<digits> when using --from-wave-table", file=sys.stderr)
            return 3
    try:
        return int(args.func(args))
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
