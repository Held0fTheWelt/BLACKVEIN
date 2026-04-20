"""Deterministic natural-language interpretation for the room runtime (no LLM, no embeddings)."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

PARSER_VERSION = "we_runtime_input_v1"

_MAX_RATIONALE_LEN = 200
_MAX_CANDIDATE_REASON_LEN = 96


class InputPrimaryMode(str, Enum):
    dialogue = "dialogue"
    action = "action"
    reaction = "reaction"
    mixed = "mixed"
    silence = "silence"
    unknown = "unknown"


class InterpretedCommandCandidate(BaseModel):
    action: str
    confidence: float
    payload: dict[str, Any] = Field(default_factory=dict)
    reason: str


class InterpretedCommandPlan(BaseModel):
    raw_text: str
    normalized_text: str
    primary_mode: InputPrimaryMode
    secondary_modes: list[InputPrimaryMode] = Field(default_factory=list)
    spoken_text_segments: list[str] = Field(default_factory=list)
    action_cues: list[str] = Field(default_factory=list)
    reaction_cues: list[str] = Field(default_factory=list)
    ambiguity_markers: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    candidates: list[InterpretedCommandCandidate] = Field(default_factory=list)
    selected_command: dict[str, Any] | None = None
    rationale: str = ""
    parser_version: str = PARSER_VERSION


_QUOTED = re.compile(r'"([^"]*)"')
_MOVE_PHRASE = re.compile(
    r"\b(?:go|head|walk|move)\s+(?:to|into|toward|towards)\s+(?:the\s+)?(.+)$",
    re.IGNORECASE,
)
_ENTER_PHRASE = re.compile(r"^\s*i\s+enter\s+(?:the\s+)?(.+)$", re.IGNORECASE)
_INSPECT_PHRASE = re.compile(
    r"\b(?:inspect|examine)\s+(?:the\s+)?([a-z0-9][a-z0-9_\s-]*)",
    re.IGNORECASE,
)
_LOOK_AT_PHRASE = re.compile(r"\blook\s+at\s+(?:the\s+)?([a-z0-9][a-z0-9_\s-]*)", re.IGNORECASE)
_USE_PHRASE = re.compile(
    r"^\s*i\s+(?:use|take|press|activate)\s+(?:the\s+)?(.+)$",
    re.IGNORECASE,
)
_SPEECH_LEAD = re.compile(
    r"^(?:i\s+)?(?:say|says|said|whisper|shout|mutter)\s*[:,-]?\s*(.+)$",
    re.IGNORECASE,
)
_TELL_ASK_LEAD = re.compile(
    r"^(?:i\s+)?(?:tell|ask)\s+(?:him|her|them)\s+(.+)$",
    re.IGNORECASE,
)
_REACTION_LEAD = re.compile(
    r"^\s*i\s+(sigh|sighs|shrug|shrugged|nod|nodded|wince|winced|gasp|gasped|laugh|laughed)\b",
    re.IGNORECASE,
)
_REACTION_BODY = re.compile(
    r"\b(look\s+away|stare|stares|staring|roll\s+my\s+eyes|facepalm)\b",
    re.IGNORECASE,
)
_WITHHOLD = re.compile(
    r"\b(?:do\s+not|don'?t)\s+answer\b|\b(?:stay|remain)\s+silent\b|\bjust\s+stare\b",
    re.IGNORECASE,
)
_SILENCE_DOTS = re.compile(r"^[\s\.…]+$")


def _strip_leading_article(phrase: str) -> str:
    return re.sub(r"^(the|a|an)\s+", "", phrase.strip(), flags=re.IGNORECASE).strip()


def _slugify_phrase(phrase: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", phrase.lower().strip()).strip("_")


def _tokens_with_alpha(text: str) -> list[str]:
    return [t for t in re.split(r"\s+", text.strip()) if any(c.isalnum() for c in t)]


def extract_spoken_text_for_say(raw_text: str) -> str:
    """Extract dialogue for a say command from quotes or leading say/tell/ask patterns."""
    text = (raw_text or "").strip()
    quoted = _QUOTED.findall(text)
    if quoted:
        return quoted[0].strip()
    m = _SPEECH_LEAD.match(text)
    if m:
        inner = m.group(1).strip()
        if inner:
            q2 = _QUOTED.search(inner)
            if q2:
                return q2.group(1).strip()
            return inner
    m = _TELL_ASK_LEAD.match(text)
    if m:
        return m.group(1).strip()
    m = re.search(
        r"\b(?:say|says|said|ask|asks|asked|tell|tells|told)\b\s*[:,-]?\s*(.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        spoken = m.group(1).strip()
        if spoken:
            return spoken
    return text


def _resolve_visible_target(phrase: str, visible_targets: list[str] | None) -> str | None:
    if not visible_targets or not phrase:
        return None
    phrase = _strip_leading_article(phrase).rstrip(".!?")
    p_underscore = phrase.lower().replace(" ", "_").replace("-", "_")
    slug = _slugify_phrase(phrase)
    if not slug and not p_underscore:
        return None
    matches: list[str] = []
    for tid in visible_targets:
        tl = tid.lower()
        if tl == p_underscore or tl == slug:
            matches.append(tid)
            continue
        tid_words = tl.split("_")
        if slug and len(slug.split("_")) == 1 and slug in tid_words:
            matches.append(tid)
    uniq = sorted(set(matches), key=len)
    if len(uniq) == 1:
        return uniq[0]
    return None


def _resolve_room(phrase: str, reachable_rooms: list[dict[str, str]] | None) -> str | None:
    if not reachable_rooms or not phrase:
        return None
    phrase = _strip_leading_article(phrase).rstrip(".!?")
    slug = _slugify_phrase(phrase)
    rid_slug = phrase.lower().replace(" ", "_").replace("-", "_")
    candidates: list[str] = []
    for room in reachable_rooms:
        rid = room.get("id", "")
        name = room.get("name", "")
        if not rid:
            continue
        rslug = _slugify_phrase(name)
        if rid.lower() == rid_slug or rid.lower() == slug or rslug == slug:
            candidates.append(rid)
    uniq = sorted(set(candidates), key=len)
    if len(uniq) == 1:
        return uniq[0]
    return None


def _resolve_action_id(phrase: str, available_actions: list[dict[str, Any]] | None) -> str | None:
    if not available_actions or not phrase:
        return None
    phrase = _strip_leading_article(phrase).rstrip(".!?")
    slug = _slugify_phrase(phrase)
    aid_exact = phrase.lower().replace(" ", "_").replace("-", "_")
    matches: list[str] = []
    for act in available_actions:
        aid = str(act.get("id", ""))
        label = str(act.get("label", ""))
        if not aid:
            continue
        al = aid.lower()
        if al == aid_exact or al == slug or _slugify_phrase(label) == slug:
            matches.append(aid)
    uniq = sorted(set(matches), key=len)
    if len(uniq) == 1:
        return uniq[0]
    return None


def interpret_runtime_input(
    text: str,
    *,
    available_actions: list[dict[str, Any]] | None = None,
    visible_targets: list[str] | None = None,
    reachable_rooms: list[dict[str, str]] | None = None,
) -> InterpretedCommandPlan:
    raw = text or ""
    normalized = " ".join(raw.split())
    lowered = normalized.lower()
    tokens = _tokens_with_alpha(normalized)

    plan = InterpretedCommandPlan(
        raw_text=raw,
        normalized_text=normalized,
        primary_mode=InputPrimaryMode.unknown,
        parser_version=PARSER_VERSION,
    )

    if not normalized.strip():
        plan.primary_mode = InputPrimaryMode.silence
        plan.confidence = 0.0
        plan.rationale = "Empty input."
        plan.ambiguity_markers.append("empty")
        return plan

    if _SILENCE_DOTS.match(normalized) or not tokens:
        plan.primary_mode = InputPrimaryMode.silence
        plan.confidence = 0.1
        plan.rationale = "No lexical content or ellipsis-only silence."
        plan.ambiguity_markers.append("silence_or_punctuation")
        return plan

    if _WITHHOLD.search(lowered) or _REACTION_BODY.search(lowered) or _REACTION_LEAD.match(normalized):
        plan.reaction_cues.append("nonverbal_or_withhold")
        plan.primary_mode = InputPrimaryMode.reaction

    if '"' in normalized or _SPEECH_LEAD.match(normalized) or _TELL_ASK_LEAD.match(normalized):
        plan.spoken_text_segments.append(extract_spoken_text_for_say(normalized))
        plan.primary_mode = InputPrimaryMode.dialogue if plan.primary_mode == InputPrimaryMode.unknown else InputPrimaryMode.mixed

    candidates: list[InterpretedCommandCandidate] = []

    if '"' in normalized:
        spoken = extract_spoken_text_for_say(normalized)
        if spoken:
            candidates.append(
                InterpretedCommandCandidate(
                    action="say",
                    confidence=0.82,
                    payload={"text": spoken},
                    reason="Quoted or extracted dialogue.",
                )
            )

    if _SPEECH_LEAD.match(normalized) or _TELL_ASK_LEAD.match(normalized):
        spoken = extract_spoken_text_for_say(normalized)
        if spoken and not any(c.action == "say" for c in candidates):
            candidates.append(
                InterpretedCommandCandidate(
                    action="say",
                    confidence=0.78,
                    payload={"text": spoken},
                    reason="Speech-leading pattern.",
                )
            )

    m = _MOVE_PHRASE.search(normalized) or _ENTER_PHRASE.match(normalized)
    if m:
        phrase = m.group(1).strip().rstrip(".!")
        room_id = _resolve_room(phrase, reachable_rooms)
        plan.action_cues.append("move_phrase")
        if room_id:
            candidates.append(
                InterpretedCommandCandidate(
                    action="move",
                    confidence=0.8,
                    payload={"target_room_id": room_id},
                    reason="Movement phrase with unique reachable room match.",
                )
            )
        else:
            plan.ambiguity_markers.append("move_target_unresolved")

    for rx, label in ((_INSPECT_PHRASE, "inspect"), (_LOOK_AT_PHRASE, "look_at")):
        m2 = rx.search(normalized)
        if m2:
            phrase = m2.group(1).strip().rstrip(".!")
            tid = _resolve_visible_target(phrase, visible_targets)
            plan.action_cues.append(label)
            if tid:
                candidates.append(
                    InterpretedCommandCandidate(
                        action="inspect",
                        confidence=0.78,
                        payload={"target_id": tid},
                        reason="Inspect pattern with unique visible target.",
                    )
                )
            else:
                plan.ambiguity_markers.append("inspect_target_unresolved")

    m3 = _USE_PHRASE.match(normalized)
    if m3:
        phrase = m3.group(1).strip().rstrip(".!")
        aid = _resolve_action_id(phrase, available_actions)
        plan.action_cues.append("use_action_phrase")
        if aid:
            candidates.append(
                InterpretedCommandCandidate(
                    action="use_action",
                    confidence=0.76,
                    payload={"action_id": aid},
                    reason="Use/take pattern with unique available action match.",
                )
            )
        else:
            plan.ambiguity_markers.append("use_action_unresolved")

    # Reaction / emote: physical narration without strong dialogue signal
    has_say_candidate = any(c.action == "say" for c in candidates)
    if (
        not has_say_candidate
        and (
            plan.primary_mode == InputPrimaryMode.reaction
            or _REACTION_LEAD.match(normalized)
            or _REACTION_BODY.search(lowered)
            or _WITHHOLD.search(lowered)
        )
    ):
        emote_text = normalized
        if len(emote_text) > 280:
            emote_text = emote_text[:277] + "..."
        candidates.append(
            InterpretedCommandCandidate(
                action="emote",
                confidence=0.62,
                payload={"text": emote_text},
                reason="Reaction or nonverbal narration.",
            )
        )

    # Short ambiguous utterance: do not add emote/say
    if len(tokens) <= 2 and len(normalized) < 16 and not candidates and '"' not in normalized:
        plan.primary_mode = InputPrimaryMode.unknown
        plan.ambiguity_markers.append("short_utterance")
        plan.rationale = "Short text without structural cues."
        plan.confidence = 0.2
        plan.candidates = []
        return plan

    # If still no candidates but looks like prose, stay unknown (conservative)
    if not candidates:
        if plan.primary_mode == InputPrimaryMode.unknown:
            plan.rationale = "No bounded pattern matched a safe command."
            plan.ambiguity_markers.append("no_candidate")
        plan.confidence = 0.25
        plan.candidates = []
        return plan

    # Deduplicate same action+payload (e.g. quote + speech-lead both yield say)
    seen: set[tuple[str, str]] = set()
    deduped: list[InterpretedCommandCandidate] = []
    for c in sorted(candidates, key=lambda x: -x.confidence):
        key = (c.action, repr(sorted(c.payload.items())))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    plan.candidates = deduped
    top = plan.candidates[0].confidence
    plan.confidence = top
    if len(plan.candidates) > 1 and abs(plan.candidates[0].confidence - plan.candidates[1].confidence) < 0.06:
        plan.ambiguity_markers.append("competing_candidates")
        plan.primary_mode = InputPrimaryMode.mixed
    plan.rationale = (plan.candidates[0].reason)[:_MAX_RATIONALE_LEN]
    return plan


def truncate_for_diagnostics(s: str, max_len: int = _MAX_CANDIDATE_REASON_LEN) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."
