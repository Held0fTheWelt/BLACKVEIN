"""Shadow-mode production gate for Souffleuse visible text (Sub-Plan 4 PR-4D).

Runs before wiring as a hard gate. Callers pass realized visible strings; the judge
returns structured violations using closed contract enums only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

VIOLATION_SELF_LABEL: str = "self_label"
VIOLATION_ROLE_LIST: str = "role_list"
VIOLATION_OUTSIDE_VOICE: str = "outside_voice"

_FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (VIOLATION_SELF_LABEL, re.compile(r"(?i)\bSouffleuse\s*:")),
    (VIOLATION_ROLE_LIST, re.compile(r"(?i)\b(for this role|you are\s+\w+,)")),
)


@dataclass(frozen=True)
class SouffleuseJudgeResult:
    schema_version: str
    passed: bool
    violations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "passed": self.passed,
            "violations": list(self.violations),
        }


def evaluate_souffleuse_visible_text_shadow(
    text: str,
    *,
    character_voice_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Shadow judge — ADR-0056 D3 smoke rules + optional voice register hint."""
    violations: list[str] = []
    body = str(text or "")
    for code, pattern in _FORBIDDEN_PATTERNS:
        if pattern.search(body):
            violations.append(code)
    if "Du bist" in body and "Souffleuse" in body:
        violations.append(VIOLATION_ROLE_LIST)
    profile = character_voice_profile if isinstance(character_voice_profile, dict) else {}
    register = str((profile.get("speech_patterns") or {}).get("register") or "").strip()
    if register and "generic" in body.lower() and register.lower() not in body.lower():
        # Soft signal only — does not fail shadow gate until model-graded contract is calibrated.
        pass
    result = SouffleuseJudgeResult(
        schema_version="souffleuse_production_judge_shadow.v1",
        passed=len(violations) == 0,
        violations=tuple(sorted(set(violations))),
    )
    return result.to_dict()


__all__ = [
    "evaluate_souffleuse_visible_text_shadow",
    "SouffleuseJudgeResult",
    "VIOLATION_SELF_LABEL",
    "VIOLATION_ROLE_LIST",
]
