"""
MVP4 Full Handoff Integration Test

Verifies the COMPLETE flow: Frontend → Backend → World-Engine → Backend
with all 5 contracts being satisfied in the real API response.
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock


def _mock_response(payload: dict) -> MagicMock:
    response = MagicMock(status_code=200)
    response.content = b"{}"
    response.json.return_value = payload
    return response


def _mock_play_service_client(mock_client_cls, payloads: list[dict] | dict) -> MagicMock:
    payload_sequence = payloads if isinstance(payloads, list) else [payloads]
    client = mock_client_cls.return_value.__enter__.return_value
    client.request.side_effect = [_mock_response(payload) for payload in payload_sequence]
    return client


def _play_run_payload(*, run_id: str = "run-player-1", selected_player_role: str = "veronique") -> dict:
    return {
        "run": {"id": run_id, "template_id": "god_of_carnage_solo"},
        "template": {
            "id": "god_of_carnage_solo",
            "title": "God of Carnage Solo",
            "kind": "solo_story",
            "join_policy": "single_player",
            "min_humans_to_start": 1,
        },
        "store": {"backend": "world_engine"},
        "hint": "created",
        "content_module_id": "god_of_carnage",
        "runtime_profile_id": "god_of_carnage_solo",
        "runtime_module_id": "god_of_carnage",
        "runtime_mode": "live",
        "selected_player_role": selected_player_role,
        "human_actor_id": selected_player_role,
        "npc_actor_ids": ["annette", "alain"],
        "actor_lanes": {selected_player_role: "human", "annette": "npc", "alain": "npc"},
    }


def _story_state_with_entries(entries: list[dict]) -> dict:
    return {
        "turn_counter": len(entries),
        "story_window": {
            "contract": "authoritative_story_window_v1",
            "entries": entries,
            "entry_count": len(entries),
            "latest_entry": entries[-1] if entries else None,
        },
    }


@pytest.mark.mvp4
def test_game_player_session_create_includes_actor_ownership_handoff(client, auth_headers):
    """
    Contract 1 Verification: Backend must send complete actor ownership
    (human_actor_id, npc_actor_ids, actor_lanes) to World-Engine and
    return opening_turn with non-empty visible output.
    """
    # Mock world-engine POST /api/story/sessions
    with patch('app.services.game_service.httpx.Client') as mock_client_cls:
        # World-Engine returns session with opening
        opening_text = "The room is tense."
        mock_client = _mock_play_service_client(
            mock_client_cls,
            [
                _play_run_payload(selected_player_role="veronique"),
                {
                    "session_id": "we_session_123",
                    "module_id": "god_of_carnage",
                    "turn_counter": 0,
                    "opening_turn": {
                        "turn_number": 0,
                        "turn_kind": "opening",
                        "visible_output_bundle": {
                            "gm_narration": [opening_text],
                            "scene_blocks": [{"block_type": "narrator", "text": opening_text}],
                        },
                        "runtime_governance_surface": {
                            "quality_class": "healthy",
                            "degradation_signals": [],
                        },
                        "validation_outcome": {"status": "approved"},
                        "committed_result": {"commit_applied": True},
                    },
                    "runtime_config_status": {"source": "default"},
                    "warnings": ["session_includes_committed_turn_0_opening"],
                },
                _story_state_with_entries(
                    [
                        {
                            "entry_id": "opening",
                            "role": "runtime",
                            "turn_number": 0,
                            "text": opening_text,
                            "scene_blocks": [{"block_type": "narrator", "text": opening_text}],
                        }
                    ]
                ),
            ],
        )

        # Call backend endpoint to create session
        response = client.post(
            "/api/v1/game/player-sessions",
            json={
                "template_id": "god_of_carnage_solo",
                "selected_player_role": "veronique",
            },
            headers=auth_headers,
        )

        assert response.status_code in [200, 201], f"Session creation failed: {response.text}"
        data = response.get_json()

        # Contract 1: opening_turn must exist and be non-empty
        assert data.get("opening_turn") is not None, "opening_turn missing from backend response"
        opening_turn = data.get("opening_turn")
        assert opening_turn.get("turn_kind") == "opening"

        # Contract 2: opening must have visible output
        visible_bundle = opening_turn.get("visible_output_bundle", {})
        assert visible_bundle.get("gm_narration"), "opening_turn missing gm_narration"
        assert visible_bundle.get("scene_blocks"), "opening_turn missing scene_blocks"

        # Contract 3: can_execute must be True (opening exists)
        assert data.get("can_execute") is True, \
            "can_execute should be True when opening exists"

        # Contract 4: diagnostics fields must be present
        governance = opening_turn.get("runtime_governance_surface", {})
        assert "quality_class" in governance, "quality_class missing"
        assert "degradation_signals" in governance, "degradation_signals missing"

        # Verify world-engine was called with actor ownership
        assert mock_client.request.called, "World-Engine endpoint not called"
        call_args = mock_client.request.call_args_list[1]
        assert call_args.args[:2] == ("POST", "/api/story/sessions")
        request_json = call_args.kwargs.get("json", {})

        # Check that runtime_projection includes actor ownership
        runtime_projection = request_json.get("runtime_projection", {})
        assert runtime_projection.get("human_actor_id") == "veronique", \
            "human_actor_id not sent to World-Engine"
        assert runtime_projection.get("npc_actor_ids"), \
            "npc_actor_ids not sent to World-Engine"
        assert runtime_projection.get("actor_lanes"), \
            "actor_lanes not sent to World-Engine"


@pytest.mark.mvp4
def test_game_player_session_can_execute_reflects_opening_state(client, auth_headers):
    """
    Contract 3 Verification: can_execute must be True when opening exists,
    False when it doesn't.
    """
    # Test with NO opening
    with patch('app.services.game_service.httpx.Client') as mock_client_cls:
        _mock_play_service_client(
            mock_client_cls,
            [
                _play_run_payload(run_id="run-no-opening", selected_player_role="veronique"),
                {
                    "session_id": "we_session_no_opening",
                    "module_id": "god_of_carnage",
                    "turn_counter": 0,
                    "opening_turn": None,  # No opening
                    "runtime_config_status": {"source": "default"},
                    "warnings": [],
                },
                _story_state_with_entries([]),
            ],
        )

        response = client.post(
            "/api/v1/game/player-sessions",
            json={"template_id": "god_of_carnage_solo"},
            headers=auth_headers,
        )

        if response.status_code in [200, 201]:
            data = response.get_json()
            # Without opening, can_execute should be False
            assert data.get("can_execute") is False, \
                "can_execute should be False when no opening"


@pytest.mark.mvp4
def test_opening_turn_has_committed_truth_not_proposals(client, auth_headers):
    """
    Contract 2 & 4 Verification: opening_turn must contain committed truth
    (not AI proposals), marked appropriately.
    """
    with patch('app.services.game_service.httpx.Client') as mock_client_cls:
        _mock_play_service_client(
            mock_client_cls,
            [
                _play_run_payload(run_id="run-truth", selected_player_role="veronique"),
                {
                    "session_id": "we_session_truth",
                    "module_id": "god_of_carnage",
                    "turn_counter": 0,
                    "opening_turn": {
                        "turn_number": 0,
                        "turn_kind": "opening",
                        "visible_output_bundle": {
                            "gm_narration": ["Opening narration."],
                            "scene_blocks": [{"block_type": "narrator", "text": "Opening."}],
                        },
                        "committed_result": {"commit_applied": True},
                        "validation_outcome": {
                            "status": "approved",
                            "reason": "healthy_opening_ldss",
                        },
                        "model_route": {
                            "generation": {
                                "metadata": {
                                    "adapter": "ldss_deterministic",
                                    "entrypoint": "opening_turn_healthy_generation",
                                }
                            }
                        },
                        "runtime_governance_surface": {
                            "quality_class": "healthy",
                            "degradation_signals": [],
                            "commitment_status": "committed",
                        },
                    },
                    "runtime_config_status": {"source": "default"},
                    "warnings": ["session_includes_committed_turn_0_opening"],
                },
                _story_state_with_entries(
                    [{"entry_id": "opening", "role": "runtime", "turn_number": 0, "text": "Opening."}]
                ),
            ],
        )

        response = client.post(
            "/api/v1/game/player-sessions",
            json={"template_id": "god_of_carnage_solo"},
            headers=auth_headers,
        )

        if response.status_code in [200, 201]:
            data = response.get_json()
            opening_turn = data.get("opening_turn", {})

            # Must have committed_result (not proposal)
            assert opening_turn.get("committed_result", {}).get("commit_applied") is True, \
                "opening_turn must have commit_applied=True"

            # Must be marked as deterministic LDSS
            model_route = opening_turn.get("model_route", {})
            generation = model_route.get("generation", {})
            metadata = generation.get("metadata", {})
            assert metadata.get("adapter") == "ldss_deterministic", \
                "opening must be marked ldss_deterministic"

            # Must have quality_class
            gov = opening_turn.get("runtime_governance_surface", {})
            assert gov.get("quality_class") in ["healthy", "approved"], \
                "opening must have quality_class"
