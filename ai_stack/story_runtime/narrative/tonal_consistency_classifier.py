"""Deterministic tonal-consistency classifier for hard live drift checks.

The classifier reads only policy-declared marker classes and visible structured
output. It intentionally does not trust generator-supplied tone labels as the
hard oracle.
"""

from __future__ import annotations

import re
from typing import Any

from ai_stack.contracts.tonal_consistency_contracts import (
    TONAL_CONSISTENCY_DEFAULT_CLASSIFICATION_SOURCE,
    TONAL_CONSISTENCY_SCHEMA_VERSION,
    TonalConsistencyClassification,
    TonalConsistencyEvidenceRef,
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value is None:
        return []
    return [value]


def _clean_str_list(value: Any) -> list[str]:
    out: list[str] = []
    for item in _as_list(value):
        text = _text(item)
        if text and text not in out:
            out.append(text)
    return out


def _clean_marker_map(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, markers in value.items():
        label = _text(key)
        cleaned = _clean_str_list(markers)
        if label and cleaned:
            out[label] = cleaned
    return out


def _evidence(source: str, field: str, value: Any) -> TonalConsistencyEvidenceRef:
    return TonalConsistencyEvidenceRef(source=source, field=field, value=value)


def _visible_texts(structured_output: dict[str, Any] | None) -> list[str]:
    structured = structured_output if isinstance(structured_output, dict) else {}
    texts: list[str] = []
    for key in (
        "narrative_response",
        "narration_summary",
        "gm_response",
        "visible_output",
        "consequence_summary",
    ):
        text = _text(structured.get(key))
        if text:
            texts.append(text)
    for key in ("spoken_lines", "action_lines", "state_effects"):
        rows = structured.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                for field in ("text", "content", "description"):
                    text = _text(row.get(field))
                    if text:
                        texts.append(text)
            else:
                text = _text(row)
                if text:
                    texts.append(text)
    return texts


def _count_marker_hits(
    marker_map: dict[str, list[str]],
    visible_text: str,
) -> dict[str, int]:
    if not visible_text:
        return {}
    folded = visible_text.casefold()
    hits: dict[str, int] = {}
    for label, markers in marker_map.items():
        count = 0
        for marker in markers:
            token = _text(marker).casefold()
            if token:
                count += len(re.findall(re.escape(token), folded))
        if count:
            hits[label] = count
    return hits


def classify_tonal_consistency_from_policy(
    *,
    tonal_consistency_target: dict[str, Any] | None,
    structured_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify visible output against policy-declared tonal markers."""

    target = tonal_consistency_target if isinstance(tonal_consistency_target, dict) else {}
    visible_text = "\n".join(_visible_texts(structured_output))
    dimension_marker_map = _clean_marker_map(target.get("dimension_marker_map"))
    forbidden_marker_map = _clean_marker_map(target.get("forbidden_marker_map"))
    dimension_hits = _count_marker_hits(dimension_marker_map, visible_text)
    forbidden_hits = _count_marker_hits(forbidden_marker_map, visible_text)
    realized_dimensions = [
        dimension_id
        for dimension_id in _clean_str_list(target.get("target_dimension_ids"))
        if dimension_id in dimension_hits
    ]
    required_dimensions = _clean_str_list(target.get("required_dimension_ids"))
    required_count = max(1, len(required_dimensions))
    coverage = len(set(realized_dimensions).intersection(required_dimensions)) / required_count
    allowed_registers = _clean_str_list(target.get("allowed_registers"))
    register_label = allowed_registers[0] if allowed_registers and coverage >= 1.0 and not forbidden_hits else None
    classification = TonalConsistencyClassification(
        schema_version=TONAL_CONSISTENCY_SCHEMA_VERSION,
        structured_classification_present=bool(visible_text.strip()),
        realized_dimension_ids=realized_dimensions,
        register_label=register_label,
        genre_label=None,
        forbidden_marker_hits=forbidden_hits,
        marker_hit_count=sum(forbidden_hits.values()),
        confidence=round(min(1.0, 0.25 + (0.7 * coverage)), 3)
        if visible_text.strip()
        else None,
        classification_source=TONAL_CONSISTENCY_DEFAULT_CLASSIFICATION_SOURCE,
        independent_classifier=True,
        source_evidence=[
            _evidence(
                "structured_output",
                "visible_text_present",
                bool(visible_text.strip()),
            ),
            _evidence(
                "module_runtime_policy",
                "tonal_consistency.dimension_marker_classes",
                sorted(dimension_marker_map.keys()),
            ),
            _evidence(
                "module_runtime_policy",
                "tonal_consistency.forbidden_marker_classes",
                sorted(forbidden_marker_map.keys()),
            ),
            _evidence(
                "deterministic_classifier",
                "dimension_hit_classes",
                sorted(dimension_hits.keys()),
            ),
            _evidence(
                "deterministic_classifier",
                "forbidden_hit_classes",
                sorted(forbidden_hits.keys()),
            ),
        ],
    )
    return classification.to_runtime_dict()
