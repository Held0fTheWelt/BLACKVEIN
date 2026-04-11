"""W2.3.4 — Canonical relationship-axis context for longer-session coherence.

Derives and maintains the most relevant interpersonal dynamics from session
history and progression signals. Surfaces salient relationship axes without
replaying full history or complete relationship state.

RelationshipAxisContext is distinct from:
- raw session history (aggregated and bounded)
- full canonical state (only salient axes extracted)
- progression summary (interpersonal focus vs structural)
- future AI request assembly (runtime context not prompt prose)
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.runtime.session_history import SessionHistory

# Task 1C: explicit path parsing for narrative_commit consequences (no free-text NLP).

_ESCALATION_PATH_SEGMENTS = frozenset(
    {
        "tension",
        "hostility",
        "conflict",
        "aggression",
        "rage",
        "enemy",
        "betrayal",
        "accusation",
    }
)
_DE_ESCALATION_PATH_SEGMENTS = frozenset(
    {
        "trust",
        "reconciliation",
        "peace",
        "alliance",
        "support",
        "calm",
        "forgiveness",
    }
)


class SalientRelationshipAxis(BaseModel):
    """A single relationship axis that matters in the current context.

    Captures the most relevant interpersonal dynamics between two characters
    based on recent activity, detected changes, and escalation signals.

    Attributes:
        character_a: First character ID in the relationship.
        character_b: Second character ID in the relationship.
        salience_score: Relevance score (0.0-1.0) based on recent activity.
        recent_change_direction: Trend (escalating, stable, de-escalating).
        signal_type: Classification (tension, alliance, instability, stable).
        involved_in_recent_triggers: Triggers mentioning these characters.
        last_involved_turn: Most recent turn this axis mattered.
    """

    character_a: str
    character_b: str
    salience_score: float  # 0.0 to 1.0
    recent_change_direction: str  # escalating, stable, de-escalating
    signal_type: str  # tension, alliance, instability, stable
    involved_in_recent_triggers: list[str] = Field(default_factory=list)
    last_involved_turn: int = 0


class RelationshipAxisContext(BaseModel):
    """Bounded, deterministic relationship-axis context for a session.

    Surfaces the most relevant interpersonal dynamics derived from session
    history and progression signals. Enables later context assembly to
    understand character relationships without full state dump.

    Attributes:
        salient_axes: Most relevant relationship axes (bounded to 10).
        total_character_pairs_known: Count of all character pairs in history.
        overall_stability_signal: General relationship health signal.
        has_escalation_markers: Whether any axes show escalation.
        has_de_escalation_markers: Whether any axes show de-escalation.
        highest_salience_axis: The relationship axis that matters most.
        highest_tension_axis: The relationship axis most in conflict.
        derived_from_turn: Last turn processed for this context.
    """

    salient_axes: list[SalientRelationshipAxis] = Field(default_factory=list)
    total_character_pairs_known: int = 0
    overall_stability_signal: str = "unknown"  # stable, mixed, escalating, de-escalating
    has_escalation_markers: bool = False
    has_de_escalation_markers: bool = False
    highest_salience_axis: Optional[tuple[str, str]] = None
    highest_tension_axis: Optional[tuple[str, str]] = None
    derived_from_turn: int = 0


def _extract_characters_from_trigger(trigger_name: str) -> set[str]:
    """Extract likely character identifiers from a trigger name.

    Simple heuristic: split by known separators and identify character-like tokens.
    For example: "accusation_veronique_giuseppe" → {"veronique", "giuseppe"}

    Args:
        trigger_name: The trigger name to analyze.

    Returns:
        Set of character identifiers mentioned in the trigger.
    """
    parts = trigger_name.lower().replace("-", "_").split("_")

    excluded = {
        "conflict",
        "tension",
        "accusation",
        "betrayal",
        "reconciliation",
        "alliance",
        "hostility",
        "support",
        "doubt",
        "escalation",
        "de",
        "resolution",
        "event",
        "trigger",
    }

    chars = {p for p in parts if p and len(p) > 2 and p not in excluded}
    return chars


def _extract_character_ids_from_state_path(path: str) -> set[str]:
    """Derive character-like IDs from a canonical state dot-path (Task 1C).

    Only structured segments — no substring search over the full session text.
    """
    parts = path.split(".")
    if not parts:
        return set()
    out: set[str] = set()
    root = parts[0].strip().lower()
    if root == "characters" and len(parts) >= 2:
        tid = parts[1].strip().lower()
        if len(tid) > 1:
            out.add(tid)
    if root == "relationships" and len(parts) >= 2:
        rel = parts[1].lower().replace("-", "_")
        for token in rel.split("_"):
            if len(token) > 2:
                out.add(token)
    return out


def _path_segment_valence(path: str) -> int:
    """Integer score from allowlisted dot-segments only."""
    score = 0
    for seg in path.lower().split("."):
        seg = seg.strip()
        if seg in _ESCALATION_PATH_SEGMENTS:
            score += 1
        if seg in _DE_ESCALATION_PATH_SEGMENTS:
            score -= 1
    return score


def _path_marks_emotion_or_relationship(path: str) -> bool:
    pl = path.lower()
    return "emotional_state" in pl or ".attitude" in pl or pl.startswith("relationships.")


def derive_relationship_axis_context(history: SessionHistory) -> RelationshipAxisContext:
    """Derive relationship-axis context from bounded session history.

    Analyzes triggers and session progression to surface the most salient
    relationship dynamics: which axes matter, what trends are visible, and
    where escalation or resolution is concentrating.

    Task 1C: also uses ``state_changed:<path>`` tokens from ``canonical_consequences``,
    parsed strictly as dot-paths with bounded segment allowlists.

    Args:
        history: A SessionHistory to analyze.

    Returns:
        A bounded RelationshipAxisContext suitable for later context assembly.
    """
    if not history.entries:
        return RelationshipAxisContext()

    from app.runtime.relationship_context_derive import (
        build_relationship_axis_context_from_maps,
        collect_axis_maps_from_history,
    )

    axis_involvement, axis_triggers, axis_path_valence, axis_path_hits = collect_axis_maps_from_history(history)
    return build_relationship_axis_context_from_maps(
        history,
        axis_involvement,
        axis_triggers,
        axis_path_valence,
        axis_path_hits,
    )
