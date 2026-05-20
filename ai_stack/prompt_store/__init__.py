"""Central prompt-store helpers shared by backend, ai_stack, and world-engine.

The backend database is the live authority. This module intentionally has no
backend dependency so tests and the play-service can still load the centralized
seed files when no database bundle has been injected.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from string import Formatter
from typing import Any


PROMPT_COLLECTION_SCHEMA_VERSION = "prompt_collection.v1"

_RUNTIME_PROMPT_BUNDLE: dict[str, dict[str, Any]] = {}
_LOCAL_PROMPT_CACHE: dict[str, dict[str, Any]] | None = None


@dataclass(frozen=True)
class PromptDefinition:
    prompt_key: str
    name: str
    category: str
    description: str
    template: str
    prompt_type: str = "runtime_prompt"
    domain: str = "ai_stack"
    tags: tuple[str, ...] = ()
    variables: tuple[str, ...] = ()
    source_path: str = ""
    source_symbol: str = ""
    seed_version: str = ""
    metadata: dict[str, Any] | None = None

    @property
    def content_hash(self) -> str:
        return sha256(self.template.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_key": self.prompt_key,
            "id": self.prompt_key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "template": self.template,
            "prompt_type": self.prompt_type,
            "domain": self.domain,
            "tags": list(self.tags),
            "variables": list(self.variables),
            "source_path": self.source_path,
            "source_symbol": self.source_symbol,
            "seed_version": self.seed_version,
            "content_hash": self.content_hash,
            "metadata": dict(self.metadata or {}),
        }


def _repo_root() -> Path:
    env_root = (os.getenv("WOS_REPO_ROOT") or "").strip()
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[2]


def default_prompt_root() -> Path:
    env_root = (os.getenv("WOS_PROMPT_STORE_DIR") or "").strip()
    if env_root:
        return Path(env_root)
    return _repo_root() / "prompts"


def _coerce_variables(raw: Any, template: str) -> tuple[str, ...]:
    if isinstance(raw, list):
        values = [str(item).strip() for item in raw if str(item).strip()]
    else:
        values = []
    if values:
        return tuple(dict.fromkeys(values))

    inferred: list[str] = []
    for _, field_name, _, _ in Formatter().parse(template):
        if not field_name:
            continue
        root = field_name.split(".", 1)[0].split("[", 1)[0].strip()
        if root and root not in inferred:
            inferred.append(root)
    return tuple(inferred)


def _coerce_tags(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(dict.fromkeys(str(item).strip() for item in raw if str(item).strip()))


def normalize_prompt_definition(raw: dict[str, Any], *, source_file: Path | None = None) -> PromptDefinition:
    if isinstance(raw.get("template_lines"), list):
        template = "\n".join(str(line) for line in raw.get("template_lines") or [])
    else:
        template = str(raw.get("template") or "")
    prompt_key = str(raw.get("prompt_key") or raw.get("id") or raw.get("key") or "").strip()
    if not prompt_key:
        raise ValueError("Prompt definition missing prompt_key")
    if not template:
        raise ValueError(f"Prompt {prompt_key!r} has an empty template")
    source_path = str(raw.get("source_path") or "").strip()
    if not source_path and source_file is not None:
        source_path = str(source_file)
    metadata = dict(raw.get("metadata") or {}) if isinstance(raw.get("metadata"), dict) else {}
    prompt_type = str(raw.get("prompt_type") or metadata.get("prompt_type") or "runtime_prompt").strip()
    domain = str(raw.get("domain") or metadata.get("domain") or "ai_stack").strip()
    tags = _coerce_tags(raw.get("tags") if "tags" in raw else metadata.get("tags"))
    return PromptDefinition(
        prompt_key=prompt_key,
        name=str(raw.get("name") or prompt_key).strip(),
        category=str(raw.get("category") or "uncategorized").strip(),
        description=str(raw.get("description") or "").strip(),
        template=template,
        prompt_type=prompt_type or "runtime_prompt",
        domain=domain or "ai_stack",
        tags=tags,
        variables=_coerce_variables(raw.get("variables"), template),
        source_path=source_path,
        source_symbol=str(raw.get("source_symbol") or "").strip(),
        seed_version=str(raw.get("seed_version") or "").strip(),
        metadata=metadata,
    )


def load_prompt_files(root: Path | str | None = None) -> list[PromptDefinition]:
    prompt_root = Path(root) if root is not None else default_prompt_root()
    if not prompt_root.exists():
        return []
    loaded: list[PromptDefinition] = []
    for path in sorted(prompt_root.rglob("*.json")):
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        seed_version = ""
        if isinstance(payload, dict):
            seed_version = str(payload.get("seed_version") or "").strip()
            raw_prompts = payload.get("prompts")
        else:
            raw_prompts = payload
        if not isinstance(raw_prompts, list):
            raise ValueError(f"Prompt seed file {path} must contain a prompts list")
        for raw in raw_prompts:
            if not isinstance(raw, dict):
                raise ValueError(f"Prompt seed file {path} contains a non-object prompt")
            item = dict(raw)
            if seed_version and not item.get("seed_version"):
                item["seed_version"] = seed_version
            loaded.append(normalize_prompt_definition(item, source_file=path))
    return loaded


def configure_prompt_bundle(bundle: dict[str, Any] | list[dict[str, Any]] | None) -> None:
    """Install a runtime prompt bundle fetched from the backend database."""
    global _RUNTIME_PROMPT_BUNDLE
    raw_prompts: Any
    if isinstance(bundle, dict):
        raw_prompts = bundle.get("prompts")
    else:
        raw_prompts = bundle
    prompts: dict[str, dict[str, Any]] = {}
    if isinstance(raw_prompts, list):
        for raw in raw_prompts:
            if not isinstance(raw, dict):
                continue
            try:
                definition = normalize_prompt_definition(raw)
            except ValueError:
                continue
            prompts[definition.prompt_key] = definition.to_dict()
    _RUNTIME_PROMPT_BUNDLE = prompts


def reset_prompt_caches() -> None:
    global _LOCAL_PROMPT_CACHE
    _LOCAL_PROMPT_CACHE = None
    _RUNTIME_PROMPT_BUNDLE.clear()


def _local_prompt_map() -> dict[str, dict[str, Any]]:
    global _LOCAL_PROMPT_CACHE
    if _LOCAL_PROMPT_CACHE is None:
        _LOCAL_PROMPT_CACHE = {
            item.prompt_key: item.to_dict()
            for item in load_prompt_files()
        }
    return _LOCAL_PROMPT_CACHE


def get_prompt_definition(prompt_key: str) -> dict[str, Any]:
    key = str(prompt_key or "").strip()
    if not key:
        raise KeyError("Prompt key is required")
    if key in _RUNTIME_PROMPT_BUNDLE:
        return deepcopy(_RUNTIME_PROMPT_BUNDLE[key])
    local = _local_prompt_map()
    if key in local:
        return deepcopy(local[key])
    raise KeyError(f"Prompt {key!r} not found in prompt store")


def list_prompt_definitions() -> list[dict[str, Any]]:
    merged = dict(_local_prompt_map())
    merged.update(_RUNTIME_PROMPT_BUNDLE)
    return [deepcopy(merged[key]) for key in sorted(merged)]


def render_prompt(prompt_key: str, **variables: Any) -> str:
    template = str(get_prompt_definition(prompt_key).get("template") or "")
    return template.format(**variables)


def render_prompt_lines(prompt_key: str, **variables: Any) -> list[str]:
    text = render_prompt(prompt_key, **variables).strip()
    return text.splitlines() if text else []
