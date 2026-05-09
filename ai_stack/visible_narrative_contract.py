"""VISIBLE-NARRATIVE-CONTRACT-01: sanitize player-visible scene block text.

Strips internal beat markers leaked from structured narration, duplicate speaker
labels, and generic scaffolding. Provides language / role legibility diagnostics
for Langfuse score metadata (not wired into live_opening_contract_pass gates).
"""

from __future__ import annotations

import re
from typing import Any

# Model / prompt sometimes echo these prefixes into list items or paragraphs.
_INTERNAL_BEAT_PREFIX_RE = re.compile(
    r"(?m)^\s*(narrator_intro|role_anchor|scene_setup)\s*:\s*",
    re.IGNORECASE,
)

# English scaffolding that must not appear in German-session visible text (names exempt by substring logic).
_GERMAN_SESSION_ENGLISH_LEAKS = (
    "you are ",
    "the paris salon:",
    "the paris salon;",
    " arriving with ",
    " into a room",
    " not as a spectator",
    " reacts immediately",
    " reacts instantly",
)

_ENGLISH_SESSION_GERMAN_LEAKS = (
    "du bist ",
    "der pariser",
    "die pariser",
    " in einen raum",
    " nicht als zuschauer",
)


def strip_internal_beat_markers(text: str) -> str:
    """Remove ``narrator_intro:`` / ``role_anchor:`` / ``scene_setup:`` line prefixes."""
    t = _INTERNAL_BEAT_PREFIX_RE.sub("", str(text or ""))
    # Also strip a single-line prefix at the very start (no newline).
    t = re.sub(
        r"^\s*(narrator_intro|role_anchor|scene_setup)\s*:\s*",
        "",
        t.strip(),
        count=1,
        flags=re.IGNORECASE,
    )
    return t.strip()


def strip_scaffolding_phrases(text: str) -> str:
    """Remove thin generic NPC / stage-direction filler."""
    t = str(text or "")
    t = re.sub(r"\s*reacts\s+immediately\.?", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*reacts\s+instantly\.?", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s{2,}", " ", t).strip()
    t = re.sub(r"\s+([.,!?;:])", r"\1", t)
    return t.strip()


def strip_duplicate_speaker_prefix(
    text: str,
    *,
    speaker_label: str | None,
    actor_id: str | None,
) -> str:
    """If dialogue repeats ``Veronique:`` while ``speaker_label`` is already Veronique, strip it."""
    t = str(text or "").strip()
    if not t:
        return t
    lab = str(speaker_label or "").strip()
    if lab:
        pat = re.compile(rf"^\s*{re.escape(lab)}\s*:\s*", re.IGNORECASE)
        if pat.match(t):
            t = pat.sub("", t).strip()
    aid = str(actor_id or "").strip()
    if aid and "_" in aid:
        short = aid.split("_")[0]
        if short:
            pat2 = re.compile(rf"^\s*{re.escape(short)}\s*:\s*", re.IGNORECASE)
            if pat2.match(t):
                t = pat2.sub("", t).strip()
    return t


def _strip_cross_lane_leakage(text: str, *, block_type: str) -> str:
    """Reduce actor_line carrying stage-direction-only leakage (heuristic)."""
    t = str(text or "").strip()
    bt = str(block_type or "").strip().lower()
    if bt == "actor_line" and t.startswith("*") and t.endswith("*"):
        return t.strip("*").strip()
    return t


def sanitize_visible_block_text(
    raw: str,
    *,
    block_type: str,
    speaker_label: str,
    actor_id: str | None,
    expected_language: str,
) -> tuple[str, dict[str, Any]]:
    """Return ``(clean_text, partial_diagnostics)`` for one projected block."""
    partial: dict[str, Any] = {}
    t = str(raw or "").strip()
    if not t:
        return "", partial
    before = t
    t = strip_internal_beat_markers(t)
    if t != before:
        partial["stripped_internal_beat_prefix"] = True
    t = strip_scaffolding_phrases(t)
    t = strip_duplicate_speaker_prefix(t, speaker_label=speaker_label, actor_id=actor_id)
    t = _strip_cross_lane_leakage(t, block_type=block_type)
    # If scaffolding stripped everything meaningful, keep beat-marker-stripped text.
    if not t.strip() and before.strip():
        t = strip_internal_beat_markers(before)
        t = strip_duplicate_speaker_prefix(
            t, speaker_label=speaker_label, actor_id=actor_id
        )
        partial["scaffold_strip_reverted"] = True
    exp = str(expected_language or "de").strip().lower()[:2]
    partial["expected_language"] = exp
    partial["english_leak"] = exp == "de" and detect_english_leak_in_german_session(t)
    partial["german_leak"] = exp == "en" and detect_german_leak_in_english_session(t)
    return t.strip(), partial


def detect_english_leak_in_german_session(text: str) -> bool:
    low = f" {text.lower()} "
    return any(x in low for x in _GERMAN_SESSION_ENGLISH_LEAKS)


def detect_german_leak_in_english_session(text: str) -> bool:
    low = f" {text.lower()} "
    return any(x in low for x in _ENGLISH_SESSION_GERMAN_LEAKS)


def sanitize_gm_narration_beat_line(line: str) -> str:
    """Normalize one GM opening beat string before it becomes a narrator scene block."""
    t = strip_internal_beat_markers(str(line or ""))
    t = strip_scaffolding_phrases(t)
    return t.strip()


def _role_token_for_legibility(*, human_actor_id: str | None, selected_player_role: str | None) -> str | None:
    blob = f"{human_actor_id or ''} {selected_player_role or ''}".lower()
    if "annette" in blob:
        return "annette"
    if "alain" in blob:
        return "alain"
    return None


def finalize_visible_scene_blocks(
    blocks: list[dict[str, Any]],
    *,
    expected_language: str,
    human_actor_id: str | None,
    selected_player_role: str | None,
    turn_number: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Dedupe consecutive identical actor blocks and attach VISIBLE-NARRATIVE-CONTRACT diagnostics."""
    out: list[dict[str, Any]] = []
    prev_key: tuple[Any, ...] | None = None
    for b in blocks:
        if not isinstance(b, dict):
            continue
        nb = dict(b)
        bt = str(nb.get("block_type") or nb.get("type") or "").strip().lower()
        txt = str(nb.get("text") or "").strip()
        lab = str(nb.get("speaker_label") or "")
        aid = str(nb.get("actor_id") or "").strip() or None
        cleaned, _p = sanitize_visible_block_text(
            txt,
            block_type=bt,
            speaker_label=lab,
            actor_id=aid,
            expected_language=expected_language,
        )
        if not cleaned:
            continue
        nb["text"] = cleaned
        key = (bt, nb.get("actor_id"), cleaned)
        if key == prev_key and bt in {"actor_line", "actor_action"}:
            continue
        prev_key = key
        out.append(nb)

    exp = str(expected_language or "de").strip().lower()[:2]
    mixed = False
    for nb in out:
        t = str(nb.get("text") or "")
        if exp == "de" and detect_english_leak_in_german_session(t):
            mixed = True
            break
        if exp == "en" and detect_german_leak_in_english_session(t):
            mixed = True
            break

    role_tok = _role_token_for_legibility(
        human_actor_id=human_actor_id,
        selected_player_role=selected_player_role,
    )
    anchor_text = ""
    if turn_number == 0 and len(out) >= 2:
        anchor_text = str(out[1].get("text") or "")
    low_anchor = anchor_text.lower()
    role_visible = bool(role_tok and role_tok in low_anchor) if role_tok else False

    detected = exp
    if mixed:
        detected = "mixed"
    contract_pass = not mixed

    diag: dict[str, Any] = {
        "visible_language_detected": detected,
        "mixed_language_detected": mixed,
        "visible_language_contract_pass": contract_pass,
        "selected_role_visible_in_opening": role_visible if turn_number == 0 else True,
        "player_identity_anchor_present": role_visible if turn_number == 0 else True,
        "visible_narrative_contract_version": "VISIBLE-NARRATIVE-CONTRACT-01",
    }
    return out, diag
