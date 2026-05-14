"""Shape constants and helpers for Quality Lab payloads (ADR-0040)."""

from __future__ import annotations

from typing import Any, Iterable

SEVERITY_BUCKETS: tuple[str, ...] = (
    "positive",
    "weak",
    "failure",
    "neutral",
    "insufficient_evidence",
)

SOURCE_KINDS: tuple[str, ...] = (
    "deterministic_gate",
    "llm_judge",
    "mcp_analysis",
    "langfuse_trace",
    "metadata",
    "rag",
    "content",
    "prompt",
    "claude_context",
    "user_note",
)


def user_decision_prompt(
    *,
    question: str,
    context_summary: str,
    options: Iterable[dict[str, Any]],
    evidence_refs: Iterable[dict[str, str]] = (),
    requires_user_decision: bool = True,
) -> dict[str, Any]:
    """Build a structured human-AI co-decision prompt per ADR-0040 §UserDecisionPrompt.

    Each option must include id, label, description, ai_action. Optional:
    tradeoff, recommended (at most one option may set recommended=True).
    """
    options_list: list[dict[str, Any]] = []
    recommended_count = 0
    for option in options:
        if not isinstance(option, dict):
            continue
        required = {"id", "label", "description", "ai_action"}
        if not required.issubset(option.keys()):
            missing = required - option.keys()
            raise ValueError(f"decision option missing required keys: {sorted(missing)}")
        normalized = {
            "id": str(option["id"]),
            "label": str(option["label"]),
            "description": str(option["description"]),
            "ai_action": str(option["ai_action"]),
            "tradeoff": str(option.get("tradeoff", "")),
            "recommended": bool(option.get("recommended", False)),
        }
        if normalized["recommended"]:
            recommended_count += 1
        options_list.append(normalized)
    if recommended_count > 1:
        raise ValueError("at most one decision option may set recommended=True")
    if not options_list:
        raise ValueError("decision_options must contain at least one option")
    return {
        "requires_user_decision": bool(requires_user_decision),
        "context_summary": str(context_summary),
        "question": str(question),
        "decision_options": options_list,
        "evidence_refs": [
            {"type": str(ref.get("type", "")), "ref": str(ref.get("ref", ""))}
            for ref in evidence_refs
            if isinstance(ref, dict)
        ],
    }
