"""Regex content search over module/direction trees (DS-034) — extracted from ``fs_tools``."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _content_search_roots(repo_root: Path) -> list[Path]:
    return [
        repo_root / "content" / "modules",
        repo_root / "content" / "direction",
    ]


def _append_line_hits_for_file(
    file_path: Path,
    repo_root: Path,
    regex: re.Pattern[str],
    results: list[dict[str, Any]],
    *,
    max_file_size: int,
    max_hits: int,
) -> bool:
    """Scan one file; return True if caller should stop (max_hits reached)."""
    if file_path.stat().st_size > max_file_size:
        return False
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, 1):
                if regex.search(line):
                    results.append(
                        {
                            "file": str(file_path.relative_to(repo_root)),
                            "line": line_num,
                            "text": line.rstrip(),
                        }
                    )
                    if len(results) >= max_hits:
                        return True
    except (OSError, UnicodeDecodeError):
        return False
    return False


def run_content_regex_search(
    pattern: str,
    repo_root: Path,
    *,
    case_sensitive: bool,
    max_file_size_mb: int,
    max_hits: int,
) -> list[dict[str, Any]]:
    """Search ``content/modules`` and ``content/direction`` with a compiled regex."""
    max_file_size = max_file_size_mb * 1024 * 1024
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error:
        return []

    results: list[dict[str, Any]] = []
    for search_dir in _content_search_roots(repo_root):
        if not search_dir.exists():
            continue
        for file_path in search_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if _append_line_hits_for_file(
                file_path,
                repo_root,
                regex,
                results,
                max_file_size=max_file_size,
                max_hits=max_hits,
            ):
                return results
    return results
