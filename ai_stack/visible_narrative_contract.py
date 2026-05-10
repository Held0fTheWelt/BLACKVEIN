"""VISIBLE-NARRATIVE-CONTRACT-02: sanitize player-visible scene block text.

Strips internal beat markers leaked from structured narration, duplicate speaker
labels, name-only actor noise, English/French *scaffolding* in German sessions,
and generic placeholder stage directions. Emits diagnostics for Langfuse score
metadata (not wired into live_opening_contract_pass gates).
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections.abc import Sequence
from typing import Any

from .goc_frozen_vocab import canonicalize_goc_actor_id, expand_goc_actor_id_aliases


def _accent_fold(s: str) -> str:
    """ASCII-ish fold for speaker-name matching (handles ``Véronique`` vs ``Veronique``)."""
    raw = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(ch for ch in raw if unicodedata.category(ch) != "Mn").lower()


def speaker_labels_match_accent_insensitive(a: str | None, b: str | None) -> bool:
    """Public accent-insensitive equality for ``speaker_label`` (player-shell card dedupe, roster UX).

    Empty labels do not match each other (avoid collapsing unrelated anonymous blocks).
    """
    la = str(a or "").strip()
    lb = str(b or "").strip()
    if not la or not lb:
        return False
    return _accent_fold(la) == _accent_fold(lb)


def _consume_label_from(text: str, start: int, lab: str) -> int | None:
    """Return exclusive end index if ``text[start:]`` begins with ``lab`` (accent-insensitive)."""
    if start >= len(text) or not str(lab or "").strip():
        return None
    target = _accent_fold(lab)
    acc = ""
    for j in range(start, len(text)):
        acc = _accent_fold(text[start : j + 1])
        if acc == target:
            return j + 1
        if len(acc) > len(target) or not target.startswith(acc):
            return None
    return None


def _strip_leading_label_colon_if_duplicate_name_follows(text: str, lab: str) -> str | None:
    """``Veronique: Véronique lächelt`` → ``Véronique lächelt`` (strip redundant first attribution)."""
    t = str(text or "")
    i = 0
    while i < len(t) and t[i].isspace():
        i += 1
    e1 = _consume_label_from(t, i, lab)
    if e1 is None:
        return None
    j = e1
    while j < len(t) and t[j].isspace():
        j += 1
    if j >= len(t) or t[j] != ":":
        return None
    tail = t[j + 1 :]
    k = 0
    while k < len(tail) and tail[k].isspace():
        k += 1
    e2 = _consume_label_from(tail, k, lab)
    if e2 is None:
        return None
    if e2 < len(tail) and (tail[e2].isalnum() or tail[e2] == "_"):
        return None
    return tail[k:].strip()


def _strip_folded_speaker_colon_prefix(text: str, candidate_label: str) -> tuple[str, bool]:
    """Strip ``Label:`` at start when ``candidate_label`` matches accent-insensitively."""
    t = str(text or "").strip()
    lab = str(candidate_label or "").strip()
    if not t or not lab:
        return t, False
    i = 0
    while i < len(t) and t[i].isspace():
        i += 1
    e1 = _consume_label_from(t, i, lab)
    if e1 is None:
        return t, False
    j = e1
    while j < len(t) and t[j].isspace():
        j += 1
    if j >= len(t) or t[j] != ":":
        return t, False
    return t[j + 1 :].strip(), True


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
    for _ in range(8):
        before = t
        lab = str(speaker_label or "").strip()
        if lab:
            pat = re.compile(rf"^\s*{re.escape(lab)}\s*:\s*", re.IGNORECASE)
            if pat.match(t):
                t = pat.sub("", t).strip()
            else:
                t2, ok = _strip_folded_speaker_colon_prefix(t, lab)
                if ok:
                    t = t2
        aid = str(actor_id or "").strip()
        if aid and "_" in aid:
            short = aid.split("_")[0]
            if short:
                pat2 = re.compile(rf"^\s*{re.escape(short)}\s*:\s*", re.IGNORECASE)
                if pat2.match(t):
                    t = pat2.sub("", t).strip()
                else:
                    t2, ok = _strip_folded_speaker_colon_prefix(t, short)
                    if ok:
                        t = t2
        if t == before:
            break
    return t


def _speaker_labels_for_strip(speaker_label: str | None, actor_id: str | None) -> list[str]:
    out: list[str] = []
    if speaker_label and str(speaker_label).strip():
        out.append(str(speaker_label).strip())
    aid = str(actor_id or "").strip()
    if aid and "_" in aid:
        short = aid.split("_")[0].strip()
        if short and all(short.lower() != x.lower() for x in out):
            out.append(short)
    return out


def _try_replace_first_double_colon_folded(t: str, lab: str) -> str | None:
    """Find first ``L: L:`` (accent-insensitive) and collapse to ``L: ``."""
    i = 0
    while i < len(t):
        if i > 0 and (t[i - 1].isalnum() or t[i - 1] == "_"):
            i += 1
            continue
        e1 = _consume_label_from(t, i, lab)
        if e1 is None:
            i += 1
            continue
        j = e1
        while j < len(t) and t[j].isspace():
            j += 1
        if j >= len(t) or t[j] != ":":
            i += 1
            continue
        j += 1
        while j < len(t) and t[j].isspace():
            j += 1
        e2 = _consume_label_from(t, j, lab)
        if e2 is None:
            i += 1
            continue
        k = e2
        while k < len(t) and t[k].isspace():
            k += 1
        if k >= len(t) or t[k] != ":":
            i += 1
            continue
        return t[:i] + lab + ": " + t[k + 1 :].lstrip()
    return None


def _collapse_accent_insensitive_double_colon(t: str, labels: list[str]) -> tuple[str, int]:
    removed = 0
    if not labels:
        return t, 0
    for lab in labels:
        for _ in range(50):
            repl = _try_replace_first_double_colon_folded(t, lab)
            if repl is None:
                break
            t = repl
            removed += 1
    return t, removed


def collapse_repeated_speaker_colon_segments(
    text: str,
    *,
    speaker_label: str | None,
    actor_id: str | None,
) -> tuple[str, int]:
    """Collapse ``Name: Name:`` (same label twice) anywhere in the string."""
    removed = 0
    t = str(text or "")
    labels = _speaker_labels_for_strip(speaker_label, actor_id)
    for lab in labels:
        pat = re.compile(rf"(?i)\b{re.escape(lab)}\s*:\s*{re.escape(lab)}\s*:\s*")
        while pat.search(t):
            t = pat.sub(f"{lab}: ", t, count=1)
            removed += 1
    t2, n2 = _collapse_accent_insensitive_double_colon(t, labels)
    return t2, removed + n2


_GOC_STUTTER_DISPLAY_NAMES = ("Michel", "Alain", "Annette", "Veronique", "Véronique")


def _goc_stutter_name_tokens(
    *,
    speaker_label: str | None = None,
    actor_id: str | None = None,
) -> tuple[str, ...]:
    """Surface tokens for ``Name: Name`` stutter collapse (roster + static GoC fallback)."""
    ordered: list[str] = []
    seen_lower: set[str] = set()

    def _add(name: str) -> None:
        n = str(name or "").strip()
        if not n:
            return
        low = _accent_fold(n)
        if low in seen_lower:
            return
        seen_lower.add(low)
        ordered.append(n)

    for n in _GOC_STUTTER_DISPLAY_NAMES:
        _add(n)
    for lab in _speaker_labels_for_strip(speaker_label, actor_id):
        _add(lab)
    aid = str(actor_id or "").strip()
    if aid:
        canon = canonicalize_goc_actor_id(aid) or aid
        for al in expand_goc_actor_id_aliases(canon):
            a = str(al).strip()
            if not a or "_" in a:
                continue
            _add(a)
            if a.islower():
                _add(a.title())
    return tuple(ordered)


def dedupe_goc_speaker_colon_stutter_visible(
    text: str,
    *,
    speaker_label: str | None = None,
    actor_id: str | None = None,
) -> str:
    """Collapse mistaken ``Name: Name …`` before stage prose (any GoC NPC), globally.

    Runs repeatedly so chained model stutter is fully removed. Safe for quoted speech:
    ``Name: "…"`` is preserved because the colon is not followed by a repeated surface name
    token. Handles ``Veronique: Véronique lächelt`` → ``Veronique lächelt``.

    When ``speaker_label`` / ``actor_id`` are provided, also folds alias spellings derived
    from the roster (not only the static GoC display tuple).
    """
    t = str(text or "")
    if not t.strip():
        return t
    names = _goc_stutter_name_tokens(speaker_label=speaker_label, actor_id=actor_id)
    for _ in range(24):
        before = t
        for name in names:
            esc = re.escape(name)
            t = re.sub(rf"(?i)\b({esc})\s*:\s*\1\s+", r"\1 ", t)
        t = re.sub(r"(?i)\b(Veronique)\s*:\s*(V[ée]ronique)\s+", r"\1 ", t)
        t = re.sub(r"(?i)\b(V[ée]ronique)\s*:\s*(Veronique)\s+", r"\1 ", t)
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                if _accent_fold(a) != _accent_fold(b) or a.lower() == b.lower():
                    continue
                ea, eb = re.escape(a), re.escape(b)
                t = re.sub(rf"(?i)\b({ea})\s*:\s*({eb})\s+", rf"{a} ", t)
                t = re.sub(rf"(?i)\b({eb})\s*:\s*({ea})\s+", rf"{b} ", t)
        if t == before:
            break
    return t


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
    dup_strip = 0
    for _ in range(8):
        prev_t = t
        for lab in _speaker_labels_for_strip(speaker_label, actor_id):
            stripped = _strip_leading_label_colon_if_duplicate_name_follows(t, lab)
            if stripped is not None:
                t = stripped
                dup_strip += 1
                break
        if t == prev_t:
            break
    if dup_strip:
        partial["duplicate_actor_label_removed"] = int(
            partial.get("duplicate_actor_label_removed") or 0
        ) + int(dup_strip)
    if str(block_type or "").strip().lower() in {"actor_line", "actor_action"}:
        t_stutter = dedupe_goc_speaker_colon_stutter_visible(
            t,
            speaker_label=str(speaker_label or "") or None,
            actor_id=str(actor_id).strip() if actor_id else None,
        )
        if t_stutter != t:
            partial["goc_speaker_colon_stutter_deduped"] = True
        t = t_stutter
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


def _word_matches_any_speaker_token(word: str, tokens: set[str]) -> bool:
    fw = _accent_fold(word)
    return any(fw == _accent_fold(tok) for tok in tokens if tok)


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
    if len(words) <= 2 and all(_word_matches_any_speaker_token(w, tokens) for w in words):
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


def _goc_visible_lane_text_fold(s: str) -> str:
    """Lowercase + light accent fold (matches world-engine ``_goc_visible_text_fold`` for substring checks)."""
    t = (s or "").strip().lower()
    for a, b in (
        ("ä", "a"),
        ("ö", "o"),
        ("ü", "u"),
        ("ß", "ss"),
        ("é", "e"),
        ("è", "e"),
        ("ê", "e"),
        ("ë", "e"),
        ("à", "a"),
        ("â", "a"),
        ("á", "a"),
        ("ô", "o"),
        ("ò", "o"),
        ("ó", "o"),
        ("ù", "u"),
        ("û", "u"),
        ("ú", "u"),
        ("ç", "c"),
        ("ï", "i"),
        ("î", "i"),
        ("ì", "i"),
        ("í", "i"),
    ):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t, flags=re.UNICODE).strip()


def prune_goc_actor_actions_subsumed_by_prior_actor_lines(
    blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove ``actor_action`` blocks already covered by prior same-actor story text.

    Uses a running concatenation of each actor's last ``actor_line`` plus any kept
    ``actor_action`` rows so a duplicate action that only appears after merging
    non-duplicate actions is still dropped. Match is **per** ``actor_id``.

    Drops when folded action is a substring of the running text, when
    ``_near_duplicate_visible_texts`` matches paraphrased duplicates, or when
    significant-token recall from the action appears in the running text
    (``_goc_npc_action_redundant_vs_running_visible``).

    Used by world-engine projection and by the backend player bundle (cumulative transcript).
    """
    out: list[dict[str, Any]] = []
    running_visible_by_actor: dict[str, str] = {}
    min_fold = 12

    def _actor_key(block: dict[str, Any]) -> str:
        return str(block.get("actor_id") or "").strip() or "__none__"

    for b in blocks:
        if not isinstance(b, dict):
            continue
        bt = str(b.get("block_type") or "").strip().lower()
        if bt == "actor_action":
            ak = _actor_key(b)
            lab = str(b.get("speaker_label") or "").strip()
            aid = str(b.get("actor_id") or "").strip() or None
            raw = str(b.get("text") or "")
            act_clean = strip_duplicate_speaker_prefix(
                raw, speaker_label=lab, actor_id=aid
            ).strip()
            act_clean = dedupe_goc_speaker_colon_stutter_visible(
                act_clean, speaker_label=lab or None, actor_id=aid
            )
            af = _goc_visible_lane_text_fold(act_clean)
            if len(af) >= min_fold:
                run = running_visible_by_actor.get(ak, "")
                if _goc_npc_action_redundant_vs_running_visible(act_clean, run):
                    continue
            out.append(b)
            prev_run = running_visible_by_actor.get(ak, "")
            running_visible_by_actor[ak] = (
                f"{prev_run} {act_clean}".strip() if prev_run else act_clean
            )
            continue

        out.append(b)
        if bt == "actor_line":
            ak = _actor_key(b)
            lab = str(b.get("speaker_label") or "").strip()
            aid = str(b.get("actor_id") or "").strip() or None
            line = str(b.get("text") or "")
            line_clean = strip_duplicate_speaker_prefix(
                line, speaker_label=lab, actor_id=aid
            ).strip()
            line_clean = dedupe_goc_speaker_colon_stutter_visible(
                line_clean, speaker_label=lab or None, actor_id=aid
            )
            running_visible_by_actor[ak] = line_clean
    return out


def polish_goc_scene_blocks_for_player_shell(blocks: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Lightweight GoC-only polish for blocks served to the player shell (HTTP bundle path).

    World-engine already finalizes at commit time; this pass fixes **persisted** cumulative
    ``story_window`` slices and any edge path that skipped projection — colon stutter and
    redundant ``actor_action`` rows that echo the same turn's ``actor_line`` tail.
    """
    if not blocks:
        return []
    out: list[dict[str, Any]] = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        nb = dict(b)
        bt = str(nb.get("block_type") or "").strip().lower()
        if bt in {"actor_line", "actor_action"}:
            nb["text"] = dedupe_goc_speaker_colon_stutter_visible(
                str(nb.get("text") or ""),
                speaker_label=str(nb.get("speaker_label") or "") or None,
                actor_id=str(nb.get("actor_id") or "").strip() or None,
            )
        out.append(nb)
    return prune_goc_actor_actions_subsumed_by_prior_actor_lines(out)


def _near_duplicate_visible_texts(a: str, b: str, *, threshold: float = 0.9) -> bool:
    na, nb = _norm_for_near_dedupe(a), _norm_for_near_dedupe(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    return difflib.SequenceMatcher(None, na, nb).ratio() >= threshold


def _goc_npc_action_redundant_vs_running_visible(
    act_clean: str,
    running_visible: str,
    *,
    min_fold: int = 12,
    near_duplicate_threshold: float = 0.88,
    near_dup_min_len: int = 24,
    min_act_chars_token_rule: int = 28,
    min_run_chars_token_rule: int = 40,
    min_distinct_tokens: int = 5,
    token_coverage_of_action: float = 0.82,
) -> bool:
    """True when NPC ``actor_action`` text is already expressed in prior same-actor story text.

    Uses (1) folded substring containment, (2) ``_near_duplicate_visible_texts`` on full
    strings, or (3) high recall of length>=4 tokens from the action in the running text
    (paraphrases where ``SequenceMatcher`` vs the full line is too low).
    """
    act = str(act_clean or "").strip()
    run = str(running_visible or "").strip()
    if not act or not run:
        return False
    af = _goc_visible_lane_text_fold(act)
    rf = _goc_visible_lane_text_fold(run)
    if len(af) >= min_fold and rf and af in rf:
        return True
    if (
        len(af) >= min_fold
        and len(act) >= near_dup_min_len
        and len(run) >= near_dup_min_len
        and _near_duplicate_visible_texts(act, run, threshold=near_duplicate_threshold)
    ):
        return True
    fold_a = _goc_visible_lane_text_fold(act)
    fold_r = _goc_visible_lane_text_fold(run)
    toks_a = set(re.findall(r"[a-z]{4,}", fold_a))
    toks_r = set(re.findall(r"[a-z]{4,}", fold_r))
    if (
        len(toks_a) >= min_distinct_tokens
        and len(act) >= min_act_chars_token_rule
        and len(run) >= min_run_chars_token_rule
    ):
        cov = len(toks_a & toks_r) / len(toks_a)
        if cov >= token_coverage_of_action:
            return True
    return False


def _collect_player_echo_strings(raw: Sequence[str] | None) -> list[str]:
    """Deduped recent player lines (min length) for NPC echo suppression."""
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        s = str(item or "").strip()
        if len(s) < 6:
            continue
        key = _norm_for_near_dedupe(s)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out[-5:]


def _is_goc_human_lane_actor_id(
    actor_id: str | None,
    *,
    human_actor_id: str | None,
    selected_player_role: str | None,
) -> bool:
    if not actor_id or not str(actor_id).strip():
        return False
    actor_canon = canonicalize_goc_actor_id(str(actor_id).strip())
    if not actor_canon:
        return False
    if human_actor_id:
        h = canonicalize_goc_actor_id(str(human_actor_id).strip())
        if h and actor_canon == h:
            return True
    if selected_player_role:
        r = canonicalize_goc_actor_id(str(selected_player_role).strip())
        if r and actor_canon == r:
            return True
    return False


def _npc_visible_text_echoes_player_line(
    cleaned: str,
    *,
    speaker_label: str,
    actor_id: str | None,
    block_type: str,
    human_actor_id: str | None,
    selected_player_role: str | None,
    player_strings: list[str],
) -> bool:
    """True when an NPC actor_line / actor_action repeats committed player input (model leak)."""
    bt = str(block_type or "").strip().lower()
    if bt not in {"actor_line", "actor_action"}:
        return False
    if _is_goc_human_lane_actor_id(
        actor_id, human_actor_id=human_actor_id, selected_player_role=selected_player_role
    ):
        return False
    compare = strip_duplicate_speaker_prefix(
        str(cleaned or "").strip(),
        speaker_label=speaker_label,
        actor_id=actor_id,
    ).strip()
    if not compare:
        return False
    cn = _norm_for_near_dedupe(compare)
    if not cn:
        return False
    for pin in player_strings:
        ps = str(pin or "").strip()
        if len(ps) < 6:
            continue
        if _near_duplicate_visible_texts(compare, ps, threshold=0.86):
            return True
        pn = _norm_for_near_dedupe(ps)
        if not pn:
            continue
        if pn == cn:
            return True
        if len(pn) >= 12 and pn in cn and len(pn) >= int(len(cn) * 0.82):
            return True
    return False


def finalize_visible_scene_blocks(
    blocks: list[dict[str, Any]],
    *,
    expected_language: str,
    human_actor_id: str | None,
    selected_player_role: str | None,
    turn_number: int,
    player_input_echo_strings: Sequence[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Sanitize, dedupe, and attach VISIBLE-NARRATIVE-CONTRACT-02 diagnostics."""
    exp = str(expected_language or "de").strip().lower()[:2] or "de"
    echo_candidates = _collect_player_echo_strings(player_input_echo_strings)
    out: list[dict[str, Any]] = []
    prev_key: tuple[Any, ...] | None = None
    counts: dict[str, int] = {
        "name_only_actor_block_removed": 0,
        "label_only_line_removed": 0,
        "duplicate_actor_label_removed": 0,
        "placeholder_action_removed": 0,
        "actor_line_action_tail_stripped": 0,
        "near_duplicate_visible_block_removed": 0,
        "actor_action_subsumed_by_actor_line_removed": 0,
        "player_input_echo_removed_from_npc_block": 0,
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
        if echo_candidates and _npc_visible_text_echoes_player_line(
            cleaned,
            speaker_label=lab,
            actor_id=aid,
            block_type=bt,
            human_actor_id=human_actor_id,
            selected_player_role=selected_player_role,
            player_strings=echo_candidates,
        ):
            counts["player_input_echo_removed_from_npc_block"] += 1
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

    # actor_action whose visible text is already contained in a prior actor_line (same actor).
    merged_subsumption: list[dict[str, Any]] = []
    for nb in out:
        bt = str(nb.get("block_type") or "").strip().lower()
        if bt == "actor_action":
            aid = str(nb.get("actor_id") or "").strip()
            nt = str(nb.get("text") or "")
            nt_st = nt.strip()
            drop = False
            if aid and len(nt_st) >= 10:
                nfold = _goc_visible_lane_text_fold(nt)
                if len(nfold) >= 12:
                    for prev_nb in reversed(merged_subsumption):
                        pbt = str(prev_nb.get("block_type") or "").strip().lower()
                        if pbt != "actor_line":
                            continue
                        if str(prev_nb.get("actor_id") or "").strip() != aid:
                            continue
                        pt = str(prev_nb.get("text") or "")
                        pfold = _goc_visible_lane_text_fold(pt)
                        if nfold and pfold and nfold in pfold:
                            drop = True
                            break
            if drop:
                counts["actor_action_subsumed_by_actor_line_removed"] += 1
                continue
        merged_subsumption.append(nb)
    out = merged_subsumption

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
        "actor_action_subsumed_by_actor_line_removed": counts[
            "actor_action_subsumed_by_actor_line_removed"
        ],
        "player_input_echo_removed_from_npc_block": counts["player_input_echo_removed_from_npc_block"],
    }
    return out, diag
