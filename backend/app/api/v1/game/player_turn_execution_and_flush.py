"""Game routes implementation concern: player turn execution and flush.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
            turn_payload = execute_story_turn_in_engine(
                session_id=runtime_session_id,
                player_input=player_input,
                trace_id=trace_id,
                langfuse_trace_id=langfuse_trace_id,
                trace_origin=str(trace_meta.get("trace_origin")),
                execution_tier=str(trace_meta.get("execution_tier")),
                canonical_player_flow=bool(trace_meta.get("canonical_player_flow")),
                test_case_id=trace_meta.get("test_case_id"),
                runtime_mode=str(trace_meta.get("runtime_mode")),
            )
            turn = turn_payload.get("turn") if isinstance(turn_payload.get("turn"), dict) else {}
            state = get_story_state(runtime_session_id, trace_id=trace_id)

            # Update root span with results
            if root_span:
                root_span.update(
                    output={
                        "status": "completed",
                        "root_trace_name": "backend.turn.execute",
                        "world_engine_turn_observation_name": "world-engine.turn.execute",
                        "turn_number": turn.get("turn_number"),
                        "canonical_turn_id": turn.get("canonical_turn_id"),
                        "turn_aspect_ledger_present": isinstance(turn.get("turn_aspect_ledger"), dict),
                        "player_input_length": len(player_input),
                        "player_input_sha256": player_input_sha256,
                        **trace_meta,
                    },
                )

            refreshed = _player_session_bundle(
                run_id=run_id,
                template_id=str(bundle.get("template_id") or ""),
                module_id=str(bundle.get("module_id") or ""),
                runtime_session_id=runtime_session_id,
                state=state,
                turn=turn,
            )
            return jsonify(refreshed), route_status_codes.ok
        except GameServiceError as exc:
            # Update root span with error
            if root_span:
                root_span.update(output={
                    "status": "error",
                    "failure_class": "world_engine_unreachable",
                    "status_code": exc.status_code,
                })

            raise
        finally:
            # End root span and flush
            if root_span:
                try:
                    adapter.end_trace(root_span)
                except Exception:
                    current_app.logger.warning("Langfuse root span end failed during game turn", exc_info=True)
            _flush_langfuse_background(adapter, context="game-turn")
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


'''
