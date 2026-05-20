"""Deterministic fixture packs A-F for research MVP golden tests."""

from __future__ import annotations

from typing import Any


def fixture_a_intake_input() -> dict[str, Any]:
    """``fixture_a_intake_input`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    return {
        "work_id": "god_of_carnage",
        "source_type": "scene_note",
        "title": "GoC Scene 1 Internal Note",
        "raw_text": (
            "Scene purpose is escalation. The couple argues over civility and status. "
            "A tactic shift appears when politeness collapses into pressure. "
            "Theme and subtext stay implicit while staging space tightens."
        ),
        "provenance": {"origin": "internal_note_fixture_a", "version": "v1"},
        "visibility": "internal",
        "copyright_posture": "internal_approved",
        "metadata": {"fixture": "A"},
    }


def fixture_b_aspect_input() -> dict[str, Any]:
    """``fixture_b_aspect_input`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    return {
        "work_id": "god_of_carnage",
        "source_type": "scene_note",
        "title": "GoC Aspect Fixture",
        "raw_text": (
            "The scene purpose is conflict. A visual stage position changes power status. "
            "Each actor objective meets a block and a tactic switch. "
            "The dramaturg notes unclear theme pressure and redundant explanation."
        ),
        "provenance": {"origin": "internal_note_fixture_b", "version": "v1"},
        "visibility": "internal",
        "copyright_posture": "internal_approved",
        "metadata": {"fixture": "B"},
    }


def fixture_c_exploration_budget() -> dict[str, Any]:
    """Describe what ``fixture_c_exploration_budget`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    return {
        "max_depth": 2,
        "max_branches_per_node": 3,
        "max_total_nodes": 12,
        "max_low_evidence_expansions": 2,
        "llm_call_budget": 15,
        "token_budget": 500,
        "time_budget_ms": 2000,
        "abort_on_redundancy": False,
        "abort_on_speculative_drift": True,
        "model_profile": "deterministic_fixture_profile",
    }


def fixture_d_candidate_payloads(anchor_ids: list[str]) -> list[dict[str, Any]]:
    """Describe what ``fixture_d_candidate_payloads`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        anchor_ids: ``anchor_ids`` (list[str]); meaning follows the type and call sites.
    
    Returns:
        list[dict[str, Any]]:
            Returns a value of type ``list[dict[str, Any]]``; see the function body for structure, error paths, and sentinels.
    """
    anchor = anchor_ids[:1]
    return [
        {
            "claim_type": "dramatic_function",
            "statement": "supported claim about conflict pressure",
            "evidence_anchor_ids": anchor,
            "perspective": "playwright",
            "notes": "fixture_supported",
            "canon_relevance_hint": True,
        },
        {
            "claim_type": "dramatic_function",
            "statement": "hard_conflict contradiction candidate",
            "evidence_anchor_ids": anchor,
            "perspective": "dramaturg",
            "notes": "fixture_contradicted",
            "canon_relevance_hint": True,
        },
        {
            "claim_type": "dramatic_function",
            "statement": "unresolved ambiguous unclear thread",
            "evidence_anchor_ids": anchor,
            "perspective": "director",
            "notes": "fixture_unresolved",
            "canon_relevance_hint": True,
        },
    ]


def fixture_e_module_id() -> str:
    """``fixture_e_module_id`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    return "god_of_carnage"


def fixture_f_full_run_input() -> dict[str, Any]:
    """Describe what ``fixture_f_full_run_input`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    return {
        "work_id": "god_of_carnage",
        "module_id": "god_of_carnage",
        "seed_question": "Where is escalation weak and how can staging improve it?",
        "source_inputs": [
            fixture_a_intake_input(),
            fixture_b_aspect_input(),
        ],
        "budget": fixture_c_exploration_budget(),
    }
