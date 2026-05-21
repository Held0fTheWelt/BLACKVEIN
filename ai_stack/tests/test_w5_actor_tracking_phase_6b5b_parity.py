"""Phase 6B-5B — narrator strict-mode parity contract (ai_stack side).

Phase 6B-5B is the test-contract rewrite phase that precedes the Phase 6B-5C
default-on flip of ``W5_AST_NARRATOR_STRICT_ENABLED`` (see
[ADR-0065](../../docs/ADR/adr-0065-w5-narrator-strict-mode-default-actor-situation-surface.md)).

These tests strengthen the existing ai_stack strict-migration coverage in:

- ``ai_stack/tests/test_w5_actor_tracking_phase_6b3b_narrator_strict_migration.py``
- ``ai_stack/tests/test_god_of_carnage_narrator_path.py``

so that the future default-on flip is gated by *semantic* assertions, not
field-presence-only assertions. The world-engine-side end-to-end parity
contract lives in
``world-engine/tests/test_story_runtime_w5_narrator_strict_phase_6b5b_parity.py``.

Scope of this file:

1. ``ai_stack.actor_tracking.w5_ast_narrator_strict_enabled`` resolver
   posture matrix (default-off, explicit-off, explicit-on, env-noise).
2. ``ai_stack.actor_tracking.w5_projection_flag_states`` reports the
   strict flag accurately under each posture.
3. ``ai_stack.story_runtime.narrator.god_of_carnage_narrator_path``:
   - Strict-off → ``source_facts["transition_from_previous"]`` is first
     class, ``_legacy_compat`` is absent.
   - Strict-on → ``source_facts["transition_from_previous"]`` is removed
     from the top-level contract, demoted to
     ``source_facts["_legacy_compat"]["transition_from_previous"]`` with
     an ``authority = "w5_projection"`` marker and a ``notice`` string
     that names the W5 narrator projection as the actor-situation
     authority and labels the breadcrumb as non-authoritative.
   - Strict-on preserves the authored hard-cut directed-transition
     breadcrumb (so operator parity audits remain possible) but the
     prompt-side authority moves to W5.
   - Canonical step ids, mandatory-beat coverage cues, and source_refs
     are unchanged by the strict flag — strict mode is a source-of-truth
     migration, not a content rewrite.
4. ``build_w5_projection_for_narrator`` carries Who / Where / What / How
   / Why summaries with semantically meaningful values and
   ``source_attribution`` / ``truth_attribution`` per fact path. The
   strict-on prompt names this projection as the actor-situation
   authority, so its semantic content is a Phase 6B-5B gate.

These tests do not flip ``W5_AST_NARRATOR_STRICT_ENABLED``, do not remove
``transition_from_previous``, do not remove ``_legacy_compat``, do not weaken
malformed-W5 fallback, and do not mutate committed events. How remains
first-class. Inferred Why remains soft truth.
"""

from __future__ import annotations

from typing import Any

import pytest


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
# 1) Strict resolver posture matrix — only forbidden package is forbidden
# ---------------------------------------------------------------------------


class TestPhase6B5BStrictResolverPosture:
    """Phase 6B-5B parity gate — the strict resolver must report posture
    accurately so Phase 6B-5C can flip the default safely. The W5 module
    is imported only from the active package
    ``ai_stack.actor_tracking``; the retired
    ``ai_stack.actor_situation`` / ``ai_stack.w5_actor_situation``
    packages must not be importable."""

    def test_active_module_path_is_actor_tracking(self) -> None:
        from ai_stack.actor_tracking import w5_ast_narrator_strict_enabled

        # The resolver originates from ai_stack/actor_tracking/diagnostics.py
        # via the package __init__ re-export. Both surfaces must be available
        # and identical.
        from ai_stack.actor_tracking.diagnostics import (
            w5_ast_narrator_strict_enabled as direct_resolver,
        )

        assert w5_ast_narrator_strict_enabled is direct_resolver

    def test_retired_packages_are_not_importable(self) -> None:
        # Phase 6B-4 + ADR-0065 require these packages to remain absent.
        import importlib

        for retired in ("ai_stack.actor_situation", "ai_stack.w5_actor_situation"):
            with pytest.raises(ModuleNotFoundError):
                importlib.import_module(retired)

    def test_default_unset_is_strict_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from ai_stack.actor_tracking import w5_ast_narrator_strict_enabled

        monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        assert w5_ast_narrator_strict_enabled() is False

    @pytest.mark.parametrize("value", ["", "  ", "garbage", "maybe"])
    def test_invalid_env_values_default_to_strict_off(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        """An ambiguous env value must not silently flip to strict-on. Phase
        6B-5C will be the *only* commit that flips the default."""

        from ai_stack.actor_tracking import w5_ast_narrator_strict_enabled

        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", value)
        assert w5_ast_narrator_strict_enabled() is False

    @pytest.mark.parametrize(
        "value", ["0", "false", "no", "off", "FALSE", "Off", "  false  "]
    )
    def test_explicit_off_values_are_strict_off(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        from ai_stack.actor_tracking import w5_ast_narrator_strict_enabled

        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", value)
        assert w5_ast_narrator_strict_enabled() is False

    @pytest.mark.parametrize(
        "value", ["1", "true", "yes", "on", "TRUE", "On", "  true  "]
    )
    def test_explicit_on_values_are_strict_on(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        from ai_stack.actor_tracking import w5_ast_narrator_strict_enabled

        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", value)
        assert w5_ast_narrator_strict_enabled() is True

    def test_flag_states_mirror_strict_resolver(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ai_stack.actor_tracking import (
            w5_ast_narrator_strict_enabled,
            w5_projection_flag_states,
        )

        monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        assert (
            w5_projection_flag_states()["narrator_strict"]
            is w5_ast_narrator_strict_enabled()
            is False
        )
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        assert (
            w5_projection_flag_states()["narrator_strict"]
            is w5_ast_narrator_strict_enabled()
            is True
        )


# ---------------------------------------------------------------------------
# 2) GoC narrator path — strict-off vs strict-on source_facts shape
# ---------------------------------------------------------------------------


def _first_block_with_legacy_transition(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    for block in blocks:
        facts = block.get("source_facts") or {}
        if (
            "transition_from_previous" in facts
            and isinstance(facts["transition_from_previous"], dict)
            and facts["transition_from_previous"].get("location_changed")
        ):
            return block
    raise AssertionError(
        "expected at least one narrator block with a legacy "
        "transition_from_previous.location_changed=True payload"
    )


def _first_block_with_legacy_compat_transition(
    blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    for block in blocks:
        facts = block.get("source_facts") or {}
        legacy = facts.get("_legacy_compat") or {}
        if (
            isinstance(legacy, dict)
            and isinstance(legacy.get("transition_from_previous"), dict)
            and legacy["transition_from_previous"].get("location_changed")
        ):
            return block
    raise AssertionError(
        "expected at least one strict-on narrator block with a demoted "
        "_legacy_compat.transition_from_previous.location_changed=True breadcrumb"
    )


class TestPhase6B5BGoCNarratorPathSourceFactsShape:
    """Phase 6B-5B parity gate — the strict flag flips the *authority surface*
    inside ``source_facts``, but content references (canonical step ids,
    mandatory-beat coverage_cues, source_refs) remain identical. This
    reflects ADR-0065's "source-of-truth migration, not content rewrite"
    constraint."""

    def test_strict_off_keeps_transition_first_class_and_no_legacy_compat(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ai_stack.story_runtime.narrator import god_of_carnage_narrator_path

        monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        opening = god_of_carnage_narrator_path.build_goc_narrator_path_opening(
            session_output_language="de",
        )
        blocks = opening["scene_blocks"]
        assert blocks
        for block in blocks:
            assert "transition_from_previous" in block["source_facts"]
            assert "_legacy_compat" not in block["source_facts"]
        # Hard-cut block exists under the legacy top-level surface.
        hard_cut_blocks = [
            block
            for block in blocks
            if (block["source_facts"].get("transition_from_previous") or {})
            .get("directed_transition", {})
            .get("kind")
            == "hard_cut"
        ]
        assert [
            block["canonical_mandatory_beat_id"] for block in hard_cut_blocks
        ] == ["room_perception_winter_light"]

    def test_strict_on_demotes_transition_with_w5_authority_notice(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ai_stack.story_runtime.narrator import god_of_carnage_narrator_path

        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        opening = god_of_carnage_narrator_path.build_goc_narrator_path_opening(
            session_output_language="de",
        )
        blocks = opening["scene_blocks"]
        assert blocks
        for block in blocks:
            facts = block["source_facts"]
            # Top-level authority is gone — semantic, not field-presence.
            assert "transition_from_previous" not in facts
            legacy = facts.get("_legacy_compat")
            assert isinstance(legacy, dict)
            assert "transition_from_previous" in legacy, (
                "strict-on must keep the legacy transition payload as a "
                "non-authoritative breadcrumb under _legacy_compat"
            )
            assert legacy["authority"] == "w5_projection", (
                "strict-on must name W5 narrator projection as the "
                "actor-situation authority on the demoted breadcrumb"
            )
            notice = str(legacy.get("notice") or "")
            assert "W5" in notice, (
                "strict-on _legacy_compat.notice must explicitly name W5"
            )
            assert "non-authoritative" in notice or "non_authoritative" in notice, (
                "strict-on _legacy_compat.notice must mark the breadcrumb as "
                "non-authoritative"
            )
            assert (
                "actor-situation authority" in notice
                or "actor_situation_authority" in notice
            ), (
                "strict-on _legacy_compat.notice must explicitly name the "
                "actor-situation authority"
            )

    def test_strict_on_preserves_hard_cut_breadcrumb_under_legacy_compat(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ai_stack.story_runtime.narrator import god_of_carnage_narrator_path

        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        opening = god_of_carnage_narrator_path.build_goc_narrator_path_opening(
            session_output_language="de",
        )
        blocks = opening["scene_blocks"]
        # The authored hard-cut transition is still inspectable for operator
        # parity, but only under _legacy_compat. This is what enables Phase
        # 6B-5E to make a separately scoped decision on demoting/removing it.
        hard_cut_blocks = [
            block
            for block in blocks
            if (
                (block["source_facts"].get("_legacy_compat") or {})
                .get("transition_from_previous", {})
                .get("directed_transition", {})
                .get("kind")
                == "hard_cut"
            )
        ]
        assert [
            block["canonical_mandatory_beat_id"] for block in hard_cut_blocks
        ] == ["room_perception_winter_light"]

    def test_strict_on_preserves_location_changed_breadcrumb_under_legacy_compat(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The strict-on legacy_compat must still carry location_changed so
        operators can correlate W5 ``where_summary.location_changed`` against
        the legacy signal during rollout. ADR-0065 'parity evidence' clause."""

        from ai_stack.story_runtime.narrator import god_of_carnage_narrator_path

        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        opening = god_of_carnage_narrator_path.build_goc_narrator_path_opening(
            session_output_language="de",
        )
        block = _first_block_with_legacy_compat_transition(opening["scene_blocks"])
        legacy = block["source_facts"]["_legacy_compat"]["transition_from_previous"]
        assert legacy["location_changed"] is True
        # current_location/previous_location are inspectable from the
        # breadcrumb so admin parity audits can still happen during rollout.
        assert legacy["current_location"]["id"]
        assert legacy["previous_location"]["id"]

    def test_strict_on_does_not_alter_canonical_content(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Strict mode is a source-of-truth migration, not a content rewrite.
        Canonical step ids, block ids, mandatory beat ids, coverage_cues,
        source_refs, and module_context must all match the unstrict run."""

        from ai_stack.story_runtime.narrator import god_of_carnage_narrator_path

        monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        unstrict = god_of_carnage_narrator_path.build_goc_narrator_path_opening(
            session_output_language="de",
        )
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        strict = god_of_carnage_narrator_path.build_goc_narrator_path_opening(
            session_output_language="de",
        )
        assert strict["canonical_step_ids"] == unstrict["canonical_step_ids"]
        assert strict["source_refs"] == unstrict["source_refs"]
        assert [block["id"] for block in strict["scene_blocks"]] == [
            block["id"] for block in unstrict["scene_blocks"]
        ]
        for strict_block, unstrict_block in zip(
            strict["scene_blocks"], unstrict["scene_blocks"]
        ):
            assert (
                strict_block["canonical_mandatory_beat_id"]
                == unstrict_block["canonical_mandatory_beat_id"]
            )
            assert (
                strict_block["source_refs"] == unstrict_block["source_refs"]
            )
            assert (
                strict_block["source_facts"]["mandatory_beat"]
                == unstrict_block["source_facts"]["mandatory_beat"]
            )
            assert (
                strict_block["source_facts"]["module_context"]
                == unstrict_block["source_facts"]["module_context"]
            )
            # text content is the canonical perception output and must not
            # change under strict mode.
            assert strict_block["text"] == unstrict_block["text"]

    def test_strict_on_unstrict_location_changed_payload_matches_demoted_breadcrumb(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Per-block: the legacy payload in strict-on
        ``_legacy_compat.transition_from_previous`` is exactly the same
        payload that strict-off keeps at top-level. Phase 6B-5B operator
        parity gate."""

        from ai_stack.story_runtime.narrator import god_of_carnage_narrator_path

        monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        unstrict = god_of_carnage_narrator_path.build_goc_narrator_path_opening(
            session_output_language="de",
        )
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        strict = god_of_carnage_narrator_path.build_goc_narrator_path_opening(
            session_output_language="de",
        )
        for strict_block, unstrict_block in zip(
            strict["scene_blocks"], unstrict["scene_blocks"]
        ):
            unstrict_transition = unstrict_block["source_facts"].get(
                "transition_from_previous"
            )
            strict_legacy = strict_block["source_facts"].get("_legacy_compat") or {}
            strict_transition = strict_legacy.get("transition_from_previous")
            assert unstrict_transition == strict_transition, (
                "strict-on demoted breadcrumb must preserve the exact legacy "
                "transition payload for operator parity"
            )


# ---------------------------------------------------------------------------
# 3) W5 narrator projection — semantic five-summary authority content
# ---------------------------------------------------------------------------


def _projection_input_snapshot(
    *,
    turn: int,
    actor_id: str,
    location: str,
    current_action: str,
    tone: str,
    intensity: str = "rising",
    motive: str = "defend_son",
) -> dict[str, Any]:
    def _fact(
        fact_id: str,
        dimension: str,
        key: str,
        value: Any,
        source: str,
        truth: str,
        visibility: str = "public",
    ) -> dict[str, Any]:
        return {
            "schema_version": "w5_fact.v1",
            "fact_id": fact_id,
            "actor_id": actor_id,
            "dimension": dimension,
            "key": key,
            "value": value,
            "source": source,
            "source_event_id": f"ct_{turn:03d}",
            "truth_level": truth,
            "confidence": 1.0,
            "valid_from_turn": turn,
            "valid_until_turn": None,
            "last_confirmed_turn": turn,
            "visibility": visibility,
            "actor_knowledge_scope": [],
            "status": "active",
            "superseded_by_fact_id": None,
            "contradicted_by_fact_id": None,
        }

    return {
        "schema_version": "w5_snapshot.v1",
        "snapshot_id": f"w5s_6b5b_ai_{turn}",
        "story_session_id": "sess_phase_6b5b_ai_parity",
        "turn_number": turn,
        "actors": {
            actor_id: {
                "actor_id": actor_id,
                "actor_type": "human",
                "actor_role_in_scene": "aggressor",
                "involvement_type": "primary",
                "where": [
                    _fact(
                        f"w5f_w_{turn}",
                        "where",
                        "scene_location",
                        location,
                        "participant_state_move",
                        "observed",
                    )
                ],
                "what": [
                    _fact(
                        f"w5f_wact_{turn}",
                        "what",
                        "current_action",
                        current_action,
                        "committed_action",
                        "observed",
                    ),
                    _fact(
                        f"w5f_winter_{turn}",
                        "what",
                        "interaction_type",
                        "confrontation",
                        "committed_action",
                        "observed",
                    ),
                ],
                "how": [
                    _fact(
                        f"w5f_htone_{turn}",
                        "how",
                        "tone",
                        tone,
                        "committed_action",
                        "observed",
                    ),
                    _fact(
                        f"w5f_hint_{turn}",
                        "how",
                        "intensity",
                        intensity,
                        "director_composition",
                        "director_assigned",
                    ),
                ],
                "why": [
                    _fact(
                        f"w5f_wmot_{turn}",
                        "why",
                        "motive",
                        motive,
                        "character_mind_record",
                        "inferred",
                        visibility="private_to_actor",
                    )
                ],
                "freshness_status": "fresh",
                "last_confirmed_turn": turn,
            }
        },
        "conflicts": [],
        "derived_from_event_ids": [f"ct_{turn:03d}"],
        "created_at": f"w5:turn:{turn}",
    }


class TestPhase6B5BNarratorProjectionSemanticContent:
    """Phase 6B-5B parity gate — ``build_w5_projection_for_narrator`` must
    carry semantically meaningful Who / Where / What / How / Why content
    and full ``source_attribution`` / ``truth_attribution``. The strict-on
    prompt names this projection as the actor-situation authority, so its
    semantic content is a Phase 6B-5C readiness gate."""

    def _build(self) -> Any:
        from ai_stack.actor_tracking import build_w5_projection_for_narrator

        previous = _projection_input_snapshot(
            turn=2,
            actor_id="veronique",
            location="foyer",
            current_action="enters",
            tone="quiet",
        )
        current = _projection_input_snapshot(
            turn=3,
            actor_id="veronique",
            location="parlor",
            current_action="accuses",
            tone="sharp",
        )
        return build_w5_projection_for_narrator(
            current,
            actor_id="veronique",
            previous_snapshot=previous,
        ).to_dict()

    def test_who_summary_identifies_actor_and_role(self) -> None:
        proj = self._build()
        who = proj["who_summary"]
        assert who["actor_id"] == "veronique"
        assert who["actor_type"] == "human"
        assert who["actor_role_in_scene"] == "aggressor"
        assert who["involvement_type"] == "primary"

    def test_where_summary_supplies_current_previous_and_change(self) -> None:
        proj = self._build()
        where = proj["where_summary"]
        assert where["current_location"] == "parlor"
        assert where["previous_location"] == "foyer"
        assert where["location_changed"] is True
        assert where["facts"]["scene_location"] == "parlor"
        # The strict prompt's hard-cut replacement signal is derived from
        # these fields; the structural attribution must be present so admin
        # diagnostics can correlate.
        assert (
            proj["source_attribution"]["where_summary.location_changed"]
            == "derived_from_where_facts"
        )
        assert (
            proj["truth_attribution"]["where_summary.location_changed"]
            == "observed"
        )

    def test_what_summary_is_observed_action_not_polluted_by_how(self) -> None:
        proj = self._build()
        what_facts = proj["what_summary"]["facts"]
        assert what_facts["current_action"] == "accuses"
        assert what_facts["interaction_type"] == "confrontation"
        for how_key in ("tone", "intensity", "manner", "pace", "physicality"):
            assert how_key not in what_facts, (
                f"How attribute '{how_key}' must not appear under "
                "what_summary.facts; ADR-0063 / ADR-0065 keep How first-class"
            )

    def test_how_summary_is_first_class_with_per_fact_truth(self) -> None:
        proj = self._build()
        how_facts = proj["how_summary"]["facts"]
        assert how_facts["tone"] == "sharp"
        assert how_facts["intensity"] == "rising"
        # The per-fact truth attribution lets the narrator distinguish
        # director-assigned How from committed-action How.
        assert (
            proj["truth_attribution"]["how_summary.facts.tone"] == "observed"
        )
        assert (
            proj["truth_attribution"]["how_summary.facts.intensity"]
            == "director_assigned"
        )
        assert (
            proj["source_attribution"]["how_summary.facts.tone"]
            == "committed_action"
        )

    def test_why_summary_is_soft_inferred_truth(self) -> None:
        proj = self._build()
        why_facts = proj["why_summary"]["facts"]
        assert why_facts["motive"] == "defend_son"
        # ADR-0063 + ADR-0065: never observed.
        assert (
            proj["truth_attribution"]["why_summary.facts.motive"] == "inferred"
        )
        assert (
            proj["source_attribution"]["why_summary.facts.motive"]
            == "character_mind_record"
        )

    def test_observed_why_is_rejected_by_model(self) -> None:
        """Negative test: the dataclass forbids constructing OBSERVED Why
        facts. ADR-0063 + ADR-0065 invariant: inferred Why may never be
        promoted to observed truth without a separate engine-owned commit
        path."""

        from ai_stack.actor_tracking.models import (
            W5Dimension,
            W5Fact,
            W5FactStatus,
            W5Source,
            W5TruthLevel,
            W5VisibilityScope,
        )

        with pytest.raises(Exception):
            W5Fact(
                schema_version="w5_fact.v1",
                fact_id="bad",
                actor_id="veronique",
                dimension=W5Dimension.WHY,
                key="motive",
                value="defend_son",
                source=W5Source.COMMITTED_ACTION,
                source_event_id="ct_999",
                truth_level=W5TruthLevel.OBSERVED,
                confidence=1.0,
                valid_from_turn=3,
                valid_until_turn=None,
                last_confirmed_turn=3,
                visibility=W5VisibilityScope.PUBLIC,
                actor_knowledge_scope=(),
                status=W5FactStatus.ACTIVE,
                superseded_by_fact_id=None,
                contradicted_by_fact_id=None,
            )


# ---------------------------------------------------------------------------
# 4) Phase 6B-5B does not regress earlier gates
# ---------------------------------------------------------------------------


class TestPhase6B5BNonRegression:
    """Phase 6B-5B must not weaken Phase 6B-3B or Phase 6B-1 contracts."""

    def test_strict_flag_is_independent_of_projection_flag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ai_stack.actor_tracking import (
            w5_ast_narrator_strict_enabled,
            w5_projection_flag_states,
        )

        # Projection flag toggled; strict flag remains default-off.
        for projection_value in ("0", "1", "false", "true", "off", "on"):
            monkeypatch.setenv("W5_AST_NARRATOR_PROJECTION_ENABLED", projection_value)
            monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
            assert w5_ast_narrator_strict_enabled() is False
            assert w5_projection_flag_states()["narrator_strict"] is False

    def test_strict_on_does_not_disable_other_w5_projections(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ai_stack.actor_tracking import w5_projection_flag_states

        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        states = w5_projection_flag_states()
        # Default-on Phase 6B-1 flags remain on under strict mode.
        assert states["narrator"] is True
        assert states["director"] is True
        assert states["npc"] is True
        assert states["narrator_strict"] is True
