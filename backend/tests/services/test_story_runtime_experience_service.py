"""Tests for story_runtime_experience_service (DB-backed persistence + truth surface).

Proves that:
* defaults seed on baseline,
* update path normalizes, validates, and persists,
* resolved-runtime-config payload carries the section,
* admin truth surface reports degradation markers rather than claiming full
  support when the runtime caps the mode.
"""
from __future__ import annotations

import pytest

from app.services.governance_runtime_service import (
    build_resolved_runtime_config,
    ensure_governance_baseline,
)
from app.services.story_runtime_experience_service import (
    build_story_runtime_experience_truth_surface,
    get_story_runtime_experience_settings,
    seed_default_story_runtime_experience,
    update_story_runtime_experience_settings,
)


def test_baseline_seeds_defaults(app):
    with app.app_context():
        ensure_governance_baseline()
        settings = get_story_runtime_experience_settings()
        assert settings["experience_mode"] == "turn_based_narrative_recap"
        assert settings["delivery_profile"] == "classic_recap"
        assert settings["max_scene_pulses_per_response"] == 1


def test_seed_is_idempotent(app):
    with app.app_context():
        first = seed_default_story_runtime_experience(actor="system")
        second = seed_default_story_runtime_experience(actor="system")
        assert first == second


def test_update_path_normalizes_and_persists(app):
    with app.app_context():
        ensure_governance_baseline()
        result = update_story_runtime_experience_settings(
            {
                "experience_mode": "dramatic_turn",
                "delivery_profile": "lean_dramatic",
                "prose_density": "HIGH",
                "max_scene_pulses_per_response": "2",
            },
            actor="tester",
        )
        assert result["settings"]["experience_mode"] == "dramatic_turn"
        assert result["settings"]["prose_density"] == "high"
        assert result["settings"]["max_scene_pulses_per_response"] == 2

        # Round-trip through the service.
        reloaded = get_story_runtime_experience_settings()
        assert reloaded["experience_mode"] == "dramatic_turn"


def test_update_returns_warnings_for_misleading_live_combo(app):
    with app.app_context():
        ensure_governance_baseline()
        result = update_story_runtime_experience_settings(
            {
                "experience_mode": "live_dramatic_scene_simulator",
                "max_scene_pulses_per_response": 1,
                "inter_npc_exchange_intensity": "off",
            },
            actor="tester",
        )
        assert result["warnings"], "live + 1 pulse + no exchange should produce warnings"


def test_admin_truth_surface_reports_degradation_for_live(app):
    with app.app_context():
        ensure_governance_baseline()
        update_story_runtime_experience_settings(
            {"experience_mode": "live_dramatic_scene_simulator"},
            actor="tester",
        )
        truth = build_story_runtime_experience_truth_surface()
        # Live mode is truthfully marked partial — the admin UI cannot claim
        # full honor when the runtime only has the foundation.
        assert truth["experience_mode_honored_fully"] is False
        assert any(
            m["marker"] == "live_simulator_partial_foundation"
            for m in truth["degradation_markers"]
        )


def test_resolved_runtime_config_carries_story_runtime_experience_section(app):
    with app.app_context():
        ensure_governance_baseline()
        resolved = build_resolved_runtime_config(persist_snapshot=False, actor="tester")
        assert "story_runtime_experience" in resolved
        section = resolved["story_runtime_experience"]
        assert "configured" in section
        assert "effective" in section
        assert "degradation_markers" in section
        assert section["packaging_contract_version"]
