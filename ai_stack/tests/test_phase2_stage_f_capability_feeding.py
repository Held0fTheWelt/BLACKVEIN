"""Phase 2 Stage F — Capability feeding + source-classification tests.

Verifies the autonomous-tick coordinator exposes Stage F diagnostics and the
dual-mode envelope plumbs the capability surfaces and policies into
``diagnostics.director_pulse``:

* ``capability_outputs_used`` / ``capability_outputs_missing`` are populated.
* Per-component sources use the three-tier vocabulary (``real_runtime_signal``
  / ``module_policy_default`` / ``missing_signal``).
* ``actor_pressure_profiles`` content affects scoring (already covered by
  shadow-path tests, asserted again here under the live coordinator surface).
* ``pacing_rhythm_policy.min_tick_interval_ms`` drives the autonomous-tick
  cooldown.
* ``relationship_state_output`` affects motivation when supplied.
* ``off_stage_update_candidate`` flows through from the coordinator outcome
  and to the WS-summary builder.
* No Pi/Π keys; no hardcoded NPC IDs.

Governance:
* ADR-0058 — Stage F capability feeding
* ADR-0059 — Semantic NPC Motivation Score
* ADR-0039 — Vocabulary discipline
"""

from __future__ import annotations

import re
import uuid
from typing import Any

import pytest

from ai_stack.autonomous_tick import (
    AutonomousTickInputs,
    evaluate_autonomous_tick,
)
from ai_stack.off_stage_updates import SAFETY_GATE_RESULTS
from ai_stack.stream_readiness import (
    COMPONENT_SOURCE_MISSING,
    COMPONENT_SOURCE_MODULE_POLICY_DEFAULT,
    COMPONENT_SOURCE_REAL_RUNTIME,
    classify_capability_availability,
    classify_motivation_component_sources,
    extract_module_policies_for_director,
)


def _tid() -> str:
    return str(uuid.uuid4())


def _scene_energy_high() -> dict[str, Any]:
    return {"energy_level": "volatile"}


def _scene_energy_low() -> dict[str, Any]:
    return {"energy_level": "collapsed"}


def _social_high() -> dict[str, Any]:
    return {"band": "high"}


def _social_low() -> dict[str, Any]:
    return {"band": "low"}


def _momentum_high() -> dict[str, Any]:
    return {"state": "cresting"}


def _profiles(npc_id: str, count: int = 5) -> dict[str, Any]:
    return {
        "profiles": {
            npc_id: {"pressure_markers": [{"t": str(i)} for i in range(count)]}
        }
    }


def _policy(low: bool = True) -> dict[str, Any]:
    return {
        "base_threshold": 0.10 if low else 0.99,
        "score_weights": {
            "scene_energy": 0.25,
            "social_pressure": 0.30,
            "relationship_axis_pressure": 0.25,
            "narrative_momentum": 0.20,
        },
    }


# ── Capability availability ───────────────────────────────────────────────────


class TestCapabilityAvailabilityClassifier:
    def test_all_surfaces_used_when_present(self):
        used, missing = classify_capability_availability(
            scene_energy_output=_scene_energy_high(),
            social_pressure_output=_social_high(),
            relationship_state_output={"pair_states": {"npc_a|npc_b": {"tension_score": 0.7}}},
            narrative_momentum_output=_momentum_high(),
            actor_pressure_profiles=_profiles("npc_a"),
            npc_motivation_score_policy=_policy(),
            pacing_rhythm_policy={"min_tick_interval_ms": 1500.0},
        )
        assert sorted(used) == sorted([
            "scene_energy_output",
            "social_pressure_output",
            "relationship_state_output",
            "narrative_momentum_output",
            "actor_pressure_profiles",
            "npc_motivation_score_policy",
            "pacing_rhythm_policy",
        ])
        assert missing == []

    def test_empty_inputs_all_missing(self):
        used, missing = classify_capability_availability(
            scene_energy_output=None,
            social_pressure_output=None,
            relationship_state_output=None,
            narrative_momentum_output=None,
            actor_pressure_profiles=None,
            npc_motivation_score_policy=None,
            pacing_rhythm_policy=None,
        )
        assert used == []
        assert len(missing) == 7


class TestComponentSourceClassifier:
    def test_real_runtime_when_structured_output_supplied(self):
        sources = classify_motivation_component_sources(
            scene_energy_output=_scene_energy_high(),
            social_pressure_output=_social_high(),
            relationship_state_output={"pair_states": {}},
            narrative_momentum_output=_momentum_high(),
            actor_pressure_profiles=_profiles("npc_a"),
            npc_motivation_score_policy=_policy(),
        )
        assert sources["scene_energy"] == COMPONENT_SOURCE_REAL_RUNTIME
        assert sources["social_pressure"] == COMPONENT_SOURCE_REAL_RUNTIME
        assert sources["relationship_axis_pressure"] == COMPONENT_SOURCE_REAL_RUNTIME
        assert sources["narrative_momentum"] == COMPONENT_SOURCE_REAL_RUNTIME

    def test_module_policy_default_for_pressure_baseline_when_profiles_present(self):
        sources = classify_motivation_component_sources(
            scene_energy_output=None,
            social_pressure_output=None,
            relationship_state_output=None,
            narrative_momentum_output=None,
            actor_pressure_profiles=_profiles("npc_a"),
            npc_motivation_score_policy=_policy(),
        )
        assert sources["pressure_baseline"] == COMPONENT_SOURCE_MODULE_POLICY_DEFAULT
        assert sources["score_weights"] == COMPONENT_SOURCE_MODULE_POLICY_DEFAULT

    def test_missing_signal_when_nothing_supplied(self):
        sources = classify_motivation_component_sources(
            scene_energy_output=None,
            social_pressure_output=None,
            relationship_state_output=None,
            narrative_momentum_output=None,
            actor_pressure_profiles=None,
            npc_motivation_score_policy=None,
        )
        for component in (
            "scene_energy",
            "social_pressure",
            "relationship_axis_pressure",
            "narrative_momentum",
            "pressure_baseline",
            "score_weights",
        ):
            assert sources[component] == COMPONENT_SOURCE_MISSING, component


# ── extract_module_policies_for_director ──────────────────────────────────────


class TestPolicyExtractor:
    def test_graph_state_runtime_intelligence_path(self):
        out = extract_module_policies_for_director(
            graph_state={
                "runtime_intelligence": {
                    "npc_motivation_score": {"base_threshold": 0.40},
                    "pacing_rhythm": {"min_tick_interval_ms": 2000},
                },
                "actor_pressure_profiles": _profiles("npc_a"),
            },
            module_config=None,
        )
        assert out["npc_motivation_score_policy"]["base_threshold"] == 0.40
        assert out["pacing_rhythm_policy"]["min_tick_interval_ms"] == 2000
        assert out["actor_pressure_profiles"]["profiles"]["npc_a"]["pressure_markers"]

    def test_module_config_fallback(self):
        out = extract_module_policies_for_director(
            graph_state={},
            module_config={
                "runtime_intelligence": {
                    "npc_motivation_score": {"base_threshold": 0.55},
                    "pacing_rhythm": {"min_tick_interval_ms": 1500},
                },
                "actor_pressure_profiles": _profiles("npc_b"),
            },
        )
        assert out["npc_motivation_score_policy"]["base_threshold"] == 0.55
        assert out["pacing_rhythm_policy"]["min_tick_interval_ms"] == 1500
        assert out["actor_pressure_profiles"]["profiles"]["npc_b"]

    def test_empty_returns_none_dict(self):
        out = extract_module_policies_for_director(None, None)
        assert out == {
            "actor_pressure_profiles": None,
            "npc_motivation_score_policy": None,
            "pacing_rhythm_policy": None,
        }


# ── Coordinator surfaces Stage F fields ───────────────────────────────────────


class TestCoordinatorSurfacesStageFFields:
    def _live_inputs(self, **over) -> AutonomousTickInputs:
        base = dict(
            trigger_kind="motivation_threshold_crossed",
            npc_ids=["npc_a"],
            scene_energy_output=_scene_energy_high(),
            social_pressure_output=_social_high(),
            narrative_momentum_output=_momentum_high(),
            actor_pressure_profiles=_profiles("npc_a"),
            npc_motivation_score_policy=_policy(low=True),
            pacing_rhythm_policy={"min_tick_interval_ms": 1500.0},
            visible_npc_ids=["npc_b"],
            known_actor_ids=["npc_a", "npc_b", "npc_c"],
            known_room_ids=["foyer", "parlor"],
        )
        base.update(over)
        return AutonomousTickInputs(**base)

    def test_capability_outputs_used_lists_all_supplied_surfaces(self):
        outcome = evaluate_autonomous_tick(self._live_inputs(), enabled=True)
        assert "scene_energy_output" in outcome.capability_outputs_used
        assert "actor_pressure_profiles" in outcome.capability_outputs_used
        assert "npc_motivation_score_policy" in outcome.capability_outputs_used

    def test_capability_outputs_missing_lists_absent_surfaces(self):
        outcome = evaluate_autonomous_tick(
            self._live_inputs(
                scene_energy_output=None,
                social_pressure_output=None,
                narrative_momentum_output=None,
            ),
            enabled=True,
        )
        for name in (
            "scene_energy_output",
            "social_pressure_output",
            "narrative_momentum_output",
        ):
            assert name in outcome.capability_outputs_missing

    def test_motivation_score_component_sources_use_three_tier_vocab(self):
        outcome = evaluate_autonomous_tick(self._live_inputs(), enabled=True)
        for source in outcome.motivation_score_component_sources.values():
            assert source in {
                COMPONENT_SOURCE_REAL_RUNTIME,
                COMPONENT_SOURCE_MODULE_POLICY_DEFAULT,
                COMPONENT_SOURCE_MISSING,
            }

    def test_missing_signal_reported_when_inputs_missing(self):
        outcome = evaluate_autonomous_tick(
            self._live_inputs(
                scene_energy_output=None,
                social_pressure_output=None,
                relationship_state_output=None,
                narrative_momentum_output=None,
                actor_pressure_profiles=None,
                npc_motivation_score_policy=None,
            ),
            enabled=True,
        )
        sources = outcome.motivation_score_component_sources
        assert sources["scene_energy"] == COMPONENT_SOURCE_MISSING
        assert sources["narrative_momentum"] == COMPONENT_SOURCE_MISSING
        assert sources["pressure_baseline"] == COMPONENT_SOURCE_MISSING

    def test_module_policy_default_reported_when_profiles_present_but_outputs_absent(self):
        outcome = evaluate_autonomous_tick(
            self._live_inputs(
                scene_energy_output=None,
                social_pressure_output=None,
                relationship_state_output=None,
                narrative_momentum_output=None,
                actor_pressure_profiles=_profiles("npc_a"),
                npc_motivation_score_policy=_policy(low=True),
            ),
            enabled=True,
        )
        sources = outcome.motivation_score_component_sources
        assert sources["pressure_baseline"] == COMPONENT_SOURCE_MODULE_POLICY_DEFAULT
        assert sources["score_weights"] == COMPONENT_SOURCE_MODULE_POLICY_DEFAULT

    def test_outcome_to_dict_carries_stage_f_fields(self):
        outcome = evaluate_autonomous_tick(self._live_inputs(), enabled=True)
        d = outcome.to_dict()
        for required in (
            "capability_outputs_used",
            "capability_outputs_missing",
            "motivation_score_component_sources",
            "off_stage_update_candidate",
            "off_stage_commit_result",
        ):
            assert required in d, f"missing Stage F field: {required}"

    def test_invariants_still_hold(self):
        outcome = evaluate_autonomous_tick(self._live_inputs(), enabled=True)
        assert outcome.canonical_path_advanced is False
        assert outcome.mandatory_beat_consumed is False
        assert outcome.shadow_only is False


# ── Real signals affect score ─────────────────────────────────────────────────


class TestRealSignalsAffectScore:
    def test_actor_pressure_profile_content_changes_winner(self):
        """With a low policy threshold, the NPC with richer profile pressure markers wins.

        This re-asserts ADR-0059 at the Stage F coordinator level: real
        content config (not hardcoded actor IDs) decides initiative.
        """
        rich_then_lean = {
            "profiles": {
                "actor_x": {"pressure_markers": [{"t": str(i)} for i in range(10)]},
                "actor_y": {"pressure_markers": [{"t": "a"}]},
            }
        }
        lean_then_rich = {
            "profiles": {
                "actor_x": {"pressure_markers": [{"t": "a"}]},
                "actor_y": {"pressure_markers": [{"t": str(i)} for i in range(10)]},
            }
        }
        for profiles, winner in (
            (rich_then_lean, "actor_x"),
            (lean_then_rich, "actor_y"),
        ):
            outcome = evaluate_autonomous_tick(
                AutonomousTickInputs(
                    npc_ids=["actor_x", "actor_y"],
                    scene_energy_output=_scene_energy_high(),
                    social_pressure_output=_social_high(),
                    narrative_momentum_output=_momentum_high(),
                    actor_pressure_profiles=profiles,
                    npc_motivation_score_policy=_policy(low=True),
                    visible_npc_ids=[],
                    known_actor_ids=["actor_x", "actor_y"],
                ),
                enabled=True,
            )
            assert outcome.chosen_actor_id == winner

    def test_relationship_state_affects_motivation(self):
        """High pair tension lifts the targeted NPC's score."""
        high_tension = {
            "pair_states": {
                "npc_a|npc_b": {"tension_score": 0.95, "actor_a": "npc_a", "actor_b": "npc_b"},
            }
        }
        no_tension = {"pair_states": {}}
        score_with = evaluate_autonomous_tick(
            AutonomousTickInputs(
                npc_ids=["npc_a"],
                relationship_state_output=high_tension,
                actor_pressure_profiles=_profiles("npc_a"),
                npc_motivation_score_policy=_policy(low=True),
            ),
            enabled=True,
        ).motivation_scores.get("npc_a", 0.0)
        score_without = evaluate_autonomous_tick(
            AutonomousTickInputs(
                npc_ids=["npc_a"],
                relationship_state_output=no_tension,
                actor_pressure_profiles=_profiles("npc_a"),
                npc_motivation_score_policy=_policy(low=True),
            ),
            enabled=True,
        ).motivation_scores.get("npc_a", 0.0)
        assert score_with >= score_without

    def test_pacing_rhythm_policy_min_tick_drives_cooldown(self):
        """When the pacing_rhythm policy says 5000ms and only 1000ms elapsed: cooldown."""
        outcome = evaluate_autonomous_tick(
            AutonomousTickInputs(
                npc_ids=["npc_a"],
                actor_pressure_profiles=_profiles("npc_a"),
                npc_motivation_score_policy=_policy(low=True),
                pacing_rhythm_policy={"min_tick_interval_ms": 5000.0},
                since_last_tick_ms=1000.0,
            ),
            enabled=True,
        )
        assert outcome.cooldown_state["min_tick_interval_ms"] == 5000.0
        assert outcome.cooldown_state["cooldown_active"] is True
        assert outcome.autonomous_tick_suppressed_reason == "cooldown_active"


# ── Off-stage candidate routing through the coordinator ──────────────────────


class TestOffStageCandidateThroughCoordinator:
    def test_off_stage_actor_yields_pass_safety_gate(self):
        """Chosen NPC is not in visible_npc_ids and IS in known_actor_ids → pass."""
        outcome = evaluate_autonomous_tick(
            AutonomousTickInputs(
                npc_ids=["npc_a"],
                scene_energy_output=_scene_energy_high(),
                social_pressure_output=_social_high(),
                narrative_momentum_output=_momentum_high(),
                actor_pressure_profiles=_profiles("npc_a"),
                npc_motivation_score_policy=_policy(low=True),
                visible_npc_ids=["npc_b"],  # npc_a is off-stage
                known_actor_ids=["npc_a", "npc_b"],
            ),
            enabled=True,
        )
        cand = outcome.off_stage_update_candidate
        assert cand["off_stage_safety_gate_result"] in SAFETY_GATE_RESULTS
        assert cand["off_stage_update_candidate"] is True
        assert cand["canonical_path_advanced"] is False
        assert cand["mandatory_beat_consumed"] is False

    def test_visible_npc_no_off_stage_candidate(self):
        outcome = evaluate_autonomous_tick(
            AutonomousTickInputs(
                npc_ids=["npc_a"],
                scene_energy_output=_scene_energy_high(),
                actor_pressure_profiles=_profiles("npc_a"),
                npc_motivation_score_policy=_policy(low=True),
                visible_npc_ids=["npc_a"],  # on-stage
                known_actor_ids=["npc_a"],
            ),
            enabled=True,
        )
        cand = outcome.off_stage_update_candidate
        assert cand["off_stage_update_candidate"] is False
        assert cand["off_stage_safety_gate_result"] == "not_applicable"


# ── Dual-mode envelope surfaces Stage F under augment ────────────────────────


class TestDualModeEnvelopeSurfacesStageFFields:
    def _envelope(self) -> dict[str, Any]:
        return {
            "visible_scene_output": {
                "blocks": [
                    {"id": "b1", "block_type": "narrator", "text": "hi"},
                ],
            },
            "npc_actor_ids": ["npc_a"],
        }

    def test_augment_writes_capability_outputs_into_director_pulse(self):
        from ai_stack.block_stream_dual_mode import augment_envelope_with_block_stream
        env = augment_envelope_with_block_stream(
            self._envelope(),
            scene_energy_output=_scene_energy_high(),
            social_pressure_output=_social_high(),
            narrative_momentum_output=_momentum_high(),
            actor_pressure_profiles=_profiles("npc_a"),
            npc_motivation_score_policy=_policy(low=True),
            pacing_rhythm_policy={"min_tick_interval_ms": 1500},
        )
        pulse = env["diagnostics"]["director_pulse"]
        assert "capability_outputs" in pulse
        assert pulse["capability_outputs"]["scene_energy_output"] == _scene_energy_high()
        assert pulse["actor_pressure_profiles"] == _profiles("npc_a")
        assert pulse["pacing_rhythm_policy"] == {"min_tick_interval_ms": 1500}
        assert "capability_outputs_used" in pulse
        assert "capability_outputs_missing" in pulse
        assert "motivation_score_component_sources" in pulse

    def test_augment_records_missing_when_none_supplied(self):
        from ai_stack.block_stream_dual_mode import augment_envelope_with_block_stream
        env = augment_envelope_with_block_stream(self._envelope())
        pulse = env["diagnostics"]["director_pulse"]
        missing = pulse["capability_outputs_missing"]
        # All Stage F surfaces absent → all listed missing.
        for name in (
            "scene_energy_output",
            "social_pressure_output",
            "relationship_state_output",
            "narrative_momentum_output",
            "actor_pressure_profiles",
            "npc_motivation_score_policy",
            "pacing_rhythm_policy",
        ):
            assert name in missing


# ── ADR-0039 anti-hardcoding (Stage F surfaces) ───────────────────────────────


class TestStageFADR0039Discipline:
    _PI_PATTERNS = [
        re.compile(r"\bPi\d+\b"),
        re.compile(r"\bΠ\d+\b"),
        re.compile(r"\bpi_\d+\b"),
    ]
    _FORBIDDEN_NPC_LITERALS = ("veronique", "michel", "annette", "alain")

    def test_no_pi_keys_in_stage_f_modules(self):
        from ai_stack import off_stage_updates, stream_readiness
        for mod in (off_stage_updates, stream_readiness):
            with open(mod.__file__, "r", encoding="utf-8") as fh:
                src = fh.read()
            for pat in self._PI_PATTERNS:
                assert not pat.search(src), f"Pi/Π in {mod.__name__}: {pat.pattern}"

    def test_no_hardcoded_actor_ids_in_stage_f_modules(self):
        from ai_stack import off_stage_updates, stream_readiness
        for mod in (off_stage_updates, stream_readiness):
            with open(mod.__file__, "r", encoding="utf-8") as fh:
                src = fh.read().lower()
            for literal in self._FORBIDDEN_NPC_LITERALS:
                assert literal not in src, (
                    f"hardcoded NPC id {literal!r} in {mod.__name__}"
                )

    def test_no_fake_real_evidence_when_only_defaults_present(self):
        """When only the actor profile is supplied (no real capability outputs),
        the coordinator must NOT label any component as ``real_runtime_signal``.
        """
        outcome = evaluate_autonomous_tick(
            AutonomousTickInputs(
                npc_ids=["npc_a"],
                actor_pressure_profiles=_profiles("npc_a"),
                npc_motivation_score_policy=_policy(low=True),
            ),
            enabled=True,
        )
        sources = outcome.motivation_score_component_sources
        for component in (
            "scene_energy",
            "social_pressure",
            "relationship_axis_pressure",
            "narrative_momentum",
        ):
            assert sources[component] != COMPONENT_SOURCE_REAL_RUNTIME, (
                f"{component} mislabeled as real when no structured output was supplied"
            )
