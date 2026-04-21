#!/usr/bin/env python3
"""
MVP re-integration Phase 1: freeze intake baseline, file manifest, and inventory/mapping stubs.

Reads every file under --mvp-root and emits:
  - source_baseline_lock.txt
  - raw/mvp_source_file_manifest.tsv
  - mvp_source_inventory.md
  - source_to_destination_mapping_table.md

Disposition and destination mapping use conservative heuristics; rows marked
`pending_verification` until human/agent reconciliation (Phase 2–3).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


OMIT_PREFIXES = (
    "__pycache__/",
    ".pytest_cache/",
    ".git/",
    ".wos/",
    "world_of_shadows_hub.egg-info/",
    ".fydata/",
    "node_modules/",
)

OMIT_SUFFIXES = (
    ".pyc",
)


def _is_omit_path(rel_posix: str) -> tuple[bool, str]:
    lower = rel_posix.lower()
    for p in OMIT_PREFIXES:
        if rel_posix.startswith(p) or f"/{p}" in f"/{rel_posix}":
            return True, f"path matches omit prefix `{p}`"
    for suf in OMIT_SUFFIXES:
        if lower.endswith(suf):
            return True, f"suffix `{suf}`"
    if rel_posix.endswith(".db") and ".fydata/" in rel_posix:
        return True, "generated .fydata database"
    if rel_posix == ".coverage" or rel_posix.endswith("/.coverage"):
        return True, "coverage artifact"
    return False, ""


def _destination_for(rel_posix: str) -> tuple[str, str, str]:
    """
    Returns (classification, destination_relpath_or_n_a, disposition).

    classification is one of: MIGRATE_DIRECT, MERGE_INTO_SECTION, PRESERVE_AS_REFERENCE, OMIT_WITH_JUSTIFICATION
    """
    omit, why = _is_omit_path(rel_posix)
    if omit:
        return "OMIT_WITH_JUSTIFICATION", "n/a", why

    # Root-level MVP snapshot files -> repo root
    if "/" not in rel_posix:
        name = rel_posix
        if name in {".gitignore", ".dockerignore", ".mcp.json", ".env.example"}:
            return "MIGRATE_DIRECT", name, ""
        if name in {"pyproject.toml", "docker-compose.yml", "README.md", "AGENTS.md", "conftest.py"}:
            return "MERGE_INTO_SECTION", name, "root-level overlap with active repo; merge required"
        if name.startswith("CHANGED_FILES") or name in {"CURRENT_STATE.md", "CHANGELOG.md"}:
            return "PRESERVE_AS_REFERENCE", "docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/migration_report.md", "historical / packaging evidence"
        if name.endswith(".md") and "MVP" in name:
            return "MERGE_INTO_SECTION", "docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/README.md", "canonical bundle absorbs MVP entry docs"
        return "MIGRATE_DIRECT", name, ""

    top, _, rest = rel_posix.partition("/")

    direct_domains = (
        "backend",
        "world-engine",
        "ai_stack",
        "frontend",
        "administration-tool",
        "story_runtime_core",
        "content",
        "docker",
        "postman",
        "schemas",
        "scripts",
        "tests",
        "tools",
        "validation",
        "writers-room",
        "governance",
        "mvp",
        "repo",
        "runtime_data",
        "evidence",
    )
    if top in direct_domains:
        dest = f"{top}/{rest}" if rest else top
        return "MIGRATE_DIRECT", dest, ""

    if top == "docs":
        return "MERGE_INTO_SECTION", f"docs/{rest}" if rest else "docs/", "docs merge; avoid blind overwrite"

    if top == "'fy'-suites":
        dest = rel_posix  # same relative under repo root
        return "MIGRATE_DIRECT", dest, ""

    if top == "story_runtime_core":
        return "MIGRATE_DIRECT", rel_posix, ""

    return "PRESERVE_AS_REFERENCE", "docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/migration_report.md", "unmapped top-level domain; route via migration report"


def _file_type(name: str) -> str:
    if "." in name:
        return name.rsplit(".", 1)[-1].lower() or "none"
    return "none"


@dataclass(frozen=True)
class FileRow:
    rel: str
    size: int
    mtime_ns: int


def gather_files(mvp_root: Path) -> list[FileRow]:
    rows: list[FileRow] = []
    for p in mvp_root.rglob("*"):
        if not p.is_file():
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        rel = p.relative_to(mvp_root).as_posix()
        rows.append(FileRow(rel=rel, size=st.st_size, mtime_ns=int(st.st_mtime_ns)))
    rows.sort(key=lambda r: r.rel)
    return rows


def list_sha256(rels: list[str]) -> str:
    h = hashlib.sha256()
    for rel in rels:
        h.update(rel.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def write_baseline(out_dir: Path, mvp_root: Path, rows: list[FileRow]) -> None:
    rels = [r.rel for r in rows]
    lock = {
        "baseline_timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mvp_root_resolved": str(mvp_root.resolve()),
        "source_root_display": "MVP/",
        "source_file_count": len(rows),
        "source_file_list_sha256": list_sha256(rels),
        "workspace_mvp_note": "If repository contains MVP/ as a working copy, compare counts and hash to this baseline before integration.",
    }
    (out_dir / "source_baseline_lock.txt").write_text(
        "\n".join(f"{k}: {v}" for k, v in lock.items()) + "\n", encoding="utf-8"
    )
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = raw_dir / "mvp_source_file_manifest.tsv"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("relative_path\tsize_bytes\tmtime_ns\n")
        for r in rows:
            fh.write(f"{r.rel}\t{r.size}\t{r.mtime_ns}\n")


def write_inventory_and_mapping(out_dir: Path, rows: list[FileRow]) -> None:
    inv_path = out_dir / "mvp_source_inventory.md"
    map_path = out_dir / "source_to_destination_mapping_table.md"

    inv_lines = [
        "# mvp_source_inventory",
        "",
        f"Total source files: {len(rows)}",
        "",
        "Machine-readable manifest: `raw/mvp_source_file_manifest.tsv`.",
        "",
        "| source path | file type | topic / intent | unique substance | overlap notes | recommended disposition |",
        "|---|---|---|---|---|---|",
    ]
    map_lines = [
        "# source_to_destination_mapping_table",
        "",
        f"Total source files: {len(rows)}",
        "",
        "| source path | file type | topic / content role | classification | unique substance present | destination file | destination section | merge target or reference target if not direct migration | omission justification if omitted | verification status |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for r in rows:
        name = Path(r.rel).name
        ext = _file_type(name)
        cls, dest, note = _destination_for(r.rel)
        disp = cls
        topic = "MVP snapshot subtree"
        substance = "yes" if r.size > 0 else "no"
        overlap = "Requires reconciliation against active repo target" if cls in {"MIGRATE_DIRECT", "MERGE_INTO_SECTION"} else "n/a"
        inv_lines.append(
            "| `{prefix}{rel}` | `{ext}` | {topic} | {substance} | {overlap} | `{disp}` |".format(
                prefix="MVP/",
                rel=r.rel.replace("`", "'"),
                ext=ext,
                topic=topic,
                substance=substance,
                overlap=overlap,
                disp=disp,
            )
        )
        omit_just = note if disp == "OMIT_WITH_JUSTIFICATION" else "n/a"
        dest_cell = dest if dest != "n/a" else "n/a"
        map_lines.append(
            "| `{prefix}{rel}` | `{ext}` | {topic} | `{cls}` | {substance} | `{dest}` | n/a | n/a | {omit} | `pending_verification` |".format(
                prefix="MVP/",
                rel=r.rel.replace("`", "'"),
                ext=ext,
                topic=topic,
                cls=cls,
                substance=substance,
                dest=dest_cell.replace("`", "'"),
                omit=omit_just.replace("`", "'"),
            )
        )

    inv_path.write_text("\n".join(inv_lines) + "\n", encoding="utf-8")
    map_path.write_text("\n".join(map_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="MVP intake baseline generator")
    parser.add_argument(
        "--mvp-root",
        type=Path,
        required=True,
        help="Absolute path to recreated MVP/ tree (source snapshot root).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Canonical bundle directory for emitted artifacts.",
    )
    args = parser.parse_args()
    mvp_root: Path = args.mvp_root
    out_dir: Path = args.out_dir
    if not mvp_root.is_dir():
        raise SystemExit(f"mvp root is not a directory: {mvp_root}")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = gather_files(mvp_root)
    write_baseline(out_dir, mvp_root, rows)
    write_inventory_and_mapping(out_dir, rows)
    summary = {
        "ok": True,
        "mvp_root": str(mvp_root.resolve()),
        "file_count": len(rows),
        "list_sha256": list_sha256([r.rel for r in rows]),
        "outputs": {
            "source_baseline_lock": str((out_dir / "source_baseline_lock.txt").resolve()),
            "manifest": str((out_dir / "raw" / "mvp_source_file_manifest.tsv").resolve()),
            "mvp_source_inventory": str((out_dir / "mvp_source_inventory.md").resolve()),
            "source_to_destination_mapping_table": str((out_dir / "source_to_destination_mapping_table.md").resolve()),
        },
    }
    (out_dir / "raw" / "mvp_intake_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
