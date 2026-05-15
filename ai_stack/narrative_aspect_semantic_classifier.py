"""Deterministic semantic classification for policy-defined narrative aspects."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any


SEMANTIC_CLASSIFIER_VERSION = "narrative_aspect_semantic_overlap_v1"
SEMANTIC_POLICY_SOURCE = "narrative_aspect_policy.semantic_profile"

DEFAULT_THRESHOLDS: dict[str, float] = {
    "min_aspect_alignment": 0.25,
    "min_dimension_alignment": 0.20,
    "min_matched_dimensions": 1.0,
}

STOPWORDS = frozenset(
    {
        "about",
        "after",
        "also",
        "and",
        "because",
        "been",
        "being",
        "cannot",
        "could",
        "does",
        "from",
        "have",
        "into",
        "just",
        "more",
        "must",
        "only",
        "over",
        "that",
        "their",
        "them",
        "there",
        "these",
        "they",
        "this",
        "those",
        "when",
        "with",
        "would",
        "your",
        "aber",
        "auch",
        "das",
        "der",
        "die",
        "ein",
        "eine",
        "einen",
        "einer",
        "ist",
        "mit",
        "nicht",
        "oder",
        "sich",
        "und",
        "von",
    }
)

_TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(str(text or "").casefold())
        if len(token) >= 4 and token not in STOPWORDS and not token.isdigit()
    }


def _float_value(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    if parsed < 0:
        return fallback
    return parsed


def _thresholds(policy: dict[str, Any]) -> dict[str, float]:
    raw = policy.get("thresholds") if isinstance(policy.get("thresholds"), dict) else {}
    return {
        key: _float_value(raw.get(key), fallback)
        for key, fallback in DEFAULT_THRESHOLDS.items()
    }


def _visible_block_text(block: dict[str, Any]) -> str:
    if not isinstance(block, dict):
        return ""
    candidates = [
        block.get("text"),
        block.get("line"),
        block.get("content"),
        block.get("narration"),
    ]
    payload = block.get("payload")
    if isinstance(payload, dict):
        candidates.extend([payload.get("text"), payload.get("content")])
    return " ".join(_text(item) for item in candidates if _text(item)).strip()


def _visible_text(blocks: list[dict[str, Any]]) -> str:
    return "\n".join(_visible_block_text(block) for block in blocks if _visible_block_text(block)).strip()


def _stable_text_hash(text: str) -> str:
    normalized = " ".join(_TOKEN_RE.findall(str(text or "").casefold()))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _profile_dimensions(profile: dict[str, Any]) -> dict[str, str]:
    if not isinstance(profile, dict):
        return {}
    return {
        str(key).strip(): _text(value)
        for key, value in profile.items()
        if str(key).strip() and _text(value)
    }


def semantic_profile_enabled(aspect: dict[str, Any]) -> bool:
    if not isinstance(aspect, dict):
        return False
    profile = aspect.get("semantic_profile")
    if not isinstance(profile, dict) or not _profile_dimensions(profile):
        return False
    policy = aspect.get("semantic_policy") if isinstance(aspect.get("semantic_policy"), dict) else {}
    return bool(policy.get("enabled", True))


def _required(aspect: dict[str, Any]) -> bool:
    policy = aspect.get("semantic_policy") if isinstance(aspect.get("semantic_policy"), dict) else {}
    return bool(policy.get("required", False))


def _dimension_score(line_tokens: set[str], profile_tokens: set[str]) -> float:
    if not line_tokens or not profile_tokens:
        return 0.0
    denominator = min(6.0, float(len(profile_tokens)))
    if denominator <= 0:
        return 0.0
    return round(min(1.0, len(line_tokens.intersection(profile_tokens)) / denominator), 3)


@dataclass(frozen=True)
class NarrativeAspectSemanticClassification:
    classifier_version: str
    aspect_id: str
    status: str
    required: bool
    semantic_alignment: float
    dimension_scores: dict[str, float] = field(default_factory=dict)
    matched_dimensions: list[str] = field(default_factory=list)
    finding_codes: list[str] = field(default_factory=list)
    policy_sources: list[str] = field(default_factory=lambda: [SEMANTIC_POLICY_SOURCE])
    table_b_refs: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


def classify_narrative_aspect_semantics(
    *,
    aspects: list[dict[str, Any]],
    selected_aspect_ids: set[str],
    visible_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Classify selected narrative aspects against visible text without prose oracles."""
    text = _visible_text(visible_blocks)
    line_tokens = _tokens(text)
    visible_block_ids = [
        str(block.get("id") or block.get("block_id") or "").strip()
        for block in visible_blocks
        if isinstance(block, dict) and str(block.get("id") or block.get("block_id") or "").strip()
    ]
    classifications: list[dict[str, Any]] = []
    for aspect in aspects:
        if not isinstance(aspect, dict) or not semantic_profile_enabled(aspect):
            continue
        aspect_id = _text(aspect.get("id"))
        if not aspect_id or aspect_id not in selected_aspect_ids:
            continue
        policy = aspect.get("semantic_policy") if isinstance(aspect.get("semantic_policy"), dict) else {}
        thresholds = _thresholds(policy)
        dimensions = _profile_dimensions(aspect.get("semantic_profile") or {})
        dimension_scores = {
            dimension: _dimension_score(line_tokens, _tokens(profile_text))
            for dimension, profile_text in sorted(dimensions.items())
        }
        matched_dimensions = [
            dimension
            for dimension, score in dimension_scores.items()
            if score >= thresholds["min_dimension_alignment"]
        ]
        semantic_alignment = round(
            sum(dimension_scores.values()) / max(len(dimension_scores), 1),
            3,
        )
        passed = (
            bool(visible_blocks)
            and semantic_alignment >= thresholds["min_aspect_alignment"]
            and len(matched_dimensions) >= int(thresholds["min_matched_dimensions"])
        )
        finding_codes: list[str] = []
        if not passed:
            finding_codes.append("weak_theme_alignment")
        metadata = aspect.get("metadata") if isinstance(aspect.get("metadata"), dict) else {}
        table_b_refs = [
            str(item).strip()
            for item in metadata.get("table_b_refs", [])
            if str(item).strip()
        ] if isinstance(metadata.get("table_b_refs"), list) else []
        version = _text(policy.get("classifier_version")) or SEMANTIC_CLASSIFIER_VERSION
        classifications.append(
            NarrativeAspectSemanticClassification(
                classifier_version=version,
                aspect_id=aspect_id,
                status="passed" if passed else "weak",
                required=_required(aspect),
                semantic_alignment=semantic_alignment,
                dimension_scores=dimension_scores,
                matched_dimensions=matched_dimensions,
                finding_codes=finding_codes,
                table_b_refs=table_b_refs,
                evidence={
                    "visible_block_ids": visible_block_ids,
                    "visible_block_count": len(visible_blocks),
                    "visible_text_sha256": _stable_text_hash(text),
                    "visible_token_count": len(line_tokens),
                    "thresholds": thresholds,
                    "low_dimensions": [
                        dimension
                        for dimension, score in dimension_scores.items()
                        if score < thresholds["min_dimension_alignment"]
                    ],
                },
            ).to_dict()
        )
    return classifications
