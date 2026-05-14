"""Generic visible block origin metadata contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


VISIBLE_ORIGIN_SCHEMA_VERSION = "visible_block_origin.v1"

ORIGIN_BEAT = "beat"
ORIGIN_NARRATOR_AUTHORITY = "narrator_authority"
ORIGIN_NPC_AUTHORITY = "npc_authority"
ORIGIN_CAPABILITY = "capability"
ORIGIN_ACTION_CONSEQUENCE = "action_consequence"
ORIGIN_OPENING = "opening"
ORIGIN_INPUT = "input"
ORIGIN_VISIBLE_PROJECTION = "visible_projection"

EVIDENCE_REQUIRED = "required"
EVIDENCE_SUPPORTING = "supporting"
EVIDENCE_DIAGNOSTIC = "diagnostic"
EVIDENCE_FALLBACK = "fallback"

REQUIRED_VISIBLE_ORIGIN_KEYS: tuple[str, ...] = (
    "origin_aspect",
    "origin_beat_id",
    "origin_capability",
    "authority_owner",
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


@dataclass(frozen=True)
class VisibleBlockOrigin:
    schema_version: str = VISIBLE_ORIGIN_SCHEMA_VERSION
    origin_aspect: str | None = None
    origin_beat_id: str | None = None
    origin_capability: str | None = None
    authority_owner: str | None = None
    expected_owner: str | None = None
    actual_owner: str | None = None
    canonical_turn_id: str | None = None
    evidence_role: str = EVIDENCE_SUPPORTING

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


def visible_origin_from_block(block: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _json_safe(block.get(key))
        for key in (
            "origin_aspect",
            "origin_beat_id",
            "origin_capability",
            "authority_owner",
            "expected_owner",
            "actual_owner",
            "canonical_turn_id",
            "evidence_role",
        )
        if key in block
    }


def block_has_required_origin(block: dict[str, Any]) -> bool:
    return all(key in block for key in REQUIRED_VISIBLE_ORIGIN_KEYS)


def preserve_folded_origin_metadata(
    surviving_block: dict[str, Any],
    folded_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Attach origin evidence from folded blocks to the surviving block."""
    out = dict(surviving_block)
    origins = []
    existing = out.get("folded_origin_evidence")
    if isinstance(existing, list):
        origins.extend(item for item in existing if isinstance(item, dict))
    for block in folded_blocks:
        if isinstance(block, dict):
            origin = visible_origin_from_block(block)
            if origin and origin not in origins:
                origins.append(origin)
    if origins:
        out["folded_origin_evidence"] = origins
        for key in REQUIRED_VISIBLE_ORIGIN_KEYS:
            if key not in out:
                for origin in origins:
                    if origin.get(key) is not None:
                        out[key] = origin.get(key)
                        break
    return out
