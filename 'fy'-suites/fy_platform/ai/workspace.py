from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    out = []
    for ch in value.lower():
        out.append(ch if ch.isalnum() else '-')
    text = ''.join(out).strip('-')
    while '--' in text:
        text = text.replace('--', '-')
    return text or 'unknown'


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_text_safe(path: Path) -> str:
    return path.read_text(encoding='utf-8', errors='replace')


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def workspace_root(start: Path | None = None) -> Path:
    start = (start or Path(__file__)).resolve()
    for ancestor in [start, *start.parents]:
        if ancestor.is_dir() and (ancestor / 'fy_governance_enforcement.yaml').is_file():
            return ancestor
        if ancestor.is_dir() and (ancestor / 'README.md').is_file() and (ancestor / 'fy_platform').is_dir():
            return ancestor
    raise RuntimeError(f'Could not resolve fy workspace root from {start}')


def ensure_workspace_layout(root: Path) -> dict[str, list[str] | str]:
    created: list[str] = []
    for rel in [
        '.fydata/registry/objects',
        '.fydata/index',
        '.fydata/journal',
        '.fydata/runs',
        '.fydata/cache',
        '.fydata/bindings',
    ]:
        p = root / rel
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created.append(rel)
    return {'workspace_root': str(root), 'created': created}


def target_repo_id(target_repo_root: Path) -> str:
    return slugify(target_repo_root.name) + '-' + sha256_text(str(target_repo_root.resolve()))[:8]


def suite_hub_dir(workspace: Path, suite: str) -> Path:
    return workspace / suite


def internal_run_dir(workspace: Path, suite: str, run_id: str) -> Path:
    return workspace / '.fydata' / 'runs' / suite / run_id


def binding_path(workspace: Path, suite: str) -> Path:
    return workspace / '.fydata' / 'bindings' / f'{suite}.json'
