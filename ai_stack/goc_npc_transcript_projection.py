"""Roster-driven segmentation for God of Carnage NPC transcript projection.

Builds speaker-prefix matchers from ``runtime_projection`` (NPC roster) and
``canonicalize_goc_actor_id`` / alias expansion — no hardcoded ``Veronique|…``
union in the world-engine split path.

Cardinality of projected blocks follows content + policy, not a fixed count.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Sequence

from ai_stack.goc_frozen_vocab import (
    canonicalize_goc_actor_id,
    expand_goc_actor_id_aliases,
)
from ai_stack.goc_yaml_authority import (
    goc_actor_display_name,
    goc_actor_ids_from_content,
    goc_actor_identity,
)


def _fold_label(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _content_actor_id(value: str) -> str:
    raw = str(value or "").strip()
    ident = goc_actor_identity(raw)
    if ident.get("actor_id"):
        return str(ident["actor_id"])
    return canonicalize_goc_actor_id(raw)


def _content_actor_aliases(actor_id: str) -> set[str]:
    aliases = set(expand_goc_actor_id_aliases(actor_id))
    ident = goc_actor_identity(actor_id)
    for key in ("actor_id", "character_key", "name", "first_name"):
        val = str(ident.get(key) or "").strip()
        if val:
            aliases.add(val)
    return aliases


def goc_shell_display_firstname(actor_id: str) -> str:
    aid = str(_content_actor_id(str(actor_id).strip()) or str(actor_id).strip()).strip()
    resolved = goc_actor_display_name(aid, first_name=True)
    if resolved != (aid.replace("_", " ").title() if aid else "Actor"):
        return resolved
    return aid.replace("_", " ").title() if aid else "Actor"


def goc_npc_roster_canonical_ids(runtime_projection: dict[str, Any] | None) -> tuple[str, ...]:
    """Canonical NPC actor ids for prefix matching (excludes bound human / role)."""
    proj = runtime_projection if isinstance(runtime_projection, dict) else {}
    exclude: set[str] = set()
    for key in ("human_actor_id", "selected_player_role"):
        c = _content_actor_id(str(proj.get(key) or "").strip())
        if c:
            exclude.add(c)
    raw = proj.get("npc_actor_ids")
    out: list[str] = []
    seen: set[str] = set()
    content_actor_ids = set(goc_actor_ids_from_content())
    if isinstance(raw, list) and raw:
        for item in raw:
            c = _content_actor_id(str(item).strip())
            if not c or c in exclude or c not in content_actor_ids:
                continue
            if c not in seen:
                seen.add(c)
                out.append(c)
        return tuple(out)
    for c in goc_actor_ids_from_content():
        if c not in exclude:
            out.append(c)
    return tuple(out)


def _prefix_tokens_for_actor(canonical_id: str) -> list[str]:
    tokens: set[str] = set()
    fn = goc_shell_display_firstname(canonical_id)
    if fn:
        tokens.add(fn)
    ident = goc_actor_identity(canonical_id)
    for key in ("name", "first_name", "character_key"):
        val = str(ident.get(key) or "").strip()
        if val:
            tokens.add(val)
    stem = canonical_id.split("_", 1)[0].strip()
    if stem:
        tokens.add(stem.title())
        tokens.add(stem.capitalize())
    for alias in expand_goc_actor_id_aliases(canonical_id):
        a = str(alias).strip()
        if not a or "_" in a:
            continue
        tokens.add(a)
        tokens.add(a.title())
        if a.islower():
            tokens.add(a.capitalize())
    return sorted(tokens, key=lambda s: (-len(s), s.lower()))


def goc_speaker_prefix_label_alternatives(roster_canonical: Sequence[str]) -> list[str]:
    """Distinct display tokens (longest-first) for alternation regex."""
    bag: list[str] = []
    seen_lower: set[str] = set()
    for aid in roster_canonical:
        for tok in _prefix_tokens_for_actor(aid):
            low = tok.lower()
            if low in seen_lower:
                continue
            seen_lower.add(low)
            bag.append(tok)
    bag.sort(key=lambda s: (-len(s), s.lower()))
    return bag


def compile_goc_line_speaker_prefix_pattern(roster_canonical: Sequence[str]) -> re.Pattern[str] | None:
    labels = goc_speaker_prefix_label_alternatives(roster_canonical)
    if not labels:
        return None
    inner = "|".join(re.escape(lab) for lab in labels)
    return re.compile(rf"\b(?P<goc_spk>{inner})\s*:\s*", re.IGNORECASE)


def goc_prefix_label_to_actor_id(label: str, roster_canonical: Sequence[str]) -> str | None:
    raw = str(label or "").strip()
    if not raw:
        return None
    roster_set = frozenset(str(x) for x in roster_canonical if str(x).strip())
    cand = canonicalize_goc_actor_id(raw)
    if cand and cand in roster_set:
        return cand
    low_raw = raw.lower()
    scored: list[tuple[int, str]] = []
    for aid in roster_canonical:
        for alias in _content_actor_aliases(aid):
            al = str(alias).strip()
            if len(al) < 2:
                continue
            al_low = al.lower()
            if low_raw.startswith(al_low) or _fold_label(low_raw).startswith(_fold_label(al_low)):
                scored.append((len(al), aid))
    if scored:
        scored.sort(key=lambda t: (-t[0], t[1]))
        return scored[0][1]
    tail = canonicalize_goc_actor_id(raw)
    if tail and tail in roster_set:
        return tail
    return None


def _ends_dialogue_then_stage_boundary(prev_body: str, next_body: str) -> bool:
    """Heuristic: prior span ends like dialogue; next span starts as stage (no opening quote)."""
    pb = str(prev_body or "").rstrip()
    nb = str(next_body or "").lstrip()
    if not pb or not nb:
        return False
    closing_end = {'"', "'", "\u201d", "\u2019", "»", ")"}
    if pb[-1] in closing_end:
        return True
    if len(pb) >= 2 and pb[-2] in closing_end and pb[-1] in ".!?":
        return True
    opening_start = {'"', "\u201c", "\u201e", "«", "„"}
    if nb[0] in opening_start:
        return False
    return False


def goc_transcript_policy_flags(story_runtime_experience: dict[str, Any] | None) -> dict[str, bool]:
    exp = story_runtime_experience if isinstance(story_runtime_experience, dict) else {}

    def _bool(key: str, default: bool) -> bool:
        v = exp.get(key)
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            lo = v.strip().lower()
            if lo in {"true", "1", "yes", "on"}:
                return True
            if lo in {"false", "0", "no", "off"}:
                return False
        return default

    return {
        "merge_consecutive_same_actor": _bool("goc_transcript_merge_consecutive_same_actor", True),
        "split_speech_stage_same_actor": _bool("goc_transcript_split_speech_stage_same_actor", False),
        "map_action_lines_to_actor_line_lane": _bool("goc_map_action_lines_to_actor_line_lane", False),
    }


def split_merged_goc_actor_line_segments(
    text: str,
    *,
    runtime_projection: dict[str, Any] | None = None,
    story_runtime_experience: dict[str, Any] | None = None,
) -> list[tuple[str, str, str]]:
    """Split one ``actor_line`` by roster speaker prefixes; merge policy is configurable."""
    t = str(text or "").strip()
    if not t:
        return []
    roster = goc_npc_roster_canonical_ids(runtime_projection)
    pat = compile_goc_line_speaker_prefix_pattern(roster)
    if pat is None:
        return []
    flags = goc_transcript_policy_flags(story_runtime_experience)
    merge_same = flags["merge_consecutive_same_actor"]
    split_stage = flags["split_speech_stage_same_actor"]

    matches = list(pat.finditer(t))
    if len(matches) < 2:
        return []
    spans: list[tuple[str, str, str]] = []
    for i, m in enumerate(matches):
        lab = str(m.group("goc_spk") or "").strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(t)
        body = t[body_start:body_end].strip()
        aid = goc_prefix_label_to_actor_id(lab, roster)
        if not aid or not body:
            continue
        sh = goc_shell_display_firstname(aid)
        spans.append((aid, sh, body))
    if len(spans) < 2:
        return []
    merged: list[tuple[str, str, str]] = []
    for aid, sh, body in spans:
        if (
            merged
            and merged[-1][0] == aid
            and merge_same
            and not (split_stage and _ends_dialogue_then_stage_boundary(merged[-1][2], body))
        ):
            p_aid, p_sh, p_body = merged[-1]
            merged[-1] = (p_aid, p_sh, f"{p_body} {body}".strip())
        else:
            merged.append((aid, sh, body))
    return merged


def goc_spoken_line_row_suspects_multiple_speakers(
    line_text: str,
    *,
    runtime_projection: dict[str, Any] | None = None,
) -> bool:
    """True when visible text carries two+ distinct roster speaker prefixes (model jam)."""
    roster = goc_npc_roster_canonical_ids(runtime_projection)
    pat = compile_goc_line_speaker_prefix_pattern(roster)
    if pat is None:
        return False
    matches = list(pat.finditer(str(line_text or "")))
    if len(matches) < 2:
        return False
    aids: set[str] = set()
    for m in matches:
        lab = str(m.group("goc_spk") or "").strip()
        aid = goc_prefix_label_to_actor_id(lab, roster)
        if aid:
            aids.add(aid)
    return len(aids) >= 2


def goc_spoken_lines_multi_speaker_row_markers(
    structured: dict[str, Any] | None,
    *,
    runtime_projection: dict[str, Any] | None = None,
) -> list[str]:
    """Diagnostics markers for structured rows that jam multiple speakers into one line."""
    if not isinstance(structured, dict):
        return []
    spoken = structured.get("spoken_lines")
    if not isinstance(spoken, list):
        return []
    for row in spoken:
        if not isinstance(row, dict):
            continue
        txt = str(row.get("text") or row.get("line") or "").strip()
        if txt and goc_spoken_line_row_suspects_multiple_speakers(txt, runtime_projection=runtime_projection):
            return ["goc_multi_speaker_merged_into_single_spoken_line_row"]
    return []
