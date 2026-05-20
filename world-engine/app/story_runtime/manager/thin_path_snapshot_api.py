from __future__ import annotations

from ._deps import *

class _ThinPathSnapshotApiMixin:
    def get_thin_path_summary(self, session_id: str, limit: int = 20) -> dict[str, Any]:
        """Slim per-turn Resolver -> Director -> Narrator evidence for the
        narrative_systems UI. Reads ``observability_path_summary`` off each
        recent diagnostics event so the operator can see, per turn:

        - the realization_plan (owner, capabilities, outcome)
        - the capability that was actually invoked
        - kanon_break decision
        - whether a visible block was produced

        Pulls only what the thin-path PR-A surfaces. LDSS-specific fields are
        deliberately excluded; they remain in the full diagnostics endpoint.
        """
        session = self.get_session(session_id)
        events = session.diagnostics[-max(1, int(limit)):]
        rows: list[dict[str, Any]] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            ps = (
                event.get("observability_path_summary")
                if isinstance(event.get("observability_path_summary"), dict)
                else None
            ) or {}
            raw_input = str(event.get("raw_input") or "").strip()
            block_count = 0
            bundle = event.get("visible_output_bundle") if isinstance(event.get("visible_output_bundle"), dict) else None
            if isinstance(bundle, dict):
                blocks = bundle.get("scene_blocks") or []
                if isinstance(blocks, list):
                    block_count = sum(1 for b in blocks if isinstance(b, dict))
            rows.append(
                {
                    "turn_number": event.get("turn_number"),
                    "turn_kind": event.get("turn_kind"),
                    "turn_status": event.get("turn_status"),
                    "raw_player_input_preview": raw_input[:120],
                    "realization_plan": ps.get("realization_plan"),
                    "realize_via_capabilities_used_capability": ps.get(
                        "realize_via_capabilities_used_capability"
                    ),
                    "realize_via_capabilities_outcome": ps.get("realize_via_capabilities_outcome"),
                    "selected_capabilities": ps.get("selected_capabilities") or [],
                    "kanon_break": ps.get("kanon_break"),
                    "kanon_break_reason": ps.get("kanon_break_reason"),
                    # PR-B: live effect propagation projection per turn.
                    "free_player_action_resolution": ps.get("free_player_action_resolution"),
                    "canonical_path_hold_effect": ps.get("canonical_path_hold_effect"),
                    "narrator_consequence_realization": ps.get(
                        "narrator_consequence_realization"
                    ),
                    "director_gathering_state": ps.get("director_gathering_state"),
                    "gathering_paused_beat_suppression": ps.get(
                        "gathering_paused_beat_suppression"
                    ),
                    "director_pause_transition_reaction": ps.get(
                        "director_pause_transition_reaction"
                    ),
                    "visible_block_emitted": bool(ps.get("visible_block_emitted")),
                    "director_path_mode": ps.get("director_path_mode"),
                    "visible_scene_block_count": block_count,
                    "nodes_executed": ps.get("nodes_executed") or [],
                    "structured_output_keys": ps.get("structured_output_keys") or [],
                    "usage_details": ps.get("usage_details"),
                    "validation_status": ps.get("validation_status"),
                }
            )
        return {
            "schema_version": "thin_path_summary.v1",
            "session_id": session.session_id,
            "turn_counter": session.turn_counter,
            "rows": rows,
        }

    def get_runtime_diagnostic_snapshot(
        self,
        session_id: str,
        *,
        turn_number: int | None = None,
        thin_path_limit: int = 20,
    ) -> dict[str, Any]:
        """Read-only aggregator for ``runtime_diagnostic_snapshot.v1``.

        Composes existing operator surfaces (thin-path rows, diagnostics events,
        pulse diagnostics) without running the graph or importing the PR-0 stub
        module into production execution paths.
        """
        session = self.get_session(session_id)
        thin = self.get_thin_path_summary(session_id, limit=thin_path_limit)
        rows = thin.get("rows") if isinstance(thin.get("rows"), list) else []

        selected_row: dict[str, Any] | None = None
        if turn_number is not None:
            for row in rows:
                if isinstance(row, dict) and row.get("turn_number") == turn_number:
                    selected_row = row
                    break
        elif rows:
            last = rows[-1]
            selected_row = last if isinstance(last, dict) else None

        def _contract_name_for_key(key: str) -> str:
            mapping = {
                "free_player_action_resolution": "free_player_action_resolution.v1",
                "director_gathering_state": "director_gathering_state.v1",
                "canonical_path_hold_effect": "canonical_path_hold_effect.v1",
                "narrator_consequence_realization": "narrator_consequence_realization.v1",
            }
            return mapping.get(key, f"{key}.v1")

        def _contract_payload(
            key: str,
            *,
            from_row: bool = True,
        ) -> dict[str, Any]:
            if from_row and selected_row and selected_row.get(key) is not None:
                return {
                    "contract_name": _contract_name_for_key(key),
                    "payload": selected_row.get(key),
                    "not_yet_wired": False,
                }
            return {
                "contract_name": _contract_name_for_key(key),
                "payload": None,
                "not_yet_wired": True,
            }

        pulse_section: dict[str, Any] = {
            "contract_name": "director_pulse_diagnostics.v1",
            "payload": None,
            "not_yet_wired": True,
        }
        bundle_parity: dict[str, Any] = {
            "contract_name": "bundle_vs_event_stream_parity.v1",
            "payload": None,
            "not_yet_wired": True,
        }
        for event in reversed(session.diagnostics):
            if not isinstance(event, dict):
                continue
            if turn_number is not None and event.get("turn_number") != turn_number:
                continue
            diag = event.get("diagnostics") if isinstance(event.get("diagnostics"), dict) else {}
            if not diag and isinstance(event.get("diagnostics_envelope"), dict):
                diag = event["diagnostics_envelope"]
            if not isinstance(diag, dict):
                diag = {}
            dp = diag.get("director_pulse")
            if not isinstance(dp, dict):
                dp = event.get("director_pulse") if isinstance(event.get("director_pulse"), dict) else None
            if isinstance(dp, dict):
                pulse_section = {
                    "contract_name": "director_pulse_diagnostics.v1",
                    "payload": dp,
                    "not_yet_wired": False,
                }
            parity = diag.get("bundle_vs_event_stream_parity")
            if not isinstance(parity, dict):
                parity = dp.get("parity") if isinstance(dp, dict) else None
            if isinstance(parity, dict):
                bundle_parity = {
                    "contract_name": "bundle_vs_event_stream_parity.v1",
                    "payload": parity,
                    "not_yet_wired": False,
                }
            if pulse_section.get("payload") is not None or bundle_parity.get("payload") is not None:
                break

        capability_names: list[str] = []
        if selected_row:
            caps = selected_row.get("selected_capabilities") or []
            if isinstance(caps, list):
                capability_names = [str(c) for c in caps if str(c).strip()]

        return {
            "schema_version": "runtime_diagnostic_snapshot.v1",
            "session_id": session.session_id,
            "turn_number": (
                turn_number
                if turn_number is not None
                else (selected_row.get("turn_number") if selected_row else None)
            ),
            "canonical_step_id": getattr(session, "canonical_step_id", None),
            "visible_block_emitted": (
                selected_row.get("visible_block_emitted") if selected_row else None
            ),
            "resolver_output": _contract_payload("free_player_action_resolution"),
            "director_gathering_state": _contract_payload("director_gathering_state"),
            "canonical_path_hold_effect": _contract_payload("canonical_path_hold_effect"),
            "narrator_consequence_realization": _contract_payload(
                "narrator_consequence_realization"
            ),
            "pulse": pulse_section,
            "bundle_vs_event_stream_parity": bundle_parity,
            "semantic_capability_consultation_names": capability_names,
            "thin_path_summary": {
                "schema_version": thin.get("schema_version"),
                "row_count": len(rows),
                "selected_turn": (
                    selected_row.get("turn_number") if selected_row else None
                ),
            },
            "aggregation_sources": [
                "thin_path_summary.v1",
                "session.diagnostics[].diagnostics.director_pulse",
                "session.diagnostics[].diagnostics.bundle_vs_event_stream_parity",
            ],
        }


__all__ = ["_ThinPathSnapshotApiMixin"]
