from __future__ import annotations

from ._deps import *

def _player_input_scene_blocks_for_story_window(
    *,
    session_id: str,
    turn_number: Any,
    raw_input: str,
    session_output_language: str,
    human_actor_id: str | None = None,
    interpreted_input: dict[str, Any] | None = None,
    module_id: str | None = None,
) -> list[dict[str, Any]]:
    """MVP5 cumulative transcript: visible player line for the story shell.

    When ``human_actor_id`` is bound (canonical solo path), **always** emit **two**
    cards: ``player_input`` (verbatim typing, italic shell lane) then
    ``player_input_outcome`` (diegetic attributed line for the selected human actor).

    Imperative greetings to a named actor still use the scripted polite
    outcome line for the second card; all other inputs use ``_goc_player_attributed_visible_text``.

    Without a human actor id (legacy / non-solo), a single ``player_input`` block
    with speaker *Du* / *You* is emitted.

    Player text is not part of runtime ``spoken_lines`` (human lane is filtered from
    scene envelope). Story-window entries must still carry ``scene_blocks`` so backend
    ``_cumulative_scene_blocks_from_story_window`` can replay the full transcript.
    """
    text = str(raw_input or "").strip()
    if not text:
        return []
    lang = str(session_output_language or DEFAULT_SESSION_LANGUAGE).strip().lower()
    exp_lang = lang[:2] or DEFAULT_SESSION_LANGUAGE
    mid = (module_id or GOD_OF_CARNAGE_MODULE_ID).strip()
    root = _goc_content_modules_root()
    turn_token = str(turn_number).strip() if turn_number is not None else "0"
    hid = str(human_actor_id or "").strip()
    if hid:
        canon = str(canonicalize_goc_actor_id(hid) or hid).strip()
        name = _goc_shell_actor_firstname(canon)
        interp = interpreted_input if isinstance(interpreted_input, dict) else {}
        # Prefer fine-grained player_input_kind (from rules) over coarse input_kind.
        pik_fine = str(interp.get("player_input_kind") or "").strip().lower()
        ik = pik_fine or str(interp.get("input_kind") or interp.get("kind") or "speech").strip().lower()
        # intent_only / reaction are verbal — keep as speech. ambiguous must NOT become speech.
        if ik in ("intent_only", "reaction"):
            ik = "speech"
        verbatim_line = text
        outcome_line: str
        pair = _goc_greeting_imperative_visible_pair(raw=text, player_shell_name=name, lang=exp_lang)
        if pair and ik in {"speech", "action", "social_nonverbal_action"}:
            verbatim_line, outcome_line = pair[0], pair[1]
        else:
            _, outcome_line = _goc_player_attributed_visible_text(
                raw_input=text,
                human_actor_id=canon,
                session_output_language=exp_lang,
                interpreted_input=interpreted_input,
            )
        delivery = {
            "mode": "typewriter",
            "characters_per_second": 44,
            "pause_before_ms": 0,
            "pause_after_ms": 120,
            "skippable": True,
        }
        pik_lane = str(interp.get("player_input_kind") or interp.get("kind") or "speech").strip().lower()
        render_hints = {"player_input_kind": pik_lane}
        player_capability = {
            "action": PLAYER_ACTION_REQUEST,
            "movement_action": PLAYER_MOVEMENT_REQUEST,
            "object_interaction": PLAYER_OBJECT_INTERACTION_REQUEST,
            "perception": PLAYER_PERCEPTION_REQUEST,
            "perception_action": PLAYER_PERCEPTION_REQUEST,
            "mixed": PLAYER_ACTION_REQUEST,
            "question": PLAYER_SPEECH_REQUEST,
            "speech": PLAYER_SPEECH_REQUEST,
        }.get(pik_lane, "player.input")
        out_blocks: list[dict[str, Any]] = []
        for suffix, line, bt in (
            ("", verbatim_line, "player_input"),
            ("-outcome", outcome_line, "player_input_outcome"),
        ):
            cleaned, _partial = sanitize_visible_block_text(
                line,
                block_type=bt,
                speaker_label=name,
                actor_id=canon,
                expected_language=exp_lang,
            )
            if cleaned:
                out_blocks.append(
                    {
                        "id": f"{session_id}-turn-{turn_token}-player-input{suffix}",
                        "block_type": bt,
                        "speaker_label": name,
                        "actor_id": canon,
                        "target_actor_id": None,
                        "text": cleaned,
                        "delivery": delivery,
                        "source": "player_input",
                        "render_hints": render_hints,
                        "origin_aspect": ASPECT_INPUT,
                        "origin_beat_id": None,
                        "origin_capability": player_capability,
                        "authority_owner": "player",
                        "expected_owner": "player",
                        "actual_owner": "player",
                        "canonical_turn_id": f"{session_id}:turn:{turn_token}",
                        "evidence_role": EVIDENCE_SUPPORTING,
                    }
                )
        if out_blocks:
            return out_blocks
    speaker_label = resolve_string(mid, "player_shell.second_person", exp_lang, content_modules_root=root)
    return [
        {
            "id": f"{session_id}-turn-{turn_token}-player-input",
            "block_type": "player_input",
            "speaker_label": speaker_label,
            "actor_id": None,
            "target_actor_id": None,
            "text": text,
            "delivery": {
                "mode": "typewriter",
                "characters_per_second": 44,
                "pause_before_ms": 0,
                "pause_after_ms": 120,
                "skippable": True,
            },
            "source": "player_commit",
            "origin_aspect": ASPECT_INPUT,
            "origin_beat_id": None,
            "origin_capability": "player.input",
            "authority_owner": "player",
            "expected_owner": "player",
            "actual_owner": "player",
            "canonical_turn_id": f"{session_id}:turn:{turn_token}",
            "evidence_role": EVIDENCE_SUPPORTING,
        }
    ]

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
