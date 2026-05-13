"""Versioned YAML fixtures for tests/gates (single oracle source for prose blobs).

Gate tests import this module after conftest appends ``tests/gates`` to ``sys.path``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def load_yaml(name: str) -> Any:
    path = _FIXTURE_DIR / name
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"Empty gate fixture: {path}")
    return data
