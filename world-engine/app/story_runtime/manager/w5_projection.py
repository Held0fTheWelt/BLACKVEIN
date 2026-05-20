from __future__ import annotations

from ._deps import *

class _W5ProjectionMixin:
    @staticmethod
    def _w5_narrator_projection_actor_candidates(session: StorySession) -> tuple[str, ...]:
        projection = (
            session.runtime_projection
            if isinstance(session.runtime_projection, dict)
            else {}
        )
        candidates: list[str] = []
        for key in ("human_actor_id", "selected_player_role"):
            raw = projection.get(key)
            if not isinstance(raw, str):
                continue
            value = raw.strip()
            if value and value not in candidates:
                candidates.append(value)
        return tuple(candidates)

    def _maybe_enrich_blocks_with_w5_narrator_projection(
        self,
        *,
        session: StorySession,
        source_blocks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Phase 2: add ``source_facts.w5_projection`` to each narrator block.

        - Fail-closed: returns ``source_blocks`` untouched when the
          ``W5_AST_NARRATOR_PROJECTION_ENABLED`` flag is disabled.
        - Defensive: any failure during projection construction records a
          ``w5_narrator_projection_failed`` diagnostic and falls back to
          legacy behavior. The turn is not failed in Phase 2.
        - Coerces persisted ``w5_latest_snapshot`` dicts through the typed
          ``build_w5_projection_for_narrator`` builder; never lets the
          narrator read the raw dict directly.
        """

        if not self._w5_ast_narrator_projection_enabled():
            return source_blocks
        try:
            latest = session.w5_latest_snapshot
            history = session.w5_history or []
            previous: dict[str, Any] | None = None
            if isinstance(history, list) and len(history) >= 2:
                cand = history[-2]
                if isinstance(cand, dict):
                    previous = cand
            actor_candidates = StoryRuntimeManager._w5_narrator_projection_actor_candidates(
                session
            )
            projection = build_w5_projection_for_narrator(
                latest,
                actor_id=actor_candidates[0] if actor_candidates else None,
                actor_id_aliases=actor_candidates[1:],
                previous_snapshot=previous,
            )
            projection_payload = projection.to_dict()
        except Exception as exc:  # pragma: no cover - defensive
            session.diagnostics.append(
                {
                    "diagnostic_kind": "w5_narrator_projection_failed",
                    "schema_version": "w5_narrator_projection_diagnostic.v1",
                    "session_id": session.session_id,
                    "turn_counter": int(session.turn_counter),
                    "error": str(exc),
                }
            )
            return source_blocks

        enriched: list[dict[str, Any]] = []
        for block in source_blocks:
            if not isinstance(block, dict):
                enriched.append(block)
                continue
            nb = dict(block)
            existing = nb.get("source_facts")
            facts = dict(existing) if isinstance(existing, dict) else {}
            facts["w5_projection"] = projection_payload
            nb["source_facts"] = facts
            enriched.append(nb)
        return enriched

    def _w5_shadow_extract_after_commit(
        self,
        *,
        session: StorySession,
        graph_state: dict[str, Any],
        event: dict[str, Any],
    ) -> None:
        """Run the W5 pure extractor and append its snapshot to ``session``.

        Shadow-only in Phase 1: failures are caught and logged as a session
        diagnostic; they must not affect the committed turn outcome.
        """

        try:
            previous_payload = session.w5_latest_snapshot
            previous_snapshot: W5Snapshot | None = None
            if isinstance(previous_payload, dict):
                try:
                    previous_snapshot = W5Snapshot.from_dict(previous_payload)
                except Exception:
                    previous_snapshot = None
            environment_state_after = (
                session.environment_state
                if isinstance(session.environment_state, dict)
                else {}
            )
            director_gathering_state = (
                graph_state.get("director_gathering_state")
                if isinstance(graph_state.get("director_gathering_state"), dict)
                else None
            )
            free_player_action_resolution = (
                graph_state.get("free_player_action_resolution")
                if isinstance(graph_state.get("free_player_action_resolution"), dict)
                else None
            )
            actor_lane_context = (
                graph_state.get("actor_lane_context")
                if isinstance(graph_state.get("actor_lane_context"), dict)
                else None
            )
            npc_agency_simulation = (
                graph_state.get("npc_agency_simulation")
                if isinstance(graph_state.get("npc_agency_simulation"), dict)
                else (
                    graph_state.get("npc_agency_plan")
                    if isinstance(graph_state.get("npc_agency_plan"), dict)
                    else None
                )
            )
            character_mind_records = (
                graph_state.get("character_mind_records")
                if isinstance(graph_state.get("character_mind_records"), dict)
                else None
            )
            active_canonical_step = (
                graph_state.get("active_canonical_step")
                if isinstance(graph_state.get("active_canonical_step"), dict)
                else (
                    {"step_id": session.canonical_step_id}
                    if session.canonical_step_id
                    else None
                )
            )
            snapshot = extract_w5_snapshot_from_committed_event(
                previous_snapshot=previous_snapshot,
                committed_event=event,
                environment_state_after=environment_state_after,
                director_gathering_state=director_gathering_state,
                free_player_action_resolution=free_player_action_resolution,
                actor_lane_context=actor_lane_context,
                npc_agency_simulation=npc_agency_simulation,
                character_mind_records=character_mind_records,
                active_canonical_step=active_canonical_step,
                story_session_id=session.session_id,
                turn_number=int(session.turn_counter),
            )
            snapshot_payload = snapshot.to_dict()
            session.w5_history.append(snapshot_payload)
            session.w5_latest_snapshot = snapshot_payload
            validation_outcome = (
                event.get("validation_outcome")
                if isinstance(event.get("validation_outcome"), dict)
                else None
            )
            event["w5_runtime_metadata"] = build_w5_runtime_metadata(
                snapshot_payload,
                latest_validation_outcome=validation_outcome,
            )
        except Exception as exc:  # pragma: no cover - defensive
            session.diagnostics.append(
                {
                    "diagnostic_kind": "w5_shadow_extraction_failed",
                    "schema_version": "w5_shadow_diagnostic.v1",
                    "session_id": session.session_id,
                    "turn_counter": int(session.turn_counter),
                    "error": str(exc),
                }
            )

    def _build_scripted_continuation(
        self,
        *,
        session: StorySession,
        after_step_id: str,
        opening_block_count: int,
        trace_id: str | None,
    ) -> dict[str, Any]:
        """Build scripted continuation blocks for steps after the opening.

        Returns the raw continuation result from
        ``build_goc_scripted_continuation`` with scene blocks that may
        contain ``requires_llm_realization=True`` entries (npc_speak).
        Those blocks are realized via the same LLM adapter used for
        narrator path output realization.
        """
        continuation = build_goc_scripted_continuation(
            after_step_id=after_step_id,
            session_output_language=session.session_output_language,
            block_index_start=opening_block_count + 1,
        )
        realized_blocks: list[dict[str, Any]] = []
        for block in continuation.get("scene_blocks", []):
            if not isinstance(block, dict):
                continue
            if block.get("requires_llm_realization"):
                realized = self._realize_npc_speak_block(
                    block=block,
                    session=session,
                    continuation=continuation,
                    trace_id=trace_id,
                )
                realized_blocks.append(realized)
            else:
                source_language = str(continuation.get("authoring_language") or "en").strip().lower()[:2] or "en"
                target_language = (
                    str(session.session_output_language or source_language).strip().lower()[:2]
                    or source_language
                )
                if target_language != source_language:
                    translated_blocks, _ = self._realize_narrator_path_output(
                        source_blocks=[block],
                        narrator_path=continuation,
                        session=session,
                    )
                    if translated_blocks:
                        realized_blocks.append(translated_blocks[0])
                    else:
                        realized_blocks.append(block)
                else:
                    realized_blocks.append(block)
        continuation["scene_blocks"] = realized_blocks
        return continuation


__all__ = ["_W5ProjectionMixin"]
