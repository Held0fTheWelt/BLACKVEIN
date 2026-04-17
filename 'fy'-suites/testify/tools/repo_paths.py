from __future__ import annotations

import os
from pathlib import Path

from fy_platform.core.project_resolver import resolve_project_root

FY_SUITES_DIRNAME = "'fy'-suites"


def repo_root(*, start: Path | None = None) -> Path:
    env = os.environ.get('TESTIFY_REPO_ROOT', '').strip()
    if env:
        forced = Path(env).expanduser().resolve()
        if forced.is_dir():
            return forced
    return resolve_project_root(start=start, marker_text=None)


def testify_hub_dir(repo: Path | None = None) -> Path:
    r = repo or repo_root()
    return r / FY_SUITES_DIRNAME / 'testify'
