"""Canonical GoC subtext policy loader and deterministic projection helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ai_stack.contracts.semantic_move_contract import SubtextRecord

SUBTEXT_POLICY_RELATIVE_PATH = "content/modules/god_of_carnage/direction/subtext_policy.yaml"
_REPO_ROOT = Path(__file__).resolve().parents[3]
SUBTEXT_POLICY_PATH = _REPO_ROOT / SUBTEXT_POLICY_RELATIVE_PATH


@lru_cache(maxsize=1)
def load_goc_subtext_policy() -> dict[str, Any]:
    """Load the reviewable policy used as the oracle for bounded subtext labels."""
    with SUBTEXT_POLICY_PATH.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def subtext_policy_values(key: str) -> frozenset[str]:
    values = load_goc_subtext_policy().get(key)
    if not isinstance(values, list):
        return frozenset()
    return frozenset(str(value).strip() for value in values if str(value).strip())


def rule_spec_for_subtext(rule_id: str) -> dict[str, str]:
    rules = load_goc_subtext_policy().get("rules")
    if not isinstance(rules, dict):
        return {}
    raw = rules.get(rule_id)
    if not isinstance(raw, dict):
        raw = rules.get("establish_situational_pressure")
    return {str(k): str(v) for k, v in (raw or {}).items() if isinstance(k, str)}


def subtext_rule_id_for_move(move_type: str, *, trace_detail: str | None = None) -> str:
    if move_type == "repair_attempt" and trace_detail == "rule:repair_plus_probe":
        return "repair_attempt_probe"
    if move_type:
        return move_type
    return "establish_situational_pressure"


def build_subtext_record_from_policy(
    *,
    move_type: str,
    explicit_intent: str | None,
    trace_detail: str | None,
    evidence_codes: list[str],
) -> SubtextRecord:
    rule_id = subtext_rule_id_for_move(move_type, trace_detail=trace_detail)
    spec = rule_spec_for_subtext(rule_id)
    if not spec:
        spec = rule_spec_for_subtext("establish_situational_pressure")
    return SubtextRecord(
        surface_mode=spec.get("surface_mode", "neutral"),
        explicit_intent=(explicit_intent or "").strip() or None,
        hidden_intent_hypothesis=spec.get("hidden_intent_hypothesis", "unknown"),
        subtext_function=spec.get("subtext_function", "unset"),
        sincerity_band=spec.get("sincerity_band", "unknown"),
        evidence_codes=[code for code in evidence_codes if code][:8],
        policy_source=SUBTEXT_POLICY_RELATIVE_PATH,
        policy_rule_id=rule_id,
    )
