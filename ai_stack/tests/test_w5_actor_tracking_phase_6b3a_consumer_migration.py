"""Phase 6B-3A — Director eager-baseline lazy reorder + Executor W5-first reads.

These tests pin the semantic contract for the first sequenced consumer migration
of Phase 6B-3:

- **F1 lazy reorder** in
  ``complete_actor_locations_for_gathering_with_optional_w5_projection``.
  The eager pre-computation of ``baseline_completion`` is gone; the legacy
  completion now runs only inside the two return paths that actually need it
  (explicit-opt-out short-circuit and malformed-W5 ``except`` branch). The W5
  success branch retains its own completion call (F4 in the inventory) over
  W5-derived actor locations. Output must remain bit-for-bit identical on the
  default-on happy path (D), explicit opt-out (O), and malformed-W5 (M).

- **F21 / F22 W5-first reads** in ``executor_action_resolution_start`` /
  ``executor_action_resolution_commit``. The inline ``_pr_c_actor_locations_raw``
  read now prefers ``where_summary.derived_actor_locations`` when the W5
  projection is available; legacy substrate (``state.actor_locations`` then
  ``environment_state.actor_locations``) is retained verbatim for:

    - ``explicit_opt_out_legacy``  (``W5_AST_DIRECTOR_PROJECTION_ENABLED=0/false/no/off``)
    - ``malformed_w5_fallback``    (default-on but projection raised)
    - ``old_payload_legacy``       (default-on but no ``w5_latest_snapshot`` in state)

  The classification is exposed on ``graph_diagnostics.actor_locations_source``
  so admin diagnostics, Langfuse metadata, and downstream consumers can audit
  the read path. No committed output or committed event is mutated by this
  classification.

Nothing in this file changes Actor Lane authority, Commit/Readiness,
``validation_outcome``, the Canonical Path, ADR-0033, ADR-0061, ADR-0063, or
W5 validation semantics. How remains first-class. Inferred Why remains soft
truth.
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
from ai_stack.langgraph.runtime_executor import public as runtime_public


W5_FLAGS = (
    "W5_AST_DIRECTOR_PROJECTION_ENABLED",
    "W5_AST_NARRATOR_PROJECTION_ENABLED",
    "W5_AST_NPC_PROJECTION_ENABLED",
    "W5_AST_VALIDATION_ENABLED",
    "W5_AST_FRONTEND_PLAYER_VIEW_ENABLED",
)


@pytest.fixture(autouse=True)
def _isolate_w5_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in W5_FLAGS:
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------------------
# Snapshot fixture builder (mirrors Phase 6B-2 inventory test helpers)
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
    turn: int = 7,
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
    turn: int = 7,
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
                value="measured",
                source=W5Source.COMMITTED_ACTION,
                turn=turn,
            ),
        ),
        why=(),
        freshness_status=W5FreshnessStatus.FRESH,
        last_confirmed_turn=turn,
    )


def _snapshot(actor_locations: dict[str, str], turn: int = 7) -> W5Snapshot:
    actors: dict[str, W5ActorSituation] = {}
    for actor_id, location in actor_locations.items():
        actor_type = (
            W5ActorType.HUMAN if actor_id.startswith("human") else W5ActorType.NPC
        )
        actors[actor_id] = _situation(
            actor_id, location=location, actor_type=actor_type, turn=turn
        )
    return W5Snapshot(
        snapshot_id=f"w5s_phase_6b3a_{turn}",
        story_session_id="sess_phase_6b3a",
        turn_number=turn,
        created_at=f"w5:turn:{turn}",
        actors=actors,
    )


def _actor_lane_context() -> dict[str, Any]:
    return {
        "human_actor_id": "human_a",
        "ai_allowed_actor_ids": ["npc_x", "npc_y"],
        "actor_lanes": {
            "human_a": "human",
            "npc_x": "npc",
            "npc_y": "npc",
        },
        "selected_player_role": "human_a",
    }


# ---------------------------------------------------------------------------
# F1 — eager-baseline lazy reorder (Phase 6B-3A step 1)
# ---------------------------------------------------------------------------


class TestF1LazyReorder:
    """F1 lazy reorder must be output-identical on the three observable paths.

    The legacy function ``complete_actor_locations_for_gathering`` is still
    the single source of truth for NPC fallback completion and
    ``gathering_scene_id`` derivation — only its placement changed. These
    tests pin the bit-for-bit behavior of the public payload so a regression
    of the reorder would surface immediately.
    """

    def test_default_on_happy_path_uses_w5_projection_source_and_skips_eager_baseline(
        self,
    ) -> None:
        """D path: W5 projection wins; the legacy baseline is never assembled
        outside the W5-success branch. Diagnostics must report
        ``derived_actor_locations_source == "w5_projection"``."""

        assert runtime_public.w5_ast_director_projection_enabled() is True
        snapshot = _snapshot(
            {"human_a": "gathering_room", "npc_x": "gathering_room", "npc_y": "gathering_room"}
        )
        payload = runtime_public.complete_actor_locations_for_gathering_with_optional_w5_projection(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context=_actor_lane_context(),
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={"action_commit_policy": "commit_action"},
            environment_current_room_id="gathering_room",
            w5_latest_snapshot=snapshot.to_dict(),
        )
        completion = payload["location_completion"]
        diagnostics = payload["diagnostics"]
        assert completion["source"] == "w5_projection_with_actor_lane_fallback"
        assert diagnostics["w5_director_projection_used"] is True
        assert diagnostics["w5_director_projection_failed"] is None
        assert diagnostics["derived_actor_locations_source"] == "w5_projection"
        assert diagnostics["gathering_pause_source"] == "w5_projection"
        assert payload["w5_projection"] is not None

    def test_default_on_w5_path_actor_locations_match_baseline_call_with_same_inputs(
        self,
    ) -> None:
        """D parity: the W5 success path's actor_locations / gathering_scene_id
        equal what the legacy completion would produce given the same
        W5-derived actor_locations input. This protects the lazy reorder from
        accidentally changing the W5 success branch."""

        snapshot = _snapshot({"human_a": "gathering_room"})
        baseline = runtime_public.complete_actor_locations_for_gathering(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context=_actor_lane_context(),
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={"action_commit_policy": "commit_action"},
            environment_current_room_id="gathering_room",
        )
        w5 = runtime_public.complete_actor_locations_for_gathering_with_optional_w5_projection(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context=_actor_lane_context(),
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={"action_commit_policy": "commit_action"},
            environment_current_room_id="gathering_room",
            w5_latest_snapshot=snapshot.to_dict(),
        )
        # Same actor_locations, same gathering_scene_id, same fallback NPC IDs.
        assert (
            w5["location_completion"]["actor_locations"]
            == baseline["actor_locations"]
        )
        assert (
            w5["location_completion"]["gathering_scene_id"]
            == baseline["gathering_scene_id"]
        )
        assert (
            w5["location_completion"]["fallback_actor_ids"]
            == baseline["fallback_actor_ids"]
        )

    def test_explicit_opt_out_payload_is_bit_for_bit_identical_to_baseline_envelope(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """O path: under explicit opt-out the payload envelope must equal the
        pre-Phase-6B-3A shape:

            {
                "location_completion": <legacy baseline completion>,
                "diagnostics": {},
                "w5_projection": None,
            }

        Even with a well-formed snapshot in state the W5 branch is never
        entered."""

        monkeypatch.setenv("W5_AST_DIRECTOR_PROJECTION_ENABLED", "0")
        assert runtime_public.w5_ast_director_projection_enabled() is False

        baseline = runtime_public.complete_actor_locations_for_gathering(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context=_actor_lane_context(),
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={"action_commit_policy": "commit_action"},
            environment_current_room_id="gathering_room",
        )
        snapshot = _snapshot({"human_a": "gathering_room"})
        payload = runtime_public.complete_actor_locations_for_gathering_with_optional_w5_projection(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context=_actor_lane_context(),
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={"action_commit_policy": "commit_action"},
            environment_current_room_id="gathering_room",
            w5_latest_snapshot=snapshot.to_dict(),  # ignored under opt-out
        )
        assert payload == {
            "location_completion": baseline,
            "diagnostics": {},
            "w5_projection": None,
        }

    def test_explicit_opt_out_disabled_via_explicit_argument_matches_env_var(
        self,
    ) -> None:
        """O path via the explicit ``w5_director_projection_enabled=False``
        argument must produce the same envelope as the env-var opt-out (this
        is the path the executor passes when it materializes the flag at
        commit time)."""

        baseline = runtime_public.complete_actor_locations_for_gathering(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context=_actor_lane_context(),
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={"action_commit_policy": "commit_action"},
            environment_current_room_id="gathering_room",
        )
        payload = runtime_public.complete_actor_locations_for_gathering_with_optional_w5_projection(
            actor_locations={"human_a": "gathering_room"},
            actor_lane_context=_actor_lane_context(),
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={"action_commit_policy": "commit_action"},
            environment_current_room_id="gathering_room",
            w5_latest_snapshot={"malformed": "ignored_when_disabled"},
            w5_director_projection_enabled=False,
        )
        assert payload["location_completion"] == baseline
        assert payload["diagnostics"] == {}
        assert payload["w5_projection"] is None

    def test_malformed_w5_returns_baseline_envelope_with_failed_diagnostic(
        self,
    ) -> None:
        """M path: default-on but a missing snapshot must return the legacy
        baseline payload AND emit ``w5_director_projection_failed`` with a
        compact reason. ``derived_actor_locations_source`` /
        ``gathering_pause_source`` must stay on ``baseline_completion``."""

        payload = runtime_public.complete_actor_locations_for_gathering_with_optional_w5_projection(
            actor_locations={"human_a": "gathering_room", "npc_x": "gathering_room"},
            actor_lane_context=_actor_lane_context(),
            current_step_scene_id="gathering_room",
            selected_human_actor_id="human_a",
            free_player_action_resolution={"action_commit_policy": "commit_action"},
            environment_current_room_id="gathering_room",
            w5_latest_snapshot=None,
        )
        completion = payload["location_completion"]
        diagnostics = payload["diagnostics"]
        assert completion["source"] == "environment_state_with_actor_lane_fallback"
        assert completion["actor_locations"] == {
            "human_a": "gathering_room",
            "npc_x": "gathering_room",
            "npc_y": "gathering_room",
        }
        assert diagnostics["w5_director_projection_used"] is False
        assert diagnostics["w5_director_projection_failed"] == "missing_w5_latest_snapshot"
        assert diagnostics["derived_actor_locations_source"] == "baseline_completion"
        assert diagnostics["gathering_pause_source"] == "baseline_completion"
        assert payload["w5_projection"] is None


# ---------------------------------------------------------------------------
# F21 / F22 — resolve_w5_first_actor_locations
# ---------------------------------------------------------------------------


class TestF21F22ResolveW5FirstActorLocations:
    """``resolve_w5_first_actor_locations`` is the helper that powers the
    F21 / F22 inline reads. Pinning each of the four classification paths
    here gives the executor-side tests below a stable contract to rely on.
    """

    def test_default_on_happy_path_returns_w5_locations_and_source_w5_projection(
        self,
    ) -> None:
        snapshot = _snapshot(
            {"human_a": "gathering_room", "npc_x": "gathering_room", "npc_y": "gathering_room"}
        )
        resolution = runtime_public.resolve_w5_first_actor_locations(
            legacy_actor_locations={"human_a": "stale_legacy_room"},
            w5_latest_snapshot=snapshot.to_dict(),
        )
        assert resolution["source"] == "w5_projection"
        assert resolution["actor_locations"] == {
            "human_a": "gathering_room",
            "npc_x": "gathering_room",
            "npc_y": "gathering_room",
        }
        # The legacy stale value MUST NOT appear in the result under D.
        assert resolution["actor_locations"]["human_a"] != "stale_legacy_room"
        assert resolution["w5_snapshot_id"] == snapshot.snapshot_id
        assert resolution["failure_reason"] is None

    def test_explicit_opt_out_returns_legacy_locations_verbatim(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_DIRECTOR_PROJECTION_ENABLED", "off")
        snapshot = _snapshot({"human_a": "gathering_room"})  # ignored under opt-out
        legacy = {"human_a": "stale_legacy_room"}
        resolution = runtime_public.resolve_w5_first_actor_locations(
            legacy_actor_locations=legacy,
            w5_latest_snapshot=snapshot.to_dict(),
        )
        assert resolution["source"] == "explicit_opt_out_legacy"
        assert resolution["actor_locations"] == legacy
        # Defensive copy — never alias caller's dict.
        assert resolution["actor_locations"] is not legacy
        assert resolution["w5_snapshot_id"] is None
        assert resolution["failure_reason"] is None

    def test_malformed_w5_returns_legacy_locations_with_failure_reason(
        self,
    ) -> None:
        """Default-on with a snapshot that the Director projection refuses to
        build (missing required fields, no derivable actor_locations, or any
        other ``build_w5_projection_for_director`` failure) must fall back to
        the legacy substrate AND surface a compact, non-empty failure reason
        on the diagnostic. The exact reason text is left to the projection
        layer; the contract here is only that the source flips to
        ``malformed_w5_fallback`` and the failure reason is preserved."""

        legacy = {"human_a": "gathering_room", "npc_x": "gathering_room"}
        # Snapshot missing required ``story_session_id`` triggers the
        # ``build_w5_projection_for_director`` failure path. This stands in
        # for any malformed/missing-field scenario that fires F3 in the
        # Phase 6B-2 inventory.
        resolution = runtime_public.resolve_w5_first_actor_locations(
            legacy_actor_locations=legacy,
            w5_latest_snapshot={"snapshot_id": "w5s_malformed", "actors": {}},
        )
        assert resolution["source"] == "malformed_w5_fallback"
        assert resolution["actor_locations"] == legacy
        assert resolution["w5_snapshot_id"] is None
        # Compact, non-empty failure reason — exact text is projection-layer
        # detail and intentionally not pinned here so this test does not
        # over-specify the W5 projection's error vocabulary.
        assert isinstance(resolution["failure_reason"], str)
        assert resolution["failure_reason"].strip()

    def test_old_payload_without_snapshot_returns_legacy_locations_and_no_failure(
        self,
    ) -> None:
        legacy = {"human_a": "gathering_room", "npc_x": "gathering_room"}
        resolution = runtime_public.resolve_w5_first_actor_locations(
            legacy_actor_locations=legacy,
            w5_latest_snapshot=None,
        )
        assert resolution["source"] == "old_payload_legacy"
        assert resolution["actor_locations"] == legacy
        assert resolution["w5_snapshot_id"] is None
        # Old-payload is not a failure — there is no W5 to project.
        assert resolution["failure_reason"] is None

    def test_old_payload_with_empty_dict_snapshot_treated_as_old_payload(
        self,
    ) -> None:
        """An empty dict is functionally equivalent to ``None`` for the
        purposes of W5 projection — there is no snapshot to project."""

        legacy = {"human_a": "gathering_room"}
        resolution = runtime_public.resolve_w5_first_actor_locations(
            legacy_actor_locations=legacy,
            w5_latest_snapshot={},
        )
        assert resolution["source"] == "old_payload_legacy"
        assert resolution["actor_locations"] == legacy

    def test_explicit_argument_overrides_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the executor materializes the flag value at the call site it
        passes ``w5_director_projection_enabled=...`` explicitly; this must
        win over the environment variable so a single turn cannot observe a
        mid-flight flag flip."""

        monkeypatch.setenv("W5_AST_DIRECTOR_PROJECTION_ENABLED", "1")
        legacy = {"human_a": "gathering_room"}
        resolution = runtime_public.resolve_w5_first_actor_locations(
            legacy_actor_locations=legacy,
            w5_latest_snapshot=_snapshot({"human_a": "different_room"}).to_dict(),
            w5_director_projection_enabled=False,
        )
        assert resolution["source"] == "explicit_opt_out_legacy"
        assert resolution["actor_locations"] == legacy

    def test_legacy_actor_locations_none_is_treated_as_empty(self) -> None:
        """``None`` for the legacy substrate input must be tolerated (old
        sessions with no committed ``actor_locations`` substrate must not
        raise) and surfaces as an empty dict under opt-out / old-payload."""

        resolution = runtime_public.resolve_w5_first_actor_locations(
            legacy_actor_locations=None,
            w5_latest_snapshot=None,
        )
        assert resolution["source"] == "old_payload_legacy"
        assert resolution["actor_locations"] == {}


# ---------------------------------------------------------------------------
# F1 → F4 contract: the inner W5-success completion stays untouched.
# ---------------------------------------------------------------------------


def test_f1_lazy_reorder_preserves_f4_w5_success_completion_call() -> None:
    """Phase 6B-2 classified F4 (the W5-success-branch
    ``complete_actor_locations_for_gathering`` call) as ``substrate_keep``.
    The lazy reorder must not remove or relocate it. We pin this by
    asserting the W5-success payload carries the
    ``"w5_projection_with_actor_lane_fallback"`` source marker — that
    marker is only set when the inner completion call ran."""

    snapshot = _snapshot({"human_a": "gathering_room"})
    payload = runtime_public.complete_actor_locations_for_gathering_with_optional_w5_projection(
        actor_locations={"human_a": "gathering_room"},
        actor_lane_context=_actor_lane_context(),
        current_step_scene_id="gathering_room",
        selected_human_actor_id="human_a",
        free_player_action_resolution={"action_commit_policy": "commit_action"},
        environment_current_room_id="gathering_room",
        w5_latest_snapshot=snapshot.to_dict(),
    )
    assert payload["location_completion"]["source"] == "w5_projection_with_actor_lane_fallback"
