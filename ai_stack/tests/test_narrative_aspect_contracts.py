"""Narrative-aspect contract tests.

ADR-0039 scope: `table_b_refs` values are legacy fixture metadata only; pass/fail
assertions use policy-derived semantic profiles and structured contract fields.
"""

from __future__ import annotations

from ai_stack.contracts.narrative_aspect_contracts import (
    normalize_narrative_aspect_policy,
    select_narrative_aspects,
    validate_narrative_aspects,
)


def _policy() -> dict:
    return {
        "schema_version": "narrative_aspect_policy.v1",
        "aspects": [
            {
                "id": "aspect_alpha",
                "enabled": True,
                "activation": {"state_paths_any": ["signals.alpha"]},
                "commit_impact": "diagnostic",
                "evidence": [
                    {
                        "id": "alpha_state",
                        "kind": "state_path_present",
                        "path": "signals.alpha",
                        "required": True,
                    },
                    {
                        "id": "alpha_visible",
                        "kind": "visible_origin_present",
                        "origin_aspect": "narrative_aspect",
                        "required": True,
                    },
                ],
            },
            {
                "id": "aspect_beta",
                "enabled": False,
                "activation": {"always": True},
                "evidence": [],
            },
        ],
    }


def _semantic_policy(required: bool = True) -> dict:
    return {
        "schema_version": "narrative_aspect_policy.v1",
        "aspects": [
            {
                "id": "aspect_alpha",
                "enabled": True,
                "activation": {"always": True},
                "commit_impact": "diagnostic",
                "semantic_policy": {
                    "enabled": True,
                    "required": required,
                    "thresholds": {
                        "min_aspect_alignment": 0.25,
                        "min_dimension_alignment": 0.20,
                        "min_matched_dimensions": 1,
                    },
                },
                "semantic_profile": {
                    "material_anchor": "glass table pressure visible room",
                    "social_mask": "polite civility courtesy mask",
                },
                "metadata": {"table_b_refs": ["pi_12"]},
            }
        ],
    }


def _text_from_semantic_profile(policy: dict) -> str:
    profile = policy["aspects"][0]["semantic_profile"]
    return " ".join(
        token
        for value in profile.values()
        for token in str(value).split()[:3]
    )


def test_narrative_aspect_policy_is_json_safe_and_module_neutral() -> None:
    policy = normalize_narrative_aspect_policy(_policy())

    assert policy["schema_version"] == "narrative_aspect_policy.v1"
    assert [row["id"] for row in policy["aspects"]] == ["aspect_alpha", "aspect_beta"]
    assert "god_of_carnage" not in str(policy)


def test_narrative_aspect_selection_uses_policy_activation_data() -> None:
    selection = select_narrative_aspects(
        narrative_aspect_policy=_policy(),
        runtime_context={"signals": {"alpha": "active"}},
    )

    assert selection.selected_aspects == ["aspect_alpha"]
    assert selection.candidate_aspects == ["aspect_alpha"]
    assert selection.selection_source == "module_policy"


def test_narrative_aspect_validation_records_visible_evidence() -> None:
    validation = validate_narrative_aspects(
        narrative_aspect_policy=_policy(),
        runtime_context={
            "signals": {"alpha": "active"},
            "visible_blocks": [
                {
                    "id": "block-1",
                    "origin_aspect": "narrative_aspect",
                    "origin_aspect_id": "aspect_alpha",
                }
            ],
        },
    )

    payload = validation.to_dict()
    assert payload["status"] == "passed"
    assert payload["selected_aspects"] == ["aspect_alpha"]
    assert payload["realized_aspects"] == ["aspect_alpha"]
    assert payload["missing_required_evidence"] == []


def test_narrative_aspect_validation_fails_only_by_policy_contract() -> None:
    validation = validate_narrative_aspects(
        narrative_aspect_policy=_policy(),
        runtime_context={"signals": {"alpha": "active"}, "visible_blocks": []},
    )

    payload = validation.to_dict()
    assert payload["status"] == "partial"
    assert payload["failure_reason"] == "missing_required_narrative_aspect_evidence"
    assert payload["missing_required_evidence"][0]["kind"] == "visible_origin_present"


def test_narrative_aspect_semantic_tracking_uses_policy_profile() -> None:
    policy = _semantic_policy()
    validation = validate_narrative_aspects(
        narrative_aspect_policy=policy,
        runtime_context={
            "visible_blocks": [
                {
                    "id": "block-1",
                    "text": _text_from_semantic_profile(policy),
                }
            ],
        },
    )

    payload = validation.to_dict()
    aspect_id = policy["aspects"][0]["id"]
    assert payload["status"] == "passed"
    assert payload["semantic_aspect_ids"] == [aspect_id]
    assert payload["realized_semantic_aspects"] == [aspect_id]
    assert payload["semantic_classification_count"] == 1
    assert payload["semantic_classifications"][0]["table_b_refs"] == ["pi_12"]
    semantic_evidence = [
        row for row in payload["evidence"] if row["kind"] == "semantic_profile_alignment"
    ]
    assert semantic_evidence[0]["present"] is True


def test_required_narrative_aspect_semantics_fail_without_visible_evidence() -> None:
    validation = validate_narrative_aspects(
        narrative_aspect_policy=_semantic_policy(required=True),
        runtime_context={"visible_blocks": []},
    )

    payload = validation.to_dict()
    assert payload["status"] == "partial"
    assert payload["semantic_weak_alignment_count"] == 1
    assert payload["semantic_required_weak_alignment_count"] == 1
    assert payload["missing_required_evidence"][0]["kind"] == "semantic_profile_alignment"
