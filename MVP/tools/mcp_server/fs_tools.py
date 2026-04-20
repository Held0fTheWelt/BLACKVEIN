"""Filesystem utilities for module and content operations."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.mcp_server.config import Config


def list_modules(repo_root: Optional[Path] = None) -> List[str]:
    """List available modules under content/modules/."""
    if repo_root is None:
        config = Config()
        repo_root = config.repo_root
    else:
        repo_root = Path(repo_root)

    modules_dir = repo_root / "content" / "modules"
    if not modules_dir.exists():
        return []
    return sorted([d.name for d in modules_dir.iterdir() if d.is_dir()])


def get_module(module_id: str, repo_root: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Get module metadata including file list."""
    if repo_root is None:
        config = Config()
        repo_root = config.repo_root
    else:
        repo_root = Path(repo_root)

    module_path = repo_root / "content" / "modules" / module_id
    if not module_path.exists():
        return None

    files = []
    for file in sorted(module_path.rglob("*")):
        if file.is_file():
            files.append(str(file.relative_to(module_path)))

    return {
        "name": module_id,
        "path": str(module_path.relative_to(repo_root)),
        "files": files,
    }


def search_content(
    pattern: str,
    repo_root: Optional[Path] = None,
    case_sensitive: bool = False,
    max_file_size_mb: int = 10,
    max_hits: int = 100,
) -> List[Dict[str, Any]]:
    """Search content with regex pattern."""
    if repo_root is None:
        config = Config()
        repo_root = config.repo_root
    else:
        repo_root = Path(repo_root)

    search_dirs = [
        repo_root / "content" / "modules",
        repo_root / "content" / "direction",
    ]

    max_file_size = max_file_size_mb * 1024 * 1024
    flags = 0 if case_sensitive else re.IGNORECASE

    try:
        regex = re.compile(pattern, flags)
    except re.error:
        return []

    results = []
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for file_path in search_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.stat().st_size > max_file_size:
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append({
                                "file": str(file_path.relative_to(repo_root)),
                                "line": line_num,
                                "text": line.rstrip(),
                            })
                            if len(results) >= max_hits:
                                return results
            except (IOError, UnicodeDecodeError):
                continue

    return results


class FileSystemTools:
    """Filesystem utilities for module discovery and content searching."""

    def __init__(self, config: Config):
        self.config = config

    def list_modules(self) -> List[str]:
        """List available modules under content/modules/."""
        return list_modules(self.config.repo_root)

    def get_module(self, module_id: str) -> Dict[str, Any]:
        """Get module metadata including file list."""
        result = get_module(module_id, self.config.repo_root)
        if result is None:
            return {"error": f"Module {module_id} not found"}
        return result

    def search_content(self, pattern: str, case_sensitive: bool = False) -> Dict[str, Any]:
        """Search content with regex pattern."""
        results = search_content(
            pattern,
            repo_root=self.config.repo_root,
            case_sensitive=case_sensitive,
            max_file_size_mb=10,
            max_hits=100,
        )
        return {
            "pattern": pattern,
            "hits": len(results),
            "results": results,
        }
