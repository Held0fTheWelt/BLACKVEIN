"""Scripted continuation helpers.

Provides deterministic scripted continuation paths used when model-driven continuation is unavailable or not desired.
"""
from __future__ import annotations

from ._deps import *

class _ScriptedContinuationMixin:
    def _realize_npc_speak_block(
        self,
        *,
        block: dict[str, Any],
        session: StorySession,
        continuation: dict[str, Any],
        trace_id: str | None,
    ) -> dict[str, Any]:
        """Realize a single ``npc_speak`` block via LLM.

        Builds a prompt from the block's ``npc_speak_directive`` and
        ``source_facts``, calls the same adapter used for narrator path
        output, and replaces the placeholder text with the realized speech.
        """
        directive = block.get("npc_speak_directive") if isinstance(block.get("npc_speak_directive"), dict) else {}
        source_facts = block.get("source_facts") if isinstance(block.get("source_facts"), dict) else {}
        actor_id = str(directive.get("actor") or block.get("actor_id") or "").strip()
        intent = str(directive.get("intent") or "").strip()
        required_facts = directive.get("required_facts") or []
        paraphrase_policy = str(directive.get("paraphrase_policy") or "structural_paraphrase_required").strip()
        minimum_visible = str(directive.get("minimum_visible") or "").strip()
        forbidden_drift = directive.get("forbidden_drift") or []
        quote_excerpt = str(directive.get("quote_anchor_excerpt") or "").strip()
        quote_use_as = str(directive.get("quote_anchor_use_as") or "").strip()
        narrator_perception = directive.get("narrator_perception")

        target_language = (
            str(session.session_output_language or DEFAULT_SESSION_LANGUAGE).strip().lower()[:2]
            or DEFAULT_SESSION_LANGUAGE
        )

        prompt_lines = [
            f"You are realizing scripted NPC speech for character '{actor_id}' in the God of Carnage interactive experience.",
            f"Output language: {target_language}",
            f"",
            f"## Directive",
            f"- Actor: {actor_id}",
            f"- Intent: {intent}",
            f"- Required facts to include: {', '.join(str(f) for f in required_facts) if isinstance(required_facts, list) else str(required_facts)}",
            f"- Paraphrase policy: {paraphrase_policy}",
            f"- Minimum visible: {minimum_visible}",
            f"- Forbidden drift: {', '.join(str(f) for f in forbidden_drift) if isinstance(forbidden_drift, list) else str(forbidden_drift)}",
        ]
        if quote_excerpt:
            prompt_lines.extend([
                f"",
                f"## Quote anchor (short reference only, do NOT reproduce verbatim)",
                f"- Excerpt: \"{quote_excerpt}\"",
                f"- Use as: {quote_use_as}",
            ])

        step_info = source_facts.get("step") if isinstance(source_facts.get("step"), dict) else {}
        presence = source_facts.get("presence") if isinstance(source_facts.get("presence"), dict) else {}
        if step_info or presence:
            prompt_lines.extend([
                f"",
                f"## Scene context",
                f"- Step: {step_info.get('name', '')}",
                f"- Present characters: {', '.join(presence.get('named_characters', []))}",
                f"- Speaker in focus: {presence.get('speaker_in_focus', actor_id)}",
            ])

        prompt_lines.extend([
            f"",
            f"## Instructions",
            f"Produce a single spoken line (1-3 sentences) for {actor_id}.",
            f"The line must:",
            f"- Be in {target_language}",
            f"- Include all required facts naturally",
            f"- Respect the paraphrase policy ({paraphrase_policy})",
            f"- Match the character's voice and personality",
            f"- Stay within the minimum_visible description",
            f"- Avoid all forbidden drift items",
            f"",
            f"Return ONLY the spoken line text, nothing else.",
        ])

        prompt_text = "\n".join(prompt_lines)

        fallback_speech = _scripted_npc_speech_text(
            actor_ref=actor_id,
            intent=intent,
            required_facts=required_facts,
            quote_excerpt=quote_excerpt,
            language=target_language,
        )
        fallback_status = "deterministic_scripted_speech"
        speech_text = fallback_speech

        model_id, provider, adapter, api_model, timeout_seconds = self._narrator_path_output_adapter_candidate()
        if adapter is not None:
            try:
                result = adapter.generate(
                    prompt_text,
                    timeout_seconds=timeout_seconds or 20.0,
                    model_name=api_model,
                )
                generated = str(result.content or "").strip() if result.success else ""
                if generated and not generated.startswith("["):
                    speech_text = generated.strip().strip("\"“”„")
                    fallback_status = "realized"
                else:
                    fallback_status = "fallback_generation_failed"
            except Exception:
                fallback_status = "fallback_adapter_error"
        else:
            fallback_status = "fallback_no_adapter"

        frame = _scripted_narration_frame(
            actor_ref=actor_id,
            intent=intent,
            perception=narrator_perception,
            language=target_language,
        )
        quoted = _scripted_quote(speech_text, language=target_language)
        visible_text = f"{frame} {quoted}".strip()
        realized_block = dict(block)
        realized_block["block_type"] = "narrator"
        realized_block["composition_kind"] = "narrated_actor_speech"
        realized_block["text"] = visible_text
        realized_block["speaker_label"] = "Narrator"
        realized_block["actor_id"] = None
        realized_block["target_actor_id"] = _resolve_goc_runtime_actor_id(actor_id) or None
        realized_block["embedded_speech_spans"] = [
            _embedded_speech_span(
                actor_ref=actor_id,
                speech_text=speech_text,
                intent=intent,
                block=block,
            )
        ]
        realized_block["realization_status"] = fallback_status
        realized_block["requires_llm_realization"] = False
        realized_block["realization_metadata"] = {
            "provider": provider,
            "model": api_model,
            "adapter": str(getattr(adapter, "adapter_id", model_id) or "") if adapter is not None else None,
            "fallback_speech_used": speech_text == fallback_speech,
            "speech_composition": "narrator_with_embedded_actor_speech",
        }
        return realized_block

    @staticmethod
    def _merge_continuation_into_opening_state(
        graph_state: dict[str, Any],
        continuation: dict[str, Any],
    ) -> dict[str, Any]:
        """Append continuation scene blocks to the opening graph state."""
        graph_state = dict(graph_state)

        # The narrator-path opening stores blocks in
        # ``visible_output_bundle.scene_blocks``.
        bundle = graph_state.get("visible_output_bundle")
        if isinstance(bundle, dict):
            bundle = dict(bundle)
            existing_blocks = list(bundle.get("scene_blocks") or [])
            existing_blocks.extend(continuation.get("scene_blocks", []))
            bundle["scene_blocks"] = existing_blocks
            gm_narration = list(bundle.get("gm_narration") or [])
            for blk in continuation.get("scene_blocks", []):
                if isinstance(blk, dict) and str(blk.get("text") or "").strip():
                    gm_narration.append(str(blk["text"]).strip())
            bundle["gm_narration"] = gm_narration
            graph_state["visible_output_bundle"] = bundle
        else:
            cont_blocks = continuation.get("scene_blocks", [])
            graph_state["visible_output_bundle"] = {
                "scene_blocks": cont_blocks,
                "gm_narration": [
                    str(blk.get("text") or "").strip()
                    for blk in cont_blocks
                    if isinstance(blk, dict) and str(blk.get("text") or "").strip()
                ],
                "spoken_lines": [],
                "action_lines": [],
            }

        opening_step_ids = list(
            graph_state.get("opening_scene_sequence", {}).get("canonical_step_ids") or []
        ) if isinstance(graph_state.get("opening_scene_sequence"), dict) else []
        cont_step_ids = continuation.get("canonical_step_ids", [])
        if cont_step_ids:
            merged_ids = list(dict.fromkeys([*opening_step_ids, *cont_step_ids]))
            if isinstance(graph_state.get("opening_scene_sequence"), dict):
                graph_state["opening_scene_sequence"] = dict(graph_state["opening_scene_sequence"])
                graph_state["opening_scene_sequence"]["canonical_step_ids"] = merged_ids
            if isinstance(graph_state.get("narrator_path"), dict):
                graph_state["narrator_path"] = dict(graph_state["narrator_path"])
                graph_state["narrator_path"]["canonical_step_ids"] = merged_ids

        graph_state["scripted_continuation_applied"] = True
        return graph_state


__all__ = ["_ScriptedContinuationMixin"]
