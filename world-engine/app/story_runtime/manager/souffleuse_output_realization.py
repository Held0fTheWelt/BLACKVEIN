from __future__ import annotations

from ._deps import *

class _SouffleuseOutputRealizationMixin:
    def _attach_souffleuse_shadow_judge_meta(
        self,
        realized: list[dict[str, Any]],
        meta: dict[str, Any],
    ) -> dict[str, Any]:
        """Non-blocking shadow gate (Sub-Plan 4 PR-4D) — diagnostics only."""
        from ai_stack.souffleuse_production_judge import evaluate_souffleuse_visible_text_shadow

        judgments: list[dict[str, Any]] = []
        for block in realized:
            source_facts = block.get("source_facts") if isinstance(block.get("source_facts"), dict) else {}
            judgments.append(
                evaluate_souffleuse_visible_text_shadow(
                    str(block.get("text") or ""),
                    character_voice_profile=source_facts.get("character_voice_profile"),
                )
            )
        out = dict(meta)
        out["souffleuse_production_judge_shadow"] = judgments
        return out

    def _realize_souffleuse_output(
        self,
        *,
        source_blocks: list[dict[str, Any]],
        session: StorySession,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        source_language = SOUFFLEUSE_INTERNAL_LANGUAGE
        target_language = str(session.session_output_language or source_language).strip().lower()[:2] or source_language
        if target_language == source_language or not source_blocks:
            realized: list[dict[str, Any]] = []
            for block in source_blocks:
                nb = dict(block)
                visible_text = _compose_souffleuse_visible_source_text(nb).strip()
                if visible_text and visible_text != str(nb.get("text") or "").strip():
                    nb["source_text"] = nb.get("text")
                    nb["text"] = visible_text
                    nb["player_display_text"] = visible_text
                    nb["output_realization_source"] = "souffleuse_source_projection"
                nb["source_language"] = source_language
                nb["session_output_language"] = target_language
                nb["visible_output_language"] = target_language
                nb["requires_output_realization"] = False
                realized.append(nb)
            meta = {
                "contract": "souffleuse_output_realization.v1",
                "status": "not_required",
                "source_language": source_language,
                "session_output_language": target_language,
                "adapter": SOUFFLEUSE_ADAPTER,
                "adapter_invocation_mode": SOUFFLEUSE_INVOCATION_MODE,
                "usage_source": "prompt_store_internal_english_visible_projection",
                "block_count": len(source_blocks),
            }
            return realized, self._attach_souffleuse_shadow_judge_meta(realized, meta)

        candidates = self._narrator_path_output_adapter_candidates()
        if not candidates:
            status = "fallback_no_output_model"
            realized = self._fallback_souffleuse_output_blocks(
                source_blocks=source_blocks,
                source_language=source_language,
                target_language=target_language,
                status=status,
            )
            return realized, {
                "contract": "souffleuse_output_realization.v1",
                "status": status,
                "source_language": source_language,
                "session_output_language": target_language,
                "visible_output_language": target_language
                if target_language == source_language
                else source_language,
                "adapter": SOUFFLEUSE_ADAPTER,
                "adapter_invocation_mode": SOUFFLEUSE_INVOCATION_MODE,
                "usage_source": "prompt_store_internal_english_visible_projection",
                "fallback_reason": "no_non_mock_output_model",
                "translation_required": target_language != source_language,
                "output_language_mismatch": target_language != source_language,
                "block_count": len(realized),
            }
        prompt = self._souffleuse_output_prompt(
            source_blocks=source_blocks,
            source_language=source_language,
            target_language=target_language,
        )
        attempts: list[dict[str, Any]] = []
        for model_id, provider, adapter, api_model, timeout_seconds in candidates:
            attempt: dict[str, Any] = {
                "provider": provider,
                "model_id": model_id,
                "api_model": api_model,
                "adapter": str(getattr(adapter, "adapter_name", "") or provider),
                "timeout_seconds": timeout_seconds or 20.0,
            }
            try:
                result = adapter.generate(
                    prompt,
                    timeout_seconds=timeout_seconds or 20.0,
                    model_name=api_model,
                )
            except Exception as exc:
                attempt["success"] = False
                attempt["error"] = str(exc) or type(exc).__name__
                attempts.append(attempt)
                continue
            result_metadata = result.metadata if isinstance(result.metadata, dict) else {}
            if not result.success:
                attempt["success"] = False
                attempt["error"] = str(result_metadata.get("error") or "souffleuse_output_module_failed")
                attempts.append(attempt)
                continue
            parsed = self._parse_narrator_path_output_json(result.content)
            rows = parsed.get("scene_blocks") if isinstance(parsed.get("scene_blocks"), list) else []
            by_id = {
                str(row.get("id") or "").strip(): row
                for row in rows
                if isinstance(row, dict) and str(row.get("id") or "").strip()
            }
            realized = []
            missing_ids: list[str] = []
            for block in source_blocks:
                block_id = str(block.get("id") or "").strip()
                out_row = by_id.get(block_id)
                text = str(out_row.get("text") or "").strip() if isinstance(out_row, dict) else ""
                if not text:
                    missing_ids.append(block_id or f"index:{len(realized)}")
                    continue
                visible_text, _partial = sanitize_visible_block_text(
                    text,
                    block_type=SOUFFLEUSE_BLOCK_TYPE,
                    speaker_label=str(block.get("speaker_label") or "Souffleuse"),
                    actor_id=None,
                    expected_language=target_language,
                )
                text = visible_text.strip() or text
                nb = dict(block)
                nb["text"] = text
                nb["player_display_text"] = text
                nb["source_language"] = source_language
                nb["session_output_language"] = target_language
                nb["visible_output_language"] = target_language
                nb["requires_output_realization"] = False
                nb["source_before_output_module"] = nb.get("source")
                nb["output_realization_source"] = "souffleuse_output_module"
                realized.append(nb)
            if missing_ids or len(realized) != len(source_blocks):
                attempt["success"] = False
                attempt["error"] = "souffleuse_output_module_incomplete_blocks"
                attempt["missing_block_ids"] = missing_ids
                attempts.append(attempt)
                continue
            meta = {
                "contract": "souffleuse_output_realization.v1",
                "status": "realized",
                "source_language": source_language,
                "session_output_language": target_language,
                "adapter": str(result_metadata.get("adapter") or getattr(adapter, "adapter_name", "") or provider),
                "adapter_invocation_mode": "souffleuse_output_module",
                "provider": provider,
                "model_id": model_id,
                "api_model": api_model,
                "usage_source": "output_module",
                "block_count": len(realized),
                "attempt_count": len(attempts) + 1,
                "failed_attempts": attempts,
            }
            return realized, self._attach_souffleuse_shadow_judge_meta(realized, meta)

        status = "fallback_output_module_failed"
        realized = self._fallback_souffleuse_output_blocks(
            source_blocks=source_blocks,
            source_language=source_language,
            target_language=target_language,
            status=status,
        )
        last_error = (
            str(attempts[-1].get("error") or "").strip()
            if attempts
            else "souffleuse_output_module_failed"
        )
        return realized, {
            "contract": "souffleuse_output_realization.v1",
            "status": status,
            "source_language": source_language,
            "session_output_language": target_language,
            "visible_output_language": target_language
            if target_language == source_language
            else source_language,
            "adapter": SOUFFLEUSE_ADAPTER,
            "adapter_invocation_mode": SOUFFLEUSE_INVOCATION_MODE,
            "usage_source": "prompt_store_internal_english_visible_projection",
            "fallback_reason": last_error or "souffleuse_output_module_failed",
            "translation_required": target_language != source_language,
            "output_language_mismatch": target_language != source_language,
            "block_count": len(realized),
            "failed_attempts": attempts,
            "attempt_count": len(attempts),
        }


__all__ = ["_SouffleuseOutputRealizationMixin"]
