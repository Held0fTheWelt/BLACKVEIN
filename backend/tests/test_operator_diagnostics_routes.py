"""API tests for operator diagnostics vitality surfaces."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

pytestmark = pytest.mark.observability


@dataclass
class _Session:
    diagnostics: list[dict]


def _allow_all_features(monkeypatch):
    from app.auth import feature_registry as fr

    monkeypatch.setattr(fr, "user_can_access_feature", lambda _user, _feature_id: True)


def test_operator_diagnostics_session_not_found_returns_404(client, moderator_headers, monkeypatch):
    _allow_all_features(monkeypatch)
    monkeypatch.setattr("app.services.session_service.get_session", lambda _sid: None)

    response = client.get("/api/v1/operator/diagnostics/session/s-missing", headers=moderator_headers)
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "session_not_found"


def test_operator_diagnostics_session_surface_shape(client, moderator_headers, monkeypatch):
    _allow_all_features(monkeypatch)
    session = _Session(
        diagnostics=[
            {
                "turn_number": 1,
                "turn_kind": "player",
                "trace_id": "trace-1",
                "runtime_governance_surface": {
                    "quality_class": "degraded",
                    "degradation_signals": ["fallback_used"],
                },
                "actor_survival_telemetry": {
                    "vitality_telemetry_v1": {
                        "schema_version": "vitality_telemetry_v1",
                        "selected_primary_responder_id": "annette_reille",
                        "selected_secondary_responder_ids": ["michel_longstreet"],
                        "realized_actor_ids": [],
                        "realized_secondary_responder_ids": [],
                        "rendered_actor_ids": [],
                        "generated_spoken_line_count": 1,
                        "validated_spoken_line_count": 1,
                        "rendered_spoken_line_count": 0,
                        "generated_action_line_count": 0,
                        "validated_action_line_count": 0,
                        "rendered_action_line_count": 0,
                        "initiative_generated_count": 1,
                        "initiative_preserved_count": 0,
                        "initiative_seizer_id": "annette_reille",
                        "initiative_loser_id": "veronique_vallon",
                        "initiative_pressure_label": "contested",
                        "quality_class": "degraded",
                        "degradation_signals": ["fallback_used"],
                        "fallback_used": True,
                        "degraded_commit": False,
                        "retry_exhausted": False,
                        "response_present": False,
                        "initiative_present": False,
                        "multi_actor_realized": False,
                        "thin_edge_applied": True,
                        "withheld_applied": True,
                        "compressed_applied": False,
                        "prior_tension_present": True,
                        "sparse_input_detected": True,
                        "sparse_input_recovery_applied": False,
                        "generated_ok": True,
                        "validation_ok": True,
                        "commit_applied": True,
                    },
                    "operator_diagnostic_hints": {
                        "hints": ["No visible actor-lane response reached render output."],
                        "actor_agency_level": "narration_only",
                        "why_turn_felt_passive": ["single_actor_only"],
                        "primary_passivity_factors": ["single_actor_only"],
                    },
                },
            }
        ]
    )
    monkeypatch.setattr("app.services.session_service.get_session", lambda _sid: session)

    response = client.get("/api/v1/operator/diagnostics/session/s-1", headers=moderator_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["diagnostics_version"] == "2.0"
    assert "turn_history" in data
    row = data["turn_history"]["rows"][0]
    assert row["schema_version"] == "vitality_telemetry_v1"
    assert "why_turn_felt_passive" in row
    assert "vitality_breakdown" in row


def test_operator_turn_history_endpoint_shape(client, moderator_headers, monkeypatch):
    _allow_all_features(monkeypatch)
    session = _Session(diagnostics=[{"turn_number": 1, "turn_kind": "player", "actor_survival_telemetry": {"vitality_telemetry_v1": {"schema_version": "vitality_telemetry_v1"}}}])
    monkeypatch.setattr("app.services.session_service.get_session", lambda _sid: session)

    response = client.get("/api/v1/operator/diagnostics/session/s-1/turn-history", headers=moderator_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["turn_history_version"] == "2.0"
    assert "rows" in data
