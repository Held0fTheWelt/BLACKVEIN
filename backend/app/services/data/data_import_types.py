"""Shared types for data import/preflight — cycle-breaking leaf module.

Extracted from data_import_service.py to break the bidirectional import cycle
between data_import_service and data_import_preflight.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ImportIssue:
    code: str
    message: str
    table: Optional[str] = None


@dataclass
class ImportPreflightResult:
    ok: bool
    issues: List[ImportIssue]
    metadata: Dict[str, Any]
