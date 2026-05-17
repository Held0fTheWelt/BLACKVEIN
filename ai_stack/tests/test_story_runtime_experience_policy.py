"""Story Runtime Experience policy extraction regressions."""

from __future__ import annotations

from ai_stack.story_runtime_experience import extract_policy_from_resolved_config


def test_extract_policy_reads_backend_truth_surface_wrapper():
    policy = extract_policy_from_resolved_config(
        {
            "story_runtime_experience": {
                "configured": {
                    "experience_mode": "live_dramatic_scene_simulator",
                    "delivery_profile": "cinematic_live",
                    "inter_npc_exchange_intensity": "strong",
                    "max_scene_pulses_per_response": 3,
                },
                "effective": {
                    "experience_mode": "live_dramatic_scene_simulator",
                    "delivery_profile": "cinematic_live",
                    "inter_npc_exchange_intensity": "strong",
                    "max_scene_pulses_per_response": 3,
                },
                "degradation_markers": [
                    {
                        "marker": "live_simulator_partial_foundation",
                        "reason": "partial foundation is declared truthfully",
                    }
                ],
                "packaging_contract_version": "1.0",
                "config_version": "1.2",
            }
        }
    )

    assert policy.effective["experience_mode"] == "live_dramatic_scene_simulator"
    assert policy.effective["delivery_profile"] == "cinematic_live"
    assert policy.effective["inter_npc_exchange_intensity"] == "strong"
    assert policy.effective["max_scene_pulses_per_response"] == 3
    assert policy.degradation_markers == [
        {
            "marker": "live_simulator_partial_foundation",
            "reason": "partial foundation is declared truthfully",
        }
    ]

