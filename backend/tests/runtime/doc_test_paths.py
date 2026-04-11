"""Resolve historical `docs/architecture/<name>` references to the current doc tree.

Area 2 gate markdown moved under `docs/archive/architecture-legacy/`; stratification and
story contract live under `docs/technical/`.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_LEGACY = REPO_ROOT / "docs" / "archive" / "architecture-legacy"
_TECH_AI = REPO_ROOT / "docs" / "technical" / "ai"
_TECH_ARCH = REPO_ROOT / "docs" / "technical" / "architecture"


def architecture_style_doc(name: str) -> Path:
    """Map a legacy architecture-relative filename to an on-disk path."""
    if name == "llm_slm_role_stratification.md":
        return _TECH_AI / "llm-slm-role-stratification.md"
    if name == "ai_story_contract.md":
        return _TECH_ARCH / "ai_story_contract.md"
    return _LEGACY / name
