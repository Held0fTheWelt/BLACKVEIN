from __future__ import annotations

from app.story_runtime_shell_readout import build_story_runtime_shell_readout, frame_story_runtime_visible_output_bundle


def _payload() -> dict[str, object]:
    return {
        "interpreted_input": {"kind": "speech", "confidence": 0.88},
        "generation": {"success": True, "metadata": {}},
        "graph_diagnostics": {"errors": []},
        "retrieval": {"domain": "runtime", "status": "ok"},
        "routing": {"selected_model": "mock"},
        "selected_scene_function": "repair_or_stabilize",
        "selected_responder_set": [{"actor_id": "veronique"}],
        "social_state_record": {
            "prior_continuity_classes": ["blame_pressure", "repair_attempt"],
            "scene_pressure_state": "high_blame",
            "active_thread_count": 2,
            "thread_pressure_summary_present": True,
            "guidance_phase_key": "containment",
            "responder_asymmetry_code": "blame_on_host_spouse_axis",
            "social_risk_band": "high",
        },
    }


def test_build_story_runtime_shell_readout_exposes_failed_exit_response_fields() -> None:
    state = {
        "current_scene_id": "hallway_threshold",
        "committed_state": {
            "current_scene_id": "hallway_threshold",
            "last_open_pressures": ["exit_pressure", "departure_shame"],
            "last_committed_consequences": ["movement_reframed_as_failed_repair"],
            "narrative_thread_continuity": {"thread_pressure_level": "high", "thread_count": 2},
        },
    }
    last_diagnostic = {
        "selected_scene_function": "repair_or_stabilize",
        "selected_responder_set": [{"actor_id": "veronique"}],
        "social_state_record": {
            "prior_continuity_classes": ["blame_pressure", "repair_attempt"],
            "scene_pressure_state": "high_blame",
            "active_thread_count": 2,
            "thread_pressure_summary_present": True,
            "guidance_phase_key": "containment",
            "responder_asymmetry_code": "blame_on_host_spouse_axis",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["social_weather_now"].startswith("Exit pressure is dominating the room")
    assert projection["live_surface_now"].startswith("The doorway is the hot surface right now")
    assert projection["carryover_now"] == "The earlier failed-exit wound is still sitting at the doorway; the room has not spent that departure shame."
    assert projection["social_geometry_now"].startswith("Pressure is sitting with the host side and spouse axis")
    assert projection["situational_freedom_now"].startswith("Distance shifts, hovering")
    assert projection["address_pressure_now"].startswith("Veronique is effectively pressing you through failed departure pressure")
    assert projection["social_moment_now"].startswith("This is a failed-exit moment under brittle civility")
    assert projection["response_pressure_now"].startswith("The room is pressing for repair, explanation")
    assert projection["response_performance_signature_now"] == "a principle-first rebuke that uses civility as correction"
    assert projection["response_mask_slip_now"] == "civility hardening into correction"
    assert projection["response_recentering_now"] == "pull the moment back under principle instead of letting the exit close it"
    assert projection["response_address_source_now"] == "Veronique answers from the host side through the spouse axis in failed repair, with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction."
    assert projection["response_exchange_now"] == "Your act drew a failed repair answer because it put the doorway under pressure again, with the earlier failed exit still sitting at the doorway, and let the reply pull the moment back under principle instead of letting the exit close it."
    assert projection["response_exchange_label_now"] == "failed repair"
    assert projection["response_carryover_now"] == "the earlier failed exit still sitting at the doorway"
    assert projection["response_line_prefix_now"] == "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway"
    assert projection["who_answers_now"] == "Veronique is the one answering now; the host side is speaking through spouse embarrassment, with civility hardening into correction."
    assert projection["why_this_reply_now"] == "The room read the act as failed repair, so the host side answered through spouse embarrassment at the doorway and let the reply pull the moment back under principle instead of letting the exit close it, in a principle-first rebuke that uses civility as correction."
    assert projection["observation_foothold_now"] == "You are inside a failed-exit exchange now; the host side is answering through departure pressure, and the reply is trying to pull the moment back under principle instead of letting the exit close it."
    assert projection["room_pressure_now"].startswith("The room feels exit-loaded")
    assert projection["zone_sensitivity_now"].startswith("The doorway zone is socially charged")
    assert projection["salient_object_now"].startswith("The threshold itself")
    assert projection["object_sensitivity_now"].startswith("The threshold itself is carrying object-like pressure")
    assert projection["situational_affordance_now"].startswith("Threshold movement")
    assert projection["role_pressure_now"].startswith("Veronique")
    assert projection["dominant_social_reading_now"].startswith("It is landing as failed repair")
    assert projection["social_axis_now"].startswith("The host side and spouse axis")
    assert projection["host_guest_pressure_now"].startswith("Host-side pressure is carrying more of the room")
    assert projection["spouse_axis_now"].startswith("One partner is carrying social cost")
    assert projection["cross_couple_now"].startswith("Cross-couple strain is live")
    assert projection["pressure_redistribution_now"].startswith("Pressure has shifted from practical movement")
    assert projection["callback_pressure_now"]
    assert projection["callback_role_frame_now"].startswith("The callback is reviving departure shame")
    assert projection["object_social_reading_now"].startswith("Right now the threshold reads as a failed-departure surface")
    assert projection["active_pressure_now"]


def test_build_story_runtime_shell_readout_can_surface_cross_couple_geometry() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["alliance_instability", "blame_pressure", "art_book_pressure"],
            "last_committed_consequences": ["book_handling_reframed_as_status_judgment"],
            "narrative_thread_continuity": {"thread_pressure_level": "high", "thread_count": 2},
        },
    }
    last_diagnostic = {
        "selected_responder_set": [{"actor_id": "annette"}],
        "social_state_record": {
            "prior_continuity_classes": ["alliance_shift", "blame_pressure"],
            "scene_pressure_state": "high_blame",
            "responder_asymmetry_code": "alliance_reposition_active",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["social_weather_now"].startswith("Judgment is dominating the room")
    assert projection["live_surface_now"].startswith("The books are the hot surface right now")
    assert projection["carryover_now"] == "The earlier taste-and-status wound is still sitting on the books, ready to be reused as judgment."
    assert projection["social_geometry_now"].startswith("The room is tilting across the couples")
    assert projection["situational_freedom_now"].startswith("Touching, not touching")
    assert projection["address_pressure_now"].startswith("Annette is effectively pressing you through taste and household judgment")
    assert projection["social_moment_now"].startswith("This is a judgment-and-status moment")
    assert projection["response_pressure_now"].startswith("The room is pressing for restraint or explanation around taste")
    assert projection["response_performance_signature_now"] == "a cutting contradiction that treats principle as performance"
    assert projection["response_mask_slip_now"] == "wit exposing morality as pose"
    assert projection["response_recentering_now"] == "pull the room back to exposed contradiction instead of letting manners cover it"
    assert projection["response_address_source_now"] == "Annette answers from the guest side across the couples in accusation, with cross-couple strain on the books, in a cutting contradiction that treats principle as performance."
    assert projection["response_exchange_now"] == "Your act drew an accusation answer because it put the books under pressure again, with the earlier taste-and-status wound still sitting on the books, and let the reply pull the room back to exposed contradiction instead of letting manners cover it."
    assert projection["response_carryover_now"] == "the earlier taste-and-status wound still sitting on the books"
    assert projection["who_answers_now"] == "Annette is the one answering now; the guest side is speaking through cross-couple strain, with wit exposing morality as pose."
    assert projection["why_this_reply_now"] == "The room read the act as taste and household judgment, so cross-couple strain answered through the books and let the reply pull the room back to exposed contradiction instead of letting manners cover it, in a cutting contradiction that treats principle as performance."
    assert projection["observation_foothold_now"] == "You are inside a judgment exchange now; the guest side is answering through taste, manners, and status, trying to pull the room back to exposed contradiction instead of letting manners cover it."
    assert projection["social_axis_now"].startswith("Cross-couple strain is carrying more of the pressure")
    assert projection["host_guest_pressure_now"].startswith("Pressure is bouncing across host and guest lines")
    assert projection["cross_couple_now"].startswith("Cross-couple strain is sharper than stable pair loyalty")
    assert projection["pressure_redistribution_now"].startswith("Pressure has shifted from object handling")
    assert projection["object_social_reading_now"].startswith("Right now the books read as a taste-and-status wound")
    assert projection["reaction_delta_now"].startswith("Your last move turned object handling into taste and status judgment")
    assert projection["carryover_delta_now"] == "The earlier taste-and-status wound was pulled back onto the books and turned active again."
    assert projection["pressure_shift_delta_now"].startswith("Pressure shifted into cross-couple strain")
    assert projection["hot_surface_delta_now"].startswith("The books are hot because the last move turned them into a fresh taste-and-status wound")




def test_build_story_runtime_shell_readout_can_surface_brittle_repair_over_flowers() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["hospitality_strain", "flower_pressure"],
            "last_committed_consequences": ["touching_flowers_reframed_as_boundary_pressure"],
            "narrative_thread_continuity": {"thread_pressure_level": "moderate", "thread_count": 1},
        },
    }
    last_diagnostic = {
        "selected_scene_function": "repair_or_stabilize",
        "selected_responder_set": [{"actor_id": "michel"}],
        "social_state_record": {
            "scene_pressure_state": "moderate_tension",
            "responder_asymmetry_code": "blame_under_repair_tension",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["response_exchange_label_now"] == "brittle repair"
    assert projection["response_carryover_now"] == "the earlier hospitality-and-manners wound still sitting on the flowers"
    assert projection["response_exchange_now"] == "Your act drew a brittle repair answer because it put the flowers under pressure again, with the earlier hospitality-and-manners wound still sitting on the flowers, and let the reply pull the room back toward manners instead of open alignment."
    assert projection["response_performance_signature_now"] == "a smoothing deflection that offers manners instead of alignment"
    assert projection["response_mask_slip_now"] == "smoothing starting to read as capitulation"
    assert projection["response_recentering_now"] == "pull the room back toward manners instead of open alignment"
    assert projection["response_address_source_now"] == "Michel answers from the host side in brittle repair, with host-side manners strain on the flowers, in a smoothing deflection that offers manners instead of alignment."
    assert projection["response_line_prefix_now"] == "Michel, from the host side, answers in brittle repair with host-side manners strain on the flowers, in a smoothing deflection that offers manners instead of alignment, the earlier hospitality-and-manners wound still sitting on the flowers"
    assert projection["who_answers_now"] == "Michel is the one answering now; the host side is speaking through brittle hospitality pressure, with smoothing starting to read as capitulation."


def test_frame_story_runtime_visible_output_bundle_uses_response_line_prefix_now() -> None:
    projection = {
        "response_line_prefix_now": "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway"
    }
    framed = frame_story_runtime_visible_output_bundle(
        visible_output_bundle={"gm_narration": ["A sharp reply."], "spoken_lines": []},
        shell_readout_projection=projection,
    )
    assert framed["gm_narration"][0].startswith(
        "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway — A sharp reply."
    )


def test_frame_story_runtime_visible_output_bundle_preserves_nonempty_lines() -> None:
    projection = {"response_line_prefix_now": "Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, in a cutting contradiction that treats principle as performance, the earlier taste-and-status wound still sitting on the books"}
    framed = frame_story_runtime_visible_output_bundle(
        visible_output_bundle={"gm_narration": ["She cuts in immediately."], "spoken_lines": ["A sharp aside."]},
        shell_readout_projection=projection,
    )
    assert framed["gm_narration"][0].startswith("Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, in a cutting contradiction that treats principle as performance, the earlier taste-and-status wound still sitting on the books — She cuts in immediately.")
    assert framed["spoken_lines"][0].startswith("Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, in a cutting contradiction that treats principle as performance, the earlier taste-and-status wound still sitting on the books — A sharp aside.")


def test_build_story_runtime_shell_readout_can_surface_hosting_surface_response_anchor() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["hosting_surface_pressure", "drink_pressure"],
            "last_committed_consequences": ["rum_opened_reframed_as_brittle_hospitality"],
            "narrative_thread_continuity": {"thread_pressure_level": "moderate", "thread_count": 1},
        },
    }
    last_diagnostic = {
        "selected_scene_function": "repair_or_stabilize",
        "selected_responder_set": [{"actor_id": "michel"}],
        "social_state_record": {
            "scene_pressure_state": "moderate_tension",
            "responder_asymmetry_code": "blame_under_repair_tension",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["social_weather_now"].startswith("Hospitality pressure is dominating the room")
    assert projection["live_surface_now"].startswith("The hosting surface is the hot surface right now")
    assert projection["salient_object_now"].startswith("The hosting surface is carrying brittle hospitality")
    assert projection["object_sensitivity_now"].startswith("The hosting surface is a hospitality-and-escalation surface")
    assert projection["object_social_reading_now"].startswith("Right now the hosting surface reads as brittle hospitality")
    assert projection["reaction_delta_now"].startswith("Your last move turned the hosting surface into visible hospitality")
    assert projection["carryover_delta_now"] == "The earlier hospitality-and-hosting line was pulled back over the hosting surface instead of settling into decorum."
    assert projection["pressure_shift_delta_now"].startswith("Pressure shifted from domestic hosting")
    assert projection["hot_surface_delta_now"].startswith("The hosting surface is hot because the last move turned drinks")
    assert projection["response_exchange_label_now"] == "brittle repair"
    assert projection["response_carryover_now"] == "the earlier hospitality-and-hosting line still sitting over the hosting surface"
    assert projection["response_exchange_now"] == "Your act drew a brittle repair answer because it put the hosting surface under pressure again, with the earlier hospitality-and-hosting line still sitting over the hosting surface, and let the reply pull the room back toward manners instead of open alignment."
    assert projection["response_performance_signature_now"] == "a smoothing deflection that offers hospitality instead of alignment"
    assert projection["response_mask_slip_now"] == "smoothing starting to read as capitulation"
    assert projection["response_recentering_now"] == "pull the room back toward manners instead of open alignment"
    assert projection["response_address_source_now"] == "Michel answers from the host side in brittle repair, with host-side hospitality strain over the hosting surface, in a smoothing deflection that offers hospitality instead of alignment."
    assert projection["response_line_prefix_now"] == "Michel, from the host side, answers in brittle repair with host-side hospitality strain over the hosting surface, in a smoothing deflection that offers hospitality instead of alignment, the earlier hospitality-and-hosting line still sitting over the hosting surface"


def test_build_story_runtime_shell_readout_can_surface_bathroom_edge_response_anchor() -> None:
    state = {
        "current_scene_id": "bathroom_recovery",
        "committed_state": {
            "current_scene_id": "bathroom_recovery",
            "last_open_pressures": ["cleanup_pressure", "bathroom_contamination"],
            "last_committed_consequences": ["help_at_bathroom_edge_reframed_as_exposure_pressure"],
            "narrative_thread_continuity": {"thread_pressure_level": "moderate", "thread_count": 1},
        },
    }
    last_diagnostic = {
        "selected_responder_set": [{"actor_id": "annette"}],
        "social_state_record": {
            "scene_pressure_state": "moderate_tension",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["live_surface_now"].startswith("The bathroom edge is the hot surface right now")
    assert projection["zone_sensitivity_now"].startswith("The bathroom edge is socially charged")
    assert projection["response_performance_signature_now"] == "a contemptuous dismantling that makes concern sound naive"
    assert projection["response_mask_slip_now"] == "intellectual distance hardening into contempt"
    assert projection["response_recentering_now"] == "pull the room toward exposure instead of polite cover"
    assert projection["response_line_prefix_now"] == "Annette, from the guest side, answers in exposure with guest-side exposure at the bathroom edge, in a contemptuous dismantling that makes concern sound naive, the earlier exposure line still sitting at the bathroom edge"



def test_build_story_runtime_shell_readout_prioritizes_phone_over_hosting_surface_in_compressed_response() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["hosting_surface_pressure", "phone_pressure", "drink_pressure"],
            "last_committed_consequences": ["phone_interrupt_reframed_as_humiliation_pressure"],
            "narrative_thread_continuity": {"thread_pressure_level": "moderate", "thread_count": 1},
        },
    }
    last_diagnostic = {
        "selected_scene_function": "withhold_or_evade",
        "selected_responder_set": [{"actor_id": "alain"}],
        "social_state_record": {
            "scene_pressure_state": "moderate_tension",
            "responder_asymmetry_code": "alliance_reposition_active",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["live_surface_now"].startswith("The phone is the hot surface right now")
    assert projection["response_exchange_label_now"] == "evasive pressure"
    assert projection["response_exchange_now"] == "Your act drew an evasive pressure answer because it put the phone under pressure again, with the earlier humiliation line still sitting on the phone, and let the reply pull the room toward manageability without ever resolving it."
    assert projection["response_performance_signature_now"] == "a tired evasive hedge dressed up as mediation"
    assert projection["response_mask_slip_now"] == "mediation thinning into evasion"
    assert projection["response_recentering_now"] == "pull the room toward manageability without ever resolving it"
    assert projection["response_address_source_now"] == "Alain answers from the guest side across the couples in evasive pressure, with cross-couple humiliation on the phone, in a tired evasive hedge dressed up as mediation."
    assert projection["response_line_prefix_now"] == "Alain, from the guest side across the couples, answers in evasive pressure with cross-couple humiliation on the phone, in a tired evasive hedge dressed up as mediation, the earlier humiliation line still sitting on the phone"
    assert projection["why_this_reply_now"] == "The room read the act through humiliation and public priority, so humiliation pressure pulled a guest side answer onto the phone and let the reply pull the room toward manageability without ever resolving it, in a tired evasive hedge dressed up as mediation."


def test_build_story_runtime_shell_readout_threads_previous_visible_reply_into_same_surface_countermove() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["alliance_instability", "blame_pressure", "art_book_pressure"],
            "last_committed_consequences": ["book_handling_reframed_as_status_judgment"],
            "narrative_thread_continuity": {"thread_pressure_level": "high", "thread_count": 2},
            "previous_reply_continuity_context": {
                "exchange_label": "failed repair",
                "surface_token": "books",
            },
        },
    }
    last_diagnostic = {
        "selected_responder_set": [{"actor_id": "annette"}],
        "social_state_record": {
            "prior_continuity_classes": ["alliance_shift", "blame_pressure"],
            "scene_pressure_state": "high_blame",
            "responder_asymmetry_code": "alliance_reposition_active",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["response_exchange_now"] == "Your act drew an accusation answer because it put the books under pressure again, turning the last failed repair back through the same books, with the earlier taste-and-status wound still sitting on the books, and let the reply pull the room back to exposed contradiction instead of letting manners cover it."
    assert projection["response_line_prefix_now"] == "Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, in a cutting contradiction that treats principle as performance, turning the last failed repair back through the same books, the earlier taste-and-status wound still sitting on the books"
    assert projection["why_this_reply_now"] == "The room read the act as taste and household judgment, so cross-couple strain answered through the books, turning the last failed repair back through the same books, and let the reply pull the room back to exposed contradiction instead of letting manners cover it, in a cutting contradiction that treats principle as performance."


def test_build_story_runtime_shell_readout_prefers_delayed_same_surface_afterlife_over_generic_previous_turn_hook() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["alliance_instability", "blame_pressure", "art_book_pressure"],
            "last_committed_consequences": ["book_handling_reframed_as_status_judgment"],
            "narrative_thread_continuity": {"thread_pressure_level": "high", "thread_count": 3},
            "previous_reply_continuity_context": {
                "exchange_label": "evasive pressure",
                "surface_token": "phone",
            },
            "earlier_reply_continuity_context": {
                "exchange_label": "failed repair",
                "surface_token": "books",
            },
        },
    }
    last_diagnostic = {
        "selected_responder_set": [{"actor_id": "annette"}],
        "social_state_record": {
            "prior_continuity_classes": ["alliance_shift", "blame_pressure"],
            "scene_pressure_state": "high_blame",
            "responder_asymmetry_code": "alliance_reposition_active",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["response_exchange_now"] == "Your act drew an accusation answer because it put the books under pressure again, pulling the earlier failed repair back onto the same books, with the earlier taste-and-status wound still sitting on the books, and let the reply pull the room back to exposed contradiction instead of letting manners cover it."
    assert projection["response_line_prefix_now"] == "Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, in a cutting contradiction that treats principle as performance, pulling the earlier failed repair back onto the same books, the earlier taste-and-status wound still sitting on the books"
    assert projection["why_this_reply_now"] == "The room read the act as taste and household judgment, so cross-couple strain answered through the books, pulling the earlier failed repair back onto the same books, and let the reply pull the room back to exposed contradiction instead of letting manners cover it, in a cutting contradiction that treats principle as performance."



def test_build_story_runtime_shell_readout_marks_evasive_same_surface_reply_as_answering_around_the_point() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["phone_pressure"],
            "last_committed_consequences": ["phone_interrupt_reframed_as_humiliation_pressure"],
            "narrative_thread_continuity": {"thread_pressure_level": "high", "thread_count": 2},
            "previous_reply_continuity_context": {
                "exchange_label": "exposure",
                "surface_token": "phone",
            },
        },
    }
    last_diagnostic = {
        "selected_scene_function": "withhold_or_evade",
        "selected_responder_set": [{"actor_id": "alain"}],
        "social_state_record": {
            "scene_pressure_state": "moderate_tension",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["response_exchange_now"] == "Your act drew an evasive pressure answer because it put the phone under pressure again, buying a beat on the same phone instead of answering it, with the earlier humiliation line still sitting on the phone, and let the reply pull the room toward manageability without ever resolving it."
    assert projection["response_line_prefix_now"] == "Alain, from the guest side, answers in evasive pressure with guest-side humiliation on the phone, in a tired evasive hedge dressed up as mediation, buying a beat on the same phone instead of answering it, the earlier humiliation line still sitting on the phone"
    assert projection["why_this_reply_now"] == "The room read the act through humiliation and public priority, so humiliation pressure pulled a guest side answer onto the phone, buying a beat on the same phone instead of answering it, and let the reply pull the room toward manageability without ever resolving it, in a tired evasive hedge dressed up as mediation."



def test_build_story_runtime_shell_readout_forces_reentry_after_same_surface_dodge() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["phone_pressure"],
            "last_committed_consequences": ["phone_interrupt_reframed_as_humiliation_pressure"],
            "narrative_thread_continuity": {"thread_pressure_level": "high", "thread_count": 2},
            "previous_reply_continuity_context": {
                "exchange_label": "evasive pressure",
                "surface_token": "phone",
            },
        },
    }
    last_diagnostic = {
        "selected_scene_function": "redirect_blame",
        "selected_responder_set": [{"actor_id": "annette"}],
        "social_state_record": {
            "scene_pressure_state": "high_blame",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["response_exchange_now"] == "Your act drew an exposure answer because it put the phone under pressure again, cutting back in before the dodge on the same phone can go quiet, with the earlier humiliation line still sitting on the phone, and let the reply pull the room toward exposure instead of polite cover."
    assert projection["response_line_prefix_now"] == "Annette, from the guest side, answers in exposure with guest-side humiliation on the phone, in a contemptuous dismantling that strips courtesy down to appetite, cutting back in before the dodge on the same phone can go quiet, the earlier humiliation line still sitting on the phone"
    assert projection["why_this_reply_now"] == "The room read the act through humiliation and public priority, so humiliation pressure pulled a guest side answer onto the phone, cutting back in before the dodge on the same phone can go quiet, and let the reply pull the room toward exposure instead of polite cover, in a contemptuous dismantling that strips courtesy down to appetite."



def test_build_story_runtime_shell_readout_marks_same_surface_evasion_as_buying_a_beat() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["phone_pressure"],
            "last_committed_consequences": ["phone_interrupt_reframed_as_humiliation_pressure"],
            "narrative_thread_continuity": {"thread_pressure_level": "high", "thread_count": 2},
            "previous_reply_continuity_context": {
                "exchange_label": "exposure",
                "surface_token": "phone",
            },
        },
    }
    last_diagnostic = {
        "selected_scene_function": "withhold_or_evade",
        "selected_responder_set": [{"actor_id": "alain"}],
        "social_state_record": {
            "scene_pressure_state": "moderate_tension",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["response_exchange_now"] == "Your act drew an evasive pressure answer because it put the phone under pressure again, buying a beat on the same phone instead of answering it, with the earlier humiliation line still sitting on the phone, and let the reply pull the room toward manageability without ever resolving it."
    assert projection["response_line_prefix_now"] == "Alain, from the guest side, answers in evasive pressure with guest-side humiliation on the phone, in a tired evasive hedge dressed up as mediation, buying a beat on the same phone instead of answering it, the earlier humiliation line still sitting on the phone"
    assert projection["why_this_reply_now"] == "The room read the act through humiliation and public priority, so humiliation pressure pulled a guest side answer onto the phone, buying a beat on the same phone instead of answering it, and let the reply pull the room toward manageability without ever resolving it, in a tired evasive hedge dressed up as mediation."



def test_build_story_runtime_shell_readout_cuts_back_in_before_same_surface_can_go_quiet() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["phone_pressure"],
            "last_committed_consequences": ["phone_interrupt_reframed_as_humiliation_pressure"],
            "narrative_thread_continuity": {"thread_pressure_level": "high", "thread_count": 2},
            "previous_reply_continuity_context": {
                "exchange_label": "evasive pressure",
                "surface_token": "phone",
            },
        },
    }
    last_diagnostic = {
        "selected_scene_function": "redirect_blame",
        "selected_responder_set": [{"actor_id": "veronique"}],
        "social_state_record": {
            "scene_pressure_state": "high_blame",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["response_exchange_now"] == "Your act drew an exposure answer because it put the phone under pressure again, cutting back in before the dodge on the same phone can go quiet, with the earlier humiliation line still sitting on the phone, and let the reply pull the room back toward answerability instead of comfort."
    assert projection["response_line_prefix_now"] == "Veronique, from the host side, answers in exposure with host-side humiliation on the phone, in a wounded moral indictment that refuses to let the hurt sound private, cutting back in before the dodge on the same phone can go quiet, the earlier humiliation line still sitting on the phone"
    assert projection["why_this_reply_now"] == "The room read the act through humiliation and public priority, so humiliation pressure pulled a host side answer onto the phone, cutting back in before the dodge on the same phone can go quiet, and let the reply pull the room back toward answerability instead of comfort, in a wounded moral indictment that refuses to let the hurt sound private."



def test_build_story_runtime_shell_readout_breaks_earlier_pause_back_over_same_surface() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["alliance_instability", "blame_pressure", "art_book_pressure"],
            "last_committed_consequences": ["book_handling_reframed_as_status_judgment"],
            "narrative_thread_continuity": {"thread_pressure_level": "high", "thread_count": 3},
            "previous_reply_continuity_context": {
                "exchange_label": "evasive pressure",
                "surface_token": "phone",
            },
            "earlier_reply_continuity_context": {
                "exchange_label": "evasive pressure",
                "surface_token": "books",
            },
        },
    }
    last_diagnostic = {
        "selected_scene_function": "redirect_blame",
        "selected_responder_set": [{"actor_id": "annette"}],
        "social_state_record": {
            "prior_continuity_classes": ["alliance_shift", "blame_pressure"],
            "scene_pressure_state": "high_blame",
            "responder_asymmetry_code": "alliance_reposition_active",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["response_exchange_now"] == "Your act drew an accusation answer because it put the books under pressure again, breaking the earlier pause back over the same books, with the earlier taste-and-status wound still sitting on the books, and let the reply pull the room back to exposed contradiction instead of letting manners cover it."
    assert projection["response_line_prefix_now"] == "Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, in a cutting contradiction that treats principle as performance, breaking the earlier pause back over the same books, the earlier taste-and-status wound still sitting on the books"


def test_build_story_runtime_shell_readout_reopens_same_surface_through_dodge_before_point_can_die() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["alliance_instability", "blame_pressure", "art_book_pressure"],
            "last_committed_consequences": ["book_handling_reframed_as_status_judgment"],
            "narrative_thread_continuity": {"thread_pressure_level": "high", "thread_count": 3},
            "previous_reply_continuity_context": {
                "exchange_label": "evasive pressure",
                "surface_token": "books",
            },
            "earlier_reply_continuity_context": {
                "exchange_label": "accusation",
                "surface_token": "books",
            },
        },
    }
    last_diagnostic = {
        "selected_scene_function": "redirect_blame",
        "selected_responder_set": [{"actor_id": "annette"}],
        "social_state_record": {
            "prior_continuity_classes": ["alliance_shift", "blame_pressure"],
            "scene_pressure_state": "high_blame",
            "responder_asymmetry_code": "alliance_reposition_active",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["response_exchange_now"] == "Your act drew an accusation answer because it put the books under pressure again, reopening the same books through the dodge before the point can die, with the earlier taste-and-status wound still sitting on the books, and let the reply pull the room back to exposed contradiction instead of letting manners cover it."
    assert projection["response_line_prefix_now"] == "Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, in a cutting contradiction that treats principle as performance, reopening the same books through the dodge before the point can die, the earlier taste-and-status wound still sitting on the books"
    assert projection["why_this_reply_now"] == "The room read the act as taste and household judgment, so cross-couple strain answered through the books, reopening the same books through the dodge before the point can die, and let the reply pull the room back to exposed contradiction instead of letting manners cover it, in a cutting contradiction that treats principle as performance."



def test_build_story_runtime_shell_readout_picks_up_same_surface_across_the_room_before_it_can_cool() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["phone_pressure", "blame_pressure"],
            "last_committed_consequences": ["phone_interrupt_reframed_as_humiliation_pressure"],
            "narrative_thread_continuity": {"thread_pressure_level": "high", "thread_count": 2},
            "previous_reply_continuity_context": {
                "exchange_label": "exposure",
                "surface_token": "phone",
                "responder_actor": "annette",
            },
        },
    }
    last_diagnostic = {
        "selected_scene_function": "redirect_blame",
        "selected_responder_set": [{"actor_id": "veronique"}],
        "social_state_record": {
            "scene_pressure_state": "high_blame",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["response_exchange_now"] == "Your act drew an exposure answer because it put the phone under pressure again, picking up the same phone across the room before it can cool, with the earlier humiliation line still sitting on the phone, and let the reply pull the room back toward answerability instead of comfort."
    assert projection["response_line_prefix_now"] == "Veronique, from the host side, answers in exposure with host-side humiliation on the phone, in a wounded moral indictment that refuses to let the hurt sound private, picking up the same phone across the room before it can cool, the earlier humiliation line still sitting on the phone"



def test_build_story_runtime_shell_readout_lets_same_pressure_jump_speakers_before_the_dodge_can_settle() -> None:
    state = {
        "current_scene_id": "living_room_main",
        "committed_state": {
            "current_scene_id": "living_room_main",
            "last_open_pressures": ["phone_pressure", "blame_pressure"],
            "last_committed_consequences": ["phone_interrupt_reframed_as_humiliation_pressure_again"],
            "narrative_thread_continuity": {"thread_pressure_level": "high", "thread_count": 3},
            "previous_reply_continuity_context": {
                "exchange_label": "evasive pressure",
                "surface_token": "phone",
                "responder_actor": "alain",
            },
            "earlier_reply_continuity_context": {
                "exchange_label": "exposure",
                "surface_token": "phone",
                "responder_actor": "annette",
            },
        },
    }
    last_diagnostic = {
        "selected_scene_function": "redirect_blame",
        "selected_responder_set": [{"actor_id": "veronique"}],
        "social_state_record": {
            "scene_pressure_state": "high_blame",
            "social_risk_band": "high",
        },
    }
    projection = build_story_runtime_shell_readout(state=state, last_diagnostic=last_diagnostic)
    assert projection["response_exchange_now"] == "Your act drew an exposure answer because it put the phone under pressure again, letting the same phone pressure jump speakers across the room before the dodge can settle, with the earlier humiliation line still sitting on the phone, and let the reply pull the room back toward answerability instead of comfort."
    assert projection["response_line_prefix_now"] == "Veronique, from the host side, answers in exposure with host-side humiliation on the phone, in a wounded moral indictment that refuses to let the hurt sound private, letting the same phone pressure jump speakers across the room before the dodge can settle, the earlier humiliation line still sitting on the phone"
    assert projection["why_this_reply_now"] == "The room read the act through humiliation and public priority, so humiliation pressure pulled a host side answer onto the phone, letting the same phone pressure jump speakers across the room before the dodge can settle, and let the reply pull the room back toward answerability instead of comfort, in a wounded moral indictment that refuses to let the hurt sound private."
