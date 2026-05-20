"""Quality Lab evaluator catalog — wraps ``ai_stack.langfuse.langfuse_evaluator_catalog``
with severity buckets and repair areas loaded from ``docs/llm-as-a-judge/``.

Per ADR-0040 the per-evaluator ``.md`` files are canonical. This module
loads the YAML frontmatter once at import time and exposes a richer view
than the code-side spec (which lacks insufficient_evidence buckets and
suggested_repair_areas).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ai_stack.langfuse.langfuse_evaluator_catalog import (
    LangfuseCategoricalEvaluatorSpec,
    WOS_CATEGORICAL_JUDGES_ORDER,
    get_categorical_evaluator_spec,
)

_JUDGE_DIR = Path(__file__).resolve().parents[2] / "docs" / "llm-as-a-judge"


@dataclass(frozen=True)
class EvaluatorView:
    """Quality Lab's enriched view of a categorical evaluator."""

    name: str
    group: str
    scope: str
    categories: tuple[str, ...]
    severity_buckets: dict[str, frozenset[str]]
    suggested_repair_areas: tuple[str, ...]
    spec: LangfuseCategoricalEvaluatorSpec


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path.name}: missing YAML frontmatter")
    _, frontmatter_text, _ = text.split("---", 2)
    parsed = yaml.safe_load(frontmatter_text) or {}
    if not isinstance(parsed, dict):
        raise ValueError(f"{path.name}: frontmatter is not a mapping")
    return parsed


def _build_view(name: str) -> EvaluatorView:
    spec = get_categorical_evaluator_spec(name)
    if spec is None:
        raise KeyError(f"unknown evaluator: {name!r}")
    fm = _parse_frontmatter(_JUDGE_DIR / f"{name}.md")
    severity_raw = fm.get("severity") or {}
    severity: dict[str, frozenset[str]] = {
        bucket: frozenset(severity_raw.get(bucket) or ())
        for bucket in ("positive", "weak", "failure", "neutral", "insufficient_evidence")
    }
    return EvaluatorView(
        name=name,
        group=str(fm.get("group") or "unknown"),
        scope=str(spec.scope),
        categories=tuple(fm.get("categories") or ()),
        severity_buckets=severity,
        suggested_repair_areas=tuple(fm.get("suggested_repair_areas") or ()),
        spec=spec,
    )


@lru_cache(maxsize=1)
def _all_views() -> dict[str, EvaluatorView]:
    return {name: _build_view(name) for name in WOS_CATEGORICAL_JUDGES_ORDER}


def evaluator_view(name: str) -> EvaluatorView | None:
    return _all_views().get(name)


def list_evaluator_views() -> tuple[EvaluatorView, ...]:
    return tuple(_all_views()[n] for n in WOS_CATEGORICAL_JUDGES_ORDER)


def evaluator_views_for_scope(scope: str) -> tuple[EvaluatorView, ...]:
    return tuple(v for v in list_evaluator_views() if v.scope == scope)


def category_severity_bucket(name: str, category: str | None) -> str:
    """Return the severity bucket for (name, category) per the canonical ``.md``.

    Returns ``"unknown"`` when the judge or category is not recognized.
    """
    if not category:
        return "unknown"
    view = evaluator_view(name)
    if view is None:
        return "unknown"
    normalized = str(category).strip()
    for bucket, members in view.severity_buckets.items():
        if normalized in members:
            return bucket
    if normalized in view.categories:
        return "unknown"
    return "unknown"
