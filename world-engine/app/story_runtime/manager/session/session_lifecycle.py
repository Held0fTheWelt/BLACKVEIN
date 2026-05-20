"""Session lifecycle helpers.

Creates, resumes, and closes story-runtime sessions while maintaining authoritative session state.
"""
from __future__ import annotations

from .._deps import *

class _SessionLifecycleMixin:
    def _emit_session_loop_observation(self, *, session: StorySession, trace_id: str | None = None) -> None:
        """Best-effort Langfuse marker for session-loop runtime initialization."""
        try:
            adapter = LangfuseAdapter.get_instance()
            if not adapter.is_enabled():
                return
        except Exception:
            logger.debug("Langfuse adapter unavailable for session loop", exc_info=True)
            return

        runtime_world = session.runtime_world if isinstance(session.runtime_world, dict) else {}
        runtime_summary = {
            "schema_version": runtime_world.get("schema_version"),
            "status": runtime_world.get("status"),
            "mode": runtime_world.get("mode"),
            "current_room_id": runtime_world.get("current_room_id"),
            "room_count": len(runtime_world.get("rooms") if isinstance(runtime_world.get("rooms"), dict) else {}),
            "prop_count": len(runtime_world.get("props") if isinstance(runtime_world.get("props"), dict) else {}),
            "exit_count": len(runtime_world.get("exits") if isinstance(runtime_world.get("exits"), dict) else {}),
            "actor_count": len(runtime_world.get("actors") if isinstance(runtime_world.get("actors"), dict) else {}),
            "diagnostic_summary": runtime_world.get("diagnostic_summary"),
        }
        observation_input = {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "current_scene_id": session.current_scene_id,
        }
        observation_output = {
            "session_id": session.session_id,
            "turn_counter": session.turn_counter,
            "history_len": len(session.history),
            "diagnostics_len": len(session.diagnostics),
            "status": "runtime_engine_initialized",
            "runtime_world": runtime_summary,
        }
        metadata = {
            "stage": "session_loop_runtime_engine_init",
            "session_id": session.session_id,
            "module_id": session.module_id,
            "session_loop_status": "runtime_engine_initialized",
            "session_loop_version": "runtime_world_v1",
        }
        previous_active_span = None
        created_root_span = None
        try:
            previous_active_span = adapter.get_active_span()
            if previous_active_span is not None:
                span = adapter.create_child_span(
                    name="story.runtime_engine.initialize",
                    input=observation_input,
                    output=observation_output,
                    metadata=metadata,
                    status_message="runtime_engine_initialized",
                )
                if span is not None:
                    span.end()
                return

            normalized_trace_id = None
            if isinstance(trace_id, str):
                candidate = trace_id.strip().lower()
                if re.fullmatch(r"[0-9a-f]{32}", candidate):
                    normalized_trace_id = candidate
            created_root_span = adapter.start_trace(
                name="world-engine.session.loop",
                session_id=session.session_id,
                input=observation_input,
                metadata=metadata,
                trace_id=normalized_trace_id,
            )
            if created_root_span is not None:
                created_root_span.update(
                    output=observation_output,
                    status_message="runtime_engine_initialized",
                )
                created_root_span.end()
                adapter.flush()
        except Exception:
            logger.debug("Session loop Langfuse observation failed", exc_info=True)
        finally:
            try:
                if created_root_span is not None or previous_active_span is not None:
                    adapter.set_active_span(previous_active_span)
            except Exception:
                logger.debug("Failed to restore Langfuse active span after session loop", exc_info=True)

    def create_session(
        self,
        *,
        module_id: str,
        runtime_projection: dict[str, Any],
        session_input_language: str | None = None,
        session_output_language: str | None = None,
        content_provenance: dict[str, Any] | None = None,
        trace_id: str | None = None,
        session_id: str | None = None,
        skip_graph_opening_on_create: bool = False,
    ) -> StorySession:
        # Generate trace_id if not provided for audit trail correlation.
        if not trace_id:
            trace_id = uuid4().hex
        module_language = _module_authoring_language(
            module_id=module_id,
            runtime_projection=runtime_projection,
            content_provenance=content_provenance,
        )
        resolved_output_language = (
            _language_code(session_output_language)
            or module_language
            or DEFAULT_SESSION_LANGUAGE
        )
        resolved_input_language = (
            _language_code(session_input_language)
            or resolved_output_language
            or module_language
            or DEFAULT_SESSION_LANGUAGE
        )
        session = self._create_story_session_record(
            module_id=module_id,
            runtime_projection=runtime_projection,
            session_input_language=resolved_input_language,
            session_output_language=resolved_output_language,
            content_provenance=content_provenance,
            session_id=session_id,
        )
        self._log_session_loop_event(
            event="runtime_engine_initialized",
            session=session,
            trace_id=trace_id,
        )
        self._emit_session_loop_observation(session=session, trace_id=trace_id)
        if skip_graph_opening_on_create or self._skip_graph_opening_on_create:
            return session
        self._assert_live_player_governance()
        if (
            len(session.diagnostics) == 1
            and isinstance(session.diagnostics[0], dict)
            and session.diagnostics[0].get("event_type") == "runtime_world_initialized"
        ):
            session.diagnostics.clear()
        attempts = self._opening_retry_count() + 1
        last_exc: BaseException | None = None
        for attempt in range(1, attempts + 1):
            try:
                with self._session_turn_lock(session.session_id):
                    self._execute_opening_locked(session.session_id, trace_id=trace_id)
                self.metrics.incr("story_opening_success", module_id=module_id, session_id=session.session_id, attempt=attempt)
                return session
            except BaseException as exc:
                last_exc = exc
                self.metrics.incr(
                    "story_opening_retry",
                    module_id=module_id,
                    session_id=session.session_id,
                    attempt=attempt,
                    error=str(exc)[:300],
                )
        self.sessions.pop(session.session_id, None)
        if self._session_store is not None:
            try:
                self._session_store.delete(session.session_id)
            except Exception:
                pass
        log_story_runtime_failure(
            trace_id=None,
            story_session_id=session.session_id,
            operation="create_session_opening",
            message=str(last_exc)[:500] if last_exc else "opening_failed",
            failure_class="opening_generation_failed",
        )
        raise RuntimeError(f"Opening generation failed for module {module_id}: {last_exc}") from last_exc

    def execute_turn(self, *, session_id: str, player_input: str, trace_id: str | None = None) -> dict[str, Any]:
        with self._session_turn_lock(session_id):
            return self._execute_turn_locked(
                session_id=session_id, player_input=player_input, trace_id=trace_id
            )


__all__ = ["_SessionLifecycleMixin"]
