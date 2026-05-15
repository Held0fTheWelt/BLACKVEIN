"""Load per-module action ontology (verb patterns -> verb + action_kind)."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from story_runtime_core.content_locale import resolve_content_modules_root
from story_runtime_core.player_input_intent_contract import (
    is_perception_like_player_input_kind,
    is_speech_like_player_input_kind,
)


@lru_cache(maxsize=32)
def _load_ontology_cached(path_s: str) -> dict[str, Any]:
    p = Path(path_s)
    if not p.is_file():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def clear_action_ontology_cache() -> None:
    _load_ontology_cached.cache_clear()


def ontology_path(module_id: str, *, content_modules_root: Path | None = None) -> Path:
    root = resolve_content_modules_root(content_modules_root)
    return root / str(module_id).strip() / "locale" / "action_ontology.yaml"


def infer_verb_and_action_kind(
    raw_text: str,
    *,
    module_id: str,
    player_input_kind: str,
    content_modules_root: Path | None = None,
) -> tuple[str, str]:
    """Return (verb, action_kind) using YAML ontology; fallback heuristics for speech/question."""
    pik = str(player_input_kind or "speech").strip().lower() or "speech"
    text = str(raw_text or "")
    if is_speech_like_player_input_kind(pik) or pik == "meta":
        low = text.strip().lower()
        if low.endswith("?"):
            return "ask", "speech"
        return "say", "speech"

    data = _load_ontology_cached(str(ontology_path(module_id, content_modules_root=content_modules_root)))
    priority = data.get("priority_order")
    if not isinstance(priority, list):
        priority = ["movement", "perception", "social_action", "manipulation", "speech"]
    kinds = data.get("action_kinds") if isinstance(data.get("action_kinds"), dict) else {}

    for kind in priority:
        kind = str(kind).strip()
        block = kinds.get(kind) if isinstance(kinds.get(kind), dict) else {}
        verb_map = block.get("verb_map") if isinstance(block.get("verb_map"), list) else []
        for row in verb_map:
            if not isinstance(row, dict):
                continue
            verb = str(row.get("verb") or "").strip()
            pats = row.get("patterns") if isinstance(row.get("patterns"), list) else []
            for pat in pats:
                if not isinstance(pat, str) or not pat.strip():
                    continue
                try:
                    if re.search(pat.strip(), text):
                        return verb or "interact", kind
                except re.error:
                    continue

    if is_perception_like_player_input_kind(pik):
        return "look_at", "perception"
    if pik == "action":
        return "interact", "movement"
    return "say", "speech"
