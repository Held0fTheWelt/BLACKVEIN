"""PLAYER-SHELL-NARRATIVE-CARD-01: player-facing projection from semantic scene_blocks.

Semantic ``block_type`` values are preserved. Presentation uses ``card_style``,
``visible_lane``, optional ``player_display_text``, and ``player_shell_semantic_span``
for typewriter remapping. No GoC name literals — folding keys on ``actor_id`` /
``speaker_label`` only.
"""

from __future__ import annotations

from typing import Any, Sequence

from ai_stack.goc_frozen_vocab import canonicalize_goc_actor_id
from ai_stack.visible_narrative_contract import (
    _goc_npc_action_redundant_vs_running_visible,
    _goc_visible_lane_text_fold,
    _is_name_only_actor_block,
    dedupe_goc_speaker_colon_stutter_visible,
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

    Diagnostics include ``near_duplicate_actor_action_removed`` for drops detected via
    near-duplicate / token-overlap (not strict folded substring) against prior story text.
    """
    policy = policy if isinstance(policy, dict) else {}
    action_before_speech = bool(policy.get("npc_card_action_before_speech", True))

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
