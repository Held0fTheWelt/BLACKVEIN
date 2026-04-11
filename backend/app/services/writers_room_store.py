"""Writers Room on-disk review storage (single module; DS-002 follow-up)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class WritersRoomStore:
    root: Path

    @classmethod
    def default(cls) -> "WritersRoomStore":
        root = Path(__file__).resolve().parents[2] / "var" / "writers_room"
        return cls(root=root)

    def ensure_dirs(self) -> None:
        (self.root / "reviews").mkdir(parents=True, exist_ok=True)

    def write_review(self, review_id: str, payload: dict[str, Any]) -> Path:
        self.ensure_dirs()
        path = self.root / "reviews" / f"{review_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return path

    def read_review(self, review_id: str) -> dict[str, Any]:
        path = self.root / "reviews" / f"{review_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))
