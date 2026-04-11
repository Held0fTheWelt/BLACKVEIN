"""Axis involvement ingestion and salience assembly (DS-043)."""

from __future__ import annotations

from app.runtime.relationship_context import (
    SalientRelationshipAxis,
    RelationshipAxisContext,
    _extract_character_ids_from_state_path,
    _extract_characters_from_trigger,
    _path_marks_emotion_or_relationship,
    _path_segment_valence,
)
from app.runtime.session_history import SessionHistory

_STATE_CHANGED_PREFIX = "state_changed:"
_MAX_STATE_PATH_LEN = 120


def collect_axis_maps_from_history(
    history: SessionHistory,
) -> tuple[
    dict[tuple[str, str], list[int]],
    dict[tuple[str, str], set[str]],
    dict[tuple[str, str], int],
    dict[tuple[str, str], int],
]:
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

    return axis_involvement, axis_triggers, axis_path_valence, axis_path_hits


def build_relationship_axis_context_from_maps(
    history: SessionHistory,
    axis_involvement: dict[tuple[str, str], list[int]],
    axis_triggers: dict[tuple[str, str], set[str]],
    axis_path_valence: dict[tuple[str, str], int],
    axis_path_hits: dict[tuple[str, str], int],
) -> RelationshipAxisContext:
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

    salient_axes: list[SalientRelationshipAxis] = []
    highest_salience = None
    highest_tension = None
    escalation_count = 0
    de_escalation_count = 0

    escalation_keywords = {"escalation", "tension", "conflict", "hostility", "accusation", "betrayal"}
    resolution_keywords = {"reconciliation", "resolution", "peace", "alliance", "support"}

    for (a, b), salience in sorted_axes:
        turns = axis_involvement[(a, b)]
        triggers = sorted(axis_triggers[(a, b)])

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
            signal: str = "alliance"
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
