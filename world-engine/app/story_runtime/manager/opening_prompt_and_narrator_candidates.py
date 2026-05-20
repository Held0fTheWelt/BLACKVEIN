"""Opening prompt and narrator candidates.

Builds opening prompt data and candidate narrator lines before the opening turn is committed.
"""
from __future__ import annotations

from ._deps import *

class _OpeningPromptAndNarratorCandidatesMixin:
    def _build_opening_prompt(self, session: StorySession) -> str:
        projection = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
        scene_id = str(projection.get("start_scene_id") or session.current_scene_id or "opening")
        scenes = projection.get("scenes") if isinstance(projection.get("scenes"), list) else []
        scene_row = next(
            (
                row
                for row in scenes
                if isinstance(row, dict) and str(row.get("scene_id") or row.get("id") or "") == scene_id
            ),
            {},
        )
        scene_name = str(scene_row.get("name") or scene_id)
        scene_desc = str(scene_row.get("description") or "")
        chars = projection.get("character_ids") if isinstance(projection.get("character_ids"), list) else []
        cast = ", ".join(str(c) for c in chars[:8]) if chars else "unknown"
        lang_label = "German" if session.session_output_language == "de" else "English"
        runtime_profile_id = _runtime_profile_id_from_projection(projection)
        opening_scene_sequence_id = ""
        opening_event_ids: list[str] = []
        opening_must_establish: list[str] = []
        opening_min_visible_blocks = 0
        opening_preferred_visible_blocks = 0
        opening_max_visible_blocks = 0
        hard_forbidden_reject_on: list[str] = []
        hard_forbidden_recover_on: list[str] = []
        first_playable_phase = ""
        anchor = "configured opening location and social premise"
        try:
            policy = load_module_runtime_policy(
                module_id=session.module_id,
                runtime_profile_id=runtime_profile_id,
            )
            policy_dict = policy.to_dict()
            opening_policy = (
                policy_dict.get("opening_policy")
                if isinstance(policy_dict.get("opening_policy"), dict)
                else {}
            )
            location_model = (
                policy_dict.get("location_model")
                if isinstance(policy_dict.get("location_model"), dict)
                else {}
            )
            anchor = str(
                location_model.get("narrative_anchor_area_id")
                or location_model.get("setting_id")
                or anchor
            ).strip() or anchor
            opening_scene_sequence_id = str(opening_policy.get("id") or "").strip()
            narration_mode = (
                opening_policy.get("narration_mode")
                if isinstance(opening_policy.get("narration_mode"), dict)
                else {}
            )
            try:
                opening_min_visible_blocks = int(narration_mode.get("min_visible_blocks") or 0)
            except (TypeError, ValueError):
                opening_min_visible_blocks = 0
            try:
                opening_preferred_visible_blocks = int(narration_mode.get("preferred_visible_blocks") or 0)
            except (TypeError, ValueError):
                opening_preferred_visible_blocks = 0
            try:
                opening_max_visible_blocks = int(narration_mode.get("max_visible_blocks") or 0)
            except (TypeError, ValueError):
                opening_max_visible_blocks = 0
            contract = (
                opening_policy.get("opening_contract")
                if isinstance(opening_policy.get("opening_contract"), dict)
                else {}
            )
            if isinstance(contract, dict):
                opening_must_establish = [
                    str(item).strip()
                    for item in (contract.get("must_establish") or [])
                    if str(item).strip()
                ]
            narrative_events = (
                opening_policy.get("narrative_events")
                if isinstance(opening_policy.get("narrative_events"), list)
                else []
            )
            if isinstance(narrative_events, list):
                opening_event_ids = [
                    str(row.get("id") or "").strip()
                    for row in narrative_events
                    if isinstance(row, dict) and str(row.get("id") or "").strip()
                ]
                for row in narrative_events:
                    if isinstance(row, dict) and row.get("first_playable_scene_phase"):
                        first_playable_phase = str(
                            row.get("first_playable_scene_phase") or first_playable_phase
                        ).strip() or first_playable_phase
                        break
            hard_forbidden_policy = (
                policy_dict.get("hard_forbidden_policy")
                if isinstance(policy_dict.get("hard_forbidden_policy"), dict)
                else {}
            )
            detection = (
                hard_forbidden_policy.get("hard_forbidden_detection")
                if isinstance(hard_forbidden_policy.get("hard_forbidden_detection"), dict)
                else {}
            )
            hard_forbidden_reject_on = [
                str(item).strip() for item in (detection.get("reject_on") or []) if str(item).strip()
            ]
            hard_forbidden_recover_on = [
                str(item).strip() for item in (detection.get("recover_on") or []) if str(item).strip()
            ]
        except Exception:
            pass
        human_actor_id = str(projection.get("human_actor_id") or "").strip()
        role_label = human_actor_id if human_actor_id else "the player character"
        first_playable_clause = (
            f"After the required opening evidence, establish first playable scene phase {first_playable_phase}. "
            if first_playable_phase
            else "After the required opening evidence, establish the configured first playable state. "
        )
        visible_min = max(opening_min_visible_blocks, min(len(opening_event_ids), 6) if opening_event_ids else 0, 6)
        visible_preferred = max(opening_preferred_visible_blocks, visible_min)
        visible_max = (
            opening_max_visible_blocks
            if opening_max_visible_blocks >= visible_preferred
            else max(visible_preferred, 12)
        )
        return render_prompt(
            "world_engine.opening_prompt",
            language_label=lang_label,
            module_id=session.module_id,
            scene_name=scene_name,
            scene_id=scene_id,
            scene_description=scene_desc or "n/a",
            cast=cast,
            anchor=anchor,
            role_label=role_label,
            first_playable_clause=first_playable_clause,
            # Backward-compatible prompt-store alias. The live DB may still
            # carry the pre-rename variable, while local seed prompts use
            # first_playable_clause.
            handover_clause=first_playable_clause,
            opening_scene_sequence_id=opening_scene_sequence_id or "opening_scene_sequence",
            opening_event_ids=opening_event_ids,
            opening_must_establish=opening_must_establish,
            visible_min=visible_min,
            visible_preferred=visible_preferred,
            visible_max=visible_max,
            hard_forbidden_reject_on=hard_forbidden_reject_on,
            hard_forbidden_recover_on=hard_forbidden_recover_on,
        )

    def _opening_commit_acceptable(self, graph_state: dict[str, Any]) -> bool:
        # Bootstrap policy for opening-turn validation.
        # Opening turns are engine-generated (not player-prompted) and do not require
        # the same committed_result contract as subsequent turns. We enforce validation
        # status and preview placeholder checks, but defer strict commit enforcement.
        # This leniency is surfaced as a degradation signal in canonical_degradation_signals()
        # and impacts quality_class assessment accordingly.
        val = graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
        if val.get("status") != "approved":
            # Log rejection reason for debugging
            self.metrics.incr("opening_rejected", reason=f"status_{val.get('status', 'unknown')}")
            return False

        # Check for preview placeholder (always enforced)
        bundle = graph_state.get("visible_output_bundle") if isinstance(graph_state.get("visible_output_bundle"), dict) else {}
        gm = bundle.get("gm_narration")
        if isinstance(gm, list):
            joined = "\n".join(str(x) for x in gm)
            if opening_text_contains_preview_placeholder(joined):
                self.metrics.incr("opening_rejected", reason="preview_placeholder")
                return False

        # Accept if validation passed (defer strict commit enforcement)
        self.metrics.incr("opening_accepted")
        return True

    def _visible_narration_present(self, graph_state: dict[str, Any]) -> bool:
        gen = graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {}
        raw = str(gen.get("content") or gen.get("model_raw_text") or "").strip()
        if raw:
            return True
        bundle = graph_state.get("visible_output_bundle") if isinstance(graph_state.get("visible_output_bundle"), dict) else {}
        gm = bundle.get("gm_narration")
        if isinstance(gm, list) and any(str(x).strip() for x in gm):
            return True
        return False

    def _narrator_path_output_adapter_candidate(
        self,
    ) -> tuple[str, str, BaseModelAdapter | None, str | None, float | None]:
        candidates = self._narrator_path_output_adapter_candidates()
        if candidates:
            return candidates[0]
        return "", "", None, None, None

    def _narrator_path_output_adapter_candidates(
        self,
    ) -> list[tuple[str, str, BaseModelAdapter, str | None, float | None]]:
        try:
            decision = self.routing.choose(task_type="narrative_formulation")
        except Exception:
            decision = None
        candidate_model_ids: list[str] = []
        if decision is not None:
            for mid in (getattr(decision, "selected_model", None), getattr(decision, "fallback_model", None)):
                text = str(mid or "").strip()
                if text and text not in candidate_model_ids:
                    candidate_model_ids.append(text)
        for spec in self.registry.all().values():
            if spec.model_name not in candidate_model_ids and spec.llm_or_slm == "llm":
                candidate_model_ids.append(spec.model_name)
        return_candidates: list[tuple[str, str, BaseModelAdapter, str | None, float | None]] = []
        for model_id in candidate_model_ids:
            spec = self.registry.get(model_id)
            if spec is None:
                continue
            provider = str(spec.provider or "").strip()
            adapter = self.adapters.get(provider)
            if adapter is None:
                continue
            if provider == "mock" or str(getattr(adapter, "adapter_name", "") or "").strip() == "mock":
                continue
            api_model = str(getattr(spec, "provider_model_name", "") or "").strip() or spec.model_name
            return_candidates.append((model_id, provider, adapter, api_model, float(spec.timeout_seconds)))
        return return_candidates


__all__ = ["_OpeningPromptAndNarratorCandidatesMixin"]
