"""Phase 2 Stage F — Off-Stage Update Scaffold tests.

Covers ``ai_stack/off_stage_updates.py``:

* Off-stage candidate only emitted when the chosen NPC is *not* visible.
* New-person / new-room / new-plot-fact / free-text-body all become closed-enum
  blockers; the candidate is then suppressed.
* Structured payloads only — no ``text`` / ``body`` / ``narration`` fields.
* ``canonical_path_advanced`` and ``mandatory_beat_consumed`` are invariant False.
* ``validate_external_candidate`` rejects payloads that try to advance the
  canonical path or consume a mandatory beat.
* ADR-0039 anti-hardcoding: no Pi/Π keys, no hardcoded NPC IDs.

Governance:
* ADR-0058 — Stage F off-stage scaffolding
* ADR-0061 — Gathering pause / off-stage discipline
* ADR-0039 — Vocabulary discipline
"""

from __future__ import annotations

import re
import uuid

import pytest

from ai_stack.off_stage_updates import (
    BLOCKER_CANONICAL_PATH_ADVANCE_ATTEMPTED,
    BLOCKER_FREE_TEXT_BODY,
    BLOCKER_MANDATORY_BEAT_CONSUME_ATTEMPTED,
    BLOCKER_NEW_PERSON,
    BLOCKER_NEW_PLOT_FACT,
    BLOCKER_NEW_ROOM,
    BLOCKER_NO_NPC_CHOSEN,
    BLOCKER_NO_OFF_STAGE_ACTOR,
    BLOCKER_REASONS,
    CANDIDATE_KIND_OFF_STAGE_MEMORY_NOTE,
    CANDIDATE_KIND_RELATIONSHIP_TENSION_UPDATE,
    OffStageUpdateInputs,
    SAFETY_GATE_BLOCKED,
    SAFETY_GATE_NOT_APPLICABLE,
    SAFETY_GATE_PASS,
    SAFETY_GATE_RESULTS,
    SCHEMA_OFF_STAGE_MEMORY_UPDATE_CANDIDATE,
    SCHEMA_OFF_STAGE_RELATIONSHIP_UPDATE_CANDIDATE,
    build_off_stage_update_candidate,
    validate_external_candidate,
)


def _tid() -> str:
    return str(uuid.uuid4())


def _inputs(**over) -> OffStageUpdateInputs:
    base = dict(
        tick_id=_tid(),
        chosen_actor_id="npc_a",
        chosen_action_kind="speak",
        motivation_scores={"npc_a": 0.72},
        visible_npc_ids=["npc_b"],
        known_actor_ids=["npc_a", "npc_b", "npc_c"],
        known_room_ids=["foyer", "parlor"],
        gathering_paused=False,
    )
    base.update(over)
    return OffStageUpdateInputs(**base)


class TestApplicability:
    def test_off_stage_npc_produces_candidate(self):
        result = build_off_stage_update_candidate(_inputs())
        assert result["off_stage_update_candidate"] is True
        assert result["off_stage_safety_gate_result"] == SAFETY_GATE_PASS
        assert result["relationship_update_candidate"] is not None
        assert result["memory_update_candidate"] is not None

    def test_visible_npc_produces_no_candidate(self):
        result = build_off_stage_update_candidate(
            _inputs(chosen_actor_id="npc_b", visible_npc_ids=["npc_b"]),
        )
        assert result["off_stage_update_candidate"] is False
        assert result["off_stage_safety_gate_result"] == SAFETY_GATE_NOT_APPLICABLE
        assert BLOCKER_NO_OFF_STAGE_ACTOR in result["blockers"]

    def test_no_npc_chosen_produces_no_candidate(self):
        result = build_off_stage_update_candidate(_inputs(chosen_actor_id=None))
        assert result["off_stage_update_candidate"] is False
        assert result["off_stage_safety_gate_result"] == SAFETY_GATE_NOT_APPLICABLE
        assert BLOCKER_NO_NPC_CHOSEN in result["blockers"]


class TestNewPersonRejection:
    def test_new_npc_outside_known_set_is_blocked(self):
        result = build_off_stage_update_candidate(
            _inputs(chosen_actor_id="stranger", known_actor_ids=["npc_a", "npc_b"]),
        )
        assert result["off_stage_update_candidate"] is False
        assert BLOCKER_NEW_PERSON in result["blockers"]
        assert result["off_stage_safety_gate_result"] == SAFETY_GATE_BLOCKED

    def test_empty_known_actor_ids_blocks_any_candidate(self):
        """If the module surface declares no actors, off-stage is impossible."""
        result = build_off_stage_update_candidate(
            _inputs(known_actor_ids=[]),
        )
        assert result["off_stage_update_candidate"] is False
        assert BLOCKER_NEW_PERSON in result["blockers"]


class TestStructuredOnly:
    def test_relationship_candidate_has_no_free_text_fields(self):
        result = build_off_stage_update_candidate(_inputs())
        candidate = result["relationship_update_candidate"]
        for key in ("text", "body", "narration", "description"):
            assert key not in candidate
        assert candidate["structured_only"] is True

    def test_memory_candidate_has_no_free_text_fields(self):
        result = build_off_stage_update_candidate(_inputs())
        candidate = result["memory_update_candidate"]
        for key in ("text", "body", "narration", "description"):
            assert key not in candidate
        assert candidate["structured_only"] is True

    def test_candidate_kinds_are_closed_enum(self):
        result = build_off_stage_update_candidate(_inputs())
        assert (
            result["relationship_update_candidate"]["candidate_kind"]
            == CANDIDATE_KIND_RELATIONSHIP_TENSION_UPDATE
        )
        assert (
            result["memory_update_candidate"]["candidate_kind"]
            == CANDIDATE_KIND_OFF_STAGE_MEMORY_NOTE
        )

    def test_schema_versions(self):
        result = build_off_stage_update_candidate(_inputs())
        assert (
            result["relationship_update_candidate"]["schema_version"]
            == SCHEMA_OFF_STAGE_RELATIONSHIP_UPDATE_CANDIDATE
        )
        assert (
            result["memory_update_candidate"]["schema_version"]
            == SCHEMA_OFF_STAGE_MEMORY_UPDATE_CANDIDATE
        )


class TestInvariants:
    def test_canonical_path_never_advanced(self):
        result = build_off_stage_update_candidate(_inputs())
        assert result["canonical_path_advanced"] is False

    def test_mandatory_beat_never_consumed(self):
        result = build_off_stage_update_candidate(_inputs())
        assert result["mandatory_beat_consumed"] is False

    def test_invariants_hold_when_blocked(self):
        result = build_off_stage_update_candidate(
            _inputs(chosen_actor_id="stranger", known_actor_ids=["npc_a"]),
        )
        assert result["canonical_path_advanced"] is False
        assert result["mandatory_beat_consumed"] is False

    def test_invariants_hold_when_no_off_stage_actor(self):
        result = build_off_stage_update_candidate(
            _inputs(chosen_actor_id="npc_b", visible_npc_ids=["npc_b"]),
        )
        assert result["canonical_path_advanced"] is False
        assert result["mandatory_beat_consumed"] is False


class TestSafetyGateEnum:
    def test_gate_value_is_in_closed_enum(self):
        for inp in (
            _inputs(),
            _inputs(chosen_actor_id=None),
            _inputs(chosen_actor_id="npc_b", visible_npc_ids=["npc_b"]),
            _inputs(chosen_actor_id="stranger", known_actor_ids=["npc_a"]),
        ):
            result = build_off_stage_update_candidate(inp)
            assert result["off_stage_safety_gate_result"] in SAFETY_GATE_RESULTS

    def test_blockers_are_all_closed_enum_values(self):
        for inp in (
            _inputs(),
            _inputs(chosen_actor_id="stranger", known_actor_ids=["npc_a"]),
            _inputs(chosen_actor_id="npc_b", visible_npc_ids=["npc_b"]),
            _inputs(chosen_actor_id=None),
        ):
            result = build_off_stage_update_candidate(inp)
            for b in result["blockers"]:
                assert b in BLOCKER_REASONS, f"non-enum blocker {b!r}"


class TestExternalValidator:
    """validate_external_candidate guards candidates built by other layers."""

    def test_unknown_actor_blocked(self):
        bl = validate_external_candidate(
            {"actor_id": "intruder"},
            known_actor_ids=["npc_a"],
            known_room_ids=[],
        )
        assert BLOCKER_NEW_PERSON in bl

    def test_unknown_room_blocked(self):
        bl = validate_external_candidate(
            {"actor_id": "npc_a", "room_id": "elsewhere"},
            known_actor_ids=["npc_a"],
            known_room_ids=["foyer"],
        )
        assert BLOCKER_NEW_ROOM in bl

    def test_free_text_body_blocked(self):
        bl = validate_external_candidate(
            {"actor_id": "npc_a", "text": "I conspire against the host."},
            known_actor_ids=["npc_a"],
            known_room_ids=[],
        )
        assert BLOCKER_FREE_TEXT_BODY in bl

    def test_plot_fact_blocked(self):
        bl = validate_external_candidate(
            {
                "actor_id": "npc_a",
                "plot_fact": "the host is secretly married to the lawyer",
            },
            known_actor_ids=["npc_a"],
            known_room_ids=[],
        )
        assert BLOCKER_NEW_PLOT_FACT in bl

    def test_canonical_path_advance_blocked(self):
        bl = validate_external_candidate(
            {"actor_id": "npc_a", "canonical_path_advance": True},
            known_actor_ids=["npc_a"],
            known_room_ids=[],
        )
        assert BLOCKER_CANONICAL_PATH_ADVANCE_ATTEMPTED in bl

    def test_mandatory_beat_consume_blocked(self):
        bl = validate_external_candidate(
            {"actor_id": "npc_a", "mandatory_beat_consume": True},
            known_actor_ids=["npc_a"],
            known_room_ids=[],
        )
        assert BLOCKER_MANDATORY_BEAT_CONSUME_ATTEMPTED in bl

    def test_clean_candidate_no_blockers(self):
        bl = validate_external_candidate(
            {"actor_id": "npc_a", "observed_motivation_score": 0.7},
            known_actor_ids=["npc_a"],
            known_room_ids=["foyer"],
        )
        assert bl == []


class TestADR0039Discipline:
    _PI_PATTERNS = [
        re.compile(r"\bPi\d+\b"),
        re.compile(r"\bΠ\d+\b"),
        re.compile(r"\bpi_\d+\b"),
    ]
    _FORBIDDEN_NPC_LITERALS = ("veronique", "michel", "annette", "alain")

    def _source(self) -> str:
        from ai_stack import off_stage_updates as mod
        with open(mod.__file__, "r", encoding="utf-8") as fh:
            return fh.read()

    def test_no_pi_keys_in_module_source(self):
        src = self._source()
        for pat in self._PI_PATTERNS:
            assert not pat.search(src), f"Pi/Π key in module: {pat.pattern}"

    def test_no_hardcoded_npc_ids_in_module_source(self):
        src = self._source().lower()
        for literal in self._FORBIDDEN_NPC_LITERALS:
            assert literal not in src, f"hardcoded NPC id '{literal}' in module"

    def test_no_pi_keys_in_candidate_payloads(self):
        result = build_off_stage_update_candidate(_inputs())
        flat = repr(result)
        for pat in self._PI_PATTERNS:
            assert not pat.search(flat), f"Pi/Π in candidate output: {pat.pattern}"
