"""Phase 6B-3B — narrator strict migration semantic tests (world-engine side).

Pins the F18 prompt-text migration and the F20 admin parity bridge labeling
for the new opt-in ``W5_AST_NARRATOR_STRICT_ENABLED`` flag.

These tests focus on three contracts:

1. **F18 narrator prompt.** Under strict-OFF the prompt continues to instruct
   the narrator that ``source_facts.transition_from_previous`` is the
   fallback when ``source_facts.w5_projection`` is absent. Under strict-ON
   the fallback paragraph is removed and the prompt treats
   ``source_facts.w5_projection`` as the sole actor-situation authority.
   In both postures the prompt must explicitly preserve Who / Where / What /
   How / Why guidance. How is first-class and not folded into What. Inferred
   Why is marked as inferred / soft truth and must not be described as
   observed fact.

2. **F20 admin parity bridge.** ``StoryRuntimeManager.get_w5_langfuse_metadata``
   computes ``w5.location_changed_this_turn`` from the typed W5 history
   projection on both strict postures (no ``transition_from_previous``
   inspection). Under strict-ON the response advertises
   ``w5.narrator_strict_enabled = True`` and annotates the legacy parity
   surface as ``demoted_to_legacy_compat``. Under strict-OFF the same
   primary signal is computed but the legacy parity surface remains
   ``legacy_compat_visible`` so operators can correlate against
   ``source_facts.transition_from_previous`` from committed narrator blocks.

3. The strict flag does not weaken Actor Lane, Commit/Readiness,
   ``validation_outcome``, ADR-0033, ADR-0061, ADR-0063, the Canonical Path,
   or W5 validation. How remains first-class. Inferred Why remains soft truth.
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
# F18 — narrator prompt strict-flag migration
# ---------------------------------------------------------------------------


def _build_narrator_prompt(target_language: str = "de") -> str:
    return StoryRuntimeManager._narrator_path_output_prompt(
        source_blocks=[
            {
                "id": "opening-narrator-path-1",
                "block_type": "narrator",
                "canonical_step_id": "opening_001_parc_montsouris_edge",
                "canonical_step_sequence": 1,
                "canonical_mandatory_beat_id": "park_edge_establishing_image",
                "visual_emphasis": {},
                "source_refs": ["canonical_path/001_parc_montsouris_edge.yaml"],
                "source_facts": {},
            }
        ],
        narrator_path={
            "source_input_mode": "semantic_frames_with_fallback_blocks",
            "path_id": "goc_opening_canonical_path",
            "canonical_step_ids": ["opening_001_parc_montsouris_edge"],
            "narrative_source_frames": [],
        },
        source_language="en",
        target_language=target_language,
    )


class TestF18NarratorPromptStrictMigration:
    def test_strict_off_preserves_legacy_fallback_paragraph(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        prompt = _build_narrator_prompt()
        # Legacy fallback guidance is still present.
        assert "transition_from_previous" in prompt
        assert (
            "Use transition_from_previous only as a fallback" in prompt
            or "as a fallback when w5_projection is absent" in prompt
        )
        # hard_cut directed-transition instruction remains for the unstrict path.
        assert "hard_cut" in prompt

    def test_strict_off_explicit_false_preserves_legacy_fallback_paragraph(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "false")
        prompt = _build_narrator_prompt()
        assert "transition_from_previous" in prompt
        assert "hard_cut" in prompt

    def test_strict_on_drops_legacy_fallback_paragraph(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        prompt = _build_narrator_prompt()
        # The strict prompt must not instruct the narrator to use
        # transition_from_previous as the primary fallback.
        assert "Use transition_from_previous only as a fallback" not in prompt
        assert (
            "source_facts.transition_from_previous.location_changed" not in prompt
        )
        assert (
            "source_facts.transition_from_previous.directed_transition" not in prompt
        )
        # The legacy_compat namespace is mentioned only as a non-authoritative
        # debug breadcrumb; it must not be promoted as primary authority.
        assert "non-authoritative" in prompt
        # The prompt instructs the narrator to disregard transition_from_previous.
        assert "Do not consult source_facts.transition_from_previous" in prompt

    @pytest.mark.parametrize("strict_value", [None, "false", "true"])
    def test_prompt_preserves_who_where_what_how_why_guidance_on_all_postures(
        self, monkeypatch: pytest.MonkeyPatch, strict_value: str | None
    ) -> None:
        if strict_value is None:
            monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        else:
            monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", strict_value)
        prompt = _build_narrator_prompt()
        # Where / What / How / Why each have an explicit summary-level mention
        # under both postures.
        for dim in ("where", "what", "how", "why"):
            assert f"{dim}_summary" in prompt, (
                f"narrator prompt must preserve {dim}_summary guidance"
            )
        # Who guidance is preserved either as ``who_summary`` (strict) or as
        # the inline ``who/where/what/how/why summaries`` enumeration (unstrict).
        assert "who_summary" in prompt or "who/where/what/how/why" in prompt
        # Where signal: location_changed remains a steering signal.
        assert "location_changed" in prompt
        # What signal: current_action / interaction_type remains named.
        assert "current_action" in prompt or "interaction_type" in prompt

    @pytest.mark.parametrize("strict_value", [None, "false", "true"])
    def test_prompt_keeps_how_first_class_and_not_folded_into_what(
        self, monkeypatch: pytest.MonkeyPatch, strict_value: str | None
    ) -> None:
        if strict_value is None:
            monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        else:
            monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", strict_value)
        prompt = _build_narrator_prompt()
        assert "how_summary" in prompt
        assert "first-class" in prompt
        assert "never folded into what" in prompt or "not folded into what" in prompt
        # how-only attributes are named under how_summary, not under what_summary.
        for attr in ("tone", "manner", "intensity", "pace", "physicality", "method", "style"):
            assert attr in prompt

    @pytest.mark.parametrize("strict_value", [None, "false", "true"])
    def test_prompt_marks_inferred_why_as_soft_truth(
        self, monkeypatch: pytest.MonkeyPatch, strict_value: str | None
    ) -> None:
        if strict_value is None:
            monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        else:
            monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", strict_value)
        prompt = _build_narrator_prompt()
        assert "why_summary" in prompt
        # Either explicit "inferred"/"soft" wording must accompany the why_summary
        # guidance — Inferred Why must not be described as observed fact.
        assert "inferred" in prompt.lower()
        # The prompt explicitly forbids narrating Why as observed fact.
        assert "never spoken as fact" in prompt or "never spoken as observed fact" in prompt


# ---------------------------------------------------------------------------
# F20 — admin parity bridge under strict flag
# ---------------------------------------------------------------------------


def _w5_snapshot(turn: int, *, actor_id: str, location: str) -> dict[str, Any]:
    def _fact(
        fact_id: str, dim: str, key: str, value: Any, source: str, truth: str,
        visibility: str = "public",
    ) -> dict[str, Any]:
        return {
            "schema_version": "w5_fact.v1",
            "fact_id": fact_id,
            "actor_id": actor_id,
            "dimension": dim,
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
        "snapshot_id": f"w5s_admin_{turn}",
        "story_session_id": "sess_admin_parity",
        "turn_number": turn,
        "actors": {
            actor_id: {
                "actor_id": actor_id,
                "actor_type": "human",
                "actor_role_in_scene": "primary",
                "involvement_type": "primary",
                "where": [
                    _fact("w5f_w", "where", "scene_location", location,
                          "participant_state_move", "observed"),
                ],
                "what": [
                    _fact("w5f_what", "what", "current_action", "speaks",
                          "committed_action", "observed"),
                ],
                "how": [
                    _fact("w5f_how", "how", "tone", "measured",
                          "committed_action", "observed"),
                ],
                "why": [],
                "freshness_status": "fresh",
                "last_confirmed_turn": turn,
            }
        },
        "conflicts": [],
        "derived_from_event_ids": [f"ct_{turn:03d}"],
        "created_at": f"w5:turn:{turn}",
    }


def _make_admin_session() -> StorySession:
    previous = _w5_snapshot(turn=2, actor_id="veronique", location="foyer")
    current = _w5_snapshot(turn=3, actor_id="veronique", location="parlor")
    return StorySession(
        session_id="sess_admin_parity",
        module_id="god_of_carnage",
        runtime_projection={"human_actor_id": "veronique"},
        created_at=datetime(2026, 5, 21, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 21, 12, 0, 5, tzinfo=timezone.utc),
        turn_counter=3,
        current_scene_id="opening",
        w5_history=[previous, current],
        w5_latest_snapshot=current,
    )


class _AdminParityManagerHarness:
    """Minimal harness exposing get_w5_langfuse_metadata without booting the
    full StoryRuntimeManager. The method only touches ``self.get_session`` and
    ``self._latest_w5_validation_outcome`` (a staticmethod)."""

    def __init__(self, session: StorySession) -> None:
        self._session = session

    def get_session(self, session_id: str) -> StorySession:
        assert session_id == self._session.session_id
        return self._session

    _latest_w5_validation_outcome = staticmethod(
        StoryRuntimeManager._latest_w5_validation_outcome
    )
    get_w5_langfuse_metadata = StoryRuntimeManager.get_w5_langfuse_metadata  # type: ignore[assignment]


class TestF20AdminParityBridge:
    def test_strict_off_reads_w5_history_first_for_location_changed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("W5_AST_NARRATOR_STRICT_ENABLED", raising=False)
        session = _make_admin_session()
        harness = _AdminParityManagerHarness(session)
        meta = harness.get_w5_langfuse_metadata(session.session_id)
        assert meta["w5.location_changed_this_turn"] is True
        assert meta["w5.location_changed_source"] == "w5_history_projection"
        assert meta["w5.narrator_strict_enabled"] is False
        # Legacy compat parity surface is visible for operator correlation.
        assert meta["w5.legacy_transition_parity"] == "legacy_compat_visible"

    def test_strict_on_uses_w5_first_and_demotes_legacy_parity_label(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        session = _make_admin_session()
        harness = _AdminParityManagerHarness(session)
        meta = harness.get_w5_langfuse_metadata(session.session_id)
        # Location_changed signal source remains W5.
        assert meta["w5.location_changed_this_turn"] is True
        assert meta["w5.location_changed_source"] == "w5_history_projection"
        assert meta["w5.narrator_strict_enabled"] is True
        # Strict explicitly demotes the legacy parity surface.
        assert meta["w5.legacy_transition_parity"] == "demoted_to_legacy_compat"

    def test_strict_on_does_not_read_transition_from_previous_for_location_changed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Even if a narrator block in session diagnostics carries a
        ``transition_from_previous.location_changed=True`` claim that
        disagrees with W5 history, strict-mode admin metadata uses the W5
        history signal."""

        monkeypatch.setenv("W5_AST_NARRATOR_STRICT_ENABLED", "true")
        # Build a session whose W5 history reports no location change but
        # whose diagnostics contain a stray legacy transition claim.
        same_loc = _w5_snapshot(turn=3, actor_id="veronique", location="foyer")
        previous_same = _w5_snapshot(turn=2, actor_id="veronique", location="foyer")
        session = StorySession(
            session_id="sess_admin_parity_conflict",
            module_id="god_of_carnage",
            runtime_projection={"human_actor_id": "veronique"},
            created_at=datetime(2026, 5, 21, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 21, 12, 0, 5, tzinfo=timezone.utc),
            turn_counter=3,
            current_scene_id="opening",
            w5_history=[previous_same, same_loc],
            w5_latest_snapshot=same_loc,
        )
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
        harness = _AdminParityManagerHarness(session)
        meta = harness.get_w5_langfuse_metadata(session.session_id)
        # W5 says no change; the strict bridge agrees.
        assert meta["w5.location_changed_this_turn"] is False
        assert meta["w5.location_changed_source"] == "w5_history_projection"
        assert meta["w5.narrator_strict_enabled"] is True
