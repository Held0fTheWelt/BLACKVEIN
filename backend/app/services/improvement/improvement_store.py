"""ImprovementStore type and shared helpers — cycle-breaking leaf module.

Extracted from improvement_service.py to break the bidirectional import cycle
between improvement_service and improvement_service_recommendation_decision.

This module only imports from stdlib and third-party, not from other app.services.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.utils.time_utils import utc_now_iso as _utc_now


def _backend_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "app" / "services").is_dir():
            return parent
    return current.parents[3]


@dataclass
class ImprovementStore:
    root: Path

    @classmethod
    def default(cls) -> "ImprovementStore":
        root = _backend_root() / "var" / "improvement"
        return cls(root=root)

    def ensure_dirs(self) -> None:
        (self.root / "variants").mkdir(parents=True, exist_ok=True)
        (self.root / "experiments").mkdir(parents=True, exist_ok=True)
        (self.root / "recommendations").mkdir(parents=True, exist_ok=True)

    def write_json(self, category: str, item_id: str, payload: dict[str, Any]) -> Path:
        self.ensure_dirs()
        path = self.root / category / f"{item_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return path

    def read_json(self, category: str, item_id: str) -> dict[str, Any]:
        path = self.root / category / f"{item_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def list_json(self, category: str) -> list[dict[str, Any]]:
        folder = self.root / category
        if not folder.exists():
            return []
        items: list[dict[str, Any]] = []
        for file in sorted(folder.glob("*.json")):
            items.append(json.loads(file.read_text(encoding="utf-8")))
        return items


def _evaluation_metrics_fingerprint(evaluation: dict[str, Any]) -> str:
    metrics = evaluation.get("metrics") if isinstance(evaluation.get("metrics"), dict) else {}
    raw = json.dumps(metrics, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
