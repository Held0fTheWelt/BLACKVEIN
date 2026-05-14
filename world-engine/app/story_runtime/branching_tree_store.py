"""Durable JSON persistence for selectable branching tree records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonBranchingTreeStore:
    """Atomic JSON file per branching tree id."""

    backend_name = "json"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, tree_id: str) -> Path:
        return self.root / f"{tree_id}.json"

    def save(self, tree_id: str, payload: dict[str, Any]) -> None:
        destination = self.path_for(tree_id)
        temp_path = destination.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_path.replace(destination)

    def load(self, tree_id: str) -> dict[str, Any]:
        path = self.path_for(tree_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("branching_tree_payload_not_object")
        return data

    def load_all_raw(self) -> dict[str, dict[str, Any]]:
        """Load every ``*.json`` branch tree snapshot in root."""

        out: dict[str, dict[str, Any]] = {}
        for path in sorted(self.root.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and isinstance(data.get("tree_id"), str):
                    out[data["tree_id"]] = data
            except Exception:
                continue
        return out

    def load_for_session(self, session_id: str) -> list[dict[str, Any]]:
        rows = [
            payload
            for payload in self.load_all_raw().values()
            if isinstance(payload, dict) and payload.get("story_session_id") == session_id
        ]
        rows.sort(key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""), reverse=True)
        return rows

    def delete(self, tree_id: str) -> None:
        path = self.path_for(tree_id)
        if path.exists():
            path.unlink()

    def describe(self) -> dict[str, str]:
        return {"backend": self.backend_name, "root": str(self.root)}
