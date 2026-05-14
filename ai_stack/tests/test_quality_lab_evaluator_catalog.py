"""Drift tests between ``docs/llm-as-a-judge/`` (canonical evaluator definitions)
and ``ai_stack/langfuse_evaluator_catalog`` (code mirror).

Per ADR-0040 the per-evaluator markdown files in ``docs/llm-as-a-judge/``
are the canonical source of truth for the WoS LLM-as-a-Judge evaluators.
This test fails CI if the directory and the code mirror disagree on names
or categories. When adding, renaming, or removing an evaluator, update both
sides in the same change.

Per ADR-0039 these assertions derive expectations from the catalog and the
directory contents — no hardcoded judge-name or category lists.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ai_stack.langfuse_evaluator_catalog import (
    WOS_CATEGORICAL_JUDGES_ORDER,
    get_categorical_evaluator_spec,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_JUDGE_DIR = _REPO_ROOT / "docs" / "llm-as-a-judge"


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise AssertionError(f"{path.name}: missing YAML frontmatter")
    _, fm, _ = text.split("---", 2)
    return yaml.safe_load(fm) or {}


def _judge_files() -> dict[str, Path]:
    return {p.stem: p for p in _JUDGE_DIR.glob("*_judge.md")}


def test_judge_directory_exists():
    assert _JUDGE_DIR.is_dir(), (
        f"Canonical evaluator directory missing: {_JUDGE_DIR}. "
        "See ADR-0040 §'Evaluator Definitions'."
    )


def test_directory_names_match_catalog_order():
    """Set of `.md` files == set of names in WOS_CATEGORICAL_JUDGES_ORDER."""
    dir_names = set(_judge_files().keys())
    code_names = set(WOS_CATEGORICAL_JUDGES_ORDER)

    only_in_dir = sorted(dir_names - code_names)
    only_in_code = sorted(code_names - dir_names)
    assert not only_in_dir and not only_in_code, (
        "Drift between docs/llm-as-a-judge/ and "
        "ai_stack/langfuse_evaluator_catalog.WOS_CATEGORICAL_JUDGES_ORDER:\n"
        f"  only in directory: {only_in_dir}\n"
        f"  only in code:      {only_in_code}\n"
        "Resolve by adding / removing both sides together."
    )


@pytest.mark.parametrize("judge_name", sorted(WOS_CATEGORICAL_JUDGES_ORDER))
def test_each_judge_has_canonical_markdown(judge_name: str):
    path = _JUDGE_DIR / f"{judge_name}.md"
    assert path.is_file(), (
        f"Missing canonical evaluator file: {path}. "
        "Every entry in WOS_CATEGORICAL_JUDGES_ORDER must have a .md."
    )


@pytest.mark.parametrize("judge_name", sorted(WOS_CATEGORICAL_JUDGES_ORDER))
def test_frontmatter_name_matches_filename(judge_name: str):
    fm = _frontmatter(_JUDGE_DIR / f"{judge_name}.md")
    assert fm.get("name") == judge_name, (
        f"{judge_name}.md frontmatter name={fm.get('name')!r} "
        "does not match filename. Names must match exactly."
    )


@pytest.mark.parametrize("judge_name", sorted(WOS_CATEGORICAL_JUDGES_ORDER))
def test_frontmatter_categories_match_spec(judge_name: str):
    """Per-judge: frontmatter categories list (order-preserving) == spec.categories."""
    fm = _frontmatter(_JUDGE_DIR / f"{judge_name}.md")
    fm_categories = tuple(fm.get("categories") or ())
    spec = get_categorical_evaluator_spec(judge_name)
    assert spec is not None, f"{judge_name}: no spec in code catalog"
    assert fm_categories == spec.categories, (
        f"{judge_name}: categories drift\n"
        f"  markdown: {fm_categories}\n"
        f"  code:     {spec.categories}\n"
        "Order matters — Langfuse renders categories in this order."
    )


@pytest.mark.parametrize("judge_name", sorted(WOS_CATEGORICAL_JUDGES_ORDER))
def test_severity_buckets_cover_only_declared_categories(judge_name: str):
    """Every category in a severity bucket must appear in the frontmatter categories list."""
    fm = _frontmatter(_JUDGE_DIR / f"{judge_name}.md")
    declared = set(fm.get("categories") or ())
    severity = fm.get("severity") or {}
    for bucket_name, members in severity.items():
        unknown = set(members or ()) - declared
        assert not unknown, (
            f"{judge_name}.md severity.{bucket_name} contains "
            f"categories not in the declared categories list: {sorted(unknown)}"
        )


@pytest.mark.parametrize("judge_name", sorted(WOS_CATEGORICAL_JUDGES_ORDER))
def test_required_body_sections_present(judge_name: str):
    """Each evaluator file must include Purpose, Prompt, and the two follow-on prompts."""
    text = (_JUDGE_DIR / f"{judge_name}.md").read_text(encoding="utf-8")
    for heading in (
        "## Purpose",
        "## Prompt",
        "## Score reasoning prompt",
        "## Category selection prompt",
    ):
        assert heading in text, f"{judge_name}.md missing section: {heading}"
