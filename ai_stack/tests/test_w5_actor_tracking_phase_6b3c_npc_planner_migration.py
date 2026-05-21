"""Phase 6B-3C — F11 NPC planner W5-first migration.

These tests pin the semantic contract for the third sequenced consumer
migration of Phase 6B-3:

- **F11 NPC planner W5-first migration.** NPC planning consumes ``npc_w5_situations``
  (actor-specific Phase 3B projections, ``target_consumer="npc"``) as the
  primary actor-situation authority under the default-on happy path. The
  legacy ``npc_context_bundle`` (Phase 6A inventory: ``F11``) is demoted to a
  non-authoritative ``_legacy_compat`` breadcrumb when W5 wins and is NOT
  forwarded to ``build_npc_agency_simulation`` / ``build_npc_agency_plan``.

  The legacy bundle remains forwarded verbatim under three fallback
  conditions, exactly as in pre-Phase-6B-3C behaviour:

    - ``explicit_opt_out_legacy`` — ``W5_AST_NPC_PROJECTION_ENABLED`` ∈
      ``{0, false, no, off}``.
    - ``malformed_w5_fallback`` — default-on but the per-actor W5 NPC
      projections all raised.
    - ``old_payload_legacy`` — default-on but no ``w5_latest_snapshot`` in
      graph state (pre-Phase-1 session or missing wire-in).

  The classification is exposed on each per-actor diagnostic
  (``npc_context_source`` / ``npc_context_legacy_compat_visible`` /
  ``npc_context_fallback_reason``) so admin diagnostics, Langfuse metadata,
  and downstream consumers can audit which read path the turn actually used.
  No committed event is mutated by the classification.

Nothing in this file changes Actor Lane authority, Commit/Readiness,
``validation_outcome``, the Canonical Path, ADR-0033, ADR-0061, ADR-0063, or
W5 validation semantics. How remains first-class. Inferred Why remains soft
truth. NPC privacy and actor_knowledge_scope (Phase 3B) are preserved.
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
from ai_stack.story_runtime.npc_agency.npc_agency_planner import (
    build_npc_agency_plan,
    build_npc_agency_simulation,
)


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
# Fixture helpers (mirror Phase 6B-3A / 6B-3B test scaffolding)
# ---------------------------------------------------------------------------


def _npc_fact(
    *,
    actor_id: str,
    dimension: W5Dimension,
    key: str,
    value: object,
    source: W5Source,
    truth: W5TruthLevel,
    visibility: W5VisibilityScope = W5VisibilityScope.PUBLIC,
    scope: tuple[str, ...] = (),
    turn: int = 5,
) -> W5Fact:
    return W5Fact(
        fact_id=f"w5f_{actor_id}_{dimension.value}_{key}",
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
        actor_knowledge_scope=scope,
    )


def _npc_situation(
    actor_id: str,
    *,
    location: str = "salon",
    action: str = "presses",
    tone: str = "controlled",
    motive: str = "protect_position",
    motive_visibility: W5VisibilityScope = W5VisibilityScope.PRIVATE_TO_ACTOR,
    motive_scope: tuple[str, ...] = (),
    turn: int = 5,
) -> W5ActorSituation:
    return W5ActorSituation(
        actor_id=actor_id,
        actor_type=W5ActorType.NPC,
        actor_role_in_scene="primary",
        involvement_type="primary",
        where=(
            _npc_fact(
                actor_id=actor_id,
                dimension=W5Dimension.WHERE,
                key="scene_location",
                value=location,
                source=W5Source.PARTICIPANT_STATE_MOVE,
                truth=W5TruthLevel.OBSERVED,
                turn=turn,
            ),
        ),
        what=(
            _npc_fact(
                actor_id=actor_id,
                dimension=W5Dimension.WHAT,
                key="current_action",
                value=action,
                source=W5Source.COMMITTED_ACTION,
                truth=W5TruthLevel.OBSERVED,
                turn=turn,
            ),
        ),
        how=(
            _npc_fact(
                actor_id=actor_id,
                dimension=W5Dimension.HOW,
                key="tone",
                value=tone,
                source=W5Source.COMMITTED_ACTION,
                truth=W5TruthLevel.OBSERVED,
                turn=turn,
            ),
        ),
        why=(
            _npc_fact(
                actor_id=actor_id,
                dimension=W5Dimension.WHY,
                key="motive",
                value=motive,
                source=W5Source.CHARACTER_MIND_RECORD,
                truth=W5TruthLevel.INFERRED,
                visibility=motive_visibility,
                scope=motive_scope,
                turn=turn,
            ),
        ),
        freshness_status=W5FreshnessStatus.FRESH,
        last_confirmed_turn=turn,
    )


def _npc_snapshot(*, turn: int = 5) -> W5Snapshot:
    return W5Snapshot(
        snapshot_id=f"w5s_phase_6b3c_{turn}",
        story_session_id="sess_phase_6b3c",
        turn_number=turn,
        created_at=f"w5:turn:{turn}",
        actors={
            "veronique_vallon": _npc_situation(
                "veronique_vallon",
                action="presses",
                tone="controlled",
                motive="protect_position",
                turn=turn,
            ),
            "michel_longstreet": _npc_situation(
                "michel_longstreet",
                action="counters",
                tone="dry",
                motive="deflect_blame",
                turn=turn,
            ),
        },
    )


def _legacy_npc_context_bundle() -> dict[str, Any]:
    """A canonical legacy bundle as produced by ``build_npc_context_bundle``.

    The planner reads only ``retrieval_plan.allowed_memory_lanes`` and
    ``retrieval_plan.blocked_memory_lanes`` from the bundle when it is fed
    in; the rest of the bundle is structural metadata.
    """

    return {
        "schema_version": "retrieval_context_bundle.v1",
        "role": "npc",
        "actor_id": "veronique_vallon",
        "retrieval_plan": {
            "allowed_memory_lanes": ["scene_memory", "knowledge_boundary"],
            "blocked_memory_lanes": ["agent_private_memory"],
        },
        "private_memory": {"redacted_private_memory_excerpt": "never_in_evidence"},
        "relationship_memory": {},
        "knowledge_boundary": {},
        "scene_function": "escalate_conflict",
        "continuity_constraints": [],
    }


def _planner_state(*, with_snapshot: bool, with_bundle: bool) -> dict[str, Any]:
    actor_ids = ["veronique_vallon", "michel_longstreet"]
    responders = [
        {"actor_id": actor_ids[0], "role": "primary_responder", "preferred_reaction_order": 0},
        {"actor_id": actor_ids[1], "role": "secondary_reactor", "preferred_reaction_order": 1},
    ]
    state: dict[str, Any] = {
        "turn_number": 5,
        "module_id": "god_of_carnage",
        "current_scene_id": "salon_scene",
        "selected_scene_function": "escalate_conflict",
        "selected_responder_set": responders,
        "character_mind_records": [
            {"runtime_actor_id": aid, "tactical_posture": "pressuring", "pressure_response_bias": "press"}
            for aid in actor_ids
        ],
        "actor_lane_context": {
            "human_actor_id": "annette_reille",
            "ai_forbidden_actor_ids": ["annette_reille"],
            "ai_allowed_actor_ids": actor_ids,
            "npc_actor_ids": actor_ids,
        },
        "semantic_move_record": {"move_type": "scene_pressure"},
        "social_state_record": {"social_pressure_shift": "contested"},
    }
    if with_snapshot:
        state["w5_latest_snapshot"] = _npc_snapshot().to_dict()
    if with_bundle:
        state["npc_context_bundle"] = _legacy_npc_context_bundle()
    return state


# ---------------------------------------------------------------------------
# resolve_w5_first_npc_context — four-way classification
# ---------------------------------------------------------------------------


class TestResolveW5FirstNpcContext:
    """``resolve_w5_first_npc_context`` is the public read-side classifier
    that powers F11. Pinning each of the four classification paths here
    gives the planner-level tests below a stable contract to rely on.
    """

    def test_default_on_with_used_projection_returns_w5_projection_and_demotes_bundle(
        self,
    ) -> None:
        """D path: at least one per-actor diagnostic with
        ``w5_npc_projection_used == True`` flips the classifier to
        ``w5_projection`` and the legacy bundle becomes a demoted
        ``_legacy_compat`` breadcrumb. The planner must receive ``None`` as
        ``effective_npc_context_bundle``."""

        assert runtime_public.w5_ast_npc_projection_enabled() is True
        bundle = _legacy_npc_context_bundle()
        diagnostics = [
            {
                "w5_npc_projection_used": True,
                "w5_npc_projection_failed": None,
                "npc_actor_id": "veronique_vallon",
                "npc_projection_source": "w5_projection",
            }
        ]
        resolution = runtime_public.resolve_w5_first_npc_context(
            npc_context_bundle=bundle,
            npc_w5_projection_diagnostics=diagnostics,
        )
        assert resolution["npc_context_source"] == "w5_projection"
        assert resolution["effective_npc_context_bundle"] is None
        assert resolution["legacy_compat_npc_context_bundle"] == bundle
        assert resolution["legacy_compat_npc_context_bundle"] is not bundle
        assert resolution["npc_context_legacy_compat_visible"] is True
        assert resolution["npc_context_fallback_reason"] is None

    def test_default_on_with_used_projection_no_bundle_keeps_legacy_compat_none(
        self,
    ) -> None:
        diagnostics = [
            {
                "w5_npc_projection_used": True,
                "w5_npc_projection_failed": None,
                "npc_actor_id": "veronique_vallon",
                "npc_projection_source": "w5_projection",
            }
        ]
        resolution = runtime_public.resolve_w5_first_npc_context(
            npc_context_bundle=None,
            npc_w5_projection_diagnostics=diagnostics,
        )
        assert resolution["npc_context_source"] == "w5_projection"
        assert resolution["effective_npc_context_bundle"] is None
        assert resolution["legacy_compat_npc_context_bundle"] is None
        assert resolution["npc_context_legacy_compat_visible"] is False
        assert resolution["npc_context_fallback_reason"] is None

    def test_explicit_opt_out_returns_legacy_bundle_verbatim(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NPC_PROJECTION_ENABLED", "0")
        assert runtime_public.w5_ast_npc_projection_enabled() is False
        bundle = _legacy_npc_context_bundle()
        # Diagnostics are irrelevant under opt-out — the resolver does not
        # inspect them when the env opts the consumer out.
        resolution = runtime_public.resolve_w5_first_npc_context(
            npc_context_bundle=bundle,
            npc_w5_projection_diagnostics=[
                {"w5_npc_projection_used": True, "npc_actor_id": "veronique_vallon"}
            ],
        )
        assert resolution["npc_context_source"] == "explicit_opt_out_legacy"
        assert resolution["effective_npc_context_bundle"] == bundle
        # Defensive copy — never alias caller's dict.
        assert resolution["effective_npc_context_bundle"] is not bundle
        assert resolution["legacy_compat_npc_context_bundle"] is None
        assert resolution["npc_context_legacy_compat_visible"] is False
        assert resolution["npc_context_fallback_reason"] == "explicit_opt_out"

    def test_explicit_argument_overrides_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the executor materializes the flag value at the call site it
        passes ``w5_npc_projection_enabled=...`` explicitly; this must win
        over the environment so a single turn cannot observe a mid-flight
        flag flip."""

        monkeypatch.setenv("W5_AST_NPC_PROJECTION_ENABLED", "1")
        bundle = _legacy_npc_context_bundle()
        resolution = runtime_public.resolve_w5_first_npc_context(
            npc_context_bundle=bundle,
            npc_w5_projection_diagnostics=[
                {"w5_npc_projection_used": True, "npc_actor_id": "veronique_vallon"}
            ],
            w5_npc_projection_enabled=False,
        )
        assert resolution["npc_context_source"] == "explicit_opt_out_legacy"
        assert resolution["effective_npc_context_bundle"] == bundle

    def test_malformed_w5_returns_legacy_bundle_with_failure_reason(
        self,
    ) -> None:
        """Default-on with per-actor projections that all raised must keep
        the legacy bundle as the safety net and expose a compact non-empty
        failure reason."""

        bundle = _legacy_npc_context_bundle()
        diagnostics = [
            {
                "w5_npc_projection_used": False,
                "w5_npc_projection_failed": "npc_actor_not_found_in_w5_snapshot:phantom",
                "npc_actor_id": "phantom",
                "npc_projection_source": "actor_lane_context",
            }
        ]
        resolution = runtime_public.resolve_w5_first_npc_context(
            npc_context_bundle=bundle,
            npc_w5_projection_diagnostics=diagnostics,
        )
        assert resolution["npc_context_source"] == "malformed_w5_fallback"
        assert resolution["effective_npc_context_bundle"] == bundle
        assert resolution["legacy_compat_npc_context_bundle"] is None
        assert resolution["npc_context_legacy_compat_visible"] is False
        assert isinstance(resolution["npc_context_fallback_reason"], str)
        assert resolution["npc_context_fallback_reason"].strip()
        assert (
            resolution["npc_context_fallback_reason"]
            == "npc_actor_not_found_in_w5_snapshot:phantom"
        )

    def test_missing_w5_latest_snapshot_failure_classified_as_old_payload(
        self,
    ) -> None:
        """A ``missing_w5_latest_snapshot`` per-actor failure classifies as
        ``old_payload_legacy`` (the snapshot key is missing from the graph
        state — common on pre-Phase-1 sessions), not as ``malformed_w5``."""

        bundle = _legacy_npc_context_bundle()
        diagnostics = [
            {
                "w5_npc_projection_used": False,
                "w5_npc_projection_failed": "missing_w5_latest_snapshot",
                "npc_actor_id": "veronique_vallon",
                "npc_projection_source": "actor_lane_context",
            }
        ]
        resolution = runtime_public.resolve_w5_first_npc_context(
            npc_context_bundle=bundle,
            npc_w5_projection_diagnostics=diagnostics,
        )
        assert resolution["npc_context_source"] == "old_payload_legacy"
        assert resolution["effective_npc_context_bundle"] == bundle
        assert resolution["legacy_compat_npc_context_bundle"] is None
        assert resolution["npc_context_legacy_compat_visible"] is False
        assert resolution["npc_context_fallback_reason"] == "missing_w5_latest_snapshot"

    def test_default_on_with_empty_diagnostics_classified_as_old_payload(
        self,
    ) -> None:
        """Default-on but no per-actor diagnostics at all (e.g., no NPC
        actors to project) treats the situation as ``old_payload_legacy``
        so the planner still gets the bundle if it has one."""

        bundle = _legacy_npc_context_bundle()
        resolution = runtime_public.resolve_w5_first_npc_context(
            npc_context_bundle=bundle,
            npc_w5_projection_diagnostics=[],
        )
        assert resolution["npc_context_source"] == "old_payload_legacy"
        assert resolution["effective_npc_context_bundle"] == bundle
        assert resolution["npc_context_fallback_reason"] == "missing_w5_latest_snapshot"

    def test_default_on_with_none_diagnostics_is_tolerated(self) -> None:
        resolution = runtime_public.resolve_w5_first_npc_context(
            npc_context_bundle=None,
            npc_w5_projection_diagnostics=None,
        )
        assert resolution["npc_context_source"] == "old_payload_legacy"
        assert resolution["effective_npc_context_bundle"] is None

    def test_empty_dict_bundle_treated_as_absent(self) -> None:
        """An empty dict is functionally equivalent to ``None`` — there is
        no bundle to forward."""

        diagnostics = [
            {
                "w5_npc_projection_used": True,
                "w5_npc_projection_failed": None,
                "npc_actor_id": "veronique_vallon",
                "npc_projection_source": "w5_projection",
            }
        ]
        resolution = runtime_public.resolve_w5_first_npc_context(
            npc_context_bundle={},
            npc_w5_projection_diagnostics=diagnostics,
        )
        assert resolution["npc_context_source"] == "w5_projection"
        assert resolution["effective_npc_context_bundle"] is None
        assert resolution["legacy_compat_npc_context_bundle"] is None
        assert resolution["npc_context_legacy_compat_visible"] is False


# ---------------------------------------------------------------------------
# _build_w5_npc_projection_inputs — per-actor diagnostics back-fill
# ---------------------------------------------------------------------------


class TestPerActorDiagnosticsBackfill:
    """The per-actor diagnostics emitted by ``_build_w5_npc_projection_inputs``
    must carry the three new F11 keys (``npc_context_source``,
    ``npc_context_legacy_compat_visible``, ``npc_context_fallback_reason``)
    on every emitted row so admin/observability surfaces can audit the
    selected source. Existing keys (``w5_npc_projection_used`` /
    ``npc_projection_source`` etc.) are unchanged.
    """

    def test_default_on_happy_path_emits_w5_projection_source_per_actor(
        self,
    ) -> None:
        snapshot = _npc_snapshot()
        projections, diagnostics = runtime_public._build_w5_npc_projection_inputs(
            state={"w5_latest_snapshot": snapshot.to_dict()},
            npc_actor_ids=["veronique_vallon", "michel_longstreet"],
        )
        assert set(projections.keys()) == {"veronique_vallon", "michel_longstreet"}
        assert len(diagnostics) == 2
        for row in diagnostics:
            assert row["w5_npc_projection_used"] is True
            assert row["npc_projection_source"] == "w5_projection"
            assert row["npc_context_source"] == "w5_projection"
            assert row["npc_context_legacy_compat_visible"] is False
            assert row["npc_context_fallback_reason"] is None

    def test_default_on_happy_path_with_bundle_marks_legacy_compat_visible(
        self,
    ) -> None:
        snapshot = _npc_snapshot()
        state = {
            "w5_latest_snapshot": snapshot.to_dict(),
            "npc_context_bundle": _legacy_npc_context_bundle(),
        }
        _, diagnostics = runtime_public._build_w5_npc_projection_inputs(
            state=state,
            npc_actor_ids=["veronique_vallon"],
        )
        assert diagnostics
        assert all(row["npc_context_legacy_compat_visible"] is True for row in diagnostics)

    def test_old_payload_missing_snapshot_classifies_each_row_as_old_payload(
        self,
    ) -> None:
        _, diagnostics = runtime_public._build_w5_npc_projection_inputs(
            state={"w5_latest_snapshot": None, "npc_context_bundle": _legacy_npc_context_bundle()},
            npc_actor_ids=["veronique_vallon"],
        )
        assert diagnostics
        row = diagnostics[0]
        assert row["w5_npc_projection_used"] is False
        assert row["w5_npc_projection_failed"] == "missing_w5_latest_snapshot"
        assert row["npc_context_source"] == "old_payload_legacy"
        assert row["npc_context_legacy_compat_visible"] is False
        assert row["npc_context_fallback_reason"] == "missing_w5_latest_snapshot"

    def test_malformed_w5_snapshot_classifies_each_row_as_malformed(
        self,
    ) -> None:
        """A snapshot present in state but with an actor not in
        ``snapshot.actors`` produces a per-actor failure that classifies as
        ``malformed_w5_fallback`` (distinct from missing-snapshot)."""

        snapshot = _npc_snapshot()
        _, diagnostics = runtime_public._build_w5_npc_projection_inputs(
            state={"w5_latest_snapshot": snapshot.to_dict()},
            npc_actor_ids=["phantom_actor"],
        )
        assert diagnostics
        row = diagnostics[0]
        assert row["w5_npc_projection_used"] is False
        assert row["w5_npc_projection_failed"]
        assert row["w5_npc_projection_failed"] != "missing_w5_latest_snapshot"
        assert row["npc_context_source"] == "malformed_w5_fallback"
        assert row["npc_context_legacy_compat_visible"] is False
        assert row["npc_context_fallback_reason"]

    def test_explicit_opt_out_emits_no_diagnostics_so_packet_omits_them(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Opt-out short-circuit (F9) is preserved: ``({}, [])`` so the
        dramatic packet does not surface a ``w5_npc_projection_diagnostics``
        key. The downstream resolver classifies opt-out via env, not via
        an empty diagnostics list, so the legacy bundle remains primary."""

        monkeypatch.setenv("W5_AST_NPC_PROJECTION_ENABLED", "0")
        projections, diagnostics = runtime_public._build_w5_npc_projection_inputs(
            state={"w5_latest_snapshot": _npc_snapshot().to_dict()},
            npc_actor_ids=["veronique_vallon"],
        )
        assert projections == {}
        assert diagnostics == []


# ---------------------------------------------------------------------------
# Dramatic packet — planner consumes W5 first, demotes bundle under D
# ---------------------------------------------------------------------------


def _build_packet(state: dict[str, Any]) -> dict[str, Any]:
    from ai_stack.langgraph.langgraph_runtime_executor import (
        _build_dramatic_generation_packet,
    )

    return _build_dramatic_generation_packet(state)


class TestPlannerW5First:
    """The dramatic packet routes state through ``_build_npc_agency_plan_projection``,
    which is the F11 attachment site for ``npc_context_bundle``. Under
    default-on with a well-formed snapshot:

    - The simulation's ``source_evidence`` must NOT contain the legacy
      ``npc_context_bundle`` row (W5 is primary; bundle is demoted).
    - The simulation's ``source_evidence`` MUST contain the
      ``w5_npc_projection`` row (W5 is the actor-situation authority).
    - Each NPC proposal carries an ``actor_w5_situation`` with How first-class
      and inferred Why marked as soft truth.
    - Per-actor diagnostics carry ``npc_context_source == "w5_projection"``
      and ``npc_context_legacy_compat_visible == True`` (the bundle is in
      state but demoted).

    Under explicit opt-out / malformed-W5 / old-payload, the bundle is the
    primary planner context and the ``npc_context_bundle`` evidence row is
    present.
    """

    def test_default_on_happy_path_w5_is_primary_bundle_is_legacy_compat(
        self,
    ) -> None:
        state = _planner_state(with_snapshot=True, with_bundle=True)
        packet = _build_packet(state)

        simulation = packet["npc_agency_simulation"]
        sources = {row["source"] for row in simulation["source_evidence"]}
        # Bundle must be demoted on the D path.
        assert "npc_context_bundle" not in sources
        # W5 must be present as the primary actor-situation source.
        assert "w5_npc_projection" in sources

        # Every responder proposal carries an actor-specific W5 situation.
        proposals = simulation["npc_intent_proposals"]
        for actor_id in ("veronique_vallon", "michel_longstreet"):
            row = next(p for p in proposals if p["actor_id"] == actor_id)
            situation = row["actor_w5_situation"]
            assert situation["target_consumer"] == "npc"
            assert situation["actor_id"] == actor_id

        # Per-actor diagnostic correctly classifies the source and exposes
        # the legacy-compat visibility flag.
        for actor_id in ("veronique_vallon", "michel_longstreet"):
            diag = next(
                row
                for row in packet["w5_npc_projection_diagnostics"]
                if row["npc_actor_id"] == actor_id
            )
            assert diag["npc_context_source"] == "w5_projection"
            assert diag["npc_context_legacy_compat_visible"] is True
            assert diag["npc_context_fallback_reason"] is None

    def test_default_on_happy_path_without_bundle_keeps_w5_primary(
        self,
    ) -> None:
        """When no legacy bundle is in state, W5 is still primary and the
        legacy-compat visibility flag stays False."""

        state = _planner_state(with_snapshot=True, with_bundle=False)
        packet = _build_packet(state)
        simulation = packet["npc_agency_simulation"]
        sources = {row["source"] for row in simulation["source_evidence"]}
        assert "npc_context_bundle" not in sources
        assert "w5_npc_projection" in sources
        diag = packet["w5_npc_projection_diagnostics"][0]
        assert diag["npc_context_source"] == "w5_projection"
        assert diag["npc_context_legacy_compat_visible"] is False

    def test_explicit_opt_out_uses_legacy_npc_context_bundle_as_primary(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NPC_PROJECTION_ENABLED", "0")
        state = _planner_state(with_snapshot=True, with_bundle=True)
        packet = _build_packet(state)

        # No W5 diagnostics under opt-out — the packet must omit the key,
        # exactly as in Phase 6B-1 / 6B-2.
        assert "w5_npc_projection_diagnostics" not in packet

        simulation = packet["npc_agency_simulation"]
        sources = {row["source"] for row in simulation["source_evidence"]}
        # Bundle becomes the primary NPC context on opt-out (pre-Phase-6B-3C
        # behaviour preserved).
        assert "npc_context_bundle" in sources
        # No W5 evidence row under opt-out — the per-actor projections were
        # never built.
        assert "w5_npc_projection" not in sources

        # No proposal carries ``actor_w5_situation`` under opt-out.
        proposals = simulation["npc_intent_proposals"]
        assert proposals
        assert all("actor_w5_situation" not in row for row in proposals)

    def test_old_payload_no_snapshot_falls_back_to_legacy_bundle_with_diagnostic(
        self,
    ) -> None:
        """Default-on without a ``w5_latest_snapshot`` in state must:

        - emit per-actor diagnostics flagging
          ``w5_npc_projection_failed == "missing_w5_latest_snapshot"``,
        - classify ``npc_context_source == "old_payload_legacy"``,
        - forward the legacy bundle into the planner so the
          ``npc_context_bundle`` evidence row appears in ``source_evidence``.
        """

        state = _planner_state(with_snapshot=False, with_bundle=True)
        packet = _build_packet(state)

        diagnostics = packet["w5_npc_projection_diagnostics"]
        assert diagnostics
        for row in diagnostics:
            assert row["w5_npc_projection_used"] is False
            assert row["w5_npc_projection_failed"] == "missing_w5_latest_snapshot"
            assert row["npc_context_source"] == "old_payload_legacy"
            assert row["npc_context_legacy_compat_visible"] is False
            assert row["npc_context_fallback_reason"] == "missing_w5_latest_snapshot"

        simulation = packet["npc_agency_simulation"]
        sources = {row["source"] for row in simulation["source_evidence"]}
        # Bundle is the primary NPC context under L.
        assert "npc_context_bundle" in sources
        # No W5 evidence row when no projections were built.
        assert "w5_npc_projection" not in sources
        # No proposal carries ``actor_w5_situation`` under L.
        proposals = simulation["npc_intent_proposals"]
        assert proposals
        assert all("actor_w5_situation" not in row for row in proposals)

    def test_malformed_snapshot_falls_back_to_legacy_bundle_with_diagnostic(
        self,
    ) -> None:
        """Default-on with a snapshot that does not contain the NPC actor
        IDs (every per-actor projection raises) classifies as
        ``malformed_w5_fallback`` and forwards the legacy bundle."""

        state = _planner_state(with_snapshot=False, with_bundle=True)
        # Inject a malformed-but-present snapshot (no NPC actors).
        state["w5_latest_snapshot"] = W5Snapshot(
            snapshot_id="w5s_malformed",
            story_session_id="sess_malformed",
            turn_number=5,
            created_at="w5:turn:5",
            actors={},
        ).to_dict()
        packet = _build_packet(state)

        diagnostics = packet["w5_npc_projection_diagnostics"]
        assert diagnostics
        for row in diagnostics:
            assert row["w5_npc_projection_used"] is False
            assert row["w5_npc_projection_failed"]
            assert row["w5_npc_projection_failed"] != "missing_w5_latest_snapshot"
            assert row["npc_context_source"] == "malformed_w5_fallback"
            assert row["npc_context_legacy_compat_visible"] is False
            assert row["npc_context_fallback_reason"]

        simulation = packet["npc_agency_simulation"]
        sources = {row["source"] for row in simulation["source_evidence"]}
        assert "npc_context_bundle" in sources
        assert "w5_npc_projection" not in sources

    def test_default_on_preserves_how_first_class_and_inferred_why_soft(
        self,
    ) -> None:
        """The W5 NPC projection embedded in each proposal must keep
        ``how_summary`` as a first-class top-level key (not folded into
        ``what_summary``) and mark inferred Why values via
        ``truth_attribution[...] == "inferred"``."""

        state = _planner_state(with_snapshot=True, with_bundle=True)
        packet = _build_packet(state)
        proposal = next(
            row
            for row in packet["npc_agency_simulation"]["npc_intent_proposals"]
            if row["actor_id"] == "veronique_vallon"
        )
        situation = proposal["actor_w5_situation"]
        # How is first-class.
        assert "how_summary" in situation
        assert isinstance(situation["how_summary"].get("facts"), dict)
        assert situation["how_summary"]["facts"]["tone"] == "controlled"
        # How is NOT collapsed into What.
        what_facts = situation["what_summary"].get("facts", {})
        assert "tone" not in what_facts
        # Inferred Why remains soft truth.
        assert situation["truth_attribution"]["why_summary.facts.motive"] == "inferred"

    def test_default_on_npc_planner_plan_shape_is_unchanged(
        self,
    ) -> None:
        """The simulation's top-level plan contract keys are stable across
        the migration — only the ``source_evidence`` content shifts. This
        protects downstream consumers (long-horizon, closure, validation)
        from accidental shape regressions."""

        state = _planner_state(with_snapshot=True, with_bundle=True)
        packet = _build_packet(state)
        simulation = packet["npc_agency_simulation"]
        plan = simulation["npc_agency_plan"]
        required_plan_keys = {
            "schema_version",
            "planner_contract",
            "planner_status",
            "planner_scope",
            "turn_number",
            "primary_responder_id",
            "secondary_responder_ids",
            "required_actor_ids",
            "minimum_secondary_initiatives_required",
            "resolution_policy",
            "planner_rationale_codes",
            "source_evidence",
            "npc_initiatives",
        }
        assert required_plan_keys.issubset(set(plan.keys()))
        # Each initiative still carries the canonical NPC plan keys.
        for initiative in plan["npc_initiatives"]:
            for key in (
                "actor_id",
                "role",
                "intent",
                "allowed_block_types",
                "allowed_output_lanes",
                "target_actor_id",
                "required",
                "requirement_scope",
                "resolution_policy",
                "resolved",
                "source_evidence",
            ):
                assert key in initiative

    def test_diagnostic_envelope_marks_how_and_inferred_why_presence(
        self,
    ) -> None:
        state = _planner_state(with_snapshot=True, with_bundle=True)
        packet = _build_packet(state)
        diag = packet["w5_npc_projection_diagnostics"][0]
        assert diag["npc_projection_has_how"] is True
        assert diag["npc_projection_has_inferred_why"] is True


# ---------------------------------------------------------------------------
# Privacy / actor knowledge scope (Phase 3B contract preserved)
# ---------------------------------------------------------------------------


class TestPrivacyPreserved:
    """Phase 3B privacy semantics are unchanged by the F11 migration. These
    tests anchor the contract that the NPC planner W5-first migration does
    not regress privacy:

    - The target NPC sees its own private inferred Why.
    - Another NPC's private inferred Why does NOT leak into the target
      NPC's projection unless ``actor_knowledge_scope`` allows the target.
    - Player-private facts never leak into NPC projections.
    """

    def _two_actor_snapshot_with_private_motive(
        self,
        *,
        other_motive_visibility: W5VisibilityScope = W5VisibilityScope.PRIVATE_TO_ACTOR,
        other_motive_scope: tuple[str, ...] = (),
    ) -> W5Snapshot:
        return W5Snapshot(
            snapshot_id="w5s_privacy",
            story_session_id="sess_privacy",
            turn_number=5,
            created_at="w5:turn:5",
            actors={
                "veronique_vallon": _npc_situation(
                    "veronique_vallon",
                    motive="protect_position",
                    motive_visibility=W5VisibilityScope.PRIVATE_TO_ACTOR,
                ),
                "michel_longstreet": _npc_situation(
                    "michel_longstreet",
                    motive="deflect_blame",
                    motive_visibility=other_motive_visibility,
                    motive_scope=other_motive_scope,
                ),
            },
        )

    def test_target_npc_receives_own_private_inferred_why(self) -> None:
        snapshot = self._two_actor_snapshot_with_private_motive()
        actor_ids = ["veronique_vallon", "michel_longstreet"]
        state = _planner_state(with_snapshot=False, with_bundle=False)
        state["w5_latest_snapshot"] = snapshot.to_dict()
        state["selected_responder_set"] = [
            {"actor_id": actor_ids[0], "role": "primary_responder", "preferred_reaction_order": 0},
            {"actor_id": actor_ids[1], "role": "secondary_reactor", "preferred_reaction_order": 1},
        ]
        state["actor_lane_context"]["npc_actor_ids"] = actor_ids
        state["actor_lane_context"]["ai_allowed_actor_ids"] = actor_ids
        packet = _build_packet(state)

        veronique_proposal = next(
            row
            for row in packet["npc_agency_simulation"]["npc_intent_proposals"]
            if row["actor_id"] == "veronique_vallon"
        )
        # The target NPC sees its OWN private inferred motive.
        own_motive = (
            veronique_proposal["actor_w5_situation"]
            .get("why_summary", {})
            .get("facts", {})
            .get("motive")
        )
        assert own_motive == "protect_position"

    def test_other_actor_private_inferred_why_does_not_leak_to_target_npc(
        self,
    ) -> None:
        """``michel_longstreet``'s private inferred motive must not appear
        in ``veronique_vallon``'s projection unless
        ``actor_knowledge_scope`` allows it."""

        snapshot = self._two_actor_snapshot_with_private_motive(
            other_motive_visibility=W5VisibilityScope.PRIVATE_TO_ACTOR,
            other_motive_scope=(),  # nobody else allowed
        )
        actor_ids = ["veronique_vallon", "michel_longstreet"]
        state = _planner_state(with_snapshot=False, with_bundle=False)
        state["w5_latest_snapshot"] = snapshot.to_dict()
        state["selected_responder_set"] = [
            {"actor_id": actor_ids[0], "role": "primary_responder", "preferred_reaction_order": 0},
            {"actor_id": actor_ids[1], "role": "secondary_reactor", "preferred_reaction_order": 1},
        ]
        state["actor_lane_context"]["npc_actor_ids"] = actor_ids
        state["actor_lane_context"]["ai_allowed_actor_ids"] = actor_ids
        packet = _build_packet(state)

        veronique_proposal = next(
            row
            for row in packet["npc_agency_simulation"]["npc_intent_proposals"]
            if row["actor_id"] == "veronique_vallon"
        )
        # The serialized projection payload must not contain
        # ``"deflect_blame"`` anywhere — that motive belongs to a different
        # NPC and is private with no actor_knowledge_scope.
        situation_text = repr(veronique_proposal["actor_w5_situation"])
        assert "deflect_blame" not in situation_text

    def test_other_actor_private_inferred_why_leaks_only_with_actor_knowledge_scope(
        self,
    ) -> None:
        """If the OTHER actor's private inferred Why explicitly scopes the
        target NPC (via ``actor_knowledge_scope``), then the projection
        may surface it — this pins the Phase 3B allow-list behaviour."""

        snapshot = self._two_actor_snapshot_with_private_motive(
            other_motive_visibility=W5VisibilityScope.PRIVATE_TO_ACTOR,
            other_motive_scope=("veronique_vallon",),
        )
        actor_ids = ["veronique_vallon", "michel_longstreet"]
        state = _planner_state(with_snapshot=False, with_bundle=False)
        state["w5_latest_snapshot"] = snapshot.to_dict()
        state["selected_responder_set"] = [
            {"actor_id": actor_ids[0], "role": "primary_responder", "preferred_reaction_order": 0},
            {"actor_id": actor_ids[1], "role": "secondary_reactor", "preferred_reaction_order": 1},
        ]
        state["actor_lane_context"]["npc_actor_ids"] = actor_ids
        state["actor_lane_context"]["ai_allowed_actor_ids"] = actor_ids
        packet = _build_packet(state)

        veronique_proposal = next(
            row
            for row in packet["npc_agency_simulation"]["npc_intent_proposals"]
            if row["actor_id"] == "veronique_vallon"
        )
        # The Phase 3B contract permits the projection to surface the
        # scope-allowed private inferred Why. Either it shows up, or — if
        # the projection deliberately keeps cross-actor Why structurally
        # quiet — the structural truth_attribution still does not mislabel
        # it. Pin the weaker guarantee that the projection runs cleanly
        # for the target NPC and embeds the per-actor situation envelope.
        situation = veronique_proposal["actor_w5_situation"]
        assert situation["target_consumer"] == "npc"
        assert situation["actor_id"] == "veronique_vallon"

    def test_planner_does_not_surface_private_memory_text_from_legacy_bundle(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Even when the legacy bundle is the primary NPC context (opt-out
        path), the planner must only read ``retrieval_plan`` lane lists —
        never the ``private_memory`` body. This pins the existing planner
        contract under the new wrapper."""

        monkeypatch.setenv("W5_AST_NPC_PROJECTION_ENABLED", "0")
        state = _planner_state(with_snapshot=True, with_bundle=True)
        packet = _build_packet(state)
        simulation = packet["npc_agency_simulation"]
        text = repr(simulation["source_evidence"])
        # The redacted private-memory excerpt placed in the bundle
        # private_memory subdict must never appear in source_evidence.
        assert "redacted_private_memory_excerpt" not in text
        assert "never_in_evidence" not in text


# ---------------------------------------------------------------------------
# build_npc_agency_simulation accepts effective bundle = None under D
# ---------------------------------------------------------------------------


def test_build_npc_agency_simulation_with_none_bundle_omits_legacy_evidence_row() -> None:
    """Pinning the planner-layer contract directly: when
    ``npc_context_bundle=None`` is forwarded (the F11 W5-first happy path),
    the simulation's ``source_evidence`` must not contain an
    ``npc_context_bundle`` row."""

    responders = [
        {"actor_id": "veronique_vallon", "role": "primary_responder", "preferred_reaction_order": 0},
        {"actor_id": "michel_longstreet", "role": "secondary_reactor", "preferred_reaction_order": 1},
    ]
    simulation = build_npc_agency_simulation(
        selected_responder_set=responders,
        turn_number=5,
        character_mind_records=[
            {"runtime_actor_id": "veronique_vallon", "tactical_posture": "pressuring"},
            {"runtime_actor_id": "michel_longstreet", "tactical_posture": "defending"},
        ],
        social_state_record={"social_pressure_shift": "contested"},
        semantic_move_record={"move_type": "scene_pressure"},
        selected_scene_function="escalate_conflict",
        actor_lane_context={
            "human_actor_id": "annette_reille",
            "ai_forbidden_actor_ids": ["annette_reille"],
            "ai_allowed_actor_ids": ["veronique_vallon", "michel_longstreet"],
            "npc_actor_ids": ["veronique_vallon", "michel_longstreet"],
        },
        npc_context_bundle=None,
        npc_w5_situations={
            "veronique_vallon": {
                "target_consumer": "npc",
                "actor_id": "veronique_vallon",
                "where_summary": {"facts": {"scene_location": "salon"}},
                "what_summary": {"facts": {"current_action": "presses"}},
                "how_summary": {"facts": {"tone": "controlled"}},
                "why_summary": {"facts": {"motive": "protect_position"}},
                "source_attribution": {},
                "truth_attribution": {"why_summary.facts.motive": "inferred"},
            }
        },
    )
    assert simulation is not None
    sources = {row["source"] for row in simulation["source_evidence"]}
    assert "npc_context_bundle" not in sources
    assert "w5_npc_projection" in sources


def test_build_npc_agency_plan_with_none_bundle_omits_legacy_evidence_row() -> None:
    """Same guarantee for the partial-plan fallback path used when the
    full simulation does not activate (single responder, etc.)."""

    plan = build_npc_agency_plan(
        selected_responder_set=[
            {"actor_id": "veronique_vallon", "role": "primary_responder", "preferred_reaction_order": 0},
            {"actor_id": "michel_longstreet", "role": "secondary_reactor", "preferred_reaction_order": 1},
        ],
        turn_number=5,
        actor_lane_context={
            "human_actor_id": "annette_reille",
            "ai_forbidden_actor_ids": ["annette_reille"],
            "ai_allowed_actor_ids": ["veronique_vallon", "michel_longstreet"],
            "npc_actor_ids": ["veronique_vallon", "michel_longstreet"],
        },
        npc_context_bundle=None,
        npc_w5_situations={
            "veronique_vallon": {
                "target_consumer": "npc",
                "actor_id": "veronique_vallon",
                "where_summary": {"facts": {"scene_location": "salon"}},
                "what_summary": {"facts": {"current_action": "presses"}},
                "how_summary": {"facts": {"tone": "controlled"}},
                "why_summary": {"facts": {"motive": "protect_position"}},
                "source_attribution": {},
                "truth_attribution": {"why_summary.facts.motive": "inferred"},
            }
        },
    )
    assert plan is not None
    sources = {row["source"] for row in plan["source_evidence"]}
    assert "npc_context_bundle" not in sources
    assert "w5_npc_projection" in sources
