"""PLAYER-SHELL-NARRATIVE-CARD-01: player-facing projection from semantic scene_blocks.

Semantic ``block_type`` values are preserved. Presentation uses ``card_style``,
``visible_lane``, optional ``player_display_text``, and ``player_shell_semantic_span``
for typewriter remapping. No GoC name literals — folding keys on ``actor_id`` /
``speaker_label`` only.
"""

from __future__ import annotations

import re
from typing import Any, Sequence

from ai_stack.goc_frozen_vocab import canonicalize_goc_actor_id
from ai_stack.visible_narrative_contract import (
    _goc_npc_action_redundant_vs_running_visible,
    _goc_visible_lane_text_fold,
    _is_name_only_actor_block,
    dedupe_goc_speaker_colon_stutter_visible,
    speaker_labels_match_accent_insensitive,
    strip_duplicate_speaker_prefix,
)


def _same_actor_lane(aid_a: str | None, aid_b: str | None) -> bool:
    a = str(aid_a or "").strip()
    b = str(aid_b or "").strip()
    if not a or not b:
        return False
    ca = canonicalize_goc_actor_id(a) or a
    cb = canonicalize_goc_actor_id(b) or b
    return ca == cb


def _card_actor_id_optional(card: dict[str, Any]) -> str | None:
    s = str(card.get("actor_id") or "").strip()
    return s or None


def _story_cards_share_voice_for_redundancy(prev: dict[str, Any], curr: dict[str, Any]) -> bool:
    """True when consecutive story cards may represent the same speaking voice (collapse guard)."""
    prev_bt = str(prev.get("block_type") or prev.get("type") or "").strip().lower()
    curr_bt = str(curr.get("block_type") or curr.get("type") or "").strip().lower()
    pa = _card_actor_id_optional(prev)
    ca = _card_actor_id_optional(curr)
    if pa and ca and _same_actor_lane(pa, ca):
        return True
    plab = str(prev.get("speaker_label") or "").strip()
    clab = str(curr.get("speaker_label") or "").strip()
    if speaker_labels_match_accent_insensitive(plab, clab):
        return True
    if prev_bt.startswith("narrator") and curr_bt.startswith("narrator") and not pa and not ca:
        return True
    return False


def _union_player_shell_semantic_spans(a: dict[str, Any], b: dict[str, Any]) -> tuple[int, int] | None:
    sa = a.get("player_shell_semantic_span")
    sb = b.get("player_shell_semantic_span")
    bounds: list[int] = []
    if isinstance(sa, tuple) and len(sa) == 2:
        bounds.extend([int(sa[0]), int(sa[1])])
    if isinstance(sb, tuple) and len(sb) == 2:
        bounds.extend([int(sb[0]), int(sb[1])])
    if len(bounds) >= 2:
        return (min(bounds), max(bounds))
    return None


def _visible_display_for_story_redundancy(card: dict[str, Any]) -> str:
    return str(card.get("player_display_text") or card.get("text") or "")


def _extract_dialogue_quote_segments(text: str) -> list[str]:
    """Extract quoted speech segments from display text (Unicode/ASCII/French quotes)."""
    s = str(text or "")
    out: list[str] = []
    for pattern in (
        r"„([^“]{6,})“",
        r"\"([^\"]{6,})\"",
        r"«([^»]{6,})»",
    ):
        out.extend([m.strip() for m in re.findall(pattern, s) if str(m).strip()])
    return out


def _actor_line_contains_new_quote_value(*, narrator_text: str, actor_line_text: str) -> bool:
    """True when actor_line has quoted speech not already covered by narrator."""
    quotes = _extract_dialogue_quote_segments(actor_line_text)
    if not quotes:
        return False
    for q in quotes:
        if not _goc_npc_action_redundant_vs_running_visible(q, narrator_text):
            return True
    return False


def _allow_narrator_adjacent_tail_redundancy(
    prev: dict[str, Any],
    curr: dict[str, Any],
    *,
    allow_actor_line: bool,
) -> bool:
    """Narrator-adjacent redundancy gate (presentation-only, direct neighbors only)."""
    if str(prev.get("visible_lane") or "") != "story" or str(curr.get("visible_lane") or "") != "story":
        return False
    prev_bt = str(prev.get("block_type") or prev.get("type") or "").strip().lower()
    curr_bt = str(curr.get("block_type") or curr.get("type") or "").strip().lower()
    if not prev_bt.startswith("narrator"):
        return False
    if curr_bt not in {"actor_action", "actor_line"}:
        return False
    if curr_bt == "actor_line" and not allow_actor_line:
        return False
    t_prev = _visible_display_for_story_redundancy(prev)
    t_curr = _visible_display_for_story_redundancy(curr)
    if not _goc_npc_action_redundant_vs_running_visible(t_curr, t_prev):
        return False
    if curr_bt == "actor_line" and _actor_line_contains_new_quote_value(
        narrator_text=t_prev,
        actor_line_text=t_curr,
    ):
        return False
    return True


def _is_story_lane(card: dict[str, Any]) -> bool:
    return str(card.get("visible_lane") or "").strip().lower() == "story"


def _collapse_consecutive_redundant_story_cards(
    cards: list[dict[str, Any]],
    *,
    allow_narrator_adjacent_actor_line_dedupe: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Collapse direct redundant story cards (presentation-only, v1 guarded rules)."""
    collapse_diag: dict[str, Any] = {
        # New contract keys (DUPLICATE-STORY-CARD-DEDUP-01)
        "consecutive_story_card_removed": 0,
        "consecutive_story_card_span_extended": 0,
        "narrator_adjacent_redundant_actor_action_removed": 0,
        "same_actor_redundant_story_card_removed": 0,
        "player_lane_collapse_skipped": 0,
        # Backward compatibility keys (kept for existing dashboards/tests)
        "consecutive_redundant_story_card_removed": 0,
        "consecutive_story_card_replaced_by_expansion": 0,
        "narrator_adjacent_redundant_story_card_removed": 0,
        "narrator_adjacent_redundant_actor_line_removed": 0,
    }
    kept: list[dict[str, Any]] = []
    for curr in cards:
        if not kept:
            kept.append(curr)
            continue
        prev = kept[-1]
        prev_lane = str(prev.get("visible_lane") or "").strip().lower()
        curr_lane = str(curr.get("visible_lane") or "").strip().lower()
        if prev_lane == "player" or curr_lane == "player":
            collapse_diag["player_lane_collapse_skipped"] += 1
            kept.append(curr)
            continue
        if not (_is_story_lane(prev) and _is_story_lane(curr)):
            kept.append(curr)
            continue

        prev_bt = str(prev.get("block_type") or prev.get("type") or "").strip().lower()
        curr_bt = str(curr.get("block_type") or curr.get("type") or "").strip().lower()
        prev_actor = _card_actor_id_optional(prev)
        curr_actor = _card_actor_id_optional(curr)
        t_prev = _visible_display_for_story_redundancy(prev)
        t_curr = _visible_display_for_story_redundancy(curr)
        remove_curr = False

        # Rule A: same actor + redundant/near-redundant direct successor.
        same_actor = bool(prev_actor and curr_actor and _same_actor_lane(prev_actor, curr_actor))
        if same_actor and curr_bt in {"actor_action", "actor_line"}:
            redundant = _goc_npc_action_redundant_vs_running_visible(t_curr, t_prev)
            if redundant:
                # Never drop real new quoted speech unless quote itself is covered.
                if curr_bt == "actor_line":
                    if allow_narrator_adjacent_actor_line_dedupe and not _actor_line_contains_new_quote_value(
                        narrator_text=t_prev,
                        actor_line_text=t_curr,
                    ):
                        remove_curr = True
                    else:
                        remove_curr = False
                else:
                    remove_curr = True
                if remove_curr:
                    collapse_diag["same_actor_redundant_story_card_removed"] += 1
                    if curr_bt == "actor_line":
                        collapse_diag["narrator_adjacent_redundant_actor_line_removed"] += 1

        # Rule B: narrator -> actor_action (v1) and optional narrator -> actor_line (guarded).
        if (
            not remove_curr
            and prev_bt.startswith("narrator")
            and curr_bt in {"actor_action", "actor_line"}
            and _goc_npc_action_redundant_vs_running_visible(t_curr, t_prev)
        ):
            if curr_bt == "actor_line":
                if allow_narrator_adjacent_actor_line_dedupe and not _actor_line_contains_new_quote_value(
                    narrator_text=t_prev,
                    actor_line_text=t_curr,
                ):
                    remove_curr = True
                    collapse_diag["narrator_adjacent_redundant_actor_line_removed"] += 1
            else:
                remove_curr = True
                collapse_diag["narrator_adjacent_redundant_actor_action_removed"] += 1
            if remove_curr:
                collapse_diag["narrator_adjacent_redundant_story_card_removed"] += 1

        if remove_curr:
            merged = dict(prev)
            us = _union_player_shell_semantic_spans(prev, curr)
            if us is not None:
                merged["player_shell_semantic_span"] = us
                collapse_diag["consecutive_story_card_span_extended"] += 1
            kept[-1] = merged
            collapse_diag["consecutive_story_card_removed"] += 1
            collapse_diag["consecutive_redundant_story_card_removed"] += 1
            continue

        kept.append(curr)
    return kept, collapse_diag


def _combine_npc_story_display(
    speech: str,
    action: str,
    *,
    speaker_label: str,
    actor_id: str | None,
    action_before_speech: bool,
) -> str:
    s = str(speech or "").strip()
    a = str(action or "").strip()
    a = strip_duplicate_speaker_prefix(a, speaker_label=speaker_label, actor_id=actor_id).strip()
    s = strip_duplicate_speaker_prefix(s, speaker_label=speaker_label, actor_id=actor_id).strip()
    if not a:
        return dedupe_goc_speaker_colon_stutter_visible(
            s, speaker_label=speaker_label or None, actor_id=actor_id
        )
    if not s:
        return dedupe_goc_speaker_colon_stutter_visible(
            a, speaker_label=speaker_label or None, actor_id=actor_id
        )
    sf = _goc_visible_lane_text_fold(s)
    af = _goc_visible_lane_text_fold(a)
    if af and len(af) >= 12 and af in sf:
        return dedupe_goc_speaker_colon_stutter_visible(
            s, speaker_label=speaker_label or None, actor_id=actor_id
        )
    if sf and len(sf) >= 12 and sf in af:
        return dedupe_goc_speaker_colon_stutter_visible(
            a, speaker_label=speaker_label or None, actor_id=actor_id
        )
    if action_before_speech:
        body = f"{a.rstrip('.')}. {s}".strip()
    else:
        body = f"{s} {a}".strip()
    return dedupe_goc_speaker_colon_stutter_visible(
        body, speaker_label=speaker_label or None, actor_id=actor_id
    )


def build_player_facing_narrative_cards(
    semantic_blocks: Sequence[dict[str, Any]],
    *,
    policy: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (player_shell_blocks, diagnostics).

    Each output dict is a shallow copy of a semantic block plus presentation fields.
    Adjacent ``actor_action`` rows with the same ``actor_id`` as a preceding
    ``actor_line`` are folded into that line's card (one DOM node); folded sources
    are listed under ``player_shell_folded_semantic_indices`` for debugging only.

    After the main pass, consecutive **story**-lane cards from the same voice may be
    merged or dropped when display text is redundant (see
    ``consecutive_redundant_story_card_removed``); player-lane cards are unchanged.

    Diagnostics include ``near_duplicate_actor_action_removed`` for drops detected via
    near-duplicate / token-overlap (not strict folded substring) against prior story text.
    """
    policy = policy if isinstance(policy, dict) else {}
    action_before_speech = bool(policy.get("npc_card_action_before_speech", True))
    allow_narrator_adjacent_actor_line_dedupe = bool(
        policy.get("narrator_adjacent_actor_line_dedupe", False)
    )

    diag: dict[str, Any] = {
        "player_card_count": 0,
        "semantic_block_count": len(semantic_blocks),
        "actor_action_folded_into_actor_card": 0,
        "subsumed_actor_action_removed": 0,
        "near_duplicate_actor_action_removed": 0,
        "name_only_actor_card_removed": 0,
        "narrator_card_preserved": 0,
    }
    out: list[dict[str, Any]] = []
    sem = [dict(b) for b in semantic_blocks if isinstance(b, dict)]
    si = 0
    while si < len(sem):
        raw = sem[si]
        b = dict(raw)
        bt = str(b.get("block_type") or b.get("type") or "").strip().lower()
        lab = str(b.get("speaker_label") or "").strip()
        aid = str(b.get("actor_id") or "").strip() or None

        if bt in {"player_input", "player_input_outcome"}:
            nb = dict(b)
            nb["card_style"] = "player_lane"
            nb["visible_lane"] = "player"
            nb["player_display_text"] = str(b.get("text") or "")
            nb["player_shell_semantic_span"] = (si, si)
            out.append(nb)
            si += 1
            continue

        if bt.startswith("narrator"):
            nb = dict(b)
            nb["card_style"] = "narrative_story"
            nb["visible_lane"] = "story"
            nb["player_display_text"] = dedupe_goc_speaker_colon_stutter_visible(
                str(b.get("text") or ""), speaker_label=lab or None, actor_id=aid
            )
            nb["player_shell_semantic_span"] = (si, si)
            out.append(nb)
            diag["narrator_card_preserved"] += 1
            si += 1
            continue

        if bt == "actor_line":
            speech = str(b.get("text") or "")
            j = si + 1
            actions: list[str] = []
            folded_idx: list[int] = []
            while j < len(sem):
                nxt = sem[j]
                nbt = str(nxt.get("block_type") or nxt.get("type") or "").strip().lower()
                if nbt != "actor_action":
                    break
                if not _same_actor_lane(b.get("actor_id"), nxt.get("actor_id")):
                    break
                act_raw = str(nxt.get("text") or "").strip()
                act = strip_duplicate_speaker_prefix(
                    act_raw, speaker_label=lab, actor_id=aid
                ).strip()
                act = dedupe_goc_speaker_colon_stutter_visible(
                    act, speaker_label=lab or None, actor_id=aid
                )
                running = speech
                for act0 in actions:
                    running = _combine_npc_story_display(
                        running,
                        act0,
                        speaker_label=lab,
                        actor_id=aid,
                        action_before_speech=action_before_speech,
                    )
                sf = _goc_visible_lane_text_fold(running)
                af = _goc_visible_lane_text_fold(act)
                substring_subsumed = bool(af and len(af) >= 12 and af in sf)
                redundant = bool(
                    len(af) >= 12
                    and _goc_npc_action_redundant_vs_running_visible(act, running)
                )
                if redundant:
                    diag["subsumed_actor_action_removed"] += 1
                    if not substring_subsumed:
                        diag["near_duplicate_actor_action_removed"] += 1
                    folded_idx.append(j)
                    j += 1
                    continue
                actions.append(act_raw)
                folded_idx.append(j)
                diag["actor_action_folded_into_actor_card"] += 1
                j += 1
            merged_speech = speech
            for act in actions:
                merged_speech = _combine_npc_story_display(
                    merged_speech,
                    act,
                    speaker_label=lab,
                    actor_id=aid,
                    action_before_speech=action_before_speech,
                )
            merged_speech = dedupe_goc_speaker_colon_stutter_visible(
                merged_speech, speaker_label=lab or None, actor_id=aid
            )
            nb = dict(b)
            nb["card_style"] = "npc_story"
            nb["visible_lane"] = "story"
            nb["player_display_text"] = merged_speech
            nb["player_shell_semantic_span"] = (si, j - 1)
            if folded_idx:
                nb["player_shell_folded_semantic_indices"] = list(folded_idx)
            disp = str(nb.get("player_display_text") or "").strip()
            if _is_name_only_actor_block(
                disp, speaker_label=lab, actor_id=aid, block_type="actor_line"
            ):
                diag["name_only_actor_card_removed"] += 1
                si = j
                continue
            out.append(nb)
            si = j
            continue

        if bt == "actor_action":
            nb = dict(b)
            nb["card_style"] = "npc_story"
            nb["visible_lane"] = "story"
            disp = strip_duplicate_speaker_prefix(
                str(b.get("text") or ""),
                speaker_label=lab,
                actor_id=aid,
            ).strip()
            disp = dedupe_goc_speaker_colon_stutter_visible(
                disp, speaker_label=lab or None, actor_id=aid
            )
            nb["player_display_text"] = disp
            nb["player_shell_semantic_span"] = (si, si)
            if _is_name_only_actor_block(
                disp, speaker_label=lab, actor_id=aid, block_type="actor_action"
            ):
                diag["name_only_actor_card_removed"] += 1
                si += 1
                continue
            af = _goc_visible_lane_text_fold(disp)
            subsumed_after_gap = False
            idx = len(out) - 1
            while idx >= 0:
                prev = out[idx]
                pbt = str(prev.get("block_type") or prev.get("type") or "").strip().lower()
                if pbt in {"player_input", "player_input_outcome"}:
                    idx -= 1
                    continue
                if pbt == "actor_line" and _same_actor_lane(aid, prev.get("actor_id")):
                    prev_disp = str(prev.get("player_display_text") or prev.get("text") or "")
                    sf = _goc_visible_lane_text_fold(prev_disp)
                    substring_subsumed = bool(af and len(af) >= 12 and sf and af in sf)
                    redundant = bool(
                        len(af) >= 12
                        and _goc_npc_action_redundant_vs_running_visible(disp, prev_disp)
                    )
                    if redundant:
                        diag["subsumed_actor_action_removed"] += 1
                        if not substring_subsumed:
                            diag["near_duplicate_actor_action_removed"] += 1
                        subsumed_after_gap = True
                    break
                break
            if subsumed_after_gap:
                si += 1
                continue
            out.append(nb)
            si += 1
            continue

        nb = dict(b)
        nb.setdefault("player_display_text", str(b.get("text") or ""))
        nb.setdefault("visible_lane", "story")
        nb.setdefault("card_style", "narrative_story")
        nb["player_shell_semantic_span"] = (si, si)
        out.append(nb)
        si += 1

    out, collapse_diag = _collapse_consecutive_redundant_story_cards(
        out,
        allow_narrator_adjacent_actor_line_dedupe=allow_narrator_adjacent_actor_line_dedupe,
    )
    diag.update(collapse_diag)
    diag["player_card_count"] = len(out)
    return out, diag


def player_shell_typewriter_start_index(
    player_cards: Sequence[dict[str, Any]],
    *,
    prior_semantic_index: int,
    used_cumulative_story_blocks: bool,
) -> int:
    """Map semantic ``prior`` index (cumulative) to first player-shell card to animate."""
    cards = [c for c in player_cards if isinstance(c, dict)]
    if not cards:
        return 0
    if not used_cumulative_story_blocks:
        return 0
    for i, card in enumerate(cards):
        span = card.get("player_shell_semantic_span")
        if not isinstance(span, tuple) or len(span) != 2:
            continue
        lo, hi = int(span[0]), int(span[1])
        if lo <= prior_semantic_index <= hi:
            return i
    return min(max(prior_semantic_index, 0), len(cards) - 1)
