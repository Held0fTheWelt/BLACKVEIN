"""Perspective-specific deterministic aspect extraction."""

from __future__ import annotations

import re
from typing import Any

from ai_stack.research_contract import Perspective


_WORD_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in tokens)


def _token_count(text: str) -> int:
    return len(_WORD_RE.findall(text.lower()))


PERSPECTIVE_RULES: dict[Perspective, tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]] = {
    Perspective.PLAYWRIGHT: (
        ("scene_function", ("purpose", "turning point", "scene"), ("dramatic_function",)),
        ("conflict", ("conflict", "argue", "tension", "pressure"), ("conflict",)),
        ("setup_payoff", ("setup", "payoff", "foreshadow"), ("structure", "payoff")),
    ),
    Perspective.DIRECTOR: (
        ("staging_opportunity", ("stage", "position", "space", "visual"), ("staging",)),
        ("tempo_contrast", ("tempo", "rhythm", "contrast"), ("tempo",)),
        ("power_dynamic", ("power", "status", "dominance"), ("power", "status")),
    ),
    Perspective.ACTOR: (
        ("objective_block", ("want", "objective", "block", "obstacle"), ("objective",)),
        ("tactic_shift", ("tactic", "switch", "change strategy"), ("tactic",)),
        ("beat_shift", ("beat", "shift", "turn"), ("beat",)),
    ),
    Perspective.DRAMATURG: (
        ("redundancy", ("redundant", "repeat", "repetition"), ("redundancy",)),
        ("coherence_gap", ("unclear", "coherent", "imbalance"), ("clarity",)),
        ("theme_pressure", ("theme", "motif", "meaning"), ("theme",)),
    ),
}


def extract_perspective_aspects(
    *,
    source_id: str,
    segments: list[dict[str, Any]],
    aspect_id_factory: callable,
) -> list[dict[str, Any]]:
    """Extract deterministic aspect records from segments across all perspectives."""
    aspects: list[dict[str, Any]] = []
    ordered_segments = sorted(segments, key=lambda s: str(s.get("segment_ref", "")))

    for perspective in Perspective:
        rules = PERSPECTIVE_RULES[perspective]
        for segment in ordered_segments:
            text = str(segment.get("text", "")).strip()
            anchor_ids = segment.get("anchor_ids") or []
            if not text or not isinstance(anchor_ids, list) or not anchor_ids:
                continue
            for aspect_type, keywords, tags in rules:
                if _contains_any(text, keywords):
                    snippet = text[:220].strip()
                    aspects.append(
                        {
                            "aspect_id": aspect_id_factory("aspect"),
                            "source_id": source_id,
                            "perspective": perspective.value,
                            "aspect_type": aspect_type,
                            "statement": f"{perspective.value}:{aspect_type}:{snippet}",
                            "evidence_anchor_ids": list(anchor_ids),
                            "tags": sorted(set(tags)),
                            "status": "exploratory",
                        }
                    )

    # Deterministic fallback: guarantee perspective coverage even on sparse text.
    if not aspects:
        for perspective in Perspective:
            first = ordered_segments[0] if ordered_segments else {"segment_ref": "seg_0001", "anchor_ids": []}
            anchor_ids = list(first.get("anchor_ids") or [])
            if not anchor_ids:
                continue
            aspects.append(
                {
                    "aspect_id": aspect_id_factory("aspect"),
                    "source_id": source_id,
                    "perspective": perspective.value,
                    "aspect_type": "baseline_observation",
                    "statement": f"{perspective.value}:baseline_observation",
                    "evidence_anchor_ids": anchor_ids,
                    "tags": ["baseline"],
                    "status": "exploratory",
                }
            )

    # Stable dedup by (perspective, aspect_type, statement, anchors).
    dedup: dict[tuple[Any, ...], dict[str, Any]] = {}
    for aspect in aspects:
        key = (
            aspect["perspective"],
            aspect["aspect_type"],
            aspect["statement"],
            tuple(aspect["evidence_anchor_ids"]),
        )
        dedup[key] = aspect
    ordered = sorted(
        dedup.values(),
        key=lambda row: (
            row["perspective"],
            row["aspect_type"],
            row["statement"],
            row["aspect_id"],
        ),
    )

    # Keep deterministic bounded output: at most 6 per perspective.
    per_perspective: dict[str, int] = {}
    bounded: list[dict[str, Any]] = []
    for row in ordered:
        perspective = row["perspective"]
        count = per_perspective.get(perspective, 0)
        if count >= 6:
            continue
        per_perspective[perspective] = count + 1
        bounded.append(row)
    return bounded


def summarize_segment_for_anchor(text: str, *, max_len: int = 180) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."


def segment_text_deterministically(text: str, *, target_words: int = 90, overlap_words: int = 15) -> list[str]:
    words = _WORD_RE.findall(text)
    if not words:
        return []
    step = max(1, target_words - overlap_words)
    segments: list[str] = []
    start = 0
    while start < len(words):
        chunk_words = words[start : start + target_words]
        if not chunk_words:
            break
        segments.append(" ".join(chunk_words))
        start += step
    return segments


def estimate_anchor_confidence(segment_text: str) -> float:
    count = _token_count(segment_text)
    if count <= 20:
        return 0.62
    if count <= 60:
        return 0.74
    return 0.86
