"""Deterministic dramatic-alignment checks for validation (GATE_SCORING_POLICY_GOC.md §1 dramatic_quality).

Implements anti-seductive rejection: fluent prose that does not support the committed scene_function
or that relies only on generic boilerplate is rejected at the validation seam — not ad hoc taste.
"""

from __future__ import annotations

from typing import Any

# Minimum narrative mass for high-stakes scene functions under normal verbal density.
_MIN_CHARS_HIGH_STAKES = 48
_MIN_CHARS_WITHHELD_OR_THIN = 12

# Tokens that must appear (substring match) to show the proposal engages the director function.
_FUNCTION_SUBSTRING_TOKENS: dict[str, tuple[str, ...]] = {
    "escalate_conflict": (
        "voice",
        "loud",
        "shout",
        "rage",
        "angry",
        "accus",
        "fight",
        "slam",
        "storm",
        "furious",
        "attack",
        "insult",
    ),
    "redirect_blame": (
        "blame",
        "fault",
        "your",
        "you",
        "accus",
        "responsib",
        "deny",
        "denial",
    ),
    "reveal_surface": (
        "truth",
        "secret",
        "admit",
        "reveal",
        "hid",
        "know",
        "knew",
        "fact",
        "confess",
    ),
    "probe_motive": (
        "why",
        "reason",
        "motive",
        "because",
        "explain",
        "justify",
    ),
    "repair_or_stabilize": (
        "sorry",
        "apolog",
        "peace",
        "calm",
        "repair",
        "truce",
        "stop",
    ),
    "establish_pressure": (
        "tight",
        "quiet",
        "look",
        "wait",
        "table",
        "room",
        "still",
        "watch",
    ),
    "withhold_or_evade": (
        "silence",
        "quiet",
        "say",
        "nothing",
        "hold",
        "still",
        "watch",
    ),
    "scene_pivot": (
        "turn",
        "shift",
        "instead",
        "another",
        "leave",
        "door",
        "topic",
        "apartment",
        "table",
        "dinner",
        "stay",
        "here",
    ),
}

# Phrases that signal polished emptiness under high-stakes functions (dramatic_quality fail).
_GENERIC_BOILERPLATE_PHRASES: tuple[str, ...] = (
    "tension in the air",
    "the scene continues",
    "the atmosphere",
    "something shifts",
    "as time passes",
    "the moment hangs",
    "everyone feels",
    "the mood",
    "a sense of",
    "the underlying",
    "in this scene",
    "the narrative suggests",
    "as a commentator",
    "the player feels",
    "as an observer",
    "the conversation illustrates",
    "this exchange demonstrates",
)

_COMMENTARY_META_PHRASES: tuple[str, ...] = (
    "as a narrator",
    "from a narrative perspective",
    "in dramatic terms",
    "the scene symbolizes",
    "the dialogue represents",
)


def extract_proposed_narrative_text(proposed_state_effects: list[dict[str, Any]]) -> str:
    """Concatenate narrative-bearing proposal fields for alignment checks."""
    parts: list[str] = []
    for eff in proposed_state_effects:
        if not isinstance(eff, dict):
            continue
        desc = eff.get("description")
        if isinstance(desc, str) and desc.strip():
            parts.append(desc.strip())
    return " ".join(parts).strip()


def _silence_mode(silence_brevity_decision: dict[str, Any] | None) -> str:
    if not isinstance(silence_brevity_decision, dict):
        return "normal"
    m = silence_brevity_decision.get("mode")
    return str(m) if m else "normal"


def dramatic_alignment_legacy_fallback_only(
    *,
    selected_scene_function: str,
    pacing_mode: str,
    silence_brevity_decision: dict[str, Any] | None,
    proposed_narrative: str,
) -> str | None:
    """Bounded legacy seam: length thresholds, withhold beat, meta-commentary bans only.

    Does **not** perform scene-function token-list checks or generic-boilerplate primary logic;
    those are owned by ``dramatic_effect_gate`` (planner-aware path).
    """
    text = proposed_narrative.strip()
    sm = _silence_mode(silence_brevity_decision)
    low = text.lower()

    if selected_scene_function == "withhold_or_evade" and sm == "withheld":
        if len(text) < 8:
            return "dramatic_alignment_withhold_requires_min_beat"
        if any(phrase in low for phrase in _COMMENTARY_META_PHRASES):
            return "dramatic_alignment_meta_commentary"
        return None

    if sm in ("withheld", "brief") or pacing_mode in ("thin_edge", "compressed"):
        if len(text) < _MIN_CHARS_WITHHELD_OR_THIN:
            return "dramatic_alignment_insufficient_mass_thin_or_silence"
        return None

    high_stakes = {"escalate_conflict", "redirect_blame", "reveal_surface"}
    if selected_scene_function not in high_stakes:
        if len(text) < 8:
            return "dramatic_alignment_narrative_too_short"
        if any(phrase in low for phrase in _COMMENTARY_META_PHRASES):
            return "dramatic_alignment_meta_commentary"
        return None

    if len(text) < _MIN_CHARS_HIGH_STAKES:
        return "dramatic_alignment_insufficient_mass"

    if any(phrase in low for phrase in _COMMENTARY_META_PHRASES):
        return "dramatic_alignment_meta_commentary"

    return None


def dramatic_alignment_violation(
    *,
    selected_scene_function: str,
    pacing_mode: str,
    silence_brevity_decision: dict[str, Any] | None,
    proposed_narrative: str,
) -> str | None:
    """Deprecated full surface path: legacy structural + token/boilerplate checks.

    Prefer ``dramatic_effect_gate`` + ``dramatic_alignment_legacy_fallback_only`` for new code.
    """
    text = proposed_narrative.strip()
    low = text.lower()
    legacy = dramatic_alignment_legacy_fallback_only(
        selected_scene_function=selected_scene_function,
        pacing_mode=pacing_mode,
        silence_brevity_decision=silence_brevity_decision,
        proposed_narrative=proposed_narrative,
    )
    if legacy:
        return legacy

    high_stakes = {"escalate_conflict", "redirect_blame", "reveal_surface"}
    if selected_scene_function in high_stakes and len(text) >= _MIN_CHARS_HIGH_STAKES:
        tokens = _FUNCTION_SUBSTRING_TOKENS.get(selected_scene_function, ())
        if tokens and not any(t in low for t in tokens):
            return "dramatic_alignment_no_function_support"

        for phrase in _GENERIC_BOILERPLATE_PHRASES:
            if phrase in low:
                if tokens and any(t in low for t in tokens):
                    continue
                return "dramatic_alignment_generic_boilerplate"

    return None
