"""Phase 6B-5B — narrator strict-mode parity contract (world-engine side).

Phase 6B-5B is the test-contract rewrite phase that precedes the Phase 6B-5C
default-on flip of ``W5_AST_NARRATOR_STRICT_ENABLED`` (see
[ADR-0065](../../docs/ADR/adr-0065-w5-narrator-strict-mode-default-actor-situation-surface.md)).

These tests strengthen — rather than replace — the existing strict-migration
coverage in:

- ``world-engine/tests/test_story_runtime_w5_narrator_projection.py``
- ``world-engine/tests/test_story_runtime_w5_narrator_strict_migration.py``
- ``ai_stack/tests/test_w5_actor_tracking_phase_6b3b_narrator_strict_migration.py``

The Phase 6B-5B gate is semantic, end-to-end, and dual-posture:

A. **Strict OFF** (current default, must continue to work)

   - ``source_facts["transition_from_previous"]`` remains a first-class
     legacy authority on the narrator path.
   - The narrator prompt still names ``transition_from_previous`` as the
     fallback when ``source_facts.w5_projection`` is absent.
   - Admin diagnostics expose ``w5.legacy_transition_parity =
     legacy_compat_visible`` so operators can correlate narrator blocks
     against the legacy surface.
   - The W5 narrator projection (default-on Phase 6B-1) coexists with the
     legacy block and supplies typed Who / Where / What / How / Why summaries
     with full ``source_attribution`` / ``truth_attribution`` regardless of
     the strict flag.

B. **Strict ON** (future default; gate target)

   - ``source_facts["transition_from_previous"]`` is removed from the
     top-level narrator contract.
   - ``source_facts._legacy_compat["transition_from_previous"]`` remains as a
     non-authoritative debug breadcrumb and explicitly names the W5 narrator
     projection as the actor-situation authority.
   - The narrator prompt:

     - explicitly treats ``source_facts.w5_projection`` as the *sole*
       actor-situation authority;
     - explicitly tells the narrator *not* to consult
       ``source_facts.transition_from_previous``;
     - mentions every W5 summary (``who_summary``, ``where_summary``,
       ``what_summary``, ``how_summary``, ``why_summary``) by name;
     - keeps How first-class with manner/tone/intensity/pace/physicality/
       method/style attributes;
     - marks inferred Why as soft / never-spoken-as-fact;
     - uses ``where_summary.location_changed`` (not the legacy
       ``transition_from_previous.location_changed``) as the scene-shift
       steering signal — i.e. the hard-cut / directed-transition
       replacement signal lives on the W5 projection.

   - W5 ``where_summary`` semantically supplies ``current_location``,
     ``previous_location``, and ``location_changed``.
   - W5 ``what_summary`` carries observed action/interaction facts without
     absorbing How (no ``tone`` / ``intensity`` / ``manner`` leak into
     ``what_summary.facts``).
   - W5 ``how_summary`` is first-class with semantically meaningful values
     and a ``how_summary.facts.*`` ``truth_attribution`` per fact.
   - W5 ``why_summary`` carries inferred motive only, with
     ``truth_attribution`` marked ``inferred`` (never ``observed``).
   - Admin diagnostics expose
     ``w5.narrator_strict_enabled = True``,
     ``w5.location_changed_source = w5_history_projection`` (W5-first), and
     ``w5.legacy_transition_parity = demoted_to_legacy_compat``.

The tests below assert semantic content, not field-presence-only. They do not
flip the runtime default, do not remove ``transition_from_previous``, do not
remove ``_legacy_compat``, do not weaken malformed-W5 fallback, and do not
mutate committed output. They prove that the future default-on flip is safe.

How remains first-class. Inferred Why remains soft truth.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from app.story_runtime.manager import StoryRuntimeManager, StorySession


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
# Helpers — typed W5 snapshot + GoC-shaped legacy narrator block
# ---------------------------------------------------------------------------


def _w5_fact(
    *,
    fact_id: str,
    actor_id: str,
    dimension: str,
    key: str,
    value: Any,
    source: str,
    truth: str,
    turn: int,
    visibility: str = "public",
    scope: tuple[str, ...] = (),
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
        "actor_knowledge_scope": list(scope),
        "status": "active",
        "superseded_by_fact_id": None,
        "contradicted_by_fact_id": None,
    }


def _w5_snapshot(
    *,
    turn: int,
    actor_id: str,
    location: str,
    current_action: str = "speaks",
    interaction_type: str = "confrontation",
    tone: str = "measured",
    intensity: str = "rising",
    motive: str = "defend_son",
) -> dict[str, Any]:
    return {
        "schema_version": "w5_snapshot.v1",
        "snapshot_id": f"w5s_6b5b_{turn}",
        "story_session_id": "sess_phase_6b5b_parity",
        "turn_number": turn,
        "actors": {
            actor_id: {
                "actor_id": actor_id,
                "actor_type": "human",
                "actor_role_in_scene": "aggressor",
                "involvement_type": "primary",
                "where": [
                    _w5_fact(
                        fact_id=f"w5f_w_{turn}",
                        actor_id=actor_id,
                        dimension="where",
                        key="scene_location",
                        value=location,
                        source="participant_state_move",
                        truth="observed",
                        turn=turn,
                    ),
                ],
                "what": [
                    _w5_fact(
                        fact_id=f"w5f_what_action_{turn}",
                        actor_id=actor_id,
                        dimension="what",
                        key="current_action",
                        value=current_action,
                        source="committed_action",
                        truth="observed",
                        turn=turn,
                    ),
                    _w5_fact(
                        fact_id=f"w5f_what_inter_{turn}",
                        actor_id=actor_id,
                        dimension="what",
                        key="interaction_type",
                        value=interaction_type,
                        source="committed_action",
                        truth="observed",
                        turn=turn,
                    ),
                ],
                "how": [
                    _w5_fact(
                        fact_id=f"w5f_how_tone_{turn}",
                        actor_id=actor_id,
                        dimension="how",
                        key="tone",
                        value=tone,
                        source="committed_action",
                        truth="observed",
                        turn=turn,
                    ),
                    _w5_fact(
                        fact_id=f"w5f_how_int_{turn}",
                        actor_id=actor_id,
                        dimension="how",
                        key="intensity",
                        value=intensity,
                        source="director_composition",
                        truth="director_assigned",
                        turn=turn,
                    ),
                ],
                "why": [
                    _w5_fact(
                        fact_id=f"w5f_why_motive_{turn}",
                        actor_id=actor_id,
                        dimension="why",
                        key="motive",
                        value=motive,
                        source="character_mind_record",
                        truth="inferred",
                        turn=turn,
                        visibility="private_to_actor",
                    ),
                ],
                "freshness_status": "fresh",
                "last_confirmed_turn": turn,
            }
        },
        "conflicts": [],
        "derived_from_event_ids": [f"ct_{turn:03d}"],
        "created_at": f"w5:turn:{turn}",
    }


def _make_session(
    *,
    actor_id: str = "veronique",
    previous_location: str = "foyer",
    current_location: str = "parlor",
) -> StorySession:
    previous = _w5_snapshot(
        turn=2,
        actor_id=actor_id,
        location=previous_location,
        current_action="enters",
        tone="quiet",
    )
    current = _w5_snapshot(
        turn=3,
        actor_id=actor_id,
        location=current_location,
        current_action="accuses",
        tone="sharp",
    )
    return StorySession(
        session_id="sess_phase_6b5b_parity",
        module_id="god_of_carnage",
        runtime_projection={"human_actor_id": actor_id},
        created_at=datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 22, 12, 0, 5, tzinfo=timezone.utc),
        turn_counter=3,
        current_scene_id="opening",
        w5_history=[previous, current],
        w5_latest_snapshot=current,
    )


def _legacy_narrator_block() -> dict[str, Any]:
    """A narrator block as it would be emitted under strict-off:
    ``source_facts.transition_from_previous`` first-class."""

    return {
        "id": "phase-6b5b-narrator-1",
        "block_type": "narrator",
        "speaker_label": "Narrator",
        "actor_id": None,
        "target_actor_id": None,
        "text": "...",
        "canonical_step_id": "opening_004_room_perception_winter_light",
        "canonical_mandatory_beat_id": "room_perception_winter_light",
        "source_facts": {
            "location": {"id": "parlor"},
            "transition_from_previous": {
                "kind": "location_or_scene_shift",
                "location_changed": True,
                "scene_changed": True,
                "previous_location": {"id": "foyer"},
                "current_location": {"id": "parlor"},
                "directed_transition": {
                    "kind": "hard_cut",
                    "applies_to": "first_visible_block_only",
                },
            },
        },
    }


def _strict_demoted_block() -> dict[str, Any]:
    """A narrator block as it would be emitted under strict-on:
    ``transition_from_previous`` demoted to ``_legacy_compat``."""

    legacy_payload = {
        "kind": "location_or_scene_shift",
        "location_changed": True,
        "scene_changed": True,
        "previous_location": {"id": "foyer"},
        "current_location": {"id": "parlor"},
        "directed_transition": {
            "kind": "hard_cut",
            "applies_to": "first_visible_block_only",
        },
    }
    return {
        "id": "phase-6b5b-narrator-1",
        "block_type": "narrator",
        "speaker_label": "Narrator",
        "actor_id": None,
        "target_actor_id": None,
        "text": "...",
        "canonical_step_id": "opening_004_room_perception_winter_light",
        "canonical_mandatory_beat_id": "room_perception_winter_light",
        "source_facts": {
            "location": {"id": "parlor"},
            "_legacy_compat": {
                "transition_from_previous": legacy_payload,
                "authority": "w5_projection",
                "notice": (
                    "non-authoritative; W5 narrator projection is the "
                    "actor-situation authority"
                ),
            },
        },
    }


def _enrich(session: StorySession, blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Invoke the W5 narrator-projection enrichment helper without booting
    the full StoryRuntimeManager."""

    class _Proxy:
        _w5_ast_narrator_projection_enabled = staticmethod(
            StoryRuntimeManager._w5_ast_narrator_projection_enabled
        )

    return StoryRuntimeManager._maybe_enrich_blocks_with_w5_narrator_projection(
        _Proxy(),  # type: ignore[arg-type]
        session=session,
        source_blocks=blocks,
    )


def _build_narrator_prompt(target_language: str = "de") -> str:
    return StoryRuntimeManager._narrator_path_output_prompt(
        source_blocks=[_legacy_narrator_block()],
        narrator_path={
            "source_input_mode": "semantic_frames_with_fallback_blocks",
            "path_id": "goc_opening_canonical_path",
            "canonical_step_ids": ["opening_004_room_perception_winter_light"],
            "narrative_source_frames": [],
        },
        source_language="en",
        target_language=target_language,
    )


class _AdminParityHarness:
    """Minimal harness exposing ``get_w5_langfuse_metadata`` without booting
    the full manager — same approach as the Phase 6B-3B F20 tests."""

    def __init__(self, session: StorySession) -> None:
        self._session = session

    def get_session(self, session_id: str) -> StorySession:
        assert session_id == self._session.session_id
        return self._session

    _latest_w5_validation_outcome = staticmethod(
        StoryRuntimeManager._latest_w5_validation_outcome
    )
    get_w5_langfuse_metadata = (  # type: ignore[assignment]
        StoryRuntimeManager.get_w5_langfuse_metadata
    )


# ---------------------------------------------------------------------------
# 1) W5 projection authoritative content (independent of strict flag)
# ---------------------------------------------------------------------------


class TestPhase6B5BW5ProjectionSemanticAuthority:
    """Phase 6B-5B parity gate — the W5 narrator projection that the
    strict-on prompt names as the actor-situation authority must carry
    *semantically meaningful* Who / Where / What / How / Why content with
    full source/truth attribution. These assertions hold under both strict
    postures because the projection itself is independent of the strict
    flag; only the *primary-authority* status of the projection vs.
    ``transition_from_previous`` changes."""

    @pytest.mark.parametrize("strict_value", [None, "false", "true"])
    def test_w5_where_summary_supplies_current_location_and_change(
        self, monkeypatch: pytest.MonkeyPatch, strict_value: str | None
    ) -> None:
        if strict_value is None:
            monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        else:
            monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", strict_value)
        session = _make_session(current_location="parlor", previous_location="foyer")
        enriched = _enrich(session, [_legacy_narrator_block()])
        proj = enriched[0]["source_facts"]["w5_projection"]
        where = proj["where_summary"]
        assert where["current_location"] == "parlor", (
            "W5 where_summary must supply the actor's current location as the "
            "strict-on actor-situation authority"
        )
        assert where["previous_location"] == "foyer"
        assert where["location_changed"] is True, (
            "W5 where_summary.location_changed must be the strict-on "
            "replacement for transition_from_previous.location_changed"
        )
        # The scene_location is preserved under facts so audit can trace the
        # underlying W5 fact, not just the promoted convenience field.
        assert where["facts"]["scene_location"] == "parlor"

    @pytest.mark.parametrize("strict_value", [None, "false", "true"])
    def test_w5_what_summary_is_action_observed_and_not_polluted_by_how(
        self, monkeypatch: pytest.MonkeyPatch, strict_value: str | None
    ) -> None:
        if strict_value is None:
            monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        else:
            monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", strict_value)
        session = _make_session()
        enriched = _enrich(session, [_legacy_narrator_block()])
        proj = enriched[0]["source_facts"]["w5_projection"]
        what_facts = proj["what_summary"]["facts"]
        assert what_facts["current_action"] == "accuses"
        assert what_facts["interaction_type"] == "confrontation"
        # ADR-0063 + ADR-0065: How is first-class, not folded into What.
        for how_key in ("tone", "intensity", "manner", "pace", "physicality", "method", "style"):
            assert how_key not in what_facts, (
                f"How attribute '{how_key}' must not appear in what_summary.facts; "
                "How is first-class per ADR-0063 / ADR-0065."
            )
        # truth_attribution preserved per fact (semantic, not field-presence).
        assert (
            proj["truth_attribution"]["what_summary.facts.current_action"]
            == "observed"
        )
        assert (
            proj["source_attribution"]["what_summary.facts.current_action"]
            == "committed_action"
        )

    @pytest.mark.parametrize("strict_value", [None, "false", "true"])
    def test_w5_how_summary_is_first_class_with_truth_attribution(
        self, monkeypatch: pytest.MonkeyPatch, strict_value: str | None
    ) -> None:
        if strict_value is None:
            monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        else:
            monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", strict_value)
        session = _make_session()
        enriched = _enrich(session, [_legacy_narrator_block()])
        proj = enriched[0]["source_facts"]["w5_projection"]
        how_facts = proj["how_summary"]["facts"]
        assert how_facts["tone"] == "sharp", "tone must be the strongest How fact"
        assert how_facts["intensity"] == "rising"
        # Per-fact truth_attribution carries the W5 truth level, which is
        # the semantic gate that prevents How from being narrated as observed
        # truth when it was director-assigned.
        assert (
            proj["truth_attribution"]["how_summary.facts.tone"] == "observed"
        )
        assert (
            proj["truth_attribution"]["how_summary.facts.intensity"]
            == "director_assigned"
        )

    @pytest.mark.parametrize("strict_value", [None, "false", "true"])
    def test_w5_why_summary_is_soft_inferred_truth(
        self, monkeypatch: pytest.MonkeyPatch, strict_value: str | None
    ) -> None:
        if strict_value is None:
            monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        else:
            monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", strict_value)
        session = _make_session()
        enriched = _enrich(session, [_legacy_narrator_block()])
        proj = enriched[0]["source_facts"]["w5_projection"]
        why_facts = proj["why_summary"]["facts"]
        assert why_facts["motive"] == "defend_son"
        # ADR-0063 + ADR-0065: inferred Why must remain soft truth — never
        # promoted to observed. The projection records this via
        # truth_attribution, and the strict-on prompt names it as such.
        assert (
            proj["truth_attribution"]["why_summary.facts.motive"] == "inferred"
        ), (
            "why_summary motive must be attributed as inferred; W5 must never "
            "present inferred Why as observed truth"
        )
        assert (
            proj["source_attribution"]["why_summary.facts.motive"]
            == "character_mind_record"
        )

    @pytest.mark.parametrize("strict_value", [None, "false", "true"])
    def test_w5_who_summary_identifies_actor(
        self, monkeypatch: pytest.MonkeyPatch, strict_value: str | None
    ) -> None:
        if strict_value is None:
            monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        else:
            monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", strict_value)
        session = _make_session()
        enriched = _enrich(session, [_legacy_narrator_block()])
        proj = enriched[0]["source_facts"]["w5_projection"]
        who = proj["who_summary"]
        # Who summary identifies the actor and scope so the narrator does not
        # need to read transition_from_previous to know which actor is on
        # stage.
        assert who["actor_id"] == "veronique"
        assert who["actor_type"] == "human"
        assert who["actor_role_in_scene"] == "aggressor"
        assert who["involvement_type"] == "primary"
        assert proj["actor_id"] == "veronique"
        assert proj["target_consumer"] == "narrator"


# ---------------------------------------------------------------------------
# 2) source_facts shape under strict-off vs strict-on
# ---------------------------------------------------------------------------


class TestPhase6B5BSourceFactsAuthorityShape:
    """Phase 6B-5B parity gate — the *primary* actor-situation surface in
    ``source_facts`` switches according to the strict flag, and the W5
    projection is always present (Phase 6B-1 default-on)."""

    def test_strict_off_keeps_transition_from_previous_as_first_class(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        session = _make_session()
        enriched = _enrich(session, [_legacy_narrator_block()])
        facts = enriched[0]["source_facts"]
        # Legacy first-class authority remains.
        assert "transition_from_previous" in facts
        legacy = facts["transition_from_previous"]
        assert legacy["location_changed"] is True
        assert legacy["directed_transition"]["kind"] == "hard_cut"
        # _legacy_compat namespace MUST NOT be created under strict-off; that
        # namespace exists only as a strict-on demotion target.
        assert "_legacy_compat" not in facts
        # W5 projection coexists as the additional default-on input.
        assert "w5_projection" in facts

    def test_strict_on_only_carries_legacy_compat_breadcrumb(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Under strict-on, the narrator path is responsible for demoting
        the legacy block into ``_legacy_compat``. We verify the demoted
        shape this phase's tests expect, alongside the W5 projection."""

        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        session = _make_session()
        enriched = _enrich(session, [_strict_demoted_block()])
        facts = enriched[0]["source_facts"]
        # Top-level transition_from_previous is removed in strict-on.
        assert "transition_from_previous" not in facts, (
            "Phase 6B-5B strict-on: transition_from_previous must NOT appear "
            "as a top-level source_facts authority."
        )
        # The demoted breadcrumb is preserved with W5-authority markers.
        legacy_compat = facts["_legacy_compat"]
        assert isinstance(legacy_compat, dict)
        assert legacy_compat["authority"] == "w5_projection"
        notice = str(legacy_compat["notice"])
        assert "W5" in notice
        assert "non-authoritative" in notice or "non_authoritative" in notice
        # The original hard-cut breadcrumb is still inspectable for operator
        # parity audit but is no longer the primary authority.
        assert (
            legacy_compat["transition_from_previous"]["directed_transition"]["kind"]
            == "hard_cut"
        )
        # The W5 projection is still present — and authoritative — and the
        # location_changed signal it carries matches the demoted breadcrumb.
        proj = facts["w5_projection"]
        assert proj["where_summary"]["location_changed"] is True
        assert proj["where_summary"]["current_location"] == "parlor"
        assert proj["where_summary"]["previous_location"] == "foyer"

    def test_strict_on_w5_projection_replaces_legacy_hard_cut_signal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the strict prompt drops legacy hard_cut guidance, the
        replacement signal must come from W5: where_summary.location_changed
        plus current/previous location."""

        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        session = _make_session(previous_location="foyer", current_location="parlor")
        enriched = _enrich(session, [_strict_demoted_block()])
        proj = enriched[0]["source_facts"]["w5_projection"]
        # The strict prompt expects all three signals from W5 alone.
        assert proj["where_summary"]["location_changed"] is True
        assert proj["where_summary"]["current_location"] == "parlor"
        assert proj["where_summary"]["previous_location"] == "foyer"
        # No top-level transition_from_previous to disagree.
        assert "transition_from_previous" not in enriched[0]["source_facts"]


# ---------------------------------------------------------------------------
# 3) Narrator prompt-contract (strict-off vs strict-on)
# ---------------------------------------------------------------------------


class TestPhase6B5BPromptContract:
    """Phase 6B-5B parity gate — the narrator output prompt must encode the
    W5-vs-legacy authority split semantically, not by field-presence-only."""

    def test_strict_off_prompt_keeps_legacy_fallback_guidance(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        prompt = _build_narrator_prompt()
        # Legacy fallback guidance is still present and explicitly conditional
        # on w5_projection being absent.
        assert "transition_from_previous" in prompt
        assert (
            "Use transition_from_previous only as a fallback" in prompt
            or "as a fallback when w5_projection is absent" in prompt
        )
        # hard_cut authored guidance remains for the unstrict path.
        assert "hard_cut" in prompt
        # W5 summaries are still named in the unstrict path so the projection
        # has consumer-side parity from day one.
        for summary in (
            "where_summary",
            "what_summary",
            "how_summary",
            "why_summary",
        ):
            assert summary in prompt

    def test_strict_on_prompt_names_w5_projection_as_sole_authority(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        prompt = _build_narrator_prompt()
        # The strict-on prompt explicitly designates the W5 projection as
        # the actor-situation authority — not merely "preferred" or
        # "available". This is the semantic gate for Phase 6B-5C.
        assert "source_facts.w5_projection" in prompt
        assert "sole actor-situation authority" in prompt, (
            "Phase 6B-5B strict-on prompt must name w5_projection as the "
            "sole actor-situation authority"
        )

    def test_strict_on_prompt_forbids_consulting_legacy_transition(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        prompt = _build_narrator_prompt()
        # The strict-on prompt explicitly tells the narrator not to consult
        # the legacy transition surface, and labels _legacy_compat as a
        # non-authoritative debug breadcrumb only.
        assert "Do not consult source_facts.transition_from_previous" in prompt
        assert "_legacy_compat" in prompt
        assert "non-authoritative" in prompt
        # The unstrict-only fallback paragraph must be absent.
        assert "Use transition_from_previous only as a fallback" not in prompt
        assert "source_facts.transition_from_previous.location_changed" not in prompt
        assert (
            "source_facts.transition_from_previous.directed_transition" not in prompt
        )

    def test_strict_on_prompt_names_all_five_w5_summaries(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        prompt = _build_narrator_prompt()
        # Strict-on must explicitly enumerate all five W5 summaries so the
        # narrator does not need to infer the contract from absence.
        for summary in (
            "who_summary",
            "where_summary",
            "what_summary",
            "how_summary",
            "why_summary",
        ):
            assert summary in prompt, (
                f"strict-on prompt must explicitly name {summary} as the "
                f"actor-situation authority for that dimension"
            )

    def test_strict_on_prompt_uses_w5_location_changed_as_shift_signal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        prompt = _build_narrator_prompt()
        # The replacement for transition_from_previous.location_changed is the
        # W5 where_summary.location_changed signal; the strict prompt steers
        # scene-shift orientation from W5, not from the legacy block.
        assert "where_summary.location_changed" in prompt

    def test_strict_on_prompt_keeps_how_first_class_with_attributes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        prompt = _build_narrator_prompt()
        assert "how_summary" in prompt
        assert "first-class" in prompt
        assert "never folded into what" in prompt or "not folded into what" in prompt
        # The strict-on prompt enumerates How attributes as steering signals.
        for attr in (
            "tone",
            "manner",
            "intensity",
            "pace",
            "physicality",
            "method",
            "style",
        ):
            assert attr in prompt, (
                f"strict-on prompt must keep '{attr}' first-class under "
                "how_summary"
            )

    def test_strict_on_prompt_marks_inferred_why_as_soft_truth(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        prompt = _build_narrator_prompt()
        assert "why_summary" in prompt
        # Inferred Why must remain visibly soft / never-spoken-as-fact, even
        # under strict-on. ADR-0063 + ADR-0065.
        assert "inferred" in prompt.lower()
        assert (
            "never spoken as fact" in prompt
            or "never spoken as observed fact" in prompt
        )


# ---------------------------------------------------------------------------
# 4) Admin / diagnostics parity (strict-off vs strict-on)
# ---------------------------------------------------------------------------


class TestPhase6B5BAdminDiagnosticsParity:
    """Phase 6B-5B parity gate — ``get_w5_langfuse_metadata`` must report
    W5-first location-change semantics under both postures and only switch
    the legacy parity label according to the strict flag."""

    def test_strict_off_reports_w5_first_and_keeps_legacy_compat_visible(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        session = _make_session()
        harness = _AdminParityHarness(session)
        meta = harness.get_w5_langfuse_metadata(session.session_id)
        # W5 history projection drives the signal even under strict-off.
        assert meta["w5.location_changed_this_turn"] is True
        assert meta["w5.location_changed_source"] == "w5_history_projection"
        assert meta["w5.narrator_strict_enabled"] is False
        # Operator parity surface remains visible.
        assert meta["w5.legacy_transition_parity"] == "legacy_compat_visible"
        # Semantic admin gates: How presence and inferred-Why presence are
        # surfaced from the W5 snapshot, not from any legacy block.
        assert meta["w5.has_how"] is True
        assert meta["w5.has_inferred_why"] is True

    def test_strict_on_reports_w5_first_and_demotes_legacy_parity_label(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        session = _make_session()
        harness = _AdminParityHarness(session)
        meta = harness.get_w5_langfuse_metadata(session.session_id)
        assert meta["w5.location_changed_this_turn"] is True
        assert meta["w5.location_changed_source"] == "w5_history_projection"
        assert meta["w5.narrator_strict_enabled"] is True
        assert meta["w5.legacy_transition_parity"] == "demoted_to_legacy_compat"
        # Semantic gates remain populated under strict-on.
        assert meta["w5.has_how"] is True
        assert meta["w5.has_inferred_why"] is True

    def test_strict_on_ignores_disagreeing_transition_from_previous_in_diagnostics(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ADR-0065 admin requirement: location-change evidence must be
        computed from W5 history/projection, NOT from a narrator block's
        ``transition_from_previous.location_changed`` claim. We seed a
        diagnostics entry whose stray legacy claim disagrees with W5 and
        verify the bridge follows W5 anyway."""

        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        same_previous = _w5_snapshot(turn=2, actor_id="veronique", location="foyer")
        same_current = _w5_snapshot(turn=3, actor_id="veronique", location="foyer")
        session = StorySession(
            session_id="sess_phase_6b5b_conflict",
            module_id="god_of_carnage",
            runtime_projection={"human_actor_id": "veronique"},
            created_at=datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 22, 12, 0, 5, tzinfo=timezone.utc),
            turn_counter=3,
            current_scene_id="opening",
            w5_history=[same_previous, same_current],
            w5_latest_snapshot=same_current,
        )
        # Stray legacy claim says location_changed=True; W5 says False.
        session.diagnostics.append(
            {
                "scene_blocks": [
                    {
                        "block_type": "narrator",
                        "source_facts": {
                            "transition_from_previous": {"location_changed": True}
                        },
                    }
                ]
            }
        )
        harness = _AdminParityHarness(session)
        meta = harness.get_w5_langfuse_metadata(session.session_id)
        # W5-first wins.
        assert meta["w5.location_changed_this_turn"] is False
        assert meta["w5.location_changed_source"] == "w5_history_projection"
        assert meta["w5.narrator_strict_enabled"] is True
        assert meta["w5.legacy_transition_parity"] == "demoted_to_legacy_compat"


# ---------------------------------------------------------------------------
# 5) Safety: opt-out and malformed-W5 paths remain testable
# ---------------------------------------------------------------------------


class TestPhase6B5BSafetyFallbacksStillRequired:
    """Phase 6B-5B does not remove safety branches. We pin that they are
    still testable so Phase 6B-5C cannot silently drop them in the same
    change as the default flip."""

    def test_explicit_projection_opt_out_keeps_legacy_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NARRATOR_PROJECTION_ENABLED", "0")
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        session = _make_session()
        blocks = [_legacy_narrator_block()]
        enriched = _enrich(session, blocks)
        # Projection enrichment is suppressed.
        assert enriched is blocks
        assert "w5_projection" not in enriched[0]["source_facts"]

    def test_malformed_w5_snapshot_falls_back_with_diagnostic(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        session = _make_session()
        session.w5_latest_snapshot = {
            "schema_version": "w5_snapshot.v1",
            "this_is": "garbage",
        }
        enriched = _enrich(session, [_legacy_narrator_block()])
        # Safety fallback: no projection added, diagnostic recorded.
        assert "w5_projection" not in enriched[0]["source_facts"]
        kinds = [d.get("diagnostic_kind") for d in session.diagnostics]
        assert "w5_narrator_projection_failed" in kinds
