from __future__ import annotations

from ._deps import *

class _NarratorOutputPromptsMixin:
    @staticmethod
    def _narrator_path_output_prompt(
        *,
        source_blocks: list[dict[str, Any]],
        narrator_path: dict[str, Any],
        source_language: str,
        target_language: str,
    ) -> str:
        payload = {
            "source_language": source_language,
            "session_output_language": target_language,
            "source_input_mode": narrator_path.get("source_input_mode"),
            "path_id": narrator_path.get("path_id"),
            "canonical_step_ids": narrator_path.get("canonical_step_ids"),
            "narrative_source_frames": narrator_path.get("narrative_source_frames")
            if isinstance(narrator_path.get("narrative_source_frames"), list)
            else [],
            "scene_blocks": [
                {
                    "id": block.get("id"),
                    "block_type": block.get("block_type"),
                    "canonical_step_id": block.get("canonical_step_id"),
                    "canonical_step_sequence": block.get("canonical_step_sequence"),
                    "canonical_mandatory_beat_id": block.get("canonical_mandatory_beat_id"),
                    "visual_emphasis": block.get("visual_emphasis")
                    if isinstance(block.get("visual_emphasis"), dict)
                    else {},
                    "source_refs": block.get("source_refs") if isinstance(block.get("source_refs"), list) else [],
                    "source_facts": block.get("source_facts") if isinstance(block.get("source_facts"), dict) else {},
                }
                for block in source_blocks
            ],
        }
        return (
            "You are the World of Shadows narrator synthesis module.\n"
            "Input is English semantic content authority, not player-visible prose. "
            "Use the canonical steps, source facts, locations, objects, sensory tags, "
            "presence, and mandatory beat coverage to write fresh player-visible narration in "
            f"session_output_language={target_language}.\n"
            "Preserve block count, block ids, order, canonical beat coverage, and narrative distance. "
            "Each output block is narrator perception, one to three natural sentences. "
            "When source_facts.w5_projection is present, treat its typed who/where/what/how/why summaries as the "
            "primary actor-situation authority for this turn. Honor where_summary.location_changed, the actor's "
            "current_location, what_summary.current_action / interaction_type, how_summary (tone/manner/intensity/"
            "pace/physicality/method/style — first-class, never folded into what), and why_summary (inferred motive/"
            "goal/pressure/dramatic_function, never spoken as fact). Use transition_from_previous only as a fallback "
            "when w5_projection is absent. "
            "If source_facts.transition_from_previous.location_changed or scene_changed is true, the block must "
            "narratively orient the shift before describing local detail. Use the current location, prior handoff, "
            "and module setting from source_facts; do not jump directly from one place into room inventory. "
            "If source_facts.transition_from_previous.directed_transition.kind is hard_cut, treat it as a hard "
            "authored scene break: briefly break out of smooth narration with a cut/scene-change cue in the target "
            "language, then establish the exact current place and tableau. Do not invent a travel bridge, do not "
            "translate direction atoms literally, and do not hardcode any specific wording. "
            "Do not copy the coverage_cues as finished prose; treat them as facts to synthesize. "
            "Avoid list cadence, template phrasing, recap language, and visible seams between source fields. "
            "Do not add dialogue, accusations, explanations, role labels, or new facts. "
            "Do not summarize multiple blocks into one block. Keep the opening playable: concrete, situated, "
            "and cinematic enough to feel generated from the room/world rather than pasted from notes.\n"
            "Return valid JSON only, with this shape: "
            '{"scene_blocks":[{"id":"...","text":"..."}]}.\n\n'
            f"Narrator synthesis input:\n{json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
        )

    @staticmethod
    def _souffleuse_output_prompt(
        *,
        source_blocks: list[dict[str, Any]],
        source_language: str,
        target_language: str,
    ) -> str:
        payload = {
            "source_language": source_language,
            "session_output_language": target_language,
            "scene_blocks": [
                {
                    "id": block.get("id"),
                    "target_actor_id": block.get("target_actor_id"),
                    "canonical_step_id": block.get("canonical_step_id"),
                    "souffleuse_cue_id": block.get("souffleuse_cue_id"),
                    "voice_mode": block.get("voice_mode"),
                    "guidance_kinds": block.get("guidance_kinds")
                    if isinstance(block.get("guidance_kinds"), list)
                    else [],
                    "source_facts": block.get("source_facts") if isinstance(block.get("source_facts"), dict) else {},
                }
                for block in source_blocks
            ],
        }
        return (
            "You are the World of Shadows Souffleuse output module.\n"
            "Input is English internal player-guidance facts, not player-visible prose. Produce a short, natural "
            f"player-visible hint in session_output_language={target_language}.\n"
            "Preserve block count, block ids, actor-specific stance, and cue boundaries. "
            "Do not name the guidance lane, do not prefix the text with 'Souffleuse:', "
            "and do not write 'inner voice'. Use familiar second person when the target language "
            "distinguishes formality. Write in the playable character's own inward register: the way "
            "that character might briefly speak to themselves while taking in the situation. If "
            "guidance_kinds includes situation_orientation or character_stance, the cue may establish "
            "who the player character is, their profession and partner if source_facts provides them, how the "
            "character stands toward what has happened, and why this meeting matters to them, using only source_facts. "
            "Follow source_facts.cue_surface_policy when present. Keep this compact: usually two short sentences, "
            "never a biography. Use source_facts.character_voice "
            "to match register and rhythm. Later-development refs may inform baseline stance only; do not reveal, "
            "quote, or anticipate future beats. Do not "
            "use outside labels such as role, tension, pressure, player, or controls in the visible text. "
            "Do not add player actions, exact line commands, NPC speech, hidden intent, or new facts. "
            "If guidance_kinds includes pre_action_inward_footing, treat the cue as the character's baseline "
            "inner footing before action or statement dispute. Use character_situational_stance, public identity, "
            "baseline attitude, voice, profession, partner, current location, and incident location; do not infer "
            "or foreground statement wording pressure unless the source block explicitly provides it for that cue. "
            "Do not use a fixed character-sheet lead such as 'You are X, profession, with Y' unless the source "
            "cannot otherwise be made clear. Weave identity, profession, and partner into the character's present "
            "inward footing instead of listing them. Do not mirror or translate source-fact wording literally.\n"
            "Treat any *_atoms, ids, or enum-like values as semantic hints, not as wording to translate. "
            "Do not copy atom names into visible text.\n"
            "Return valid JSON only, with this shape: "
            '{"scene_blocks":[{"id":"...","text":"..."}]}.\n\n'
            f"Souffleuse output-module input:\n{json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
        )

    @staticmethod
    def _parse_narrator_path_output_json(raw: str) -> dict[str, Any]:
        text = str(raw or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text).strip()
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(text[start : end + 1])
                    return parsed if isinstance(parsed, dict) else {}
                except json.JSONDecodeError:
                    return {}
        return {}

    @staticmethod
    def _fallback_narrator_path_output_blocks(
        *,
        source_blocks: list[dict[str, Any]],
        source_language: str,
        target_language: str,
        status: str,
    ) -> list[dict[str, Any]]:
        visible_language = target_language if target_language == source_language else source_language
        realized: list[dict[str, Any]] = []
        for block in source_blocks:
            nb = dict(block)
            nb.setdefault("source_language", source_language)
            nb["session_output_language"] = target_language
            nb["visible_output_language"] = visible_language
            nb["output_realization_status"] = status
            nb["output_realization_source"] = "canonical_content_renderer_fallback"
            if target_language != source_language:
                nb["requires_output_realization"] = True
                nb["output_language_mismatch"] = True
            realized.append(nb)
        return realized

    @staticmethod
    def _fallback_souffleuse_output_blocks(
        *,
        source_blocks: list[dict[str, Any]],
        source_language: str,
        target_language: str,
        status: str,
    ) -> list[dict[str, Any]]:
        visible_language = target_language if target_language == source_language else source_language
        realized: list[dict[str, Any]] = []
        for block in source_blocks:
            nb = dict(block)
            visible_text = _compose_souffleuse_visible_source_text(nb).strip()
            if visible_text and visible_text != str(nb.get("text") or "").strip():
                nb["source_text"] = nb.get("text")
                nb["text"] = visible_text
                nb["player_display_text"] = visible_text
            nb["source_language"] = source_language
            nb["session_output_language"] = target_language
            nb["visible_output_language"] = visible_language
            nb["requires_output_realization"] = target_language != source_language
            nb["output_realization_status"] = status
            nb["output_realization_source"] = "souffleuse_source_projection_fallback"
            if target_language != source_language:
                nb["output_language_mismatch"] = True
            realized.append(nb)
        return realized


__all__ = ["_NarratorOutputPromptsMixin"]
