"""GoC knowledge runtime gates with German player-visible fixtures."""

from __future__ import annotations

from ai_stack.story_runtime.god_of_carnage.god_of_carnage_knowledge_runtime_gates import build_knowledge_path_summary
from ai_stack.story_runtime.turn.god_of_carnage_turn_seams import run_validation_seam
from ai_stack.story_runtime.god_of_carnage.god_of_carnage_yaml_authority import (
    load_goc_hard_forbidden_rules_yaml,
    load_goc_opening_scene_sequence_yaml,
)


def _knowledge() -> tuple[dict, dict]:
    return load_goc_opening_scene_sequence_yaml(), load_goc_hard_forbidden_rules_yaml()


def _actor_lane_context(role: str = "annette_reille") -> dict:
    return {
        "human_actor_id": role,
        "selected_player_role": role,
        "ai_forbidden_actor_ids": [role],
        "ai_allowed_actor_ids": ["michel_longstreet", "veronique_vallon", "alain_reille"],
    }


def _generation(structured: dict) -> dict:
    return {
        "success": True,
        "content": "",
        "metadata": {"structured_output": structured},
    }


def _validate_opening(structured: dict, *, scene_phase: str = "phase_1") -> dict:
    opening, hard = _knowledge()
    text = "\n".join(
        str(item)
        for item in structured.get("narration_summary", [])
        if str(item).strip()
    )
    return run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=[{"effect_type": "narrative_projection", "description": text}],
        generation=_generation(structured),
        actor_lane_context=_actor_lane_context(),
        opening_scene_sequence=opening,
        hard_forbidden_rules=hard,
        turn_input_class="opening",
        scene_plan_record={"opening_first_playable_scene_phase": scene_phase},
        current_scene_id="scene_1_opening",
    )


def _full_opening_structured() -> dict:
    return {
        "opening_event_ids": [
            "event_01_triggering_incident",
            "event_02_adult_consequence",
            "event_03_arrival_threshold",
            "event_04_apartment_as_stage",
            "event_05_role_anchor",
            "event_06_first_playable_moment",
        ],
        "narration_summary": [
            (
                "Auf dem Schulhof ist der Streit zwischen den Jungen ernst geworden: "
                "ein Stock, ein verletzter Zahn, ein Moment, den die Erwachsenen nicht mehr ignorieren koennen."
            ),
            "Darum treffen sich die Eltern nun in der Wohnung der Vallons und halten die Hoeflichkeit fest.",
            "An der Tuer wird aus Besuch eine Pflicht; Gaeste und Gastgeber treten ueber dieselbe Schwelle.",
            "Im Wohnzimmer ordnen Stuehle, Couchtisch, Kunstbaende und Tulpen die Spannung wie eine Buehne.",
            "Annette Reille ist als Gast im Raum, mit Platz zu sprechen, zu beobachten oder sich zurueckzuziehen.",
            "Jetzt wartet ein erster spielbarer Moment, und die naechste Handlung bleibt offen.",
        ],
        "spoken_lines": [
            {"speaker_id": "michel_longstreet", "text": "Vielleicht beginnen wir ruhig."}
        ],
        "action_lines": [],
    }


def test_forbidden_player_speech_is_rejected_by_hard_forbidden_detection() -> None:
    opening, hard = _knowledge()
    outcome = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=[{"effect_type": "narrative_projection", "description": "Annette spricht."}],
        generation=_generation(
            {
                "narration_summary": ["Der Raum wartet."],
                "spoken_lines": [
                    {"speaker_id": "annette_reille", "text": "Ich sage jetzt, was wir tun."}
                ],
            }
        ),
        actor_lane_context=_actor_lane_context(),
        opening_scene_sequence=opening,
        hard_forbidden_rules=hard,
        turn_input_class="opening",
    )

    assert outcome["status"] == "rejected"
    assert outcome["reason"] == "ai_controlled_human_actor"
    detection = outcome["hard_forbidden_detection"]
    assert detection["reject_on_detected"] == ["forced_player_speech"]
    assert outcome["hard_forbidden_absent"] is False


def test_summary_only_opening_is_recoverable_not_committable() -> None:
    outcome = _validate_opening(
        {
            "narration_summary": [
                (
                    "Nach dem Vorfall auf dem Schulhof treffen sich die Eltern in der Wohnung, "
                    "um alles zivilisiert zu klaeren."
                )
            ],
            "spoken_lines": [],
            "action_lines": [],
        }
    )

    assert outcome["status"] == "rejected"
    assert outcome["reason"] == "summary_only_opening"
    assert outcome["recoverable_rejection"] is True
    assert outcome["hard_forbidden_detection"]["recover_on_detected"] == ["summary_only_opening"]
    assert outcome["opening_summary_only_absent"] is False


def test_six_narrator_opening_with_event_coverage_is_not_summary_only() -> None:
    structured = _full_opening_structured()
    structured["spoken_lines"] = []
    structured["action_lines"] = []

    outcome = _validate_opening(structured)

    assert outcome["reason"] != "summary_only_opening"
    assert outcome["opening_summary_only_absent"] is True
    assert outcome["opening_event_coverage_pass"] is True


def test_npc_exposition_of_room_is_rejected() -> None:
    outcome = _validate_opening(
        {
            "narration_summary": ["Die Eltern stehen im Wohnzimmer."],
            "runtime_gate_detections": [
                {"detection_key": "npc_world_explanation", "source": "semantic_runtime_marker"}
            ],
            "spoken_lines": [
                {
                    "speaker_id": "michel_longstreet",
                    "text": (
                        "Du siehst das Wohnzimmer, die Wohnung, den Tisch und die Tuer; "
                        "ich erklaere dir, warum dieser Raum wichtig ist."
                    ),
                }
            ],
            "action_lines": [],
        }
    )

    assert outcome["status"] == "rejected"
    assert outcome["reason"] == "npc_world_explanation"
    assert outcome["hard_boundary_failure"] is True
    assert outcome["hard_forbidden_detection"]["reject_on_detected"] == ["npc_world_explanation"]


def test_opening_events_and_phase_one_first_playable_pass_for_full_fixture() -> None:
    outcome = _validate_opening(_full_opening_structured())

    assert outcome["status"] == "approved"
    assert outcome["opening_event_coverage_pass"] is True
    coverage = outcome["opening_event_coverage"]
    assert coverage["missing_event_ids"] == []
    assert coverage["first_playable_scene_phase_expected"] == "phase_1"
    assert coverage["first_playable_scene_phase_actual"] == "phase_1"
    assert outcome["hard_forbidden_absent"] is True
    assert outcome["opening_summary_only_absent"] is True


def test_opening_transition_mismatch_blocks_commit() -> None:
    outcome = _validate_opening(_full_opening_structured(), scene_phase="phase_2")

    assert outcome["status"] == "rejected"
    assert outcome["reason"] == "opening_first_playable_scene_phase_mismatch"
    assert outcome["opening_event_coverage"]["first_playable_scene_phase_expected"] == "phase_1"
    assert outcome["opening_event_coverage"]["first_playable_scene_phase_actual"] == "phase_2"


def test_turn0_ldss_fallback_rejects_mid_conflict_npc_line() -> None:
    """STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P2: a Turn-0 NPC line that
    jumps into prosecutorial / mid-conflict framing must trigger the recover_on
    npc_phase_one_premature_escalation detection."""
    outcome = _validate_opening(
        {
            **_full_opening_structured(),
            "spoken_lines": [
                {
                    "speaker_id": "veronique_vallon",
                    "text": "You keep turning this into a legal question. It is not a legal question.",
                }
            ],
        }
    )
    assert outcome["status"] == "rejected"
    detection = outcome["hard_forbidden_detection"]
    keys = [hit.get("detection_key") for hit in (detection.get("detected") or [])]
    assert "npc_phase_one_premature_escalation" in keys
    # Recover_on detections must not commit as healthy.
    assert outcome["hard_forbidden_absent"] is False


def test_turn0_opening_npc_lines_follow_phase_one_policy() -> None:
    """P2: a polite phase-1 NPC line (ritual greeting / hospitality fiction) must NOT
    trigger npc_phase_one_premature_escalation."""
    outcome = _validate_opening(
        {
            **_full_opening_structured(),
            "spoken_lines": [
                {"speaker_id": "michel_longstreet", "text": "Vielleicht beginnen wir ruhig."}
            ],
        }
    )
    detection = outcome["hard_forbidden_detection"]
    keys = [hit.get("detection_key") for hit in (detection.get("detected") or [])]
    assert "npc_phase_one_premature_escalation" not in keys


def test_turn0_opening_npc_line_in_german_also_triggers_phase_one_constraint() -> None:
    """P2: detector must catch German runtime language variants too (e.g. 'Wie könnt ihr'),
    not only English markers, since session output language may be German."""
    outcome = _validate_opening(
        {
            **_full_opening_structured(),
            "spoken_lines": [
                {
                    "speaker_id": "veronique_vallon",
                    "text": "Wie könnt ihr behaupten, das sei juristisch — es ist eine Frechheit.",
                }
            ],
        }
    )
    detection = outcome["hard_forbidden_detection"]
    keys = [hit.get("detection_key") for hit in (detection.get("detected") or [])]
    assert "npc_phase_one_premature_escalation" in keys


def test_opening_summary_only_detector_ignores_actor_lane_escape() -> None:
    """STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P3: actor lane presence
    must not suppress summary-only detection when narrator realization is thin."""
    outcome = _validate_opening(
        {
            "narration_summary": [
                "Zwei Familien treffen sich in einer Wohnung wegen eines Vorfalls auf dem Schulhof.",
                "Du bist Annette Reille; die Wohnung gehört dir und das Treffen war deine Idee.",
                "Im Salon stehen Tulpen und Kunstbände; vier Stühle warten um einen Tisch.",
            ],
            "spoken_lines": [
                {"speaker_id": "michel_longstreet", "text": "Vielleicht beginnen wir ruhig."}
            ],
            "action_lines": [],
        }
    )
    # Detector must still flag summary-only because narrator realization is abstract and
    # narrative_events were not covered, even though an actor lane exists.
    assert outcome["status"] == "rejected"
    assert outcome["reason"] == "summary_only_opening"
    assert outcome["opening_summary_only_absent"] is False
    detection = outcome["hard_forbidden_detection"]
    detected_keys = [hit.get("detection_key") for hit in (detection.get("detected") or [])]
    assert "summary_only_opening" in detected_keys


def test_opening_summary_only_detector_requires_scenic_narrator_realization() -> None:
    """P3: summary-only detector must flag missing scenic event realization."""
    outcome = _validate_opening(
        {
            "narration_summary": [
                "Eine Wohnung. Ein Vorfall. Ein höfliches Gespräch ist geplant.",
            ],
            "spoken_lines": [],
            "action_lines": [],
        }
    )
    assert outcome["status"] == "rejected"
    assert outcome["reason"] == "summary_only_opening"
    detection = outcome["hard_forbidden_detection"]
    detected_hits = [hit for hit in (detection.get("detected") or []) if hit.get("detection_key") == "summary_only_opening"]
    assert detected_hits
    reasons = detected_hits[0].get("summary_only_reasons") or []
    # At least one of the new structural reasons must surface.
    assert any(r in reasons for r in {
        "too_few_visible_blocks_for_opening_policy",
        "too_few_narrator_blocks_for_opening_policy",
        "missing_scenic_event_realization",
        "narrator_blocks_are_abstract_summary",
    })


def test_opening_summary_only_absent_drops_to_zero_for_three_summary_blocks_plus_actor_line() -> None:
    """P3: the exact failure shape observed in staging (3 abstract narrator blocks + 1 actor
    line, no event coverage) must produce opening_summary_only_absent = False."""
    outcome = _validate_opening(
        {
            "narration_summary": [
                "Two couples meet in a Paris apartment on behalf of their children.",
                "You are Annette Reille; the apartment is yours.",
                "The salon: four chairs arranged around a low table.",
            ],
            "spoken_lines": [
                {"speaker_id": "veronique_vallon", "text": "You keep turning this into a legal question."}
            ],
            "action_lines": [
                {"speaker_id": "alain_reille", "text": "Alain glances at his phone but does not pick it up."}
            ],
        }
    )
    assert outcome["opening_summary_only_absent"] is False
    assert outcome["status"] == "rejected"
    assert outcome["reason"] == "summary_only_opening"


def test_path_summary_exposes_runtime_gate_diagnostics() -> None:
    opening, hard = _knowledge()
    structured = _full_opening_structured()
    blocks = [
        {"block_type": "narrator", "text": text, "opening_event_id": event_id}
        for text, event_id in zip(structured["narration_summary"], structured["opening_event_ids"], strict=False)
    ] + [
        {
            "block_type": "actor_line",
            "actor_id": "michel_longstreet",
            "speaker_label": "Michel",
            "text": "Vielleicht beginnen wir ruhig.",
        }
    ]
    summary = build_knowledge_path_summary(
        graph_state={
            "opening_scene_sequence": opening,
            "hard_forbidden_rules": hard,
            "turn_input_class": "opening",
            "scene_plan_record": {"opening_first_playable_scene_phase": "phase_1"},
            "current_scene_id": "scene_1_opening",
            "generation": _generation(structured),
        },
        event={
            "turn_number": 0,
            "turn_kind": "opening",
            "visible_output_bundle": {"scene_blocks": blocks},
        },
        actor_lane_context=_actor_lane_context(),
    )

    assert summary["opening_scene_sequence_id"] == "goc_opening_sequence_v1"
    assert summary["opening_event_coverage_pass"] is True
    assert summary["hard_forbidden_absent"] is True
    assert summary["opening_summary_only_absent"] is True
