"""Canonical player-input intent taxonomy shared by runtime and tests.

ADR-0039 requires tests and gates to derive intent assertions from a shared
contract instead of copying hardcoded kind lists into each runtime surface.
"""

from __future__ import annotations

import unicodedata
from typing import Any

INTENT_CONTRACT_VERSION = "player_input_intent_contract.v1"

PLAYER_INPUT_KINDS: frozenset[str] = frozenset(
    {
        "speech",
        "question",
        "action",
        "perception",
        "reaction",
        "mixed",
        "intent_only",
        "explicit_command",
        "meta",
        "unclear",
        "ambiguous",
        "movement_action",
        "perception_action",
        "object_interaction",
        "social_nonverbal_action",
        "social_speech_action",
        "physical_action",
        "hostile_action",
        "environment_interaction",
        "wait_or_observe",
        "mixed_action_speech",
    }
)

SPEECH_PROJECTION_KINDS: frozenset[str] = frozenset(
    {"speech", "question", "social_speech_action"}
)

SPEECH_LIKE_KINDS: frozenset[str] = frozenset(
    {"speech", "question", "reaction", "intent_only", "social_speech_action"}
)

NON_STORY_CONTROL_INPUT_KINDS: frozenset[str] = frozenset({"meta"})

MIXED_INPUT_KINDS: frozenset[str] = frozenset({"mixed", "mixed_action_speech"})

PERCEPTION_LIKE_KINDS: frozenset[str] = frozenset(
    {"perception", "perception_action"}
)

ACTION_LIKE_KINDS: frozenset[str] = frozenset(
    {
        "action",
        "movement_action",
        "object_interaction",
        "social_nonverbal_action",
        "social_speech_action",
        "physical_action",
        "hostile_action",
        "environment_interaction",
        "mixed",
        "mixed_action_speech",
    }
)

QUESTION_SHAPE_MAY_PROBE_KINDS: frozenset[str] = frozenset(
    {"speech", "question", "social_speech_action", "mixed", "mixed_action_speech"}
)

QUESTION_PUNCTUATION_PROBE_GUARDED_KINDS: frozenset[str] = frozenset(
    {
        "action",
        "perception",
        "movement_action",
        "perception_action",
        "object_interaction",
        "social_nonverbal_action",
        "physical_action",
        "hostile_action",
        "environment_interaction",
        "wait_or_observe",
        "ambiguous",
        "unclear",
    }
)

NARRATOR_ONLY_KINDS: frozenset[str] = frozenset(
    {
        "action",
        "perception",
        "movement_action",
        "perception_action",
        "object_interaction",
        "physical_action",
        "hostile_action",
        "environment_interaction",
        "wait_or_observe",
        "ambiguous",
    }
)

FORBIDDEN_NON_SPEECH_ACTION_SEMANTIC_MOVES: frozenset[str] = frozenset(
    {"probe_inquiry", "provoke", "demand_explanation"}
)


def normalize_player_input_kind(kind: Any) -> str:
    return str(kind or "").strip().lower()


def normalize_for_intent_matching(text: Any) -> str:
    """Lowercase, collapse whitespace, and fold accents for intent matching."""
    decomposed = unicodedata.normalize("NFKD", str(text or "")).lower()
    folded = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(folded.split())


def is_known_player_input_kind(kind: Any) -> bool:
    return normalize_player_input_kind(kind) in PLAYER_INPUT_KINDS


def is_action_like_player_input_kind(kind: Any) -> bool:
    return normalize_player_input_kind(kind) in ACTION_LIKE_KINDS


def is_perception_like_player_input_kind(kind: Any) -> bool:
    return normalize_player_input_kind(kind) in PERCEPTION_LIKE_KINDS


def is_speech_like_player_input_kind(kind: Any) -> bool:
    return normalize_player_input_kind(kind) in SPEECH_LIKE_KINDS


def is_non_story_control_player_input_kind(kind: Any) -> bool:
    return normalize_player_input_kind(kind) in NON_STORY_CONTROL_INPUT_KINDS


def is_mixed_player_input_kind(kind: Any) -> bool:
    return normalize_player_input_kind(kind) in MIXED_INPUT_KINDS


def question_shape_may_probe(kind: Any) -> bool:
    return normalize_player_input_kind(kind) in QUESTION_SHAPE_MAY_PROBE_KINDS


def is_question_punctuation_probe_guarded(kind: Any) -> bool:
    return normalize_player_input_kind(kind) in QUESTION_PUNCTUATION_PROBE_GUARDED_KINDS


def is_narrator_only_player_input_kind(kind: Any) -> bool:
    return normalize_player_input_kind(kind) in NARRATOR_ONLY_KINDS


def player_input_kind_family(kind: Any) -> str:
    k = normalize_player_input_kind(kind)
    if k in PERCEPTION_LIKE_KINDS:
        return "perception"
    if k in {"social_nonverbal_action"}:
        return "social_nonverbal_action"
    if k in {"social_speech_action"}:
        return "social_speech_action"
    if k in MIXED_INPUT_KINDS:
        return "mixed"
    if k in ACTION_LIKE_KINDS:
        return "action"
    if k in SPEECH_LIKE_KINDS:
        return "speech"
    if k == "wait_or_observe":
        return "wait_or_observe"
    if k in {"meta", "explicit_command", "unclear", "ambiguous"}:
        return k
    return "unknown"


def default_commit_flags_for_player_input_kind(kind: Any) -> dict[str, bool]:
    k = normalize_player_input_kind(kind)
    if k in NON_STORY_CONTROL_INPUT_KINDS:
        return {
            "player_action_committed": False,
            "player_speech_committed": False,
            "narrator_response_expected": False,
            "npc_response_expected": False,
        }
    if k in {"action", "movement_action", "perception", "perception_action"}:
        return {
            "player_action_committed": True,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        }
    if k in MIXED_INPUT_KINDS:
        return {
            "player_action_committed": True,
            "player_speech_committed": True,
            "narrator_response_expected": True,
            "npc_response_expected": True,
        }
    if k in {"speech", "question"}:
        return {
            "player_action_committed": False,
            "player_speech_committed": True,
            "narrator_response_expected": False,
            "npc_response_expected": True,
        }
    if k == "social_speech_action":
        return {
            "player_action_committed": True,
            "player_speech_committed": True,
            "narrator_response_expected": False,
            "npc_response_expected": True,
        }
    if k == "social_nonverbal_action":
        return {
            "player_action_committed": True,
            "player_speech_committed": False,
            "narrator_response_expected": False,
            "npc_response_expected": True,
        }
    if k == "object_interaction":
        return {
            "player_action_committed": True,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        }
    if k in {"physical_action", "hostile_action", "environment_interaction"}:
        return {
            "player_action_committed": True,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        }
    if k in {"wait_or_observe", "ambiguous"}:
        return {
            "player_action_committed": False,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        }
    return {
        "player_action_committed": False,
        "player_speech_committed": False,
        "narrator_response_expected": True,
        "npc_response_expected": True,
    }
