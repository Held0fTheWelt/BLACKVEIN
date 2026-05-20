from __future__ import annotations

from ._deps import *

class _NarratorOutputRealizationMixin:
    def _realize_narrator_path_output(
        self,
        *,
        source_blocks: list[dict[str, Any]],
        narrator_path: dict[str, Any],
        session: StorySession,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        source_language = str(narrator_path.get("authoring_language") or "en").strip().lower()[:2] or "en"
        target_language = str(session.session_output_language or source_language).strip().lower()[:2] or source_language
        # ADR-0063 Phase 2: optionally enrich each block's ``source_facts`` with
        # the typed W5 narrator projection. Fail-closed flag — when disabled,
        # behavior is identical to pre-Phase-2 (no w5_projection key emitted).
        source_blocks = self._maybe_enrich_blocks_with_w5_narrator_projection(
            session=session, source_blocks=source_blocks
        )
        candidates = self._narrator_path_output_adapter_candidates()
        if not candidates:
            status = "fallback_no_output_model"
            realized = self._fallback_narrator_path_output_blocks(
                source_blocks=source_blocks,
                source_language=source_language,
                target_language=target_language,
                status=status,
            )
            return realized, {
                "contract": "narrator_path_output_realization.v1",
                "status": status,
                "source_language": source_language,
                "session_output_language": target_language,
                "visible_output_language": target_language
                if target_language == source_language
                else source_language,
                "adapter": NARRATOR_PATH_ADAPTER,
                "adapter_invocation_mode": NARRATOR_PATH_INVOCATION_MODE,
                "usage_source": "canonical_content_renderer_fallback",
                "fallback_reason": "no_non_mock_output_model",
                "translation_required": target_language != source_language,
                "output_language_mismatch": target_language != source_language,
            }

        prompt = self._narrator_path_output_prompt(
            source_blocks=source_blocks,
            narrator_path=narrator_path,
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
                attempt["error"] = str(
                    result_metadata.get("error") or "narrator_path_synthesis_module_failed"
                )
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
                nb = dict(block)
                nb["source_before_output_module"] = nb.get("source")
                nb["text"] = text
                if "player_display_text" in nb:
                    nb["player_display_text"] = text
                nb["source_language"] = source_language
                nb["session_output_language"] = target_language
                nb["visible_output_language"] = target_language
                nb["source"] = "narrator_path_synthesis_module"
                realized.append(nb)
            if missing_ids or len(realized) != len(source_blocks):
                attempt["success"] = False
                attempt["error"] = "narrator_path_synthesis_module_incomplete_blocks"
                attempt["missing_block_ids"] = missing_ids
                attempts.append(attempt)
                continue
            return realized, {
                "contract": "narrator_path_output_realization.v1",
                "status": "synthesized",
                "source_language": source_language,
                "session_output_language": target_language,
                "adapter": str(result_metadata.get("adapter") or getattr(adapter, "adapter_name", "") or provider),
                "adapter_invocation_mode": "narrator_path_synthesis_module",
                "provider": provider,
                "model_id": model_id,
                "api_model": api_model,
                "usage_source": "narrator_synthesis_module",
                "block_count": len(realized),
                "attempt_count": len(attempts) + 1,
                "failed_attempts": attempts,
            }

        status = "fallback_output_module_failed"
        realized = self._fallback_narrator_path_output_blocks(
            source_blocks=source_blocks,
            source_language=source_language,
            target_language=target_language,
            status=status,
        )
        last_error = (
            str(attempts[-1].get("error") or "").strip()
            if attempts
            else "narrator_path_synthesis_module_failed"
        )
        return realized, {
            "contract": "narrator_path_output_realization.v1",
            "status": status,
            "source_language": source_language,
            "session_output_language": target_language,
            "visible_output_language": target_language
            if target_language == source_language
            else source_language,
            "adapter": NARRATOR_PATH_ADAPTER,
            "adapter_invocation_mode": NARRATOR_PATH_INVOCATION_MODE,
            "usage_source": "canonical_content_renderer_fallback",
            "fallback_reason": last_error or "narrator_path_synthesis_module_failed",
            "translation_required": target_language != source_language,
            "output_language_mismatch": target_language != source_language,
            "failed_attempts": attempts,
            "attempt_count": len(attempts),
        }


__all__ = ["_NarratorOutputRealizationMixin"]
