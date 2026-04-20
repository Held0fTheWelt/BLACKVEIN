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
_STATE_CHANGED_PREFIX = "state_changed:"
_MAX_STATE_PATH_LEN = 120

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

    axis_involvement: dict[tuple[str, str], list[int]] = {}
    axis_triggers: dict[tuple[str, str], set[str]] = {}
    axis_path_valence: dict[tuple[str, str], int] = {}
    axis_path_hits: dict[tuple[str, str], int] = {}

    for entry in history.entries:
        for trigger in entry.detected_triggers:
            chars = _extract_characters_from_trigger(trigger)
            char_list = sorted(chars)
            for i, a in enumerate(char_list):
                for b in char_list[i + 1 :]:
                    axis = (a, b)
                    if axis not in axis_involvement:
                        axis_involvement[axis] = []
                        axis_triggers[axis] = set()
                    axis_involvement[axis].append(entry.turn_number)
                    axis_triggers[axis].add(trigger)

        for raw in entry.canonical_consequences:
            if not raw.startswith(_STATE_CHANGED_PREFIX):
                continue
            path = raw[len(_STATE_CHANGED_PREFIX) :].strip()
            if not path:
                continue
            if len(path) > _MAX_STATE_PATH_LEN:
                path = path[:_MAX_STATE_PATH_LEN]
            chars = _extract_character_ids_from_state_path(path)
            char_list = sorted(chars)
            valence = _path_segment_valence(path)
            label = f"state_path:{path[:72]}"
            for i, a in enumerate(char_list):
                for b in char_list[i + 1 :]:
                    axis = (a, b)
                    if axis not in axis_involvement:
                        axis_involvement[axis] = []
                        axis_triggers[axis] = set()
                    axis_involvement[axis].append(entry.turn_number)
                    axis_triggers[axis].add(label)
                    axis_path_valence[axis] = axis_path_valence.get(axis, 0) + valence
                    axis_path_hits[axis] = axis_path_hits.get(axis, 0) + 1

    total_axes = len(axis_involvement)

    axis_salience: dict[tuple[str, str], float] = {}

    for axis, turns in axis_involvement.items():
        most_recent_turn = max(turns)
        age = (history.entries[-1].turn_number - most_recent_turn) + 1
        recency_score = max(0, 1.0 - (age / max(10, len(history.entries))))
        frequency_score = min(1.0, len(turns) / 5.0)
        salience = (recency_score * 0.6) + (frequency_score * 0.4)
        path_boost = min(0.25, axis_path_hits.get(axis, 0) * 0.06)
        axis_salience[axis] = min(1.0, salience + path_boost)

    sorted_axes = sorted(axis_salience.items(), key=lambda x: -x[1])[:10]

    salient_axes = []
    highest_salience = None
    highest_tension = None
    escalation_count = 0
    de_escalation_count = 0

    for (a, b), salience in sorted_axes:
        turns = axis_involvement[(a, b)]
        triggers = sorted(axis_triggers[(a, b)])

        escalation_keywords = {"escalation", "tension", "conflict", "hostility", "accusation", "betrayal"}
        resolution_keywords = {"reconciliation", "resolution", "peace", "alliance", "support"}

        escalation_mentions = sum(1 for t in triggers if any(k in t.lower() for k in escalation_keywords))
        resolution_mentions = sum(1 for t in triggers if any(k in t.lower() for k in resolution_keywords))

        path_v = axis_path_valence.get((a, b), 0)
        escalation_mentions += max(0, path_v)
        resolution_mentions += max(0, -path_v)

        if escalation_mentions > resolution_mentions:
            trend = "escalating"
            escalation_count += 1
        elif resolution_mentions > escalation_mentions:
            trend = "de-escalating"
            de_escalation_count += 1
        else:
            trend = "stable"

        if any("alliance" in t or "support" in t for t in triggers):
            signal = "alliance"
        elif any("hostility" in t or "conflict" in t or "tension" in t for t in triggers):
            signal = "tension"
        elif any("doubt" in t or "unstable" in t for t in triggers):
            signal = "instability"
        else:
            signal = "stable"

        if signal == "stable" and axis_path_hits.get((a, b), 0) > 0:
            any_escal_path = any(
                _path_marks_emotion_or_relationship(t[len("state_path:") :])
                and _path_segment_valence(t[len("state_path:") :]) > 0
                for t in triggers
                if t.startswith("state_path:")
            )
            any_calm_path = any(
                t.startswith("state_path:")
                and _path_segment_valence(t[len("state_path:") :]) < 0
                for t in triggers
            )
            if any_escal_path:
                signal = "tension"
            elif any_calm_path:
                signal = "alliance"

        axis_model = SalientRelationshipAxis(
            character_a=a,
            character_b=b,
            salience_score=salience,
            recent_change_direction=trend,
            signal_type=signal,
            involved_in_recent_triggers=triggers[:5],
            last_involved_turn=max(turns),
        )

        salient_axes.append(axis_model)

        if highest_salience is None:
            highest_salience = (a, b)
        if highest_tension is None and signal == "tension":
            highest_tension = (a, b)

    if escalation_count > de_escalation_count:
        stability = "escalating"
    elif de_escalation_count > escalation_count:
        stability = "de-escalating"
    elif escalation_count > 0 or de_escalation_count > 0:
        stability = "mixed"
    else:
        stability = "stable" if salient_axes else "unknown"

    return RelationshipAxisContext(
        salient_axes=salient_axes,
        total_character_pairs_known=total_axes,
        overall_stability_signal=stability,
        has_escalation_markers=(escalation_count > 0),
        has_de_escalation_markers=(de_escalation_count > 0),
        highest_salience_axis=highest_salience,
        highest_tension_axis=highest_tension,
        derived_from_turn=history.entries[-1].turn_number if history.entries else 0,
    )
