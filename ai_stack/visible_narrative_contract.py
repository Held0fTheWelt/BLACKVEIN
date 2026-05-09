"""VISIBLE-NARRATIVE-CONTRACT-02: sanitize player-visible scene block text.

Strips internal beat markers leaked from structured narration, duplicate speaker
labels, name-only actor noise, English/French *scaffolding* in German sessions,
and generic placeholder stage directions. Emits diagnostics for Langfuse score
metadata (not wired into live_opening_contract_pass gates).
"""

from __future__ import annotations

import difflib
import re
from typing import Any

# Model / prompt sometimes echo these prefixes into list items or paragraphs.
_INTERNAL_BEAT_PREFIX_RE = re.compile(
    r"(?m)^\s*(narrator_intro|role_anchor|scene_setup)\s*:\s*",
    re.IGNORECASE,
)

# English scaffolding / stage-direction leaks in German-session visible text.
_GERMAN_SESSION_ENGLISH_LEAKS = (
    "you are ",
    "the paris salon:",
    "the paris salon;",
    " arriving with ",
    " into a room",
    " not as a spectator",
    " reacts immediately",
    " reacts instantly",
    " gently nods",
    "gently nods",
    " offers a warm",
    "offers a warm",
    " maintaining eye contact",
    "maintaining eye contact",
    " to set a civil",
    "to set a civil",
    " warm smile",
)

# Instructional French scaffolding (not in-character quoted lines alone).
_GERMAN_SESSION_FRENCH_SCAFFOLD_LEAKS = (
    "vous êtes ",
    "vous arrivez ",
    "vous n'êtes pas ",
    "en tant que ",
    "pas comme spectateur",
    "dans une salle",
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


def collapse_repeated_speaker_colon_segments(
    text: str,
    *,
    speaker_label: str | None,
    actor_id: str | None,
) -> tuple[str, int]:
    """Collapse ``Name: Name:`` (same label twice) anywhere in the string."""
    removed = 0
    t = str(text or "")
    labels: list[str] = []
    if speaker_label and speaker_label.strip():
        labels.append(speaker_label.strip())
    if actor_id and "_" in str(actor_id):
        short = str(actor_id).split("_")[0].strip()
        if short and all(short.lower() != x.lower() for x in labels):
            labels.append(short)
    for lab in labels:
        pat = re.compile(rf"(?i)\b{re.escape(lab)}\s*:\s*{re.escape(lab)}\s*:\s*")
        while pat.search(t):
            t = pat.sub(f"{lab}: ", t, count=1)
            removed += 1
    return t, removed


def _strip_cross_lane_leakage(text: str, *, block_type: str) -> str:
    """Reduce actor_line carrying stage-direction-only leakage (heuristic)."""
    t = str(text or "").strip()
    bt = str(block_type or "").strip().lower()
    if bt == "actor_line" and t.startswith("*") and t.endswith("*"):
        return t.strip("*").strip()
    return t


def _is_label_colon_without_substance(text: str) -> bool:
    """True when visible text is only ``Name:`` / ``Name:   `` with nothing after the colon."""
    raw = str(text or "").strip()
    if ":" not in raw:
        return False
    head, tail = raw.split(":", 1)
    return bool(head.strip()) and not tail.strip()


def _placeholder_action_was_stripped(before: str, after: str) -> bool:
    low_b, low_a = before.lower(), after.lower()
    for needle in ("reacts immediately", "reacts instantly"):
        if needle in low_b and needle not in low_a:
            return True
    return False


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
    before_scaffold = t
    t = strip_scaffolding_phrases(t)
    if _placeholder_action_was_stripped(before_scaffold, t):
        partial["placeholder_action_removed"] = True
    t = strip_duplicate_speaker_prefix(t, speaker_label=speaker_label, actor_id=actor_id)
    t2, dup_n = collapse_repeated_speaker_colon_segments(
        t, speaker_label=speaker_label, actor_id=actor_id
    )
    t = t2
    if dup_n:
        partial["duplicate_actor_label_removed"] = int(dup_n)
    t = _strip_cross_lane_leakage(t, block_type=block_type)
    if not t.strip() and before.strip():
        t = strip_internal_beat_markers(before)
        t = strip_duplicate_speaker_prefix(t, speaker_label=speaker_label, actor_id=actor_id)
        t, _ = collapse_repeated_speaker_colon_segments(
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


def detect_french_scaffold_in_german_session(text: str) -> bool:
    low = f" {text.lower()} "
    return any(x in low for x in _GERMAN_SESSION_FRENCH_SCAFFOLD_LEAKS)


def detect_german_leak_in_english_session(text: str) -> bool:
    low = f" {text.lower()} "
    return any(x in low for x in _ENGLISH_SESSION_GERMAN_LEAKS)


def _mixed_language_in_session_text(text: str, *, expected_language: str) -> bool:
    exp = str(expected_language or "de").strip().lower()[:2]
    if exp == "de":
        return detect_english_leak_in_german_session(text) or detect_french_scaffold_in_german_session(
            text
        )
    if exp == "en":
        return detect_german_leak_in_english_session(text)
    return False


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


def _speaker_name_tokens(speaker_label: str, actor_id: str | None) -> set[str]:
    out: set[str] = set()
    lab = str(speaker_label or "").strip()
    if lab:
        out.add(lab.lower())
        if " " in lab:
            out.add(lab.split()[0].lower())
    if actor_id and "_" in str(actor_id):
        out.add(str(actor_id).split("_")[0].lower())
    return {x for x in out if x}


def _is_name_only_actor_block(
    text: str,
    *,
    speaker_label: str,
    actor_id: str | None,
    block_type: str,
) -> bool:
    bt = str(block_type or "").strip().lower()
    if bt not in {"actor_line", "actor_action"}:
        return False
    t = str(text or "").strip()
    if not t:
        return True
    tokens = _speaker_name_tokens(speaker_label, actor_id)
    low = re.sub(r"[^\w\säöüéèêàâîïôùûçß]", "", t.lower(), flags=re.UNICODE)
    words = [w for w in low.split() if w]
    if not words:
        return True
    if len(words) <= 2 and all(w in tokens for w in words):
        return True
    stripped = t
    for tok in sorted(tokens, key=len, reverse=True):
        if tok:
            stripped = re.sub(rf"(?i)^{re.escape(tok)}\s*:\s*", "", stripped).strip()
            stripped = re.sub(rf"(?i)\b{re.escape(tok)}\b\s*", "", stripped).strip()
    letters = sum(1 for c in stripped if c.isalpha())
    return letters < 3


def _strip_actor_line_mixed_tail(
    text: str,
    *,
    expected_language: str,
    block_type: str,
) -> tuple[str, bool]:
    """If an actor_line ends with English stage prose in a German session, keep the dialogue prefix."""
    if str(block_type or "").strip().lower() != "actor_line":
        return text, False
    if str(expected_language or "de").strip().lower()[:2] != "de":
        return text, False
    raw = str(text or "").strip()
    if not raw or not detect_english_leak_in_german_session(raw):
        return text, False
    parts = re.split(r"(?<=[.!?])\s+", raw)
    if len(parts) < 2:
        return text, False
    first = parts[0].strip()
    tail = " ".join(parts[1:]).strip()
    if detect_english_leak_in_german_session(tail) and not detect_english_leak_in_german_session(first):
        return first, True
    return text, False


def _strip_actor_line_after_repeated_speaker_colon(
    text: str,
    *,
    speaker_label: str,
    expected_language: str,
    block_type: str,
) -> tuple[str, bool]:
    """``Speaker: … Speaker: <english>`` in one line — keep first speech chunk only (German sessions)."""
    if str(block_type or "").strip().lower() != "actor_line":
        return text, False
    if str(expected_language or "de").strip().lower()[:2] != "de":
        return text, False
    lab = str(speaker_label or "").strip()
    raw = str(text or "").strip()
    if not lab or not raw or not detect_english_leak_in_german_session(raw):
        return text, False
    pat = re.compile(rf"(?i){re.escape(lab)}\s*:\s*")
    segments = [s.strip() for s in pat.split(raw) if str(s).strip()]
    if len(segments) < 2:
        return text, False
    head = segments[0].strip()
    tail = " ".join(segments[1:]).strip()
    if detect_english_leak_in_german_session(tail) and not detect_english_leak_in_german_session(head):
        return f"{lab}: {head}".strip(), True
    return text, False


def _norm_for_near_dedupe(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w]", "", s.lower(), flags=re.UNICODE))


def _near_duplicate_visible_texts(a: str, b: str, *, threshold: float = 0.9) -> bool:
    na, nb = _norm_for_near_dedupe(a), _norm_for_near_dedupe(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    return difflib.SequenceMatcher(None, na, nb).ratio() >= threshold


def finalize_visible_scene_blocks(
    blocks: list[dict[str, Any]],
    *,
    expected_language: str,
    human_actor_id: str | None,
    selected_player_role: str | None,
    turn_number: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Sanitize, dedupe, and attach VISIBLE-NARRATIVE-CONTRACT-02 diagnostics."""
    exp = str(expected_language or "de").strip().lower()[:2] or "de"
    out: list[dict[str, Any]] = []
    prev_key: tuple[Any, ...] | None = None
    counts: dict[str, int] = {
        "name_only_actor_block_removed": 0,
        "label_only_line_removed": 0,
        "duplicate_actor_label_removed": 0,
        "placeholder_action_removed": 0,
        "actor_line_action_tail_stripped": 0,
        "near_duplicate_visible_block_removed": 0,
    }

    for b in blocks:
        if not isinstance(b, dict):
            continue
        nb = dict(b)
        bt = str(nb.get("block_type") or nb.get("type") or "").strip().lower()
        txt = str(nb.get("text") or "").strip()
        lab = str(nb.get("speaker_label") or "")
        aid = str(nb.get("actor_id") or "").strip() or None
        cleaned, partial = sanitize_visible_block_text(
            txt,
            block_type=bt,
            speaker_label=lab,
            actor_id=aid,
            expected_language=expected_language,
        )
        if partial.get("placeholder_action_removed"):
            counts["placeholder_action_removed"] += 1
        counts["duplicate_actor_label_removed"] += int(partial.get("duplicate_actor_label_removed") or 0)
        if not cleaned:
            continue
        if _is_label_colon_without_substance(cleaned) and bt in {
            "narrator",
            "narrator_scene",
            "narrator_perception",
            "stage_direction",
            "environmental",
        }:
            counts["label_only_line_removed"] += 1
            continue
        if _is_name_only_actor_block(cleaned, speaker_label=lab, actor_id=aid, block_type=bt):
            counts["name_only_actor_block_removed"] += 1
            continue
        cleaned2, rep_stripped = _strip_actor_line_after_repeated_speaker_colon(
            cleaned, speaker_label=lab, expected_language=exp, block_type=bt
        )
        if rep_stripped:
            counts["actor_line_action_tail_stripped"] += 1
        cleaned = cleaned2.strip()
        cleaned2, tail_stripped = _strip_actor_line_mixed_tail(
            cleaned, expected_language=exp, block_type=bt
        )
        if tail_stripped:
            counts["actor_line_action_tail_stripped"] += 1
        cleaned = cleaned2.strip()
        if not cleaned:
            continue
        nb["text"] = cleaned
        key = (bt, nb.get("actor_id"), cleaned)
        if key == prev_key and bt in {"actor_line", "actor_action"}:
            counts["near_duplicate_visible_block_removed"] += 1
            continue
        prev_key = key
        out.append(nb)

    # Near-identical consecutive actor_line / actor_action (same actor).
    deduped: list[dict[str, Any]] = []
    for nb in out:
        if not deduped:
            deduped.append(nb)
            continue
        prev = deduped[-1]
        pbt = str(prev.get("block_type") or "").strip().lower()
        bt = str(nb.get("block_type") or "").strip().lower()
        if (
            bt in {"actor_line", "actor_action"}
            and pbt in {"actor_line", "actor_action"}
            and prev.get("actor_id") == nb.get("actor_id")
            and prev.get("actor_id")
        ):
            if _near_duplicate_visible_texts(str(prev.get("text") or ""), str(nb.get("text") or "")):
                counts["near_duplicate_visible_block_removed"] += 1
                continue
        deduped.append(nb)
    out = deduped

    mixed = False
    for nb in out:
        t = str(nb.get("text") or "")
        if _mixed_language_in_session_text(t, expected_language=exp):
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
        "visible_narrative_contract_version": "VISIBLE-NARRATIVE-CONTRACT-02",
        "name_only_actor_block_removed": counts["name_only_actor_block_removed"],
        "label_only_line_removed": counts["label_only_line_removed"],
        "duplicate_actor_label_removed": counts["duplicate_actor_label_removed"],
        "placeholder_action_removed": counts["placeholder_action_removed"],
        "actor_line_action_tail_stripped": counts["actor_line_action_tail_stripped"],
        "near_duplicate_visible_block_removed": counts["near_duplicate_visible_block_removed"],
    }
    return out, diag
