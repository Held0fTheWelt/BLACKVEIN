"""Phase 6B-4 — Post-migration legacy fallback / consumer inventory proofs.

After Phase 6B-3A (F1 lazy reorder + F21/F22 W5-first reads), Phase 6B-3B
(F8/F18/F19/F20 narrator strict migration behind ``W5_AST_NARRATOR_STRICT_
ENABLED``, default-off), and Phase 6B-3C (F11 NPC planner W5-first under
default-on with ``effective_npc_context_bundle=None``), Phase 6B-4 produces a
*fresh* legacy-consumer inventory and re-classifies every remaining branch
under the new taxonomy:

  - ``still_needed_explicit_opt_out`` — branch fires only when an operator
    explicitly sets ``W5_AST_*=0/false/no/off``.
  - ``still_needed_malformed_w5_safety`` — branch fires only when the W5
    snapshot is missing/malformed for the consumer.
  - ``still_needed_old_payload_compatibility`` — branch fires only on legacy
    sessions without a W5 wire-in (no ``w5_latest_snapshot`` in state).
  - ``still_needed_public_client_compatibility`` — branch fires because a
    public WS/frontend payload contract still names the legacy field.
  - ``substrate_keep_future_adr`` — substrate writer/reader. Consolidation
    deferred to a future ADR.
  - ``w5_first_migrated_keep_temporarily`` — Phase 6B-3 migrated the call
    site; the legacy helper/branch is preserved as the O / M / L safety net.
  - ``newly_dead_candidate_for_6b5`` — Phase 6B-4 conclusion: **none**.
  - ``needs_dedicated_adr_before_removal`` — narrator strict permanent flip,
    player-shell ``current_room_id``, WS ``viewer_room_id``,
    ``narrator_consequence_contracts.current_area`` / sensory engine.
  - ``test_only_update`` / ``doc_only_update`` / ``unknown_needs_runtime_trace``.

These tests prove the reachability classifications. They do not introduce any
new runtime behavior, do not remove any legacy branch, do not change the
default value of any W5 flag, and do not mutate any committed event or
committed output. Actor Lane authority, Commit/Readiness, ``validation_
outcome``, the Canonical Path, ADR-0033, ADR-0061, ADR-0063, and W5
validation semantics are unchanged. How remains first-class. Inferred Why
remains soft truth.
"""

from __future__ import annotations

from typing import Any

import pytest

from ai_stack.actor_tracking import (
    W5ActorSituation,
    W5ActorType,
    W5Dimension,
    W5Fact,
    W5FactStatus,
    W5FreshnessStatus,
    W5Snapshot,
    W5Source,
    W5TruthLevel,
    W5VisibilityScope,
)
from ai_stack.actor_tracking.diagnostics import w5_projection_flag_states


W5_FLAGS = (
    "W5_AST_DIRECTOR_PROJECTION_ENABLED",
    "W5_AST_NARRATOR_PROJECTION_ENABLED",
    "W5_AST_NPC_PROJECTION_ENABLED",
    "W5_AST_VALIDATION_ENABLED",
    "W5_AST_FRONTEND_PLAYER_VIEW_ENABLED",
    "W5_AST_NARRATOR_STRICT_ENABLED",
)


@pytest.fixture(autouse=True)
def _isolate_w5_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in W5_FLAGS:
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------------------
# Snapshot fixture builder (re-uses the Phase 6B-2/6B-3A/6B-3C shape).
# ---------------------------------------------------------------------------


def _fact(
    *,
    fact_id: str,
    actor_id: str,
    dimension: W5Dimension,
    key: str,
    value: object,
    source: W5Source = W5Source.PARTICIPANT_STATE_MOVE,
    truth: W5TruthLevel = W5TruthLevel.OBSERVED,
    visibility: W5VisibilityScope = W5VisibilityScope.PUBLIC,
    turn: int = 4,
) -> W5Fact:
    return W5Fact(
        fact_id=fact_id,
        actor_id=actor_id,
        dimension=dimension,
        key=key,
        value=value,
        source=source,
        truth_level=truth,
        valid_from_turn=turn,
        last_confirmed_turn=turn,
        visibility=visibility,
        status=W5FactStatus.ACTIVE,
    )


def _situation(
    actor_id: str,
    *,
    location: str,
    actor_type: W5ActorType,
    turn: int = 4,
) -> W5ActorSituation:
    return W5ActorSituation(
        actor_id=actor_id,
        actor_type=actor_type,
        actor_role_in_scene="primary",
        involvement_type="primary",
        where=(
            _fact(
                fact_id=f"w5f_{actor_id}_where",
                actor_id=actor_id,
                dimension=W5Dimension.WHERE,
                key="scene_location",
                value=location,
                turn=turn,
            ),
        ),
        what=(
            _fact(
                fact_id=f"w5f_{actor_id}_what",
                actor_id=actor_id,
                dimension=W5Dimension.WHAT,
                key="current_action",
                value="speaks",
                source=W5Source.COMMITTED_ACTION,
                turn=turn,
            ),
        ),
        how=(
            _fact(
                fact_id=f"w5f_{actor_id}_how",
                actor_id=actor_id,
                dimension=W5Dimension.HOW,
                key="tone",
                value="firm",
                source=W5Source.COMMITTED_ACTION,
                turn=turn,
            ),
        ),
        why=(),
        freshness_status=W5FreshnessStatus.FRESH,
        last_confirmed_turn=turn,
    )


def _snapshot_two_actors(turn: int = 4) -> W5Snapshot:
    return W5Snapshot(
        snapshot_id=f"w5s_phase_6b4_{turn}",
        story_session_id="sess_phase_6b4",
        turn_number=turn,
        created_at=f"w5:turn:{turn}",
        actors={
            "veronique": _situation(
                "veronique", location="parlor", actor_type=W5ActorType.HUMAN, turn=turn
            ),
            "michel": _situation(
                "michel", location="parlor", actor_type=W5ActorType.NPC, turn=turn
            ),
        },
    )


def _runtime_public():
    from ai_stack.langgraph.runtime_executor import public as runtime_public

    return runtime_public


# ===========================================================================
# F1 lazy reorder — proves default-on NO longer eager-runs legacy baseline.
# ===========================================================================


class TestF1DefaultOnDoesNotEagerRunLegacyBaseline:
    """Phase 6B-4 classification: ``w5_first_migrated_keep_temporarily``.

    Under default-on the eager pre-computation that Phase 6B-3A removed must
    not return. The W5-success branch must produce a completion whose
    ``source`` reflects the W5-derived inputs (not the raw substrate). The
    legacy helper is still reachable on O / M / L and must be preserved.
    """

    def test_f1_default_on_W5_success_source_is_w5_projection_with_actor_lane_fallback(
        self,
    ) -> None:
        pub = _runtime_public()
        assert pub.w5_ast_director_projection_enabled() is True

        payload = pub.complete_actor_locations_for_gathering_with_optional_w5_projection(
            actor_locations={"veronique": "parlor"},
            actor_lane_context={
                "ai_allowed_actor_ids": ["michel"],
                "human_actor_id": "veronique",
            },
            current_step_scene_id="scene_1",
            selected_human_actor_id="veronique",
            free_player_action_resolution=None,
            environment_current_room_id="parlor",
            w5_latest_snapshot=_snapshot_two_actors().to_dict(),
        )

        completion = payload["location_completion"]
        diagnostics = payload["diagnostics"]
        # The W5-success path produces the W5-source classification, proving
        # F1 has not silently regressed to the pre-Phase-6B-3A eager
        # baseline (the eager path tagged source =
        # "environment_state_with_actor_lane_fallback").
        assert completion["source"] == "w5_projection_with_actor_lane_fallback"
        assert diagnostics["derived_actor_locations_source"] == "w5_projection"
        assert diagnostics["gathering_pause_source"] == "w5_projection"
        # The W5 projection payload is present on D — proves the W5 branch
        # is the one that ran.
        assert payload["w5_projection"] is not None

    def test_f1_opt_out_branch_still_uses_baseline_completion(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Phase 6B-4 still_needed_explicit_opt_out: explicit opt-out reverts
        to the legacy baseline path exactly as before Phase 6B-3A."""

        monkeypatch.setenv("W5_AST_DIRECTOR_PROJECTION_ENABLED", "0")
        pub = _runtime_public()

        payload = pub.complete_actor_locations_for_gathering_with_optional_w5_projection(
            actor_locations={"veronique": "parlor"},
            actor_lane_context={
                "ai_allowed_actor_ids": ["michel"],
                "human_actor_id": "veronique",
            },
            current_step_scene_id="scene_1",
            selected_human_actor_id="veronique",
            environment_current_room_id="parlor",
            w5_latest_snapshot=_snapshot_two_actors().to_dict(),
        )
        completion = payload["location_completion"]
        assert completion["source"] == "environment_state_with_actor_lane_fallback"
        assert payload["diagnostics"] == {}
        assert payload["w5_projection"] is None

    def test_f1_malformed_w5_branch_still_uses_baseline_completion(self) -> None:
        """Phase 6B-4 still_needed_malformed_w5_safety: missing W5 snapshot
        under default-on still returns the legacy baseline with the
        ``w5_director_projection_failed`` diagnostic."""

        pub = _runtime_public()
        payload = pub.complete_actor_locations_for_gathering_with_optional_w5_projection(
            actor_locations={"veronique": "parlor"},
            actor_lane_context={
                "ai_allowed_actor_ids": ["michel"],
                "human_actor_id": "veronique",
            },
            current_step_scene_id="scene_1",
            selected_human_actor_id="veronique",
            environment_current_room_id="parlor",
            w5_latest_snapshot=None,
        )
        completion = payload["location_completion"]
        diagnostics = payload["diagnostics"]
        assert completion["source"] == "environment_state_with_actor_lane_fallback"
        assert diagnostics["w5_director_projection_used"] is False
        assert diagnostics["w5_director_projection_failed"]
        assert diagnostics["derived_actor_locations_source"] == "baseline_completion"
        assert diagnostics["gathering_pause_source"] == "baseline_completion"


# ===========================================================================
# F21 / F22 — proves W5-first read path is primary under default-on.
# ===========================================================================


class TestF21F22DefaultOnRemainsW5First:
    """Phase 6B-4 classification: ``w5_first_migrated_keep_temporarily``.

    The four-way classification stays exactly as Phase 6B-3A specified —
    Phase 6B-4 introduces no behavioral change. These tests pin the
    reachability matrix one more time so the inventory doc's classification
    table cannot regress silently.
    """

    def test_f21_default_on_with_snapshot_classifies_as_w5_projection(self) -> None:
        pub = _runtime_public()
        resolution = pub.resolve_w5_first_actor_locations(
            legacy_actor_locations={"veronique": "legacy_room"},
            w5_latest_snapshot=_snapshot_two_actors().to_dict(),
        )
        assert resolution["source"] == "w5_projection"
        assert resolution["actor_locations"] == {
            "veronique": "parlor",
            "michel": "parlor",
        }
        assert resolution["failure_reason"] is None
        assert resolution["w5_snapshot_id"] is not None

    def test_f21_explicit_opt_out_classifies_as_explicit_opt_out_legacy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_DIRECTOR_PROJECTION_ENABLED", "0")
        pub = _runtime_public()
        resolution = pub.resolve_w5_first_actor_locations(
            legacy_actor_locations={"veronique": "legacy_room"},
            w5_latest_snapshot=_snapshot_two_actors().to_dict(),
        )
        assert resolution["source"] == "explicit_opt_out_legacy"
        assert resolution["actor_locations"] == {"veronique": "legacy_room"}
        assert resolution["failure_reason"] is None
        assert resolution["w5_snapshot_id"] is None

    def test_f22_malformed_w5_classifies_as_malformed_w5_fallback(self) -> None:
        pub = _runtime_public()
        resolution = pub.resolve_w5_first_actor_locations(
            legacy_actor_locations={"veronique": "legacy_room"},
            # Snapshot present but malformed (empty actors → projection
            # raises ``w5_projection_missing_actor_locations``).
            w5_latest_snapshot={"snapshot_id": "w5s_malformed"},
        )
        assert resolution["source"] == "malformed_w5_fallback"
        assert resolution["actor_locations"] == {"veronique": "legacy_room"}
        assert resolution["failure_reason"]

    def test_f22_old_payload_classifies_as_old_payload_legacy(self) -> None:
        pub = _runtime_public()
        resolution = pub.resolve_w5_first_actor_locations(
            legacy_actor_locations={"veronique": "legacy_room"},
            w5_latest_snapshot=None,
        )
        assert resolution["source"] == "old_payload_legacy"
        assert resolution["actor_locations"] == {"veronique": "legacy_room"}
        assert resolution["failure_reason"] is None


# ===========================================================================
# F8 / F18 / F19 / F20 — narrator strict (Phase 6B-3B). Default config
# (strict-OFF) keeps the legacy transition surface first-class; strict-ON
# demotes it.
# ===========================================================================


class TestF8F18F19F20NarratorStrictDefaultOffKeepsLegacyFirstClass:
    """Phase 6B-4 classification: ``w5_first_migrated_keep_temporarily``
    + ``needs_dedicated_adr_before_removal``.

    The default configuration (``W5_AST_NARRATOR_STRICT_ENABLED`` unset /
    explicit-off) preserves the Phase 6B-3A behavior: the legacy
    ``transition_from_previous`` block is written as first-class narrator
    situation input, and the prompt still names it as a fallback. Removal
    requires a separate ADR that flips strict-on permanently AND rewrites
    parity tests in lockstep.
    """

    def test_strict_resolver_default_off(self) -> None:
        from ai_stack.actor_tracking import w5_ast_narrator_strict_enabled

        assert w5_ast_narrator_strict_enabled() is False

    def test_projection_flag_states_includes_narrator_strict_false_default(
        self,
    ) -> None:
        states = w5_projection_flag_states()
        assert states["narrator_strict"] is False

    def test_strict_on_demotes_transition_from_previous_to_legacy_compat(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the strict flag is opt-in enabled the legacy block must be
        demoted into ``source_facts._legacy_compat`` so admin parity can still
        inspect it. Phase 6B-4 does NOT delete this branch — it is kept as the
        debug breadcrumb until the strict flag is permanently flipped on."""

        from ai_stack.story_runtime.narrator import god_of_carnage_narrator_path

        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "1")
        # _block lives in the narrator path module's private API. We
        # construct a minimal step + beat shape just to exercise the
        # _legacy_compat demotion. The narrator path tests
        # (test_god_of_carnage_narrator_path.py) cover the full block-shape
        # contract.
        step = {
            "id": "step_x",
            "sequence": 0,
            "location_ref": "parlor",
            "scene_anchor": {"scene_id": "scene_1"},
            "mandatory_beats": [{"id": "beat_open"}],
        }
        block = god_of_carnage_narrator_path._block(
            index=1,
            text="x",
            beat="opening_observation",
            step=step,
            mandatory_beat={"id": "beat_open"},
            previous_step=None,
        )
        source_facts = block["source_facts"]
        assert "transition_from_previous" not in source_facts
        legacy_compat = source_facts.get("_legacy_compat")
        assert isinstance(legacy_compat, dict)
        assert "transition_from_previous" in legacy_compat
        assert legacy_compat.get("authority") == "w5_projection"

    def test_strict_off_keeps_transition_from_previous_first_class(self) -> None:
        from ai_stack.story_runtime.narrator import god_of_carnage_narrator_path

        step = {
            "id": "step_x",
            "sequence": 0,
            "location_ref": "parlor",
            "scene_anchor": {"scene_id": "scene_1"},
            "mandatory_beats": [{"id": "beat_open"}],
        }
        block = god_of_carnage_narrator_path._block(
            index=1,
            text="x",
            beat="opening_observation",
            step=step,
            mandatory_beat={"id": "beat_open"},
            previous_step=None,
        )
        source_facts = block["source_facts"]
        assert "transition_from_previous" in source_facts
        # Under default the legacy_compat surface is absent.
        assert "_legacy_compat" not in source_facts


# ===========================================================================
# F11 — NPC planner default-on yields effective_npc_context_bundle=None.
# ===========================================================================


class TestF11NpcDefaultOnReturnsNoneBundle:
    """Phase 6B-4 classification: ``w5_first_migrated_keep_temporarily``.

    Under default-on with at least one usable W5 NPC projection, the resolver
    must return ``effective_npc_context_bundle=None`` so the planner does not
    receive the legacy bundle as a primary substrate. The legacy bundle is
    forwarded verbatim on O / M / L — those branches remain the safety net.
    """

    def test_f11_default_on_resolver_returns_none_bundle_under_w5_projection(
        self,
    ) -> None:
        pub = _runtime_public()
        legacy_bundle = {"retrieval_plan": {"allowed_memory_lanes": ["public"]}}
        resolution = pub.resolve_w5_first_npc_context(
            npc_context_bundle=legacy_bundle,
            npc_w5_projection_diagnostics=[
                {
                    "w5_npc_projection_used": True,
                    "w5_npc_projection_failed": None,
                    "npc_actor_id": "michel",
                    "npc_projection_source": "w5_projection",
                }
            ],
        )
        assert resolution["npc_context_source"] == "w5_projection"
        assert resolution["effective_npc_context_bundle"] is None
        assert resolution["legacy_compat_npc_context_bundle"] == legacy_bundle
        assert resolution["npc_context_legacy_compat_visible"] is True

    def test_f11_explicit_opt_out_still_forwards_legacy_bundle(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NPC_PROJECTION_ENABLED", "0")
        pub = _runtime_public()
        legacy_bundle = {"retrieval_plan": {"allowed_memory_lanes": ["public"]}}
        resolution = pub.resolve_w5_first_npc_context(
            npc_context_bundle=legacy_bundle,
            npc_w5_projection_diagnostics=None,
        )
        assert resolution["npc_context_source"] == "explicit_opt_out_legacy"
        assert resolution["effective_npc_context_bundle"] == legacy_bundle
        assert resolution["legacy_compat_npc_context_bundle"] is None
        assert resolution["npc_context_legacy_compat_visible"] is False

    def test_f11_malformed_w5_still_forwards_legacy_bundle(self) -> None:
        pub = _runtime_public()
        legacy_bundle = {"retrieval_plan": {"allowed_memory_lanes": ["public"]}}
        resolution = pub.resolve_w5_first_npc_context(
            npc_context_bundle=legacy_bundle,
            npc_w5_projection_diagnostics=[
                {
                    "w5_npc_projection_used": False,
                    "w5_npc_projection_failed": "malformed_w5_snapshot",
                    "npc_actor_id": "michel",
                    "npc_projection_source": "actor_lane_context",
                }
            ],
        )
        assert resolution["npc_context_source"] == "malformed_w5_fallback"
        assert resolution["effective_npc_context_bundle"] == legacy_bundle
        assert resolution["legacy_compat_npc_context_bundle"] is None

    def test_f11_old_payload_still_forwards_legacy_bundle(self) -> None:
        pub = _runtime_public()
        legacy_bundle = {"retrieval_plan": {"allowed_memory_lanes": ["public"]}}
        resolution = pub.resolve_w5_first_npc_context(
            npc_context_bundle=legacy_bundle,
            npc_w5_projection_diagnostics=[
                {
                    "w5_npc_projection_used": False,
                    "w5_npc_projection_failed": "missing_w5_latest_snapshot",
                    "npc_actor_id": "michel",
                    "npc_projection_source": "actor_lane_context",
                }
            ],
        )
        assert resolution["npc_context_source"] == "old_payload_legacy"
        assert resolution["effective_npc_context_bundle"] == legacy_bundle
        assert resolution["legacy_compat_npc_context_bundle"] is None


# ===========================================================================
# Inventory ↔ script consistency. The inventory script's Phase 6B-4
# classification table must agree with the closed taxonomy listed in
# PHASE_6B4_TAXONOMY. This protects the doc/script from drifting apart.
# ===========================================================================


class TestPhase6B4InventoryScriptConsistency:
    def _load_script_module(self) -> Any:
        import importlib.util
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        script_path = repo_root / "scripts" / "inventory_w5_legacy_consumers.py"
        spec = importlib.util.spec_from_file_location(
            "inventory_w5_legacy_consumers_phase_6b4", script_path
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules["inventory_w5_legacy_consumers_phase_6b4"] = module
        spec.loader.exec_module(module)
        return module

    def test_phase_6b4_classification_present_for_every_surface(self) -> None:
        module = self._load_script_module()
        legacy_keys = {key for key, _ in module.LEGACY_SURFACES}
        classified_keys = set(module.PHASE_6B4_CLASSIFICATION.keys())
        missing = legacy_keys - classified_keys
        assert not missing, (
            "Phase 6B-4 classification is missing entries for surfaces: "
            f"{sorted(missing)}"
        )

    def test_phase_6b4_taxonomy_includes_newly_dead_candidate_for_6b5(
        self,
    ) -> None:
        """Phase 6B-4 conclusion is that no surface is a newly-dead candidate.
        The taxonomy still has to *contain* the candidate label so Phase 6B-5
        can promote a finding into it if a future inventory pass identifies a
        genuinely unreachable branch."""

        module = self._load_script_module()
        assert "newly_dead_candidate_for_6b5" in module.PHASE_6B4_TAXONOMY
        # The Phase 6B-4 conclusion: no surface in the current label table
        # falls into newly_dead_candidate_for_6b5 (every surface in
        # PHASE_6B4_CLASSIFICATION fires on at least one of D/O/M/L or is
        # substrate/test/doc only).
        labels = " || ".join(module.PHASE_6B4_CLASSIFICATION.values())
        assert "newly_dead_candidate_for_6b5" not in labels

    def test_phase_6b4_taxonomy_lists_required_labels(self) -> None:
        module = self._load_script_module()
        required = {
            "still_needed_explicit_opt_out",
            "still_needed_malformed_w5_safety",
            "still_needed_old_payload_compatibility",
            "still_needed_public_client_compatibility",
            "substrate_keep_future_adr",
            "w5_first_migrated_keep_temporarily",
            "newly_dead_candidate_for_6b5",
            "needs_dedicated_adr_before_removal",
            "test_only_update",
            "doc_only_update",
            "unknown_needs_runtime_trace",
        }
        present = set(module.PHASE_6B4_TAXONOMY)
        missing = required - present
        assert not missing, f"Phase 6B-4 taxonomy is missing labels: {sorted(missing)}"

    def test_inventory_script_main_remains_non_failing(self) -> None:
        import io
        from contextlib import redirect_stdout

        module = self._load_script_module()
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = module.main(["--root", str(_repo_root_for_test()), "--json"])
        assert rc == 0


def _repo_root_for_test() -> str:
    from pathlib import Path

    return str(Path(__file__).resolve().parents[2])
