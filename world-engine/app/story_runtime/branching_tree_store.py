"""Durable JSON persistence for selectable branching tree records."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.runtime.json_at_rest import JsonAtRestCodec, associated_data


class JsonBranchingTreeStore:
    """Atomic JSON file per branching tree id."""

    backend_name = "json"

    def __init__(self, root: Path, *, codec: JsonAtRestCodec | None = None) -> None:
        self.root = root
        self.codec = codec or JsonAtRestCodec.plain()
        self.backend_name = self.codec.backend_name("json")
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, tree_id: str) -> Path:
        return self.codec.path_for(self.root, tree_id)

    def _aad(self, tree_id: str) -> bytes:
        return associated_data("branching-tree", tree_id)

    def save(self, tree_id: str, payload: dict[str, Any]) -> None:
        destination = self.path_for(tree_id)
        temp_path = destination.with_suffix(destination.suffix + ".tmp")
        temp_path.write_text(self.codec.dumps(payload, aad=self._aad(tree_id)), encoding="utf-8")
        temp_path.replace(destination)

    def load(self, tree_id: str) -> dict[str, Any]:
        path = self.path_for(tree_id)
        data = self.codec.loads(path.read_text(encoding="utf-8"), aad=self._aad(tree_id))
        if not isinstance(data, dict):
            raise ValueError("branching_tree_payload_not_object")
        return data

    def load_all_raw(self) -> dict[str, dict[str, Any]]:
        """Load every ``*.json`` branch tree snapshot in root."""

        out: dict[str, dict[str, Any]] = {}
        for path in sorted(self.root.glob(f"*{self.codec.extension}")):
            try:
                tree_id = path.name.removesuffix(self.codec.extension)
                data = self.codec.loads(path.read_text(encoding="utf-8"), aad=self._aad(tree_id))
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
        for suffix in (".json", ".json.enc"):
            path = self.root / f"{tree_id}{suffix}"
            if path.exists():
                path.unlink()

    def describe(self) -> dict[str, str]:
        return {
            "backend": self.backend_name,
            "root": str(self.root),
            "encrypted_at_rest": "yes" if self.codec.encrypted else "no",
        }
